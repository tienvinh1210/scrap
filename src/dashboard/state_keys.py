"""Canonical state-key encoding for the dashboard JSON cache."""

from __future__ import annotations

from typing import Mapping


def build_state_key(page: str, **controls: str) -> str:
    """Return a pipe-delimited key with sorted control names."""

    parts = [page]
    for name in sorted(controls):
        parts.append(f"{name}={controls[name]}")
    return "|".join(parts)


def parse_state_key(key: str) -> tuple[str, dict[str, str]]:
    """Parse a state key into page name and control mapping."""

    segments = key.split("|")
    page = segments[0]
    controls: dict[str, str] = {}
    for segment in segments[1:]:
        if "=" not in segment:
            continue
        name, value = segment.split("=", 1)
        controls[name] = value
    return page, controls


def validate_coverage(
    expected: Mapping[str, set[str]],
    actual: set[str],
) -> list[str]:
    """Return missing state keys."""

    missing = sorted(expected.keys() - actual)
    return missing
