import unittest

from driftwood.gitlog import FileChurn
from driftwood.scoring import normalize, rank_hotspots


def _churn(churn, commits=1, added=None, deleted=0):
    added = churn if added is None else added
    return FileChurn(commits=commits, added=added, deleted=deleted)


class NormalizeTests(unittest.TestCase):
    def test_scales_to_unit_interval(self):
        self.assertEqual(
            normalize({"a": 1.0, "b": 3.0, "c": 5.0}),
            {"a": 0.0, "b": 0.5, "c": 1.0},
        )

    def test_flat_positive_values_saturate_and_zeros_stay_zero(self):
        self.assertEqual(normalize({"a": 4.0, "b": 4.0, "c": 0.0}), {"a": 1.0, "b": 1.0, "c": 0.0})

    def test_empty_mapping(self):
        self.assertEqual(normalize({}), {})


class RankHotspotsTests(unittest.TestCase):
    def test_blends_normalized_metrics(self):
        churn = {"hot.py": _churn(100), "cold.py": _churn(1)}
        complexity = {"hot.py": 5, "cold.py": 50}
        ranked = rank_hotspots(churn, complexity, top=2)
        self.assertEqual([item.path for item in ranked], ["hot.py", "cold.py"])
        self.assertAlmostEqual(ranked[0].score, 0.6)
        self.assertAlmostEqual(ranked[1].score, 0.4)

    def test_missing_complexity_counts_as_zero(self):
        ranked = rank_hotspots({"a.py": _churn(10)}, {})
        self.assertEqual(ranked[0].complexity, 0)
        self.assertAlmostEqual(ranked[0].score, 0.6)

    def test_single_churned_file_is_not_scored_zero(self):
        ranked = rank_hotspots({"only.py": _churn(17)}, {"only.py": 3})
        self.assertEqual(len(ranked), 1)
        self.assertAlmostEqual(ranked[0].score, 1.0)

    def test_top_limits_rows_and_is_deterministic(self):
        churn = {"b.py": _churn(5), "a.py": _churn(5), "c.py": _churn(9)}
        ranked = rank_hotspots(churn, {}, top=3)
        self.assertEqual([item.path for item in ranked], ["c.py", "a.py", "b.py"])

    def test_empty_churn_returns_empty(self):
        self.assertEqual(rank_hotspots({}, {"a": 3}), [])

    def test_negative_weights_and_bad_top_are_rejected(self):
        with self.assertRaises(ValueError):
            rank_hotspots({"a": _churn(1)}, {}, churn_weight=-1)
        with self.assertRaises(ValueError):
            rank_hotspots({"a": _churn(1)}, {}, top=0)


if __name__ == "__main__":
    unittest.main()
