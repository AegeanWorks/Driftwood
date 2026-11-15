"""Read per-file churn from a local git repository without third-party tools."""

from __future__ import annotations

import codecs
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

COMMIT_MARKER = "__COMMIT__"
_ADDED, _DELETED, _PATH = 0, 1, 2

PER_CALL_TIMEOUT_SECONDS = 60.0
GIT_TOTAL_BUDGET_SECONDS = 240.0
_EXHAUSTED_TIMEOUT_SECONDS = 0.05

_budget_deadline: float | None = None


@contextmanager
def git_session(total_seconds: float = GIT_TOTAL_BUDGET_SECONDS) -> Iterator[None]:
    """Cap the cumulative wall time of the git calls made inside the block.

    Each call inside the session may use whatever budget remains, so one slow
    `git log --numstat` on a huge repository gets more than the per-call
    default without letting the whole invocation run unbounded.
    """
    global _budget_deadline
    _budget_deadline = time.monotonic() + total_seconds
    try:
        yield
    finally:
        _budget_deadline = None


def session_deadline() -> float | None:
    """The active session's absolute deadline, or None outside git_session()."""
    return _budget_deadline


def _call_timeout() -> float:
    if _budget_deadline is None:
        return PER_CALL_TIMEOUT_SECONDS
    remaining = _budget_deadline - time.monotonic()
    return remaining if remaining > _EXHAUSTED_TIMEOUT_SECONDS else _EXHAUSTED_TIMEOUT_SECONDS


class GitError(RuntimeError):
    """A git invocation failed; the message carries Why and Fix guidance."""


@dataclass(frozen=True)
class FileChurn:
    """Aggregated history for one file: commit count and added/deleted lines."""

    commits: int = 0
    added: int = 0
    deleted: int = 0

    def with_change(self, added: int, deleted: int) -> "FileChurn":
        return FileChurn(self.commits + 1, self.added + added, self.deleted + deleted)

    @property
    def churn(self) -> int:
        return self.added + self.deleted


Runner = Callable[[Path, list[str]], str]


def _run_git(repo: Path, args: list[str]) -> str:
    timeout = _call_timeout()
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError(
            "Why: git is not installed or not on PATH.\n"
            "Fix: install git and reopen the terminal, then retry."
        ) from exc
    except OSError as exc:
        raise GitError(
            f"Why: could not launch git ({exc}).\n"
            "Fix: check that git is installed and the repository is accessible."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        if _budget_deadline is not None and timeout <= _EXHAUSTED_TIMEOUT_SECONDS:
            detail = f"; the {GIT_TOTAL_BUDGET_SECONDS:.0f}s cumulative git budget is exhausted"
        elif _budget_deadline is not None:
            detail = f" (of the {GIT_TOTAL_BUDGET_SECONDS:.0f}s cumulative git budget)"
        else:
            detail = ""
        raise GitError(
            f"Why: git did not answer within {timeout:.2g}s{detail}.\n"
            "Fix: check that the repository is healthy and retry; very large "
            "histories may need a larger git_session budget."
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "no output"
        raise GitError(
            f"Why: git {' '.join(args)} failed (exit {result.returncode}).\n"
            f"Detail: {detail}\n"
            f"Fix: run this command inside a git work tree and check it with "
            f"`git -C \"{repo}\" status`."
        )
    return result.stdout


def _unquote_path(raw: str) -> tuple[str, bool]:
    """Decode git's C-style quoted path and say whether the input was quoted."""
    text = raw.strip()
    if len(text) < 2 or not (text.startswith('"') and text.endswith('"')):
        return text, False
    try:
        decoded = codecs.escape_decode(text[1:-1].encode("utf-8"))[0].decode("utf-8")
    except ValueError:
        decoded = text[1:-1]
    return decoded, True


def normalize_path(raw: str) -> str:
    """Reduce git's rename notation to the newest path, using forward slashes."""
    path, quoted = _unquote_path(raw)
    if " => " in path:
        prefix, _, suffix = path.partition(" => ")
        if "{" in prefix and "}" in suffix:
            head, _, tail = suffix.partition("}")
            path = prefix.split("{", 1)[0] + head + tail
        else:
            path = suffix
    return path if quoted else path.replace("\\", "/")


def parse_numstat(text: str) -> dict[str, FileChurn]:
    """Aggregate `git log --numstat --format=__COMMIT__%H` output per file.

    Binary entries (``-`` counts) are ignored: line churn is undefined for them.
    """
    churn: dict[str, FileChurn] = {}
    for line in text.splitlines():
        if not line or line.startswith(COMMIT_MARKER):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added, deleted = parts[_ADDED], parts[_DELETED]
        raw_path = "\t".join(parts[_PATH:])
        if added == "-" or deleted == "-":
            continue
        try:
            added_int, deleted_int = int(added), int(deleted)
        except ValueError:
            continue
        if added_int < 0 or deleted_int < 0:
            continue
        path = normalize_path(raw_path)
        if not path:
            continue
        current = churn.get(path, FileChurn())
        churn[path] = current.with_change(added_int, deleted_int)
    return churn


def collect_churn(
    repo: Path,
    *,
    since: str | None = None,
    max_commits: int | None = None,
    runner: Runner = _run_git,
) -> dict[str, FileChurn]:
    """Return `{path: FileChurn}` for history up to `max_commits` commits."""
    args = ["log", f"--format={COMMIT_MARKER}%H", "--numstat"]
    if since is not None:
        if not isinstance(since, str) or not since.strip():
            raise ValueError("since must be a non-blank string")
        args.append(f"--since={since}")
    if max_commits is not None:
        if isinstance(max_commits, bool) or not isinstance(max_commits, int):
            raise TypeError("max_commits must be an integer")
        if max_commits < 1:
            raise ValueError("max_commits must be a positive integer")
        args.append(f"--max-count={max_commits}")
    return parse_numstat(runner(Path(repo), args))


def repo_root(repo: Path, runner: Runner = _run_git) -> Path:
    """Resolve the work-tree root that `repo` belongs to."""
    raw = runner(Path(repo), ["rev-parse", "--show-toplevel"])
    if not isinstance(raw, str):
        raise GitError(
            "Why: git rev-parse returned non-text output.\n"
            f"Fix: run this command inside a git work tree and check it with "
            f"`git -C \"{repo}\" status`."
        )
    text = raw.strip("\r\n")
    if not text.strip() or "\n" in text or "\r" in text:
        raise GitError(
            "Why: git rev-parse returned empty output.\n"
            f"Fix: run this command inside a git work tree and check it with "
            f"`git -C \"{repo}\" status`."
        )
    return Path(text)
