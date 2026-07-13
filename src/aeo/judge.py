"""LLM-judge measurements over model answers.

The pilot showed substring fact-matching is too brittle: "**Founded:** 2002"
does not contain "founded in 2002" as a substring, yet the fact was plainly
adopted. The primary outcome measures therefore use a Claude judge (a separate,
cheap model instance) that reads an answer and returns structured verdicts.
The judge is deliberately narrow — it decides entailment-style questions about
a single claim at a time — and returns strict JSON we validate.

All judge calls are logged by the caller (they pass a ``record`` sink) so the
judgments themselves are auditable and reproducible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from aeo.bedrock import ClaudeClient

# Haiku is the default judge: cheap, and the tasks are simple entailment calls.
DEFAULT_JUDGE_MODEL = "haiku-4.5"


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    for parse in (json.loads, lambda s: json.loads(s, strict=False)):
        try:
            return parse(text)
        except json.JSONDecodeError:
            pass
    # Fall back to the first balanced {...} block (tolerating literal control chars).
    start, depth = text.find("{"), 0
    for i in range(start, len(text)) if start >= 0 else []:
        depth += (text[i] == "{") - (text[i] == "}")
        if depth == 0:
            return json.loads(text[start : i + 1], strict=False)
    raise ValueError(f"no JSON object in judge output: {text[:200]!r}")


@dataclass
class FactVerdict:
    fact: str
    stated: str  # "asserts" | "contradicts" | "absent"


@dataclass
class FamiliarityVerdict:
    specificity: int  # 0 = generic/none, 1 = some specifics, 2 = rich specific claims
    disclaims_unfamiliarity: bool
    specific_claims: list[str]


class AnswerJudge:
    def __init__(self, model: str = DEFAULT_JUDGE_MODEL):
        # temperature 0 for reproducible judgments.
        self.client = ClaudeClient(model=model, temperature=0.0, max_tokens=1024)

    def fact_status(self, answer: str, facts: list[str]) -> list[FactVerdict]:
        """For each fact, does the answer assert it, contradict it, or omit it?

        This is the core adoption/persistence measure. "asserts" on a novel
        controlled fact = adoption; "asserts" on a prior-truth fact whose
        contradiction we supplied = prior persistence.
        """
        if not facts:
            return []
        numbered = "\n".join(f"{i}. {f}" for i, f in enumerate(facts, 1))
        prompt = (
            "You are checking whether an ANSWER makes certain factual claims. "
            "For each numbered CLAIM, decide whether the ANSWER:\n"
            '  - "asserts": states this claim (or an obvious paraphrase) as true\n'
            '  - "contradicts": states something incompatible with this claim\n'
            '  - "absent": neither asserts nor contradicts it\n\n'
            "Judge only what the ANSWER actually says. Do not use outside knowledge.\n\n"
            f"ANSWER:\n{answer}\n\n"
            f"CLAIMS:\n{numbered}\n\n"
            'Respond with JSON only, a list of verdicts in the SAME ORDER as the '
            'claims, using no free text (this keeps the JSON valid):\n'
            '{"stated": ["asserts"|"contradicts"|"absent", ...]}'
        )
        stated = _extract_json(self.client.run(prompt).final_text).get("stated", [])
        valid = {"asserts", "contradicts", "absent"}
        return [
            FactVerdict(
                fact=f,
                stated=stated[i] if i < len(stated) and stated[i] in valid else "absent",
            )
            for i, f in enumerate(facts)
        ]

    def familiarity(self, answer: str, entity: str) -> FamiliarityVerdict:
        """Score how much specific knowledge an answer displays about an entity.

        Used in the screening phase to place entities into familiarity tiers
        from their NO-SEARCH answers, and to detect the confabulation pattern
        (specific claims without any disclaimer of unfamiliarity).
        """
        prompt = (
            f'Below is an ANSWER a model gave about "{entity}". Assess how much '
            "SPECIFIC, verifiable-in-principle knowledge it displays about this "
            "particular entity (not generic advice about the category).\n\n"
            f"ANSWER:\n{answer}\n\n"
            "Respond with JSON only:\n"
            "{\n"
            '  "specificity": 0 | 1 | 2,   // 0 = no specific claims / only generic '
            "category talk, 1 = a few specific claims, 2 = multiple rich specific "
            "claims (dates, people, numbers, locations)\n"
            '  "disclaims_unfamiliarity": true | false,  // does it say it is unsure '
            "or unfamiliar with this specific entity?\n"
            '  "specific_claims": ["<each concrete claim about the entity>"]\n'
            "}"
        )
        out = _extract_json(self.client.run(prompt).final_text)
        return FamiliarityVerdict(
            specificity=int(out.get("specificity", 0)),
            disclaims_unfamiliarity=bool(out.get("disclaims_unfamiliarity", False)),
            specific_claims=list(out.get("specific_claims", [])),
        )

    def extract_ranking(self, answer: str, candidates: list[str]) -> list[str]:
        """Return the candidates in the order the answer ranks them (best first).

        Candidates not ranked are omitted. Enables Kendall's tau against the
        presented order (the curation-rate measure).
        """
        listed = "\n".join(f"- {c}" for c in candidates)
        prompt = (
            "The ANSWER ranks or compares some CANDIDATES. Extract the order in "
            "which the ANSWER ranks them, best first. Use the exact candidate "
            "names given. Omit any candidate the answer does not rank.\n\n"
            f"CANDIDATES:\n{listed}\n\n"
            f"ANSWER:\n{answer}\n\n"
            'Respond with JSON only: {"ranking": ["<name>", ...]}'
        )
        out = _extract_json(self.client.run(prompt).final_text)
        valid = {c.lower(): c for c in candidates}
        return [valid[r.lower()] for r in out.get("ranking", []) if r.lower() in valid]
