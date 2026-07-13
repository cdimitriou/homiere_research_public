"""Outcome measures over model answers.

Pilot-grade implementations: normalized string matching for entity mentions
and fact adoption, pattern-based abstention detection. The full study will add
entailment-based fact matching and embedding similarity; these versions exist
so pilot plumbing produces real numbers end-to-end.
"""

from __future__ import annotations

import re


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower())


def mentions(answer: str, entity: str, aliases: list[str] | None = None) -> bool:
    hay = _norm(answer)
    return any(_norm(name).strip() in hay for name in [entity, *(aliases or [])])


def adopted_facts(answer: str, fact_probes: list[str]) -> dict[str, bool]:
    """Which controlled fact-probe strings surfaced in the answer.

    Probes are short distinctive spans we planted in the corpus (a founding
    year, an agent count, a founder's surname) — chosen so a normalized
    substring match is a reliable adoption signal.
    """
    hay = _norm(answer)
    return {probe: _norm(probe).strip() in hay for probe in fact_probes}


_ABSTAIN_PATTERNS = [
    r"i don'?t have (any |specific |reliable |verified )?(information|details|knowledge)",
    r"i'?m not (familiar|aware)",
    r"i couldn'?t find",
    r"no (information|results?) (was |were |is |are )?(found|available)",
    r"i don'?t know",
    r"not able to (find|locate|verify)",
    r"doesn'?t appear (in|to)",
    r"unable to (find|verify|confirm)",
    r"may not exist",
    r"i have no (information|record)",
]


def abstains(answer: str) -> bool:
    low = answer.lower()
    return any(re.search(p, low) for p in _ABSTAIN_PATTERNS)
