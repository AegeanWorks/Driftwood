"""Command-line entry point for the driftwood hotspot report."""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

from driftwood import __version__
from driftwood.complexity import complexity_map
from driftwood.gitlog import GitError, collect_churn, repo_root
from driftwood.report import format_json, format_table
from driftwood.scoring import rank_hotspots


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected an integer, got {raw!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def _non_negative_float(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a number, got {raw!r}") from None
    if not 0 <= value < float("inf"):
        raise argparse.ArgumentTypeError("must be a finite non-negative number")
    return value


_SINCE_ABSOLUTE = re.compile(
    r"^(?P<year>\d{4})-?(?P<month>\d{2})?-?(?P<day>\d{2})?"
    r"(?:[ T](?P<hour>\d{2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?)?"
    r"(?: ?(?P<tz>[+-]\d{2}:?\d{2}|Z))?$"
)
_SINCE_RELATIVE = re.compile(
    r"^\d+(?:\s*\.\s*|\s+)(?:second|minute|hour|day|week|month|year)s?"
    r"(?:\s*\.\s*|\s+)ago$"
)
_SINCE_WEEKDAY = re.compile(
    r"^(?:(?:last|next)\s+)?"
    r"(?:monday|mon|tuesday|tues|tue|wednesday|weds|wed|thursday|thurs|thu"
    r"|friday|fri|saturday|sat|sunday|sun)$"
)
_SINCE_KEYWORDS = {"now", "today", "yesterday"}


def _is_supported_since(value: str) -> bool:
    """Reject git's silent approxidate fallbacks, accept documented forms only."""
    lowered = value.lower()
    if lowered in _SINCE_KEYWORDS:
        return True
    if _SINCE_ABSOLUTE.match(value):
        match = _SINCE_ABSOLUTE.match(value)
        try:
            year, month = int(match.group("year")), 1
            if match.group("month"):
                month = int(match.group("month"))
                if match.group("day"):
                    date(year, month, int(match.group("day")))
        except ValueError:
            return False
        if match.group("hour") and int(match.group("hour")) > 23:
            return False
        if match.group("minute") and int(match.group("minute")) > 59:
            return False
        return not (match.group("second") and int(match.group("second")) > 59)
    return (
        bool(_SINCE_RELATIVE.match(lowered))
        or bool(_SINCE_WEEKDAY.match(lowered))
        or (lowered.startswith("@") and lowered[1:].isdigit())
    )


def _since_value(raw: str) -> str:
    value = raw.strip()
    if value and _is_supported_since(value):
        return value
    raise argparse.ArgumentTypeError(
        f"invalid argument: expected a date like '12.months.ago', "
        f"'2 weeks ago', '2024-01-15' or 'last monday', got {raw!r}. "
        f"Why: git silently parses unknown words as 'now', which would "
        f"truncate history without an error. Fix: use one of the accepted forms."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="driftwood",
        description="Rank code hotspots by combining git churn with file complexity.",
    )
    parser.add_argument("repo", nargs="?", default=".", help="path inside the git work tree")
    parser.add_argument(
        "--since",
        type=_since_value,
        help="git date filter: '12.months.ago', '2 weeks ago', '2024-01-15', "
        "'@epoch', 'now', 'yesterday' or 'last monday'; anything else exits 2",
    )
    parser.add_argument(
        "--commits", type=_positive_int, help="only the newest N commits"
    )
    parser.add_argument(
        "--top", type=_positive_int, default=20, help="rows to show (default: 20)"
    )
    parser.add_argument(
        "--format", choices=("table", "json"), default="table", help="output format"
    )
    parser.add_argument(
        "--include",
        action="append",
        default=None,
        metavar="GLOB",
        help="keep matching paths (repeatable, case-sensitive, * spans /; empty keeps all)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="GLOB",
        help="drop matching paths (repeatable, case-sensitive; exclude wins)",
    )
    parser.add_argument(
        "--min-score",
        type=_non_negative_float,
        default=0.0,
        help="hide rows below this score (applied before --top)",
    )
    parser.add_argument("--version", action="version", version=f"driftwood {__version__}")
    return parser


def _matches(path: str, include: Sequence[str], exclude: Sequence[str]) -> bool:
    if include and not any(
        fnmatch.fnmatchcase(path, pattern) for pattern in include
    ):
        return False
    return not any(fnmatch.fnmatchcase(path, pattern) for pattern in exclude)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        repo_path = Path(args.repo)
        if repo_path.is_file():
            repo_path = repo_path.parent
        root = repo_root(repo_path)
    except GitError as exc:
        print(f"driftwood: {exc}", file=sys.stderr)
        return 1
    try:
        churn = collect_churn(root, since=args.since, max_commits=args.commits)
    except GitError as exc:
        print(f"driftwood: {exc}", file=sys.stderr)
        return 1
    except (ValueError, TypeError) as exc:
        print(f"driftwood: invalid argument: {exc}", file=sys.stderr)
        return 2

    include = [pattern for pattern in (args.include or []) if pattern]
    exclude = args.exclude or []
    selected = {
        path: stat
        for path, stat in churn.items()
        if _matches(path, include, exclude)
    }
    complexity = complexity_map(root, sorted(selected))
    ranked = rank_hotspots(selected, complexity)
    shown = [item for item in ranked if item.score >= args.min_score][: args.top]

    renderer = format_json if args.format == "json" else format_table
    try:
        print(renderer(shown))
    except BrokenPipeError:
        # hygiene: allow silent broken-pipe exit for `| head` usability; redirect
        # the fd instead of closing the shared stdout object that hosts capture
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            os.close(devnull)
        except OSError:  # hygiene: allow silent-except: capture-host streams and dead fds have no log channel
            pass
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
