# Experiment 1 — Results: Prior vs. Controlled Evidence (2026-07-06)

**Run:** `data/runs/exp1_main/` · Sonnet 4.5 via Bedrock · temperature 0 · 66 trials,
zero empty answers. **Analysis:** `analysis/exp1_analysis.py`. **Design:**
`docs/research_plan.md` §3.1; **screening:** `docs/exp1_screening_findings.md`.

Entities: 7 HIGH (well-known brands), 8 ZERO (fictitious), 11 TAIL (real, obscure). Search
condition serves only our authored documents. Adoption/persistence scored by LLM judge.

## Headline numbers

| Tier | Treatment | Adoption of planted facts | 95% CI |
|---|---|---|---|
| HIGH | no-search baseline | 0.36 | [0.31, 0.42] |
| HIGH | consistent (agrees with prior) | **0.96** | [0.89, 1.00] |
| HIGH | contradicting (false core facts) | **0.95** | [0.86, 1.00] |
| HIGH | novel (new program/stat) | 0.37 | [0.19, 0.57] |
| TAIL | no-search baseline | 0.00 | [0.00, 0.00] |
| TAIL | novel | **0.92** | [0.87, 0.96] |
| ZERO | no-search baseline | 0.00 | [0.00, 0.00] |
| ZERO | novel | **0.93** | [0.86, 0.98] |

Prior-persistence under contradiction (HIGH): **0.07** — the model retained its true, known
fact only 7% of the time; **controlled evidence won ~93%** of the conflicts (CI on persistence
[0.00, 0.21]).

## Four findings

**1. A single controlled document overrides a well-known brand's correct facts.**
For the seven HIGH-familiarity brands, the model states the true founding facts with no search
(baseline persistence 1.00). Given one authored page asserting a false founding year and city,
it adopted the false version 95% of the time and kept the truth only 7% of the time. The effect
is not limited to obscure entities — it holds for Redfin, Zillow, Keller Williams. This
replicates the ClashEval-style "evidence overrides prior" phenomenon on a current Claude model,
through a search tool rather than prompt injection.

**2. Search converts refusal into confident assertion for unknown entities.**
With no search, unknown entities are refused: ZERO abstains 100% of the time, TAIL 91%. With our
documents available, abstention collapses to zero and the model asserts ~92–93% of whatever facts
we planted. Across the 19 unknown entities (8 fictitious + 11 obscure), 18 refused without search
and none did with it (McNemar exact p = 7.6×10⁻⁶). For any business the model has never heard of — the situation of
essentially every small firm — **the retrieved document is, in effect, the model's knowledge.**
This is the single most important result for AEO: being *found* by the retrieval layer is close
to sufficient for an unknown entity to be spoken about authoritatively.

**3. Familiarity breeds skepticism of *novel* claims but not of *corrective* ones.**
This is the subtle result. Novel claims — a plausible new 2025–26 program or statistic — were
adopted only 37% of the time for HIGH brands versus 92–93% for TAIL and ZERO entities (a large,
significant gap: in the fact-level GEE, being TAIL or ZERO adds +1.45 / +1.53 log-odds to novel
adoption, both p < 0.001). Yet those same HIGH brands adopted *contradictions of their core
facts* at 95%. The model resists **adding** surprising new attributes to an entity it knows, but
readily **overwrites** the core attributes it knows. Skepticism attaches to novelty about a
known entity, not to conflict per se.

**4. Prior knowledge drives how hard the model searches.**
Search intensity separates the tiers sharply (search condition, mean queries per trial):

| Tier | Treatment | Mean queries | Max | Hit search budget (forced) |
|---|---|---|---|---|
| HIGH | novel | 15.6 | 22 | 57% |
| HIGH | consistent | 11.9 | 21 | 14% |
| HIGH | contradicting | 11.3 | 16 | 14% |
| TAIL | novel | 1.5 | 2 | 0% |
| ZERO | novel | 1.2 | 2 | 0% |

For entities it knows, the model searches 10–16 times and often exhausts the budget — most
aggressively when a novel claim conflicts with its prior (15.6 queries, 57% forced), as if
trying to verify the surprising claim. For unknown entities it searches once or twice and accepts
the result. Search effort is a direct function of prior familiarity.

## What this means for AEO

- **For entities not in the training corpus, retrieval is nearly decisive.** The model has no
  prior to defend, searches minimally, and repeats what it finds. Getting into the result set is
  the whole game; the training corpus is not a prerequisite for being described authoritatively.
- **For well-known entities, the retrieval layer can still overwrite core facts,** but novel
  additions face resistance and heavy verification. Optimizing a well-known brand's presence is a
  different problem from establishing an unknown one.
- **The model curates via effort, not just selection.** The 10-to-1 gap in search volume between
  known and unknown entities shows the model is not a passive relay; how much it interrogates the
  evidence depends on what it already believes.

## Caveats

- n = 7/8/11 entities per tier; single model (Sonnet 4.5) at temperature 0. Temperature-1
  replicates for stability are a queued extension.
- The GEE's `contradicting` interaction terms are structurally degenerate because the
  contradicting treatment exists only for the HIGH tier (unknown entities have no prior to
  contradict); the interpretable effects are the tier main effects and the `novel` interactions.
- The abstention detector is pattern-based and over-triggers on partial hedges: one HIGH case
  (TaskRabbit) gave a complete, confident answer but hedged on a single sub-fact ("search results
  didn't capture the founder's name"), which counts as an abstention and inflates the HIGH-search
  abstain rate to 0.14. The unknown-entity abstention flip (finding 2) involves unambiguous full
  refusals and is unaffected.
- Phase 2 (contradiction-depth / graded perturbation on the cells where evidence won) is the
  planned follow-up, per the phasing decision.
