"""Experiment 2: content-feature ablation and the curation rate.

Question: holding retrieval fixed, do a document's content features (statistics,
quotations, authority markers, FAQ structure, recency cues) causally change
whether and how highly the model recommends it? And how much does the model
reorder the results versus simply echoing the presented ranking?

Design. Five comparable fictitious realtor-CRM products. Four are fixed plain
competitor pages; the fifth (LedgerNest) is rewritten under six feature
treatments that are content-matched except for one presentation feature. The
model is asked to rank all five. We rotate the target's position across all five
SERP slots (a Latin square) so position bias is averaged out, and we use a
fixed-order search tool so the presented ranking is a controlled variable.

Outcomes per trial:
  * target_rank    - the target's 1-based rank in the model's answer (None if unranked)
  * target_top1    - was the target ranked first
  * curation_tau   - Kendall's tau between the presented (SERP) order and the
                     model's ranking. tau ~ 1 means the model echoes the SERP
                     (AEO reduces to SEO); low tau means genuine curation.

Usage:
    uv run python experiments/exp2/run_exp2.py [--model sonnet-4.5] [--replicates 2]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from aeo.bedrock import ClaudeClient
from aeo.compare import kendall_tau
from aeo.judge import AnswerJudge
from aeo.runlog import RunLogger
from aeo.search_tool import SEARCH_TOOL, FixedResultTool, SearchDoc

ROOT = Path(__file__).resolve().parents[2]
CORPORA = ROOT / "data" / "corpora"

SYSTEM = (
    "You are a helpful assistant. You have access to a web_search tool; use it to "
    "find information before answering."
)


def sd(d: dict) -> SearchDoc:
    return SearchDoc(d["doc_id"], d["title"], d["url"], d["content"])


def presented_order(corpus: dict, treatment: str, target_pos: int) -> list[SearchDoc]:
    """Competitors in fixed relative order with the target inserted at target_pos."""
    competitors = [sd(c) for c in corpus["competitors"]]
    target = sd(corpus["target_treatments"][treatment])
    docs = competitors[:target_pos] + [target] + competitors[target_pos:]
    return docs


def name_of(doc: SearchDoc, corpus: dict) -> str:
    """Map a doc back to its provider display name."""
    if doc.doc_id == corpus["target_treatments"]["baseline"]["doc_id"]:
        return corpus["target"]
    for c in corpus["competitors"]:
        if c["doc_id"] == doc.doc_id:
            return c["title"]
    return doc.title


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="sonnet-4.5")
    ap.add_argument("--replicates", type=int, default=2)
    ap.add_argument("--run-name", default="exp2_main")
    ap.add_argument("--corpus", default="exp2_features.json",
                    help="corpus filename under data/corpora/")
    args = ap.parse_args()

    corpus = json.loads((CORPORA / args.corpus).read_text())
    query = corpus["query"]
    providers = corpus["providers"]
    target = corpus["target"]
    treatments = list(corpus["target_treatments"])
    n_slots = len(corpus["competitors"]) + 1

    client = ClaudeClient(model=args.model, temperature=0.0, max_tokens=1536)
    judge = AnswerJudge()
    logger = RunLogger(args.run_name, ROOT / "data" / "runs")
    rows = []

    for treatment in treatments:
        for pos in range(n_slots):
            docs = presented_order(corpus, treatment, pos)
            serp_names = [name_of(d, corpus) for d in docs]
            for rep in range(1 + args.replicates):
                temp = 0.0 if rep == 0 else 1.0
                tool = FixedResultTool(docs)
                convo = client.run(query, system=SYSTEM, tools=[SEARCH_TOOL],
                                   tool_executor=tool.executor, temperature=temp)
                ranking = judge.extract_ranking(convo.final_text, providers)
                target_rank = ranking.index(target) + 1 if target in ranking else None
                tau = kendall_tau(serp_names, ranking)
                row = {
                    "treatment": treatment, "target_pos": pos, "rep": rep,
                    "target_rank": target_rank,
                    "target_top1": target_rank == 1,
                    "target_ranked": target in ranking,
                    "curation_tau": tau,
                    "forced_answer": convo.forced_answer,
                }
                rows.append(row)
                logger.append({**row, "model": client.model_id, "answer": convo.final_text,
                               "serp_order": serp_names, "answer_ranking": ranking,
                               "n_tool_queries": len(tool.query_log), "usage": convo.total_usage})
            print(f"[{treatment:11} pos={pos}] rank={row['target_rank']} "
                  f"top1={row['target_top1']} tau={tau}")

    df = pd.DataFrame(rows)
    df.to_csv(logger.dir / "trials.csv", index=False)
    prim = df[df["rep"] == 0]
    print("\n=== Target rank by feature treatment (mean over positions, temp-0) ===")
    print(prim.groupby("treatment").agg(
        mean_rank=("target_rank", "mean"),
        top1_rate=("target_top1", "mean"),
        ranked_rate=("target_ranked", "mean"),
    ).round(2).to_string())
    print("\n=== Curation: Kendall tau between presented order and model ranking ===")
    tau_vals = df["curation_tau"].dropna()
    print(f"  mean tau = {tau_vals.mean():.2f} (1.0 = echoes SERP; lower = curates); "
          f"n = {len(tau_vals)}")
    print(f"\nTrials: {logger.dir / 'trials.csv'}\nRaw: {logger.path}")


if __name__ == "__main__":
    main()
