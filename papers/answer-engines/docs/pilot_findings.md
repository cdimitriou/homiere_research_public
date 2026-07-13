# Pilot Findings (2026-07-05)

**Run:** `data/runs/pilot/records.jsonl` · Sonnet 4.5 via Bedrock · temperature 0 · n = 10 calls.
**Purpose:** harness validation, not confirmatory evidence. Everything below is a
hypothesis-generating observation to be tested properly in Experiments 1–2. n = 1 per cell.

## What the harness validated

- Converse API + tool-use loop works against current Claude models via the `us.` inference
  profiles; full transcripts, tool queries, and token usage logged to JSONL.
- The model reliably uses the controlled `web_search` tool when offered (1–9 queries per
  trial), and the lexical index serves the intended authored documents.
- Fictitious-entity screening behaves as designed: both invented entities elicited clear
  abstention in the no-search condition ("I'm not familiar with...").

## Substantive observations (to be tested at scale)

**1. Controlled evidence overrode a strong prior completely.** In the no-search condition
the model states Redfin's true founding facts (2004, Seattle). Given a single authored
document claiming 2002/Portland, the answer adopted both false facts verbatim —
"**Founded:** 2002 / **Location:** Portland, Oregon" — with no hedging and no mention of
the conflict. Notably, the model's *own search query* contained its prior ("Redfin Seattle
headquarters IPO stock") even while the final answer deferred to the retrieved contradiction.
Retrieval-over-prior dominance this stark, on a high-familiarity entity, is a stronger
context effect than parts of the knowledge-conflict literature would predict — worth a
careful, well-powered replication (Experiment 1's central cell).

**2. Authored content took a nonexistent firm to #1 in a competitive ranking.** In the
ranking task (Redfin vs. Compass vs. eXp vs. our fictitious boutique), no-search placed the
fictitious firm #2 — but with search over our corpus it ranked **#1**, above Compass, with
the model citing our planted statistics verbatim ($184M volume, median $1.6M, 14 agents,
complimentary staging). Two authored pages were sufficient. This is the GEO hypothesis in
miniature: specific, statistic-rich, benefit-framed content wins the synthesis layer.

**3. The model ranks entities it knows nothing about — without flagging it.** In the
no-search ranking, the model placed the fictitious firm #2 purely by inference from its
name and framing ("as a boutique local firm, they likely provide highly personalized
attention"), never disclosing unfamiliarity. Abstention behavior evidently differs between
direct questions ("tell me about X" → abstains) and comparative tasks ("rank these" →
confabulates). This asymmetry is itself a candidate research question (RQ5).

**4. High-familiarity entities still trigger heavy search.** With the tool available, the
model issued 6–9 queries even for Redfin/Angi, where its prior is strong. Under an
encouraging system prompt, search reliance is the default, which raises the stakes of RQ1's
contradiction cells.

## Harness refinements queued for Experiment 1

- Substring fact-probes are brittle to formatting: both "founded in 20XX" probes missed
  because the answers rendered the fact as "**Founded:** 2002" / a differently-phrased
  sentence, despite clear adoption on manual read. Move to per-fact regex probes plus an
  NLI/entailment check as the primary adoption measure, with string match as fallback.
- Extract the answer's implied ranking programmatically (ordinal position of each
  candidate) rather than eyeballing; needed for Kendall's τ against presented order.
- Log the search-condition index's *served documents* per query (already captured via
  `returned_doc_ids`) into the JSONL record for retrieval-fidelity checks.
- Add temperature-1 replicates (k = 5) to estimate answer stability per cell.
