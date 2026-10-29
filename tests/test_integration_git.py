import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from driftwood.gitlog import collect_churn, repo_root

GIT = shutil.which("git")


def _git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


@unittest.skipIf(GIT is None, "git is not installed on this machine")
class RealRepositoryTests(unittest.TestCase):
    def setUp(self):
        raw_dir = tempfile.mkdtemp(prefix="driftwood-it-")
        self.addCleanup(shutil.rmtree, raw_dir, True)
        self.repo = Path(raw_dir)
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "test@example.com")
        _git(self.repo, "config", "user.name", "Driftwood Test")
        _git(self.repo, "config", "commit.gpgsign", "false")
        _git(self.repo, "config", "core.quotePath", "true")

    def _commit(self, message):
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", message)

    def test_collect_churn_reads_real_history(self):
        module = self.repo / "src" / "app.py"
        module.parent.mkdir(parents=True)
        module.write_text("value = 1\n", encoding="utf-8")
        (self.repo / "notes.md").write_text("hello\n", encoding="utf-8")
        self._commit("feat: add initial files")

        module.write_text("value = 1\nvalue = 2\nvalue = 3\n", encoding="utf-8")
        (self.repo / "notes.md").write_text("hello\nworld\n", encoding="utf-8")
        self._commit("feat: expand modules")

        churn = collect_churn(self.repo)
        self.assertGreaterEqual(churn["src/app.py"].commits, 2)
        self.assertGreaterEqual(churn["src/app.py"].churn, 2)
        self.assertEqual(churn["notes.md"].commits, 2)

        limited = collect_churn(self.repo, max_commits=1)
        self.assertTrue(limited)
        self.assertLessEqual(max(item.commits for item in limited.values()), 1)

    def test_repo_root_resolves_subdirectory(self):
        nested = self.repo / "pkg" / "deep"
        nested.mkdir(parents=True)
        (nested / "mod.py").write_text("x = 1\n", encoding="utf-8")
        self._commit("chore: nested module")
        self.assertEqual(repo_root(nested).resolve(), self.repo.resolve())

    def test_rename_moves_churn_to_new_path(self):
        original = self.repo / "legacy.py"
        original.write_text("x = 1\n", encoding="utf-8")
        self._commit("feat: add legacy module")
        _git(self.repo, "mv", "legacy.py", "modern.py")
        self._commit("refactor: rename module")

        churn = collect_churn(self.repo, max_commits=1)
        self.assertIn("modern.py", churn)
        self.assertNotIn("legacy.py", churn)

    def test_non_ascii_path_is_decoded(self):
        module = self.repo / "src" / "café.py"
        module.parent.mkdir(parents=True)
        module.write_text("value = 1\n", encoding="utf-8")
        self._commit("feat: add non-ascii module")

        churn = collect_churn(self.repo, max_commits=1)
        self.assertIn("src/café.py", churn)


if __name__ == "__main__":
    unittest.main()
