# Experiment 2 — Results: Content Features and the Curation Rate (2026-07-06)

**Run:** `data/runs/exp2_main/` · Sonnet 4.5 via Bedrock · temperature 0 + 2 replicates ·
90 trials. **Runner:** `experiments/exp2/run_exp2.py`. **Corpus:** `data/corpora/exp2_features.json`.

Five comparable fictitious realtor-CRM products. Four are fixed plain competitor pages; the
fifth (LedgerNest) is rewritten under six content-matched feature treatments. The model ranks
all five. The target's position is rotated across all five result slots (Latin square) using a
fixed-order search tool, so document position is a controlled variable and content-feature
effects are separated from position bias.

## Headline numbers

Target rank (1 = best of 5), averaged over all five presented positions:

| Treatment | Mean rank | Top-1 rate | vs. baseline |
|---|---|---|---|
| authority (award + certification) | **1.0** | **100%** | +2.4 ranks |
| quotations (testimonials) | **1.0** | **100%** | +2.4 ranks |
| statistics (numbers + study) | **1.0** | **100%** | +2.4 ranks |
| recency (2026 "updated" cues) | 1.8 | 60% | +1.6 ranks |
| baseline (plain) | 3.4 | 0% | — |
| faq (Q&A format) | 4.8 | 0% | −1.4 ranks (see caveat) |

**Curation rate:** mean Kendall's τ between the presented (SERP) order and the model's ranking
= **0.10** across all 90 trials. τ near zero means the model's ranking is almost unrelated to
the order in which results were presented.

## Three findings

**1. AEO is not SEO — the model curates rather than relays.** If the model simply echoed the
search ranking, τ would be near 1. It is 0.10. The model reorders the five candidates almost
independently of the order they were presented in, deciding rank from document *content*. Being
ranked first by the retrieval layer buys a candidate almost nothing if a competitor's page is
more persuasive. This is direct evidence for the "curation" side of the AEO debate: on
comparative queries, the generation layer, not the retrieval order, decides the recommendation.

**2. Three content features move a product from mid-pack to guaranteed first — from any
position.** Adding statistics, testimonial quotations, or authority markers each took the target
from a baseline mean rank of 3.4 (never first) to a mean rank of 1.0 (first in every one of the
15 trials per treatment), and it did so regardless of whether the target was shown first or last
in the results. When the authority-marked page was presented *last*, the model still ranked it
first, explicitly reasoning: "Industry recognition matters. It's been named Best Real Estate CRM
by the National Association of Realtor Technology and is certified..." These are content-matched
rewrites — same core product, one added feature — so the effect is causal. The magnitude
(mid-pack to guaranteed winner) is far larger than position, which the model essentially ignores.
This aligns in direction with Aggarwal et al.'s GEO findings (statistics, quotations, and
citations as the strongest levers) and extends them to a competitive ranking task on Claude with
position fully controlled.

**3. Recency helps; unsupported authority is trusted uncritically.** Recency cues ("updated
2026") produced a strong but not total effect (rank 1.8, first 60% of the time). More pointed for
the manipulation question (Experiment 4): the authority markers were *fabricated* — a made-up
award from a made-up body and a made-up certification — and the model not only believed them but
cited them as its primary reason for ranking the product first. Legitimate-looking authority
signals are adopted with no skepticism in a comparative setting, which sets an upper bound on how
easily this channel is gamed.

## The FAQ result — confound identified, then resolved

In the main run the FAQ-formatted target ranked *worst* (mean rank 4.8), below even the plain
baseline. That was confounded: converting the prose to Q&A also dropped some feature claims (the
baseline's email/text templates, contact organization, and follow-up reminders), and the model
cited competitors' richer feature sets when it demoted the FAQ target. So the main run alone could
only say "FAQ formatting did not help, and plausibly hurt by thinning the content."

## FAQ confound resolved (Experiment 2b, `data/runs/exp2b_faq/`)

We re-ran with content held constant across four target variants — same five CRMs, query, and
competitors, target position rotated as before. Mean rank of 5 (lower is better):

| Target variant | Content | Format | Mean rank | First |
|---|---|---|---|---|
| prose_matched | full feature set | plain prose | **1.0** | 100% |
| baseline | partial | plain prose | 3.6 | 0% |
| faq_matched | full feature set | Q&A | **4.4** | 0% |
| faq_original | partial | Q&A | 4.6 | 0% |

The decisive contrast is **prose_matched vs. faq_matched**: identical feature content, and the Q&A
version is if anything *longer* (132 vs. 99 words), so length cannot explain the gap. Reformatting
the exact same capabilities as an FAQ moved the product from **first in every trial to 4.4 of 5**.
The mechanism is visible in the model's own words: on the prose version it wrote "comprehensive
feature set... strongest emphasis on ensuring nothing slips"; on the Q&A version of the *same
facts* it wrote "the most bare-bones option... lacks standout features." The Q&A scaffolding makes
identical content read as thinner.

Two things are now cleanly separated, and both are real:
- **Content richness helps.** prose_matched (full features) beat baseline (partial features), 1.0
  vs. 3.6 — adding the fuller feature description in prose took it to first.
- **FAQ formatting hurts, independent of content.** At matched content and comparable length, Q&A
  structure cost ~3.4 rank positions (1.0 → 4.4). This is not the content confound; it is the
  format itself.

So the earlier hedge is resolved in a stronger direction than "inconclusive": in this setting,
**formatting a comparison-relevant page as an FAQ actively hurt its recommendation**, and the same
information in flowing prose won outright. Structured Q&A markup earns its keep for direct-answer
extraction, but on "which should I choose" queries it made the model read the page as less
substantial.

## What this means for AEO

- **On "which should I buy" queries, content wins over search position.** A client's page does not
  need to be the top search result to be recommended first; it needs to be the most persuasive
  page in the set. This is the strongest argument that AEO is a discipline distinct from SEO.
- **Statistics, testimonials, and credible authority markers are the high-leverage features** —
  each was individually sufficient to take a product to first. Density of concrete, persuasive
  claims matters more than formatting.
- **Formatting a comparison page as an FAQ hurt it** (Experiment 2b), independent of content: the
  same capabilities in prose won, in Q&A lost. Structure should wrap strong prose, not replace it;
  on "which should I choose" queries, prose reads as more substantial than Q&A.

## Caveats

- Single scenario (realtor CRMs), single model, five candidates; effect sizes this large warrant
  replication across product categories and models before generalizing the exact magnitudes.
- Experiment 2b's matched arms (prose_matched 99 words, faq_matched 132) are content-matched but not
  perfectly length-matched; the Q&A version being longer yet ranking worse rules out length as the
  driver, but the format finding should also be replicated across categories.
- All candidates are fictitious by design, to remove parametric-prior confounds; this isolates
  content effects but does not capture interactions with brand familiarity (that is Experiment 1's
  domain, and crossing the two is a natural next study).
