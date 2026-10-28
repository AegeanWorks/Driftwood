import tempfile
import unittest
from pathlib import Path

from driftwood.complexity import (
    complexity_map,
    file_complexity,
    generic_complexity,
    python_complexity,
)


class PythonComplexityTests(unittest.TestCase):
    def test_counts_decision_tokens(self):
        source = (
            "def f(x):\n"
            "    if x and y:\n"
            "        return 1\n"
            "    for item in x:\n"
            "        while item:\n"
            "            break\n"
            "    return 0\n"
        )
        self.assertEqual(python_complexity(source), 5)

    def test_syntax_error_falls_back_to_line_scan(self):
        source = "if x:\n  return 1\n"
        self.assertEqual(python_complexity(source), 2)

    def test_trivial_module_is_one(self):
        self.assertEqual(python_complexity("VALUE = 1\n"), 1)


class GenericComplexityTests(unittest.TestCase):
    def test_counts_branch_lines_across_languages(self):
        source = (
            "// comment if\n"
            "if (a) {\n"
            "  return 1;\n"
            "}\n"
            "while (a && b) {\n"
            "}\n"
        )
        self.assertEqual(generic_complexity(source), 3)

    def test_comment_and_blank_lines_are_skipped(self):
        self.assertEqual(generic_complexity("# if\n\n"), 1)


class FileComplexityTests(unittest.TestCase):
    def test_dispatches_python_and_generic_files(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            (root / "mod.py").write_text("if x:\n    pass\n", encoding="utf-8")
            (root / "app.js").write_text("if (x) {\n}\n", encoding="utf-8")
            (root / "notes.txt").write_text("plain\n", encoding="utf-8")
            self.assertEqual(file_complexity(root / "mod.py"), 2)
            self.assertEqual(file_complexity(root / "app.js"), 2)
            self.assertEqual(file_complexity(root / "notes.txt"), 1)

    def test_missing_file_and_map_skip_absent_paths(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            (root / "keep.py").write_text("pass\n", encoding="utf-8")
            self.assertEqual(file_complexity(root / "gone.py"), 0)
            self.assertEqual(
                complexity_map(root, ["keep.py", "gone.py"]), {"keep.py": 1}
            )


if __name__ == "__main__":
    unittest.main()
