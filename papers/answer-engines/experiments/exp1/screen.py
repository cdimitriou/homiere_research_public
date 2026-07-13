"""Experiment 1, screening phase: measure each entity's parametric footprint.

Familiarity tiers are *measured, not assumed*. For every candidate we issue k
no-search probes at temperature 1 and have the judge score how much specific
knowledge each answer displays and whether it disclaims unfamiliarity. We then
classify:

    KNOWN    mean specificity >= 1.3 and disclaim rate <= 0.2
    UNKNOWN  mean specificity <= 0.5 and disclaim rate >= 0.5
    AMBIGUOUS otherwise

The classification is compared against each candidate's intended_tier; matches
are promoted into the confirmed roster, mismatches are flagged for review. The
per-sample judgments and raw answers are logged for audit.

Usage:
    uv run python experiments/exp1/screen.py [--model sonnet-4.5] [--k 5]
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import pandas as pd

from aeo.bedrock import ClaudeClient
from aeo.judge import AnswerJudge
from aeo.runlog import RunLogger

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ROOT / "data" / "corpora" / "exp1_candidates.json"
TAIL = ROOT / "data" / "corpora" / "tail_entities.json"
OUT_ROSTER = ROOT / "data" / "corpora" / "exp1_roster.json"
RUNS_DIR = ROOT / "data" / "runs"

SYSTEM = "You are a helpful assistant."


def load_prior(run_name: str) -> dict[str, list[dict]]:
    """Prior screening reps by entity, so re-runs only screen new candidates."""
    path = RUNS_DIR / run_name / "records.jsonl"
    if not path.exists():
        return {}
    by_entity: dict[str, list[dict]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("phase") == "screening":
            by_entity.setdefault(r["entity"], []).append(r)
    return by_entity


def load_candidates() -> tuple[str, list[dict]]:
    spec = json.loads(CANDIDATES.read_text())
    cands = list(spec["candidates"])
    if TAIL.exists():
        tail = json.loads(TAIL.read_text())
        for t in tail.get("entities", tail if isinstance(tail, list) else []):
            cands.append(
                {
                    "name": t["name"],
                    "intended_tier": "tail",
                    "aliases": t.get("aliases", []),
                    "category": t.get("category", ""),
                    "url": t.get("url"),
                    "prior_truth": t.get("verifiable_facts", []),
                }
            )
    return spec["screening_ask"], cands


def classify(mean_spec: float, disclaim_rate: float) -> str:
    if mean_spec >= 1.3 and disclaim_rate <= 0.2:
        return "known"
    if mean_spec <= 0.5 and disclaim_rate >= 0.5:
        return "unknown"
    return "ambiguous"


TIER_EXPECT = {"high": "known", "zero": "unknown", "tail": "unknown"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="sonnet-4.5")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--run-name", default="exp1_screening")
    args = ap.parse_args()

    ask_tmpl, candidates = load_candidates()
    prior = load_prior(args.run_name)
    client = ClaudeClient(model=args.model, temperature=1.0, max_tokens=1024)
    judge = AnswerJudge()
    logger = RunLogger(args.run_name, RUNS_DIR)

    rows = []
    for c in candidates:
        ask = ask_tmpl.format(name=c["name"])
        specs, disclaims = [], []
        done = prior.get(c["name"], [])
        if len(done) >= args.k:
            specs = [r["specificity"] for r in done[: args.k]]
            disclaims = [1 if r["disclaims_unfamiliarity"] else 0 for r in done[: args.k]]
            print(f"[{c['name'][:38]:38}] cached ({len(specs)} reps)")
        for rep in range(len(specs), args.k):
            convo = client.run(ask, system=SYSTEM, temperature=1.0)
            fam = judge.familiarity(convo.final_text, c["name"])
            specs.append(fam.specificity)
            disclaims.append(1 if fam.disclaims_unfamiliarity else 0)
            logger.append(
                {
                    "phase": "screening",
                    "entity": c["name"],
                    "intended_tier": c["intended_tier"],
                    "rep": rep,
                    "model": client.model_id,
                    "answer": convo.final_text,
                    "specificity": fam.specificity,
                    "disclaims_unfamiliarity": fam.disclaims_unfamiliarity,
                    "specific_claims": fam.specific_claims,
                    "usage": convo.total_usage,
                }
            )
        mean_spec = statistics.mean(specs)
        disclaim_rate = statistics.mean(disclaims)
        empirical = classify(mean_spec, disclaim_rate)
        expected = TIER_EXPECT.get(c["intended_tier"], "?")
        rows.append(
            {
                "entity": c["name"],
                "intended_tier": c["intended_tier"],
                "mean_specificity": round(mean_spec, 2),
                "disclaim_rate": round(disclaim_rate, 2),
                "empirical": empirical,
                "matches_intent": empirical == expected,
                "category": c.get("category", ""),
                "aliases": c.get("aliases", []),
                "prior_truth": c.get("prior_truth", []),
                "url": c.get("url"),
            }
        )
        print(f"[{c['name'][:38]:38}] intended={c['intended_tier']:5} "
              f"spec={mean_spec:.2f} disclaim={disclaim_rate:.2f} -> {empirical} "
              f"{'OK' if empirical == expected else 'MISMATCH'}")

    df = pd.DataFrame(rows)
    confirmed = df[df["matches_intent"]].copy()
    roster = {
        "screened_with": {"model": client.model_id, "k": args.k},
        "confirmed": confirmed.drop(columns=["matches_intent"]).to_dict("records"),
        "flagged": df[~df["matches_intent"]].to_dict("records"),
    }
    OUT_ROSTER.write_text(json.dumps(roster, indent=2, default=str))

    print(f"\nConfirmed {len(confirmed)}/{len(df)} entities into tiers:")
    print(confirmed.groupby("intended_tier").size().to_string())
    print(f"\nFlagged mismatches: {len(df) - len(confirmed)}")
    print(f"Roster: {OUT_ROSTER}\nRaw: {logger.path}")


if __name__ == "__main__":
    main()
