"""Language-aware complexity estimates that need only the standard library."""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

PYTHON_SUFFIXES = {".py", ".pyi"}
DECISION_KEYWORDS = {
    "if",
    "elif",
    "for",
    "while",
    "except",
    "and",
    "or",
    "assert",
    "case",
}
GENERIC_MARKERS = (
    " if ",
    "if(",
    "if (",
    " else if",
    "else if",
    " for ",
    "for(",
    "for (",
    " while ",
    "while(",
    "while (",
    " case ",
    "catch",
    "switch",
    "&&",
    "||",
    "?",
)
MAX_BYTES = 400_000


def python_complexity(source: str) -> int:
    """Cyclomatic-style count for Python: 1 + decision points (bounded by source size)."""
    total = 1
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.NAME and token.string in DECISION_KEYWORDS:
                total += 1
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return 1 + sum(
            1 for line in source.splitlines() if _line_has_decision(line)
        )
    return total


def generic_complexity(source: str) -> int:
    """Cheap multi-language estimate: 1 + lines carrying a branching marker."""
    return 1 + sum(1 for line in source.splitlines() if _line_has_decision(line))


def _line_has_decision(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "//", "/*", "*")):
        return False
    padded = f" {stripped} "
    return any(marker in padded for marker in GENERIC_MARKERS)


def file_complexity(path: Path) -> int:
    """Estimate complexity for a file, returning 0 for unreadable or oversized files."""
    try:
        if path.stat().st_size > MAX_BYTES:
            return 0
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    if path.suffix.lower() in PYTHON_SUFFIXES:
        return python_complexity(source)
    return generic_complexity(source)


def complexity_map(root: Path, paths: list[str]) -> dict[str, int]:
    """Map each existing relative path in `paths` to its complexity estimate."""
    result: dict[str, int] = {}
    for rel in paths:
        candidate = root / rel
        if candidate.is_file():
            result[rel] = file_complexity(candidate)
    return result
