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

    def test_invalid_numeric_flags_exit_two(self):
        for argv in (["repo", "--top", "0"], ["repo", "--commits", "-3"], ["repo", "--min-score", "-1"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as ctx:
                with contextlib.redirect_stderr(io.StringIO()):
                    cli.main(argv)
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
