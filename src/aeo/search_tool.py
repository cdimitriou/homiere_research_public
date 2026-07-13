"""The controlled 'artificial search' instrument.

The model is offered a generic ``web_search`` tool, but every result it sees
comes from a corpus we authored. This is the core of the experimental design:
it gives full control over the evidence available in the search condition, so
answer behavior can be causally attributed to document content rather than to
whatever a live search engine happened to return.

The index also records every query the model issues — the queries themselves
are data (they reveal what the model believes it needs to look up).
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field

SEARCH_TOOL = {
    "toolSpec": {
        "name": "web_search",
        "description": (
            "Search the web. Returns the most relevant pages for a query, "
            "each with a title, URL, and page content."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"],
            }
        },
    }
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class SearchDoc:
    doc_id: str
    title: str
    url: str
    content: str
    # Free-form labels: entity, condition, treatment arm, fact probes, etc.
    tags: dict = field(default_factory=dict)


@dataclass
class SearchEvent:
    query: str
    returned_doc_ids: list[str]


class ControlledSearchIndex:
    """Lexical index over authored documents, exposed as a web_search tool.

    Scoring is IDF-weighted token overlap between the query and each document's
    title + content. Corpora are small and authored, so this is deliberately
    simple; what matters is determinism and full experimenter control, not
    retrieval quality.
    """

    def __init__(self, docs: list[SearchDoc], k: int = 5):
        self.docs = list(docs)
        self.k = k
        self.query_log: list[SearchEvent] = []
        self._doc_tokens = [set(_tokens(d.title + " " + d.content)) for d in self.docs]
        df = Counter(tok for toks in self._doc_tokens for tok in toks)
        n = max(len(self.docs), 1)
        self._idf = {tok: math.log((n + 1) / (count + 0.5)) for tok, count in df.items()}

    def search(self, query: str) -> list[SearchDoc]:
        q = set(_tokens(query))
        scored = [
            (sum(self._idf.get(tok, 0.0) for tok in q & toks), doc)
            for doc, toks in zip(self.docs, self._doc_tokens)
        ]
        scored.sort(key=lambda pair: -pair[0])
        hits = [doc for score, doc in scored[: self.k] if score > 0]
        self.query_log.append(SearchEvent(query, [d.doc_id for d in hits]))
        return hits

    def executor(self, name: str, tool_input: dict) -> str:
        """Adapter with the (tool_name, tool_input) -> str signature ClaudeClient expects."""
        if name != "web_search":
            return json.dumps({"error": f"unknown tool {name}"})
        hits = self.search(tool_input.get("query", ""))
        return format_results(hits) if hits else "No results found."


def format_results(docs: list[SearchDoc]) -> str:
    return "\n\n".join(
        f"Result {i}:\nTitle: {d.title}\nURL: {d.url}\nContent: {d.content}"
        for i, d in enumerate(docs, start=1)
    )


class FixedResultTool:
    """Search tool that returns a preset, fixed-order result list for any query.

    Experiment 2 needs the presented ranking (SERP order) to be a controlled
    variable so content-feature effects can be separated from position effects.
    Unlike ControlledSearchIndex, this ignores the query and always returns the
    same documents in the same order, so a Latin square over document positions
    fully neutralizes position bias.
    """

    def __init__(self, docs: list[SearchDoc]):
        self.docs = list(docs)
        self.query_log: list[str] = []

    def executor(self, name: str, tool_input: dict) -> str:
        if name != "web_search":
            return json.dumps({"error": f"unknown tool {name}"})
        self.query_log.append(tool_input.get("query", ""))
        return format_results(self.docs)
