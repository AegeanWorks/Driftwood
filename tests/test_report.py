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

    def test_generator_input_renders(self):
        gen = (item for item in SAMPLE)
        output = format_table(gen)
        self.assertIn("src/app.py", output)
        empty_gen = (item for item in [])
        self.assertIn("Why:", format_table(empty_gen))


class FormatJsonTests(unittest.TestCase):
    def test_payload_is_stable_and_parseable(self):
        payload = json.loads(format_json(SAMPLE))
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["hotspots"][0]["path"], "src/app.py")
        self.assertEqual(payload["hotspots"][0]["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
