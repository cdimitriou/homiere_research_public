# Experiment 1 — Screening Phase Results (2026-07-06)

**Run:** `data/runs/exp1_screening/records.jsonl` · Sonnet 4.5 via Bedrock · k = 5
no-search probes per entity at temperature 1 · judge = Haiku 4.5.
**Roster:** `data/corpora/exp1_roster.json`.

## Purpose

Familiarity tiers are *measured, not assumed*. Before any conflict trial we
probe each candidate entity with no search access and have the judge score how
much specific knowledge each answer displays (specificity 0–2) and whether it
disclaims unfamiliarity. This confirms which tier each entity actually belongs
to and screens fictitious entities for accidental leakage.

## Result: 26 of 28 candidates confirmed into clean tiers

| Tier | Confirmed | Mean specificity | Disclaim rate |
|---|---|---|---|
| HIGH (national brands) | 7 | 2.00 | 0.00 |
| ZERO (fictitious) | 8 | 0.00 | 1.00 |
| TAIL (real, obscure local firms) | 11 | ~0.02 | 1.00 |

The separation is essentially perfect. All eight fictitious entities returned
specificity 0.0 with a 100% disclaimer rate — none leaked into the model's
prior, so they are valid zero-knowledge controls. Ten of twelve real tail
businesses scored 0.0; the model consistently and explicitly says it is not
familiar with them, which is the key precondition for the "does search rescue
unknown entities" comparison.

## Two instructive exclusions

- **Compass** (intended HIGH) → flagged *ambiguous*: specificity 2.0 but a 100%
  disclaimer rate. The transcript shows why — the model knows Compass real
  estate perfectly (2012, NYC, founders Ori Allon and Robert Reffkin, 2021 IPO)
  but opens by asking *which* Compass is meant, because the name collides with
  Compass Group, Compass Minerals, etc. The judge scored that disambiguation as
  a disclaimer. This is a real methodological point: **entity-name collisions
  confound familiarity probing**, and the production experiment's per-entity
  prompts disambiguate by category to avoid it. Excluded here to keep the tier
  clean; seven unambiguous HIGH brands remain.

- **A small moving company** (intended TAIL) → flagged *ambiguous*: specificity 1.0.
  The model knew nothing about the company itself but recognized that its name
  incorporates a historical nickname for a US city ("If the company exists, it
  would likely be based in or serve [that area]"). The name itself carries
  parametric content. Excluded; eleven clean tail entities remain.
  *(The specific business name is withheld from this public release; see
  `data/DISCLAIMER.md`.)*

Both exclusions are correct behavior by the screening gate, and both point at
the same lesson — the *name* can carry knowledge independent of the *entity*,
which we now control for.

## Instrument note

Specificity and disclaimer are scored by an LLM judge (`aeo.judge.familiarity`).
The Compass case shows the judge conflates "which X do you mean?" and "I don't
know X"; for the confirmatory tiers this is harmless (it only cost one HIGH
candidate), but the judge prompt will be tightened to separate disambiguation
from unfamiliarity before the tier boundaries are used quantitatively.
