# Disclaimer: the document corpora contain fabricated facts

The experiments in this repository work by feeding the model documents we wrote and measuring
which of their claims it repeats. To do that, the corpora in `data/corpora/` and the authored
pages in `data/evidence_raw/` **deliberately contain false and invented statements**. That is the
experimental manipulation, not an error.

Specifically:

- **Fictitious entities.** Several entities (e.g. "Harrowfield & Vance Realty", "Tidecrest Home
  Concierge", and the CRM products in Experiment 2 such as "LedgerNest") are invented for the
  study. They do not exist. Their pages, and any awards, statistics, or testimonials on them, are
  fabricated.

- **Well-known brands with altered or invented facts.** For well-known brands (e.g. Redfin,
  Zillow, Keller Williams), some documents state deliberately **incorrect** facts (for example a
  wrong founding year or city) or describe **invented programs** that do not exist, in order to
  test whether the model adopts them over its correct prior knowledge. These statements are false
  by design and should not be taken as factual claims about those companies.

The model's answers recorded in `data/runs/` therefore also contain fabricated and incorrect
statements, because they are responses to these authored documents. They are records of model
behavior under controlled inputs, not statements of fact.

## Data availability: the tail tier is withheld

One tier of Experiment 1 (`TAIL`) used real but obscure small businesses, chosen because the model
had no prior knowledge of them. Because that tier involved authoring fabricated facts about real,
named small businesses, **its raw inputs and outputs are withheld from this public release** to
avoid publicly associating those businesses with invented content. The paper reports the tier's
aggregate results (which name no business); the `HIGH` (well-known brands) and `ZERO` (fictitious)
tiers are fully included and reproducible. The withheld tail-tier data is retained privately and
available to researchers on request.
