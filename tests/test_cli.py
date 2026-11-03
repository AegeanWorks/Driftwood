import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest import mock

from driftwood import cli
from driftwood.gitlog import FileChurn, GitError


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
        with mock.patch.object(cli, "repo_root", return_value=Path(".")):
            with mock.patch.object(cli, "collect_churn", return_value={}):
                with mock.patch.object(cli, "complexity_map", return_value={}):
                    code, out, _ = self._run(["repo"], churn={})
                    # _run mocks collect_churn with default churn; call directly for empty
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
                        code = cli.main(["repo"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
