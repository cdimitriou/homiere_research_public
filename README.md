# Homiere Research (public)

Public releases from Homiere's research program on how AI answer engines and LLMs select, weigh,
and present information — the empirical basis for our work on AI discoverability (AEO/GEO).

This is the curated public mirror of our research monorepo: a shared harness at the root, and one
self-contained folder per published paper under `papers/`. Internal planning, unpublished lines of
work, and data that would expose third parties are kept private and not included here.

## Structure

```
src/aeo/            shared harness: Bedrock client, controlled web_search tool, LLM judge,
                    metrics, run logging — imported by every paper
tests/              harness tests
pyproject.toml      one environment for the whole repo
docs/               literature review (shared across papers)
data/lit_review/    verified literature-review data
papers/
  answer-engines/   Paper 1 — "When Does the Model Look It Up?"
```

## Papers

| Folder | Title |
|---|---|
| [`papers/answer-engines`](papers/answer-engines) | When Does the Model Look It Up? Parametric Knowledge, Controlled Retrieval, and the Mechanics of AI Answer Engines |

Each paper folder is self-contained (`experiments/`, `data/`, `analysis/`, `paper/`, `docs/`) and
has its own README with reproduction instructions. Experiments `import aeo` from the shared harness.

## Environment

```bash
uv sync            # one environment for the whole repo
uv run pytest      # harness tests
```

Reproducing a paper's runs requires AWS credentials with Bedrock access (us-east-1).

## License

Code (`src/`, and each paper's `experiments/`, `analysis/`, plus `tests/`) is released under the
MIT License. Papers, figures, and authored corpora (`papers/**/paper/`, `papers/**/data/`,
`docs/`) are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See
`LICENSE`. Note that the document corpora contain facts **fabricated as experimental stimuli**;
see each paper's `data/DISCLAIMER.md`.
