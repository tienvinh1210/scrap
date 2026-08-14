"""Load chart catalog JSON."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = REPO_ROOT / "outputs" / "dashboard" / "dashboard_states.json"


def load_dashboard_cache(cache_path: str) -> dict:
    path = Path(cache_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dashboard cache not found at {path}. Run: python3 -m src.dashboard.build_cache"
        )
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
