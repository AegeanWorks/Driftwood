"""Blend churn and complexity into a single, comparable hotspot score."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from driftwood.gitlog import FileChurn

DEFAULT_CHURN_WEIGHT = 0.6
DEFAULT_COMPLEXITY_WEIGHT = 0.4


@dataclass(frozen=True)
class Hotspot:
    """One ranked file: raw metrics plus the normalized blended score."""

    path: str
    commits: int
    added: int
    deleted: int
    churn: int
    complexity: int
    score: float


def normalize(values: Mapping[str, float]) -> dict[str, float]:
    """Min-max scale values to 0..1.

    A flat metric has no spread, so its positive values map to 1.0 (the single
    file that exists is the hottest one) and zeros stay zero.
    """
    if not values:
        return {}
    low = min(values.values())
    high = max(values.values())
    if high <= low:
        return {key: (1.0 if value > 0 else 0.0) for key, value in values.items()}
    span = high - low
    return {key: (value - low) / span for key, value in values.items()}


def rank_hotspots(
    churn: Mapping[str, FileChurn],
    complexity: Mapping[str, int],
    *,
    top: int | None = None,
    churn_weight: float = DEFAULT_CHURN_WEIGHT,
    complexity_weight: float = DEFAULT_COMPLEXITY_WEIGHT,
) -> list[Hotspot]:
    """Return hotspots ordered by score, highest first.

    Files with neither churn nor complexity are dropped; a tie breaks on path so
    repeated runs stay deterministic.
    """
    if churn_weight < 0 or complexity_weight < 0:
        raise ValueError("weights must be non-negative")
    if top is not None and top < 1:
        raise ValueError("top must be a positive integer")
    if not churn:
        return []

    churn_norm = normalize({path: stat.churn for path, stat in churn.items()})
    paths = sorted(churn)
    complexity_norm = normalize({path: float(complexity.get(path, 0)) for path in paths})

    ranked: list[Hotspot] = []
    for path in paths:
        stat = churn[path]
        complexity_value = complexity.get(path, 0)
        score = (
            churn_weight * churn_norm[path]
            + complexity_weight * complexity_norm[path]
        )
        if score <= 0 and stat.churn <= 0 and complexity_value <= 0:
            continue
        ranked.append(
            Hotspot(
                path=path,
                commits=stat.commits,
                added=stat.added,
                deleted=stat.deleted,
                churn=stat.churn,
                complexity=complexity_value,
                score=round(score, 4),
            )
        )
    ranked.sort(key=lambda item: (-item.score, item.path))
    return ranked[:top] if top is not None else ranked
