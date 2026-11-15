"""Language-aware complexity estimates that need only the standard library."""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

PYTHON_SUFFIXES = {".py", ".pyi"}
# Files whose generic branching markers mean something structural. Outside
# this set, prose and data formats score complexity 0 when they have no
# churn history (`--all`): branching words in legal or README text are noise.
CODE_SUFFIXES = PYTHON_SUFFIXES | {
    ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cxx",
    ".java", ".kt", ".kts", ".scala", ".swift", ".go", ".rs",
    ".rb", ".php", ".cs", ".dart", ".lua", ".m", ".mm", ".vue", ".svelte",
    ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".sql",
}
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
    "case(",
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
    except (tokenize.TokenError, SyntaxError):
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
    """Estimate complexity for a file, returning 0 for unreadable, oversized or binary files."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_BYTES + 1)
    except OSError:
        return 0
    if len(data) > MAX_BYTES:
        return 0
    if b"\x00" in data:
        return 0
    source = data.decode("utf-8", errors="replace")
    if path.suffix.lower() in PYTHON_SUFFIXES:
        return python_complexity(source)
    return generic_complexity(source)


def complexity_map(root: Path, paths: list[str]) -> dict[str, int]:
    """Map each existing relative path in `paths` to its complexity estimate.

    Absolute paths, parent escapes (``..``) and symlinks are skipped to keep
    analysis rooted at `root`.
    """
    result: dict[str, int] = {}
    for rel in paths:
        parts = Path(rel).parts
        if Path(rel).is_absolute() or ".." in parts:
            continue
        candidate = root / rel
        if candidate.is_symlink() or not candidate.resolve().is_relative_to(root.resolve()):
            continue
        if candidate.is_file():
            result[rel] = file_complexity(candidate)
    return result
