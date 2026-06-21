import unittest
from datetime import date
from unittest.mock import patch

import numpy as np

from backend.main import (
    MatchData,
    PlayerStats,
    _feature_row,
    _normalize_match_probabilities,
    get_players,
)


class BackendProbabilityTests(unittest.TestCase):
    def test_match_probabilities_sum_to_one_and_preserve_ranking(self):
        raw = np.array([0.2, 0.8, 0.4])

        normalized = _normalize_match_probabilities(raw)

        self.assertAlmostEqual(float(normalized.sum()), 1.0)
        self.assertEqual(normalized.argsort().tolist(), raw.argsort().tolist())

    def test_equal_scores_receive_equal_probability(self):
        normalized = _normalize_match_probabilities(np.array([0.5, 0.5]))

        np.testing.assert_allclose(normalized, np.array([0.5, 0.5]))

    def test_prediction_contract_does_not_accept_match_stats_as_features(self):
        match = MatchData(
            home_team="Arsenal",
            away_team="Chelsea",
            prediction_date=date(2026, 6, 14),
            players=[
                PlayerStats(
                    name="Unknown Player",
                    team="Arsenal",
                    position="FW",
                    is_home=1,
                )
            ],
        )

        row = _feature_row(match, match.players[0])

        self.assertNotIn("home_score", row)
        self.assertNotIn("goals", row)
        self.assertNotIn("rating", row)
        self.assertIn("rolling_rating_5", row)

    def test_result_payload_exposes_all_rolling_model_indicators(self):
        from backend.main import _result_payload

        player = PlayerStats(name="Player", team="Team", position="FW")
        feature_row = {
            "rolling_rating_5": 7.2,
            "rolling_minutes_5": 80,
            "rolling_starts_5": 0.8,
            "rolling_goals_5": 0.4,
            "rolling_assists_5": 0.2,
            "rolling_shots_5": 3,
            "rolling_shots_on_target_5": 1.5,
            "rolling_key_passes_5": 2,
            "rolling_pass_accuracy_5": 84,
            "rolling_tackles_5": 1,
            "rolling_interceptions_5": 0.5,
            "rolling_clearances_5": 0.4,
            "rolling_aerial_won_5": 1.2,
            "rolling_dribbles_won_5": 1.1,
            "rolling_motm_rate_10": 0.1,
        }

        payload = _result_payload(player, 0.25, feature_row)

        self.assertEqual(len(payload["recent_form"]), 15)
        self.assertEqual(payload["recent_form"]["pass_accuracy"], 84)
        self.assertEqual(payload["recent_form"]["motm_rate"], 0.1)

    def test_team_roster_uses_latest_season_only(self):
        import asyncio
        import pandas as pd

        frame = pd.DataFrame(
            [
                {
                    "season": "2024/2025", "team": "Team", "name": "Old Player",
                    "position": "FW", "match_date": pd.Timestamp("2025-01-01"), "match_id": "1",
                    "age": 30, "rating": 7, "goals": 0, "assists": 0,
                    "shots_total": 1, "key_passes": 0, "tackles": 0,
                },
                {
                    "season": "2025/2026", "team": "Team", "name": "Current Player",
                    "position": "FW", "match_date": pd.Timestamp("2026-01-01"), "match_id": "2",
                    "age": 25, "rating": 7, "goals": 0, "assists": 0,
                    "shots_total": 1, "key_passes": 0, "tackles": 0,
                },
            ]
        )

        with patch("backend.main.history_df", return_value=frame), patch(
            "backend.main._latest_season", return_value="2025/2026"
        ):
            result = asyncio.run(get_players("Team", date(2026, 6, 14)))

        self.assertEqual([player["name"] for player in result["players"]], ["Current Player"])

    def test_player_history_excludes_matches_on_or_after_prediction_date(self):
        import pandas as pd
        from backend.main import _player_history

        frame = pd.DataFrame(
            [
                {
                    "name_key": "player", "team_key": "team",
                    "team": "Team",
                    "match_date": pd.Timestamp("2025-01-01"), "match_id": "1",
                },
                {
                    "name_key": "player", "team_key": "team",
                    "team": "Team",
                    "match_date": pd.Timestamp("2025-02-01"), "match_id": "2",
                },
                {
                    "name_key": "player", "team_key": "team",
                    "team": "Team",
                    "match_date": pd.Timestamp("2025-03-01"), "match_id": "3",
                },
            ]
        )
        player = PlayerStats(name="Player", team="Team")

        with patch("backend.main.history_df", return_value=frame):
            rows = _player_history(player, date(2025, 2, 1))

        self.assertEqual(rows["match_id"].tolist(), ["1"])


if __name__ == "__main__":
    unittest.main()
