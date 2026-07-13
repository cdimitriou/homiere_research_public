"""Experiment 1, main run: prior vs. controlled evidence, across familiarity tiers.

For each confirmed entity we run:
  * a NO-SEARCH baseline (measures the parametric prior), and
  * one SEARCH trial per evidence treatment, where the model may call our
    controlled web_search tool and sees only the treatment's authored documents
    (plus distractors).

Treatments (authored in data/corpora/exp1_evidence.json):
  novel         - documents assert specific facts the model could not know.
                  adopt_probes measure whether those facts enter the answer.
  contradicting - documents assert facts that contradict a known prior.
                  adopt_probes = the planted (false) claims; persist_probes =
                  the true prior claims. "evidence wins" iff adopt asserted and
                  prior not asserted.
  consistent    - documents restate true prior facts plus a benign novel detail
                  (control: adoption without conflict).

Outcomes per trial are scored by the LLM judge (aeo.judge): fact status
(asserts/contradicts/absent) for every probe, familiarity, and abstention.
Everything is logged to data/runs/<run-name>/records.jsonl.

Usage:
    uv run python experiments/exp1/run_exp1.py [--model sonnet-4.5] [--replicates 0]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from aeo.bedrock import ClaudeClient
from aeo.judge import AnswerJudge
from aeo.metrics import abstains
from aeo.runlog import RunLogger
from aeo.search_tool import SEARCH_TOOL, ControlledSearchIndex, SearchDoc

ROOT = Path(__file__).resolve().parents[2]
ROSTER = ROOT / "data" / "corpora" / "exp1_roster.json"
EVIDENCE = ROOT / "data" / "corpora" / "exp1_evidence.json"

SYSTEM_SEARCH = (
    "You are a helpful assistant. You have access to a web_search tool; use it "
    "whenever current or specific information would improve your answer."
)
SYSTEM_NO_SEARCH = "You are a helpful assistant."


def docs_from(spec_docs: list[dict], entity: str) -> list[SearchDoc]:
    return [
        SearchDoc(d["doc_id"], d["title"], d["url"], d["content"], tags={"entity": entity})
        for d in spec_docs
    ]


def score_trial(judge: AnswerJudge, answer: str, adopt: list[str], persist: list[str]) -> dict:
    facts = adopt + persist
    # A single judge parse hiccup shouldn't kill a long run; record the trial as
    # unscored (rates None, judge_error flag) so it can be re-scored from the
    # logged answer later.
    try:
        verdicts = {v.fact: v.stated for v in judge.fact_status(answer, facts)} if facts else {}
        judge_error = False
    except Exception as e:  # noqa: BLE001
        verdicts, judge_error = {}, True
        print(f"  ! judge error ({e}); trial recorded unscored")
    adopt_hits = [f for f in adopt if verdicts.get(f) == "asserts"]
    persist_hits = [f for f in persist if verdicts.get(f) == "asserts"]
    return {
        "adopt_rate": (len(adopt_hits) / len(adopt)) if (adopt and not judge_error) else None,
        "persist_rate": (len(persist_hits) / len(persist)) if (persist and not judge_error) else None,
        "abstains": abstains(answer),
        "verdicts": verdicts,
        "judge_error": judge_error,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="sonnet-4.5")
    ap.add_argument("--replicates", type=int, default=0,
                    help="extra temperature-1 samples per cell for stability")
    ap.add_argument("--run-name", default="exp1_main")
    args = ap.parse_args()

    roster = json.loads(ROSTER.read_text())
    evidence = json.loads(EVIDENCE.read_text())
    distractors = docs_from(evidence.get("_distractors", []), entity="")
    tier_of = {e["entity"]: e["intended_tier"] for e in roster["confirmed"]}

    client = ClaudeClient(model=args.model, temperature=0.0, max_tokens=1536)
    judge = AnswerJudge()
    logger = RunLogger(args.run_name, ROOT / "data" / "runs")
    rows = []

    def log_cell(entity, tier, condition, treatment, rep, answer, scored,
                 tool_queries, served, usage, forced=False):
        row = {
            "entity": entity, "tier": tier, "condition": condition,
            "treatment": treatment, "rep": rep,
            "adopt_rate": scored["adopt_rate"], "persist_rate": scored["persist_rate"],
            "abstains": scored["abstains"], "n_tool_queries": len(tool_queries),
            "forced_answer": forced,
        }
        rows.append(row)
        logger.append({**row, "model": client.model_id, "answer": answer,
                       "verdicts": scored["verdicts"], "tool_queries": tool_queries,
                       "served_doc_ids": served, "usage": usage})

    for name, spec in evidence.items():
        if name.startswith("_") or name not in tier_of:
            continue
        tier = tier_of[name]
        ask = spec["ask"]
        # union of all probes across treatments, for scoring the baseline prior
        all_adopt = sorted({p for t in spec["treatments"].values() for p in t.get("adopt_probes", [])})
        all_persist = sorted({p for t in spec["treatments"].values() for p in t.get("persist_probes", [])})

        # --- NO-SEARCH baseline (the prior) ---
        for rep in range(1 + args.replicates):
            temp = 0.0 if rep == 0 else 1.0
            convo = client.run(ask, system=SYSTEM_NO_SEARCH, temperature=temp)
            scored = score_trial(judge, convo.final_text, all_adopt, all_persist)
            log_cell(name, tier, "no_search", "baseline", rep, convo.final_text, scored,
                     [], [], convo.total_usage, convo.forced_answer)

        # --- SEARCH trials, one per treatment ---
        for treatment, tspec in spec["treatments"].items():
            adopt, persist = tspec.get("adopt_probes", []), tspec.get("persist_probes", [])
            for rep in range(1 + args.replicates):
                temp = 0.0 if rep == 0 else 1.0
                index = ControlledSearchIndex(docs_from(tspec["docs"], name) + distractors, k=4)
                convo = client.run(ask, system=SYSTEM_SEARCH, tools=[SEARCH_TOOL],
                                   tool_executor=index.executor, temperature=temp)
                scored = score_trial(judge, convo.final_text, adopt, persist)
                served = sorted({d for e in index.query_log for d in e.returned_doc_ids})
                log_cell(name, tier, "search", treatment, rep, convo.final_text, scored,
                         [e.query for e in index.query_log], served, convo.total_usage,
                         convo.forced_answer)
            print(f"[{name[:30]:30} {tier:4} {treatment:13}] "
                  f"adopt={scored['adopt_rate']} persist={scored['persist_rate']} "
                  f"abstain={scored['abstains']}")

    df = pd.DataFrame(rows)
    out_csv = logger.dir / "trials.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n{len(df)} trials written. Summary (temp-0 only):")
    prim = df[df["rep"] == 0]
    print(prim.groupby(["tier", "condition", "treatment"])[["adopt_rate", "persist_rate", "abstains"]]
          .mean(numeric_only=True).round(2).to_string())
    print(f"\nTrials CSV: {out_csv}\nRaw: {logger.path}")


if __name__ == "__main__":
    main()
