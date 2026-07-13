"""Pilot: end-to-end validation of the experiment harness.

Not a confirmatory study — the goal is to verify the plumbing produces real,
loggable numbers for every measure Experiment 1 needs:

  1. Bedrock Converse + tool-use loop works against current Claude models.
  2. The model actually calls our controlled web_search tool when offered it.
  3. No-search condition: fictitious entities should elicit abstention.
  4. Search condition: controlled facts should be adopted into answers.
  5. Contradiction probe (Redfin founding year/city): does controlled evidence
     override the model's prior?
  6. A ranking task including a fictitious candidate with strong authored docs.

Usage:
    uv run python experiments/pilot/run_pilot.py [--model sonnet-4.5] [--run-name pilot]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from aeo.bedrock import ClaudeClient
from aeo.metrics import abstains, adopted_facts, mentions
from aeo.runlog import RunLogger
from aeo.search_tool import SEARCH_TOOL, ControlledSearchIndex, SearchDoc

ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "data" / "corpora" / "pilot.json"

SYSTEM_SEARCH = (
    "You are a helpful assistant. You have access to a web_search tool; "
    "use it whenever current or specific information would improve your answer."
)
SYSTEM_NO_SEARCH = "You are a helpful assistant."


def build_index(corpus: dict) -> ControlledSearchIndex:
    docs = [
        SearchDoc(d["doc_id"], d["title"], d["url"], d["content"], tags={"entity": e["name"]})
        for e in corpus["entities"]
        for d in e["docs"]
    ]
    docs += [
        SearchDoc(d["doc_id"], d["title"], d["url"], d["content"], tags={"entity": None})
        for d in corpus["distractors"]
    ]
    return ControlledSearchIndex(docs, k=4)


def run_entity_probes(client: ClaudeClient, corpus: dict, logger: RunLogger) -> list[dict]:
    rows = []
    for entity in corpus["entities"]:
        for condition in ("no_search", "search"):
            # Fresh index per trial so query logs don't bleed across trials.
            index = build_index(corpus) if condition == "search" else None
            convo = client.run(
                entity["ask"],
                system=SYSTEM_SEARCH if index else SYSTEM_NO_SEARCH,
                tools=[SEARCH_TOOL] if index else None,
                tool_executor=index.executor if index else None,
            )
            answer = convo.final_text
            probes = {
                f"{group}:{probe}": hit
                for group, plist in entity["fact_probes"].items()
                for probe, hit in adopted_facts(answer, plist).items()
            }
            row = {
                "task": "entity_probe",
                "entity": entity["name"],
                "entity_type": entity["type"],
                "condition": condition,
                "mentions_entity": mentions(answer, entity["name"], entity["aliases"]),
                "abstains": abstains(answer),
                "n_tool_queries": len(index.query_log) if index else 0,
                **probes,
            }
            rows.append(row)
            logger.append(
                {
                    **row,
                    "model": client.model_id,
                    "prompt": entity["ask"],
                    "answer": answer,
                    "tool_queries": [q.query for q in index.query_log] if index else [],
                    "usage": convo.total_usage,
                }
            )
            print(f"[{entity['name']} / {condition}] "
                  f"abstains={row['abstains']} tool_queries={row['n_tool_queries']}")
    return rows


def run_ranking_task(client: ClaudeClient, corpus: dict, logger: RunLogger) -> list[dict]:
    task = corpus["ranking_task"]
    rows = []
    for condition in ("no_search", "search"):
        index = build_index(corpus) if condition == "search" else None
        convo = client.run(
            task["ask"],
            system=SYSTEM_SEARCH if index else SYSTEM_NO_SEARCH,
            tools=[SEARCH_TOOL] if index else None,
            tool_executor=index.executor if index else None,
        )
        answer = convo.final_text
        row = {
            "task": "ranking",
            "entity": task["fictitious_candidate"],
            "entity_type": "fictitious",
            "condition": condition,
            "mentions_entity": mentions(answer, task["fictitious_candidate"], ["Harrowfield"]),
            "abstains": abstains(answer),
            "n_tool_queries": len(index.query_log) if index else 0,
        }
        rows.append(row)
        logger.append(
            {
                **row,
                "model": client.model_id,
                "prompt": task["ask"],
                "answer": answer,
                "candidates": task["candidates"],
                "tool_queries": [q.query for q in index.query_log] if index else [],
                "usage": convo.total_usage,
            }
        )
        print(f"[ranking / {condition}] tool_queries={row['n_tool_queries']}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="sonnet-4.5")
    parser.add_argument("--run-name", default="pilot")
    args = parser.parse_args()

    corpus = json.loads(CORPUS_PATH.read_text())
    client = ClaudeClient(model=args.model)
    logger = RunLogger(args.run_name, ROOT / "data" / "runs")

    rows = run_entity_probes(client, corpus, logger)
    rows += run_ranking_task(client, corpus, logger)

    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 50)
    print("\n=== Pilot summary ===")
    print(df.fillna("").to_string(index=False))
    print(f"\nRaw records: {logger.path}")


if __name__ == "__main__":
    main()
