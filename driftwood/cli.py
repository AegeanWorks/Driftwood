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
    if not 0 <= value < float("inf"):
        raise argparse.ArgumentTypeError("must be a finite non-negative number")
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

    include = args.include or []
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
        # hygiene: allow silent broken-pipe exit for `| head` usability
        try:
            sys.stdout.close()
        except OSError:  # hygiene: allow close may fail on dead pipe
            pass
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
