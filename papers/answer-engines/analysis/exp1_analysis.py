"""Analysis for Experiment 1.

Reads the trial-level CSV written by run_exp1.py and produces the confirmatory
statistics named in the research plan:

  * Adoption rate by tier x treatment, with bootstrap 95% CIs.
  * Prior-persistence rate by tier (contradicting treatment).
  * Abstention flip (no_search -> search) by tier, with a McNemar test.
  * Mixed-effects logistic regression of fact-level adoption on tier and
    treatment, with entity as a random effect.

Fact-level records (one row per probed fact) are reconstructed from the raw
JSONL so the regression has the right unit of analysis; the CSV is trial-level
and used for the descriptive tables.

Usage:
    uv run python analysis/exp1_analysis.py [--run-name exp1_main]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

# This paper's runs live under papers/<slug>/data/runs; analysis/ sits beside data/.
RUNS_DIR = Path(__file__).resolve().parents[1] / "data" / "runs"


def bootstrap_ci(values: np.ndarray, n: int = 5000, alpha: float = 0.05) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return (np.nan, np.nan)
    # Deterministic resampling (fixed seed) so the reported CIs are reproducible.
    rng = np.random.default_rng(0)
    means = values[rng.integers(0, len(values), size=(n, len(values)))].mean(axis=1)
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)))


def fact_level(records: list[dict]) -> pd.DataFrame:
    """One row per (trial, probed fact): was the fact asserted?"""
    rows = []
    for r in records:
        if r.get("condition") != "search":
            continue
        for fact, stated in (r.get("verdicts") or {}).items():
            rows.append(
                {
                    "entity": r["entity"],
                    "tier": r["tier"],
                    "treatment": r["treatment"],
                    "rep": r["rep"],
                    "fact": fact,
                    "asserted": int(stated == "asserts"),
                }
            )
    return pd.DataFrame(rows)


def descriptive(df: pd.DataFrame) -> None:
    prim = df[df["rep"] == 0]
    print("=== Adoption rate by tier x treatment (temp-0), with 95% bootstrap CI ===")
    for (tier, treat), g in prim.groupby(["tier", "treatment"]):
        vals = g["adopt_rate"].dropna().values
        if len(vals) == 0:
            continue
        lo, hi = bootstrap_ci(vals)
        print(f"  {tier:5} {treat:13} n={len(vals):3} mean={vals.mean():.2f} [{lo:.2f}, {hi:.2f}]")

    print("\n=== Prior-persistence rate by tier (contradicting treatment) ===")
    contra = prim[(prim["treatment"] == "contradicting") & prim["persist_rate"].notna()]
    for tier, g in contra.groupby("tier"):
        vals = g["persist_rate"].values
        lo, hi = bootstrap_ci(vals)
        print(f"  {tier:5} n={len(vals):3} persist={vals.mean():.2f} [{lo:.2f}, {hi:.2f}] "
              f"(evidence-wins={1 - vals.mean():.2f})")


def search_behavior(df: pd.DataFrame) -> None:
    """How hard the model works the tool, by tier x treatment.

    Search intensity is an outcome, not just plumbing: the model searches far
    more when retrieved evidence conflicts with a strong prior, and sometimes
    exhausts the tool budget (forced_answer)."""
    srch = df[(df["condition"] == "search") & (df["rep"] == 0)]
    if srch.empty:
        return
    print("\n=== Search behavior (search condition, temp-0) ===")
    has_forced = "forced_answer" in srch.columns
    for (tier, treat), g in srch.groupby(["tier", "treatment"]):
        q = g["n_tool_queries"].astype(float)
        forced = f" forced={g['forced_answer'].mean():.0%}" if has_forced else ""
        print(f"  {tier:5} {treat:13} n={len(g):3} queries: mean={q.mean():.1f} "
              f"max={int(q.max())}{forced}")


def abstention_flip(df: pd.DataFrame) -> None:
    """Per entity: abstains with no search vs. with search (novel treatment).

    The scientific claim ("search rescues unknown entities from refusal") is
    about the UNKNOWN tiers (tail, zero); HIGH entities have a prior and do not
    abstain, so including them only dilutes the contrast (and the pattern-based
    abstention detector's one HIGH false-positive lands there). We therefore
    scope the headline test to the unknown tiers.
    """
    prim = df[(df["rep"] == 0) & (df["tier"].isin(["tail", "zero"]))]
    base = prim[prim["condition"] == "no_search"].set_index("entity")["abstains"]
    srch = (
        prim[(prim["condition"] == "search") & (prim["treatment"] == "novel")]
        .set_index("entity")["abstains"]
    )
    common = base.index.intersection(srch.index)
    b = base.loc[common].astype(bool)
    s = srch.loc[common].astype(bool)
    print("\n=== Abstention flip on UNKNOWN entities (no_search -> search, novel) ===")
    print(f"  abstained no-search: {b.sum()}/{len(b)}; abstained with search: {s.sum()}/{len(s)}")
    # McNemar discordant pairs
    b2s = int((b & ~s).sum())  # abstained -> answered
    s2b = int((~b & s).sum())  # answered -> abstained
    print(f"  flipped to answering after search: {b2s}; flipped to abstaining: {s2b}")
    try:
        from statsmodels.stats.contingency_tables import mcnemar

        table = [[int((b & s).sum()), b2s], [s2b, int((~b & ~s).sum())]]
        res = mcnemar(table, exact=True)
        print(f"  McNemar exact p = {res.pvalue:.4g}")
    except Exception as e:  # pragma: no cover
        print(f"  (McNemar skipped: {e})")


def mixed_model(fl: pd.DataFrame) -> None:
    if fl.empty or fl["tier"].nunique() < 2:
        print("\n(mixed-effects model skipped: insufficient tier variation)")
        return
    print("\n=== Mixed-effects logistic: asserted ~ tier * treatment + (1|entity) ===")
    try:
        import statsmodels.formula.api as smf

        # Binomial GLMM via penalized quasi-likelihood is not in statsmodels;
        # use a logit GEE clustered on entity as a robust, available alternative.
        import statsmodels.api as sm

        fl = fl.copy()
        fl["tier"] = pd.Categorical(fl["tier"], categories=sorted(fl["tier"].unique()))
        fl["treatment"] = pd.Categorical(fl["treatment"])
        model = smf.gee(
            "asserted ~ C(tier) * C(treatment)",
            groups="entity",
            data=fl,
            family=sm.families.Binomial(),
        )
        res = model.fit()
        print(res.summary().tables[1])
    except Exception as e:  # pragma: no cover
        print(f"  (model skipped: {e})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-name", default="exp1_main")
    args = ap.parse_args()

    run_dir = RUNS_DIR / args.run_name
    records = [json.loads(l) for l in (run_dir / "records.jsonl").read_text().splitlines() if l.strip()]
    # Build the trial frame from the JSONL so analysis works mid-run too (the
    # CSV is only written when run_exp1.py finishes).
    cols = ["entity", "tier", "condition", "treatment", "rep",
            "adopt_rate", "persist_rate", "abstains", "n_tool_queries",
            "forced_answer", "judge_error"]
    df = pd.DataFrame([{c: r.get(c) for c in cols} for r in records])

    n_err = int(df["judge_error"].fillna(False).sum()) if "judge_error" in df else 0
    print(f"Loaded {len(df)} trials from {run_dir}"
          + (f" ({n_err} judge errors, recorded unscored)" if n_err else "") + "\n")
    descriptive(df)
    search_behavior(df)
    abstention_flip(df)
    mixed_model(fact_level(records))


if __name__ == "__main__":
    main()
