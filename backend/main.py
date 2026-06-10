"""
MOTM Predictor — FastAPI Backend (API only)
Run:  uvicorn main:app --reload --port 8000
"""

import os
import numpy as np
import pandas as pd
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = FastAPI(title="MOTM Predictor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "motm_clean.xlsx")
df = pd.read_excel(DATA_PATH)
df["rating"]          = pd.to_numeric(df["rating"],          errors="coerce")
df["is_man_of_match"] = pd.to_numeric(df["is_man_of_match"], errors="coerce")

ml_model = None
try:
    import joblib
    ml_model = joblib.load(os.path.join(os.path.dirname(__file__), "motm_model.pkl"))
    print("✅  ML model loaded")
except Exception:
    print("ℹ️  No trained model — using scoring-based predictor")

# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────
class PlayerStats(BaseModel):
    name: str
    team: str
    position: str = "MC"
    is_home: int = 0
    is_first_eleven: int = 1
    minutes_played: float = 90.0
    rating: float = 7.0
    goals: int = 0
    assists: int = 0
    shots_total: int = 0
    shots_on_target: int = 0
    key_passes: int = 0
    passes_completed: int = 30
    passes_total: int = 40
    tackles: int = 0
    interceptions: int = 0
    clearances: int = 0
    dribbles_won: int = 0
    fouls_committed: int = 0


class MatchData(BaseModel):
    home_team: str
    away_team: str
    home_score: int = 0
    away_score: int = 0
    players: List[PlayerStats]


# ─────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────
GK_SET  = {"GK"}
DEF_SET = {"DC", "DL", "DR", "DLC", "DRC", "WBL", "WBR"}
MID_SET = {"DMC", "MC", "ML", "MR", "MLC", "MRC", "AMC", "AML", "AMR"}


def _pos_group(pos: str) -> str:
    p = pos.upper().strip()
    if p in GK_SET:  return "GK"
    if p in DEF_SET: return "DEF"
    if p in MID_SET: return "MID"
    return "FWD"


def _score_player(p: PlayerStats, score_margin: int) -> float:
    pos    = _pos_group(p.position)
    is_gk  = pos == "GK"
    is_def = pos == "DEF"
    is_mid = pos == "MID"

    score = (p.rating / 10.0) * 35.0
    score += min(p.goals,  4) * 6.25
    score += min(p.assists, 3) * 5.0
    score += min(p.shots_on_target, 6) * 0.83
    score += min(p.key_passes, 8) * 1.0

    if is_gk:
        score += min(p.clearances, 6) * 1.2
        score += min(p.tackles,    4) * 0.6
    elif is_def:
        score += min(p.tackles,       6)  * 0.9
        score += min(p.interceptions, 5)  * 0.8
        score += min(p.clearances,   10)  * 0.4
    elif is_mid:
        score += min(p.tackles,       5) * 0.6
        score += min(p.interceptions, 4) * 0.5
    else:
        score += min(p.dribbles_won, 5) * 0.5

    min_factor = min(p.minutes_played, 90) / 90.0
    score *= min_factor
    score -= p.fouls_committed * 0.25

    if not p.is_first_eleven:
        score *= 0.82

    if abs(score_margin) >= 2:
        winning_side = (p.is_home and score_margin > 0) or (not p.is_home and score_margin < 0)
        if winning_side:
            score *= 1.04

    player_rows = df[df["name"].str.lower() == p.name.lower()]
    if len(player_rows) >= 3:
        avg_rating = player_rows["rating"].mean(skipna=True)
        motm_rate  = player_rows["is_man_of_match"].mean(skipna=True)
        if not np.isnan(avg_rating):
            score += (avg_rating / 10.0) * 2.5
        if not np.isnan(motm_rate):
            score += motm_rate * 5.0

    return float(np.clip(score, 0, 100))


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────
@app.get("/api/teams")
async def get_teams():
    teams = sorted(
        set(df["home_team"].dropna().tolist() + df["away_team"].dropna().tolist())
    )
    return {"teams": teams}


@app.get("/api/players/{team}")
async def get_players(team: str):
    rows = df[df["team"] == team][["name", "position", "position_group"]]
    freq = rows.groupby("name").size().reset_index(name="freq")
    rows = (
        rows.drop_duplicates("name")
        .merge(freq, on="name")
        .sort_values("freq", ascending=False)
    )
    return {"players": rows[["name", "position", "position_group"]].to_dict("records")}


@app.post("/api/predict")
async def predict_motm(match: MatchData):
    score_margin = match.home_score - match.away_score
    results = []

    for p in match.players:
        if p.minutes_played < 20:
            continue
        raw = _score_player(p, score_margin)
        results.append({
            "name":     p.name,
            "team":     p.team,
            "position": p.position,
            "score":    round(raw, 2),
            "stats": {
                "rating":          p.rating,
                "goals":           p.goals,
                "assists":         p.assists,
                "shots_on_target": p.shots_on_target,
                "key_passes":      p.key_passes,
                "tackles":         p.tackles,
                "interceptions":   p.interceptions,
                "minutes_played":  p.minutes_played,
            },
        })

    if not results:
        return {"error": "No eligible players (min 20 minutes required)"}

    results.sort(key=lambda x: x["score"], reverse=True)
    return {
        "motm":           results[0],
        "top_contenders": results[1:6],
        "all_players":    results,
        "match_info": {
            "home_team": match.home_team,
            "away_team": match.away_team,
            "score":     f"{match.home_score} \u2013 {match.away_score}",
        },
        "top_score": results[0]["score"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
