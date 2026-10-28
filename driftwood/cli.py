"""Command-line entry point for the driftwood hotspot report."""

from __future__ import annotations

import argparse
import fnmatch
import sys
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
    if value < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="driftwood",
        description="Rank code hotspots by combining git churn with file complexity.",
    )
    parser.add_argument("repo", nargs="?", default=".", help="path inside the git work tree")
    parser.add_argument("--since", help="git date filter, for example '12.months.ago'")
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
        "--include", action="append", default=[], metavar="GLOB", help="keep matching paths"
    )
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="GLOB", help="drop matching paths"
    )
    parser.add_argument(
        "--min-score",
        type=_non_negative_float,
        default=0.0,
        help="hide rows below this score",
    )
    parser.add_argument("--version", action="version", version=f"driftwood {__version__}")
    return parser


def _matches(path: str, include: Sequence[str], exclude: Sequence[str]) -> bool:
    if include and not any(fnmatch.fnmatch(path, pattern) for pattern in include):
        return False
    return not any(fnmatch.fnmatch(path, pattern) for pattern in exclude)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        root = repo_root(Path(args.repo))
        churn = collect_churn(root, since=args.since, max_commits=args.commits)
    except GitError as exc:
        print(f"driftwood: {exc}", file=sys.stderr)
        return 1

    selected = {
        path: stat
        for path, stat in churn.items()
        if _matches(path, args.include, args.exclude)
    }
    complexity = complexity_map(root, sorted(selected))
    ranked = rank_hotspots(selected, complexity)
    shown = [item for item in ranked if item.score >= args.min_score][: args.top]

    renderer = format_json if args.format == "json" else format_table
    print(renderer(shown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
