import unittest
from pathlib import Path

from driftwood.gitlog import (
    COMMIT_MARKER,
    FileChurn,
    collect_churn,
    normalize_path,
    parse_numstat,
    repo_root,
)


class ParseNumstatTests(unittest.TestCase):
    def test_aggregates_changes_across_commits(self):
        text = "\n".join(
            [
                f"{COMMIT_MARKER}aaa",
                "",
                "3\t1\tsrc/app.py",
                "10\t0\tdocs/readme.md",
                f"{COMMIT_MARKER}bbb",
                "",
                "2\t5\tsrc/app.py",
            ]
        )
        result = parse_numstat(text)
        self.assertEqual(
            result["src/app.py"], FileChurn(commits=2, added=5, deleted=6)
        )
        self.assertEqual(
            result["docs/readme.md"], FileChurn(commits=1, added=10, deleted=0)
        )

    def test_ignores_binary_and_malformed_lines(self):
        text = "\n".join(
            [
                f"{COMMIT_MARKER}aaa",
                "-\t-\tlogo.png",
                "nonsense",
                "4\t4\tsrc/app.py",
            ]
        )
        result = parse_numstat(text)
        self.assertEqual(list(result), ["src/app.py"])

    def test_renamed_paths_resolve_to_new_location(self):
        text = "\n".join(
            [
                f"{COMMIT_MARKER}aaa",
                "1\t1\tsrc/{old => new}/mod.py",
                "2\t0\tlegacy.py => modern.py",
            ]
        )
        result = parse_numstat(text)
        self.assertIn("src/new/mod.py", result)
        self.assertIn("modern.py", result)

    def test_empty_input_is_empty_mapping(self):
        self.assertEqual(parse_numstat(""), {})

    def test_non_numeric_counts_are_skipped(self):
        text = "\n".join(
            [
                f"{COMMIT_MARKER}aaa",
                "abc\tdef\tsrc/app.py",
                "3\t1\tsrc/ok.py",
            ]
        )
        result = parse_numstat(text)
        self.assertEqual(list(result), ["src/ok.py"])


class NormalizePathTests(unittest.TestCase):
    def test_plain_path_keeps_forward_slashes(self):
        self.assertEqual(normalize_path("a\\b\\c.py"), "a/b/c.py")

    def test_quoted_path_is_unquoted(self):
        self.assertEqual(normalize_path('"src/a b.py"'), "src/a b.py")

    def test_quoted_non_ascii_path_is_decoded(self):
        self.assertEqual(normalize_path('"src/caf\\303\\251.py"'), "src/café.py")

    def test_quoted_backslash_is_not_a_separator(self):
        self.assertEqual(normalize_path('"src\\\\mod.py"'), "src\\mod.py")


class CollectChurnTests(unittest.TestCase):
    def test_passes_filters_and_reuses_parser(self):
        calls = []

        def runner(repo, args):
            calls.append((repo, args))
            return f"{COMMIT_MARKER}abc\n1\t2\tx.py"

        churn = collect_churn(
            Path("repo"), since="2.weeks.ago", max_commits=50, runner=runner
        )
        self.assertEqual(churn["x.py"].churn, 3)
        _, args = calls[0]
        self.assertIn("--since=2.weeks.ago", args)
        self.assertIn("--max-count=50", args)
        self.assertIn("--numstat", args)

    def test_rejects_non_positive_commit_limit(self):
        with self.assertRaises(ValueError):
            collect_churn(Path("repo"), max_commits=0, runner=lambda *_: "")
        with self.assertRaises(TypeError):
            collect_churn(Path("repo"), max_commits="50", runner=lambda *_: "")
        with self.assertRaises((TypeError, ValueError)):
            collect_churn(Path("repo"), max_commits=True, runner=lambda *_: "")
        with self.assertRaises((TypeError, ValueError)):
            collect_churn(Path("repo"), max_commits=2.5, runner=lambda *_: "")

    def test_rejects_blank_since(self):
        with self.assertRaises(ValueError):
            collect_churn(Path("repo"), since="   ", runner=lambda *_: "")

    def test_negative_counts_are_skipped(self):
        text = "\n".join([f"{COMMIT_MARKER}a", "-5\t3\ta.py", "3\t-1\tb.py"])
        self.assertEqual(parse_numstat(text), {})

    def test_extra_tab_path_joined(self):
        text = "\n".join([f"{COMMIT_MARKER}a", "1\t1\ta\tb.py"])
        result = parse_numstat(text)
        self.assertIn("a\tb.py", result)

    def test_repo_root_strips_whitespace(self):
        root = repo_root(Path("repo"), runner=lambda *_: "/tmp/project\n")
        self.assertEqual(root, Path("/tmp/project"))

    def test_repo_root_rejects_empty_output(self):
        from driftwood.gitlog import GitError

        with self.assertRaises(GitError):
            repo_root(Path("repo"), runner=lambda *_: "\n")
        with self.assertRaises(GitError):
            repo_root(Path("repo"), runner=lambda *_: "  \n")

    def test_repo_root_preserves_trailing_space(self):
        root = repo_root(Path("repo"), runner=lambda *_: "/tmp/proj \n")
        self.assertEqual(root, Path("/tmp/proj "))


if __name__ == "__main__":
    unittest.main()
