"""JSONL run logging.

Every model interaction lands in ``<runs_dir>/<run_name>/records.jsonl`` with
enough context (model id, params, full message transcript, tool queries, git
sha) to reproduce or re-analyze the run without touching the API again.

The runs directory is passed in by the caller rather than hard-coded, because
this harness is shared across papers in the monorepo and each paper keeps its
own ``data/runs`` under ``papers/<slug>/``.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Repo root (for git operations only); the aeo package lives at src/aeo.
REPO_ROOT = Path(__file__).resolve().parents[2]


def git_sha() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except Exception:
        return "unknown"


class RunLogger:
    def __init__(self, run_name: str, runs_dir: str | Path):
        self.dir = Path(runs_dir) / run_name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "records.jsonl"
        self._sha = git_sha()

    def append(self, record: dict) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "git_sha": self._sha,
            **record,
        }
        with self.path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")
