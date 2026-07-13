"""Assemble exp1_evidence.json from the evidence-authoring workflow output.

The workflow (exp1-evidence-author) writes one record per entity with authored
treatment documents and probe lists. This step:
  1. Validates that every adopt/persist probe is actually supported by its
     treatment's document text (fuzzy token-overlap check; flags weak ones).
  2. Attaches a shared distractor set (generic category advice) so the search
     index always returns competition, not just the target's pages.
  3. Writes the corpus run_exp1.py consumes.

Usage:
    uv run python experiments/exp1/build_corpus.py --from <workflow_output.json>
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "corpora" / "exp1_evidence.json"

DISTRACTORS = [
    {
        "doc_id": "generic_choose_brokerage",
        "title": "How to choose a real estate brokerage",
        "url": "https://www.homesellerhandbook.com/choosing-a-brokerage",
        "content": (
            "When choosing a brokerage, compare commission structure, local market share, "
            "marketing services, and agent experience. Boutique firms often offer more "
            "hands-on service; national brands offer wider reach and technology platforms."
        ),
    },
    {
        "doc_id": "generic_home_services",
        "title": "Hiring a home services provider: what to look for",
        "url": "https://www.homesellerhandbook.com/hiring-home-services",
        "content": (
            "Evaluate home service providers on licensing, insurance, verified reviews, "
            "response time, and clear written quotes. Ask about guarantees and whether the "
            "company uses employees or subcontractors."
        ),
    },
]

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall(s.lower()))


def probe_supported(probe: str, doc_text: str) -> bool:
    """A probe is 'supported' if most of its content words appear in the docs.

    Loose on purpose: the judge does the real semantic scoring at run time; this
    is a sanity gate to catch probes the author forgot to actually write into a
    document. Ignores common stopwords so short claims aren't unfairly failed.
    """
    stop = {"the", "a", "an", "was", "is", "in", "of", "to", "and", "by", "with", "that", "it"}
    pt = _tokens(probe) - stop
    if not pt:
        return True
    dt = _tokens(doc_text)
    return len(pt & dt) / len(pt) >= 0.6


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True, help="workflow output JSON file")
    args = ap.parse_args()

    authored = json.loads(Path(args.src).read_text())
    corpus: dict = {"_distractors": DISTRACTORS}
    weak = []

    for e in authored:
        name = e["name"]
        treatments = {}
        for tname, t in e["treatments"].items():
            doc_text = " ".join(d["content"] for d in t["docs"])
            # Only adopt_probes must be asserted by the docs. persist_probes are
            # the TRUE prior facts a contradicting treatment negates; by design
            # they are absent from those docs, so they are not checked here.
            for p in t.get("adopt_probes", []):
                if not probe_supported(p, doc_text):
                    weak.append((name, tname, "adopt_probes", p))
            treatments[tname] = {
                "docs": t["docs"],
                "adopt_probes": t.get("adopt_probes", []),
                "persist_probes": t.get("persist_probes", []),
            }
        corpus[name] = {"ask": e["ask"], "tier": e["tier"], "treatments": treatments}

    OUT.write_text(json.dumps(corpus, indent=2))
    n_entities = len([k for k in corpus if not k.startswith("_")])
    n_treat = sum(len(v["treatments"]) for k, v in corpus.items() if not k.startswith("_"))
    print(f"Wrote {OUT}: {n_entities} entities, {n_treat} treatments.")
    if weak:
        print(f"\n{len(weak)} probes weakly supported by their docs (review):")
        for name, tname, kind, p in weak:
            print(f"  [{name} / {tname} / {kind}] {p!r}")
    else:
        print("All probes supported by their documents.")


if __name__ == "__main__":
    main()
