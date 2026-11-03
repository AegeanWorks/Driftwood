"""Render ranked hotspots as a fixed-width table or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Sequence

from driftwood.scoring import Hotspot

HEADER = ("#", "Score", "Churn", "Cplx", "Commits", "File")


def _sanitize_path(path: str) -> str:
    """Keep one-hotspot-one-line: replace control characters in paths."""
    return path.replace("\r", "?").replace("\n", "?").replace("\t", "?").replace("\x1b", "?")


def _row(index: int, item: Hotspot) -> tuple[str, ...]:
    return (
        str(index),
        f"{item.score:.3f}",
        str(item.churn),
        str(item.complexity),
        str(item.commits),
        _sanitize_path(item.path),
    )


def format_table(hotspots: Sequence[Hotspot]) -> str:
    """Render an aligned, header-first table; paths stay at the end to avoid wrapping.

    Scores display ``.3f`` while stored scores keep ``.4f`` precision, so two
    differently-ranked rows can render identically on the last digit.
    """
    items = list(hotspots) if not isinstance(hotspots, list) else hotspots
    if not items:
        return "No hotspots found. Why: no text churn in the selected range.\nFix: widen --since, raise --commits, or check the path."
    rows = [_row(index, item) for index, item in enumerate(items, start=1)]
    widths = [
        max(len(HEADER[column]), *(len(row[column]) for row in rows))
        for column in range(len(HEADER) - 1)
    ]
    lines = []
    header = "  ".join(
        HEADER[column].ljust(widths[column]) for column in range(len(widths))
    )
    lines.append(f"{header}  {HEADER[-1]}")
    lines.append("  ".join("-" * width for width in widths) + f"  {'-' * 4}")
    for row in rows:
        cells = [
            row[column].ljust(widths[column]) for column in range(len(widths))
        ]
        lines.append(f"{'  '.join(cells)}  {row[-1]}")
    return "\n".join(lines)


def format_json(hotspots: Sequence[Hotspot]) -> str:
    """Render hotspots as stable JSON for scripting."""
    items = list(hotspots) if not isinstance(hotspots, list) else hotspots
    payload = {
        "count": len(items),
        "hotspots": [asdict(item) for item in items],
    }
    return json.dumps(payload, indent=2, sort_keys=True)
