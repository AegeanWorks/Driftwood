import contextlib
import io
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from driftwood import cli
from driftwood.gitlog import FileChurn, GitError
from driftwood.scoring import Hotspot


def _churn():
    return {
        "src/app.py": FileChurn(commits=4, added=40, deleted=10),
        "docs/readme.md": FileChurn(commits=1, added=2, deleted=0),
    }


class CliTests(unittest.TestCase):
    def _run(self, argv, churn=None, error=None):
        output = io.StringIO()
        errors = io.StringIO()
        patched_churn = mock.patch.object(
            cli, "collect_churn", side_effect=error, return_value=churn or _churn()
        )
        patched_root = mock.patch.object(cli, "repo_root", return_value=Path("."))
        with patched_churn, patched_root:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = cli.main(argv)
        return code, output.getvalue(), errors.getvalue()

    def test_table_output_sorted_by_score(self):
        code, out, _ = self._run(["repo"])
        self.assertEqual(code, 0)
        self.assertIn("src/app.py", out)
        self.assertLess(out.index("src/app.py"), out.index("docs/readme.md"))

    def test_json_output(self):
        code, out, _ = self._run(["repo", "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["count"], 2)

    def test_exclude_filter_drops_paths(self):
        code, out, _ = self._run(["repo", "--format", "json", "--exclude", "docs/*"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([item["path"] for item in payload["hotspots"]], ["src/app.py"])

    def test_include_filter_keeps_matching_paths(self):
        code, out, _ = self._run(["repo", "--format", "json", "--include", "src/*"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([item["path"] for item in payload["hotspots"]], ["src/app.py"])

    def test_empty_include_keeps_all_paths(self):
        code, out, _ = self._run(["repo", "--format", "json", "--include", ""])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["count"], 2)

    def test_git_error_returns_one_with_remediation(self):
        code, out, err = self._run(["repo"], error=GitError("Why: nope\nFix: retry"))
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Why: nope", err)

    def test_min_score_filters_before_top_slices(self):
        churn = {
            "hot/a.py": FileChurn(commits=2, added=100, deleted=0),
            "warm/b.py": FileChurn(commits=1, added=50, deleted=0),
            "cold/c.py": FileChurn(commits=1, added=1, deleted=0),
        }
        code, out, _ = self._run(
            ["repo", "--format", "json", "--min-score", "0.2", "--top", "2"],
            churn=churn,
        )
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([item["path"] for item in payload["hotspots"]], ["hot/a.py", "warm/b.py"])

    def test_display_score_matches_table_column(self):
        self.assertEqual(cli._display_score(0.2996), 0.3)
        self.assertEqual(cli._display_score(0.0004), 0.0)

    def test_min_score_keeps_row_that_displays_above_threshold(self):
        # score 0.2996 renders as "0.300"; --min-score 0.3 must keep it,
        # otherwise the user sees a 0.300 row vanish under a 0.3 threshold.
        ranked = [
            Hotspot(
                path="edge/a.py", commits=2, added=2, deleted=0, churn=2,
                complexity=2, score=0.2996,
            ),
            Hotspot(
                path="low/b.py", commits=1, added=1, deleted=0, churn=1,
                complexity=0, score=0.2,
            ),
        ]
        output = io.StringIO()
        with mock.patch.object(cli, "repo_root", return_value=Path(".")):
            with mock.patch.object(cli, "collect_churn", return_value={}):
                with mock.patch.object(cli, "complexity_map", return_value={}):
                    with mock.patch.object(cli, "rank_hotspots", return_value=ranked):
                        with contextlib.redirect_stdout(output):
                            code = cli.main(
                                ["repo", "--format", "json", "--min-score", "0.3"]
                            )
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual([item["path"] for item in payload["hotspots"]], ["edge/a.py"])

    def test_include_match_is_case_sensitive(self):
        self.assertTrue(cli._matches("src/app.py", ["src/*"], []))
        self.assertFalse(cli._matches("SRC/app.py", ["src/*"], []))

    def test_invalid_numeric_flags_exit_two(self):
        for argv in (
            ["repo", "--top", "0"],
            ["repo", "--commits", "-3"],
            ["repo", "--min-score", "-1"],
            ["repo", "--min-score", "nan"],
            ["repo", "--min-score", "inf"],
        ):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as ctx:
                with contextlib.redirect_stderr(io.StringIO()):
                    cli.main(argv)
            self.assertEqual(ctx.exception.code, 2)

    def test_parser_defaults_are_fresh(self):
        parser = cli.build_parser()
        first = parser.parse_args(["--include", "x"])
        second = parser.parse_args([])
        self.assertEqual(first.include, ["x"])
        self.assertEqual(second.include, None)
        self.assertEqual(second.exclude, None)
        third = parser.parse_args(["--include", "y"])
        self.assertEqual(third.include, ["y"])

    def test_empty_churn_table_returns_zero_with_guidance(self):
        output = io.StringIO()
        with mock.patch.object(cli, "repo_root", return_value=Path(".")):
            with mock.patch.object(cli, "collect_churn", return_value={}):
                with mock.patch.object(cli, "complexity_map", return_value={}):
                    with contextlib.redirect_stdout(output):
                        code = cli.main(["repo"])
        self.assertEqual(code, 0)
        self.assertIn("No hotspots found", output.getvalue())

    def test_repo_root_git_error_returns_one(self):
        code, out, err = self._run(["repo"], error=GitError("Why: bad\nFix: check"))
        self.assertEqual(code, 1)
        with mock.patch.object(cli, "repo_root", side_effect=GitError("Why: bad\nFix: check")):
            output = io.StringIO()
            errors = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = cli.main(["repo"])
            self.assertEqual(code, 1)
            self.assertIn("Why: bad", errors.getvalue())

    def test_file_arg_uses_parent_dir(self):
        seen = {}

        def fake_root(repo):
            seen["repo"] = repo
            return Path(".")

        with mock.patch.object(cli, "repo_root", side_effect=fake_root):
            with mock.patch.object(cli, "collect_churn", return_value={}):
                with mock.patch.object(cli, "complexity_map", return_value={}):
                    with contextlib.redirect_stdout(io.StringIO()):
                        cli.main([__file__])
        self.assertEqual(seen["repo"], Path(__file__).parent)

    def test_broken_pipe_does_not_raise(self):
        with mock.patch.object(cli, "repo_root", return_value=Path(".")):
            with mock.patch.object(cli, "collect_churn", return_value=_churn()):
                with mock.patch.object(cli, "complexity_map", return_value={"a": 1}):
                    with mock.patch("builtins.print", side_effect=BrokenPipeError(32, "Broken pipe")):
                        with contextlib.redirect_stdout(io.StringIO()):
                            code = cli.main(["repo"])
        self.assertEqual(code, 0)

    def test_broken_pipe_on_real_fd_redirects_to_devnull(self):
        read_fd, write_fd = os.pipe()
        stream = os.fdopen(write_fd, "w", encoding="utf-8")
        self.addCleanup(stream.close)
        self.addCleanup(os.close, read_fd)
        with mock.patch.object(cli, "repo_root", return_value=Path(".")):
            with mock.patch.object(cli, "collect_churn", return_value=_churn()):
                with mock.patch.object(cli, "complexity_map", return_value={"a": 1}):
                    with mock.patch("builtins.print", side_effect=BrokenPipeError(32, "Broken pipe")):
                        with contextlib.redirect_stdout(stream):
                            code = cli.main(["repo"])
        self.assertEqual(code, 0)
        # the fd survives: writes go to devnull instead of raising again
        stream.write("swallowed")
        stream.flush()

    def test_broken_pipe_does_not_close_stdout(self):
        output = io.StringIO()
        with mock.patch.object(cli, "repo_root", return_value=Path(".")):
            with mock.patch.object(cli, "collect_churn", return_value=_churn()):
                with mock.patch.object(cli, "complexity_map", return_value={"a": 1}):
                    with mock.patch("builtins.print", side_effect=BrokenPipeError(32, "Broken pipe")):
                        with contextlib.redirect_stdout(output):
                            code = cli.main(["repo"])
        self.assertEqual(code, 0)
        output.write("still usable")

    def test_main_runs_git_inside_budget_session(self):
        from driftwood import gitlog

        seen = {}

        def fake_root(repo):
            seen["deadline"] = gitlog.session_deadline()
            return Path(".")

        with mock.patch.object(cli, "repo_root", side_effect=fake_root):
            with mock.patch.object(cli, "collect_churn", return_value={}):
                with mock.patch.object(cli, "complexity_map", return_value={}):
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = cli.main(["repo"])
        self.assertEqual(code, 0)
        self.assertIsNotNone(seen["deadline"])
        self.assertIsNone(gitlog.session_deadline())

    def test_since_accepts_documented_forms(self):
        parser = cli.build_parser()
        for value in (
            "12.months.ago",
            "6 months ago",
            "1.week.ago",
            "2 hours ago",
            "2024-01-15",
            "2024-01-15 10:30",
            "2024-01-15T10:30:00+03:00",
            "@1730000000",
            "now",
            "today",
            "yesterday",
            "last monday",
            "monday",
        ):
            with self.subTest(value=value):
                self.assertEqual(parser.parse_args(["--since", value]).since, value)

    def test_since_rejects_approxidate_garbage(self):
        parser = cli.build_parser()
        for value in (
            "banana",
            "0",
            "1.unit.ago",
            "fortnight",
            "2024-13-45",
            "2024-01-15 25:00",
            "",
            "   ",
        ):
            with self.subTest(value=value), self.assertRaises(SystemExit) as ctx:
                parser.parse_args(["--since", value])
            self.assertEqual(ctx.exception.code, 2)

    def test_since_garbage_exits_two_before_git(self):
        errors = io.StringIO()
        with mock.patch.object(
            cli, "repo_root", side_effect=AssertionError("git must not be reached")
        ) as root_mock:
            with contextlib.redirect_stderr(errors), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["repo", "--since", "banana"])
        self.assertEqual(ctx.exception.code, 2)
        root_mock.assert_not_called()
        self.assertIn("invalid argument", errors.getvalue())

    def test_blank_since_returns_two_without_traceback(self):
        # argparse now rejects blank --since itself: SystemExit(2) with usage
        # guidance on stderr, before repo_root or git are ever reached.
        with mock.patch.object(
            cli, "repo_root", side_effect=AssertionError("git must not be reached")
        ):
            errors = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["repo", "--since", "   "])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("invalid argument", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
