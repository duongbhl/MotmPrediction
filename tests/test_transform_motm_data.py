import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.transform_motm_data import (  # noqa: E402
    QualityReport,
    add_features,
    clean_base_data,
    normalize_id,
    parse_match_date,
)


class TransformMotmDataTests(unittest.TestCase):
    def test_parse_match_date_supported_formats(self):
        self.assertEqual(str(parse_match_date("2025-02-15").date()), "2025-02-15")
        self.assertEqual(str(parse_match_date("Fri, 01-May-26").date()), "2026-05-01")
        self.assertEqual(str(parse_match_date(45300).date()), "2024-01-09")

    def test_normalize_id_removes_excel_decimal_suffix(self):
        self.assertEqual(normalize_id("1903415.0"), "1903415")
        self.assertEqual(normalize_id(4511.0), "4511")

    def test_clean_base_data_marks_invalid_numeric_values(self):
        raw = pd.DataFrame(
            [
                {
                    "match_id": "1.0",
                    "player_id": "10.0",
                    "match_date": "2025-02-15",
                    "is_man_of_match": 1,
                    "rating": 46363,
                    "pass_accuracy": 46112,
                    "minutes_played": -3,
                    "is_home": 1,
                    "is_first_eleven": 1,
                }
            ]
        )
        report = QualityReport()
        cleaned = clean_base_data(raw, report)

        self.assertTrue(np.isnan(cleaned.loc[0, "rating"]))
        self.assertTrue(np.isnan(cleaned.loc[0, "pass_accuracy"]))
        self.assertEqual(cleaned.loc[0, "minutes_played"], 0)
        self.assertEqual(report.invalid_rating_rows, 1)
        self.assertEqual(report.invalid_pass_accuracy_rows, 1)
        self.assertEqual(report.negative_minutes_rows, 1)

    def test_rolling_features_use_previous_matches_only(self):
        raw = pd.DataFrame(
            [
                {
                    "match_id": "1",
                    "player_id": "10",
                    "match_date": pd.Timestamp("2025-01-01"),
                    "rating": 6.0,
                    "goals": 1,
                    "assists": 0,
                    "shots_total": 2,
                    "key_passes": 1,
                    "tackles": 3,
                    "is_home": 1,
                    "home_score": 2,
                    "away_score": 1,
                    "shots_on_target": 1,
                    "minutes_played": 90,
                    "position": "FW",
                },
                {
                    "match_id": "2",
                    "player_id": "10",
                    "match_date": pd.Timestamp("2025-01-08"),
                    "rating": 8.0,
                    "goals": 0,
                    "assists": 1,
                    "shots_total": 1,
                    "key_passes": 2,
                    "tackles": 0,
                    "is_home": 0,
                    "home_score": 0,
                    "away_score": 1,
                    "shots_on_target": 1,
                    "minutes_played": 90,
                    "position": "FW",
                },
            ]
        )

        featured = add_features(raw)

        self.assertTrue(np.isnan(featured.loc[0, "rolling_rating_5"]))
        self.assertEqual(featured.loc[1, "rolling_rating_5"], 6.0)
        self.assertEqual(featured.loc[1, "rolling_goals_5"], 1.0)


if __name__ == "__main__":
    unittest.main()
