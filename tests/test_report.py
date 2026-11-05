import json
import unittest

from driftwood.report import format_json, format_table
from driftwood.scoring import Hotspot

SAMPLE = [
    Hotspot("src/app.py", commits=3, added=10, deleted=5, churn=15, complexity=4, score=1.0),
    Hotspot("docs/readme.md", commits=1, added=2, deleted=0, churn=2, complexity=1, score=0.2),
]


class FormatTableTests(unittest.TestCase):
    def test_header_and_rows(self):
        output = format_table(SAMPLE)
        lines = output.splitlines()
        self.assertIn("Score", lines[0])
        self.assertIn("File", lines[0])
        self.assertIn("src/app.py", lines[2])
        self.assertIn("1.000", lines[2])

    def test_empty_report_explains_why_and_fix(self):
        output = format_table([])
        self.assertIn("Why:", output)
        self.assertIn("Fix:", output)

    def test_embedded_newline_does_not_add_row(self):
        evil = Hotspot("a\nb.py", commits=1, added=1, deleted=0, churn=1, complexity=1, score=0.5)
        self.assertEqual(len(format_table([evil]).splitlines()), 3)

    def test_all_control_chars_sanitized(self):
        evil = Hotspot(
            "a\x00b\x07c\x1fv\x0bw.py",
            commits=1, added=1, deleted=0, churn=1, complexity=1, score=0.5,
        )
        out = format_table([evil])
        self.assertEqual(len(out.splitlines()), 3)
        for bad in ("\x00", "\x07", "\x1f", "\x0b"):
            self.assertNotIn(bad, out)
        self.assertIn("a?b?c?v?w.py", out)

    def test_unicode_line_separators_sanitized(self):
        evil = Hotspot(
            "a\u2028b\u2029c\x85.py",
            commits=1, added=1, deleted=0, churn=1, complexity=1, score=0.5,
        )
        out = format_table([evil])
        self.assertEqual(len(out.splitlines()), 3)
        self.assertIn("a?b?c?.py", out)

    def test_generator_input_renders(self):
        gen = (item for item in SAMPLE)
        output = format_table(gen)
        self.assertIn("src/app.py", output)
        empty_gen = (item for item in [])
        self.assertIn("Why:", format_table(empty_gen))

    def test_long_path_truncated_with_ellipsis(self):
        from driftwood.report import MAX_TABLE_PATH

        long_path = "a/" * 80 + "file.py"
        evil = Hotspot(long_path, commits=1, added=1, deleted=0, churn=1, complexity=1, score=0.5)
        lines = format_table([evil]).splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn("...", lines[2])
        self.assertLessEqual(len(lines[2].split("  ")[-1]), MAX_TABLE_PATH + 3)

    def test_json_preserves_unicode_and_rejects_nan(self):
        payload = json.loads(format_json([Hotspot("日本.py", 1, 1, 0, 1, 1, 0.5)]))
        self.assertEqual(payload["hotspots"][0]["path"], "日本.py")
        raw = format_json([Hotspot("日本.py", 1, 1, 0, 1, 1, 0.5)])
        self.assertIn("日本.py", raw)
        with self.assertRaises(ValueError):
            format_json([Hotspot("a.py", 1, 1, 0, 1, 1, float("nan"))])


class FormatJsonTests(unittest.TestCase):
    def test_payload_is_stable_and_parseable(self):
        payload = json.loads(format_json(SAMPLE))
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["hotspots"][0]["path"], "src/app.py")
        self.assertEqual(payload["hotspots"][0]["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
