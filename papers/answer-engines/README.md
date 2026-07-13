# When Does the Model Look It Up?

*Parametric Knowledge, Controlled Retrieval, and the Mechanics of AI Answer Engines.*
Paper 1 of the [Homiere research program](../../README.md).

The core instrument: Claude, invoked via AWS Bedrock with tool use, is given a `web_search` tool
whose results are entirely authored by us. That makes the evidence set a controlled variable, so
answer behavior can be attributed to (a) the model's prior familiarity with an entity, (b) the
content of retrieved documents, and (c) their interaction. The shared harness lives at the repo
root (`src/aeo`); everything else this paper needs is in this folder.

## The paper

`paper/paper.pdf` is the compiled paper; `paper/paper.tex` is the source. Figures are generated
from the raw run data, so it is reproducible end to end:

```bash
cd paper && make          # regenerates figures from ./data/runs, then compiles paper.pdf
```

Requires [`tectonic`](https://tectonic-typesetting.github.io/) (`brew install tectonic`).

## Layout

```
experiments/   pilot (harness validation), exp1 (prior vs. evidence), exp2 (feature ablation)
data/corpora/  authored document corpora (the "web" the search tool serves)
data/runs/     raw model outputs, JSONL, one record per API interaction
analysis/      statistics (exp1_analysis.py) and figure generation (make_figures.py)
paper/         paper.tex -> paper.pdf, references.bib, figures/, Makefile
docs/          findings write-ups and screening results
```

## The two experiments

1. **Prior vs. evidence** (`experiments/exp1/`, `docs/exp1_findings.md`) — across three
   empirically screened familiarity tiers, when retrieved content contradicts or extends what the
   model already believes, which wins? Controlled evidence overrode well-known brands' correct
   founding facts 93% of the time; providing documents converted near-universal refusal about
   unknown entities into 92–93% fact adoption.
2. **Is AEO real?** (`experiments/exp2/`, `docs/exp2_findings.md`) — holding retrieval fixed and
   rotating document position, which content features causally change a document's rank? The model
   reorders almost independently of search position (Kendall's τ = 0.10); statistics, quotations,
   or authority markers each move a target from mid-pack to first.

## Reproducing the runs

From the repo root (so `uv` resolves the shared environment):

```bash
uv run python papers/answer-engines/experiments/exp1/screen.py     # familiarity screening
uv run python papers/answer-engines/experiments/exp1/run_exp1.py   # prior vs. evidence
uv run python papers/answer-engines/experiments/exp2/run_exp2.py   # content-feature ablation
uv run python papers/answer-engines/analysis/exp1_analysis.py      # statistics
uv run python papers/answer-engines/analysis/make_figures.py       # figures
```

## Data availability

This public release fully includes the well-known-brand and fictitious tiers of Experiment 1 and
all of Experiment 2. The **tail tier** (real but obscure small businesses) authored fabricated
facts about real, named businesses, so its raw inputs and outputs are **withheld** here to avoid
publicly associating those businesses with invented content; the paper reports that tier's
aggregate results (which name no business), and the withheld data is available on request.
Regenerating the figures from this public subset reproduces the well-known-brand and fictitious
tiers; the committed figures and `paper.pdf` additionally show the tail tier's aggregate results.

The document corpora in `data/` contain facts **fabricated as experimental stimuli** (invented
programs, deliberately altered facts about well-known brands, fictitious entities). They are not
factual claims — see `data/DISCLAIMER.md`.
