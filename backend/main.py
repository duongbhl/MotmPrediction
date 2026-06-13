"""
MOTM Predictor FastAPI backend.

Run from backend:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
PROCESSED_DATA = ROOT / "data" / "processed" / "motm_model_ready.csv"

MODEL_PATH = ARTIFACTS_DIR / "best_model.joblib"
PREPROCESSOR_PATH = ARTIFACTS_DIR / "preprocessor.joblib"
FEATURES_PATH = ARTIFACTS_DIR / "feature_columns.json"
META_PATH = ARTIFACTS_DIR / "best_model_meta.json"

ROLLING_SOURCE_COLUMNS = {
    "rolling_rating_5": "rating",
    "rolling_goals_5": "goals",
    "rolling_assists_5": "assists",
    "rolling_shots_5": "shots_total",
    "rolling_key_passes_5": "key_passes",
    "rolling_tackles_5": "tackles",
}

POSITION_GROUP = {
    "GK": "GK",
    "DC": "DEF",
    "DR": "DEF",
    "DL": "DEF",
    "DLC": "DEF",
    "DRC": "DEF",
    "WBL": "DEF",
    "WBR": "DEF",
    "DMC": "MID",
    "DMR": "MID",
    "DML": "MID",
    "MC": "MID",
    "MR": "MID",
    "ML": "MID",
    "MLC": "MID",
    "MRC": "MID",
    "AMC": "ATT",
    "AMR": "ATT",
    "AML": "ATT",
    "FW": "ATT",
    "FWR": "ATT",
    "FWL": "ATT",
    "ST": "ATT",
    "Sub": "Sub",
}


app = FastAPI(title="MOTM Predictor API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlayerStats(BaseModel):
    name: str
    team: str
    position: str = "MC"
    is_home: int = 0
    is_first_eleven: int = 1
    age: float | None = None
    minutes_played: float = 90.0
    rating: float | None = None
    goals: float = 0
    assists: float = 0
    shots_total: float = 0
    shots_on_target: float = 0
    key_passes: float = 0
    passes_completed: float = 30
    passes_total: float = 40
    pass_accuracy: float | None = None
    tackles: float = 0
    interceptions: float = 0
    clearances: float = 0
    aerial_won: float = 0
    dribbles_won: float = 0
    fouls_committed: float = 0


class MatchData(BaseModel):
    home_team: str
    away_team: str
    home_score: int = Field(default=0, ge=0)
    away_score: int = Field(default=0, ge=0)
    season: str | None = None
    players: list[PlayerStats]


def _json_number(value: Any) -> float | int | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if number.is_integer():
        return int(number)
    return round(number, 4)


def _clean_position(position: str | None) -> str:
    return (position or "MC").strip() or "MC"


def _position_group(position: str | None) -> str:
    return POSITION_GROUP.get(_clean_position(position), "Other")


@lru_cache(maxsize=1)
def history_df() -> pd.DataFrame:
    if not PROCESSED_DATA.exists():
        raise RuntimeError(f"Processed data not found: {PROCESSED_DATA}")

    df = pd.read_csv(PROCESSED_DATA, low_memory=False)
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df["name_key"] = df["name"].astype(str).str.lower().str.strip()
    df["team_key"] = df["team"].astype(str).str.lower().str.strip()
    return df.sort_values(["match_date", "match_id"])


@lru_cache(maxsize=1)
def model_bundle() -> dict[str, Any]:
    missing = [
        str(path.relative_to(ROOT))
        for path in (MODEL_PATH, PREPROCESSOR_PATH, FEATURES_PATH)
        if not path.exists()
    ]
    if missing:
        raise RuntimeError(
            "Missing model artifacts: "
            + ", ".join(missing)
            + ". Run `venv/bin/python src/train_models.py` first."
        )

    with FEATURES_PATH.open(encoding="utf-8") as f:
        feature_meta = json.load(f)

    meta = {}
    if META_PATH.exists():
        with META_PATH.open(encoding="utf-8") as f:
            meta = json.load(f)

    return {
        "model": joblib.load(MODEL_PATH),
        "preprocessor": joblib.load(PREPROCESSOR_PATH),
        "feature_columns": feature_meta["feature_columns"],
        "meta": meta,
    }


def _latest_season() -> str:
    values = history_df()["season"].dropna().astype(str)
    if values.empty:
        return "2025/2026"
    return sorted(values.unique())[-1]


def _player_history(player: PlayerStats) -> pd.DataFrame:
    df = history_df()
    name_key = player.name.lower().strip()
    team_key = player.team.lower().strip()
    rows = df[(df["name_key"] == name_key) & (df["team_key"] == team_key)]
    if rows.empty:
        rows = df[df["name_key"] == name_key]
    return rows


def _recent_defaults(rows: pd.DataFrame) -> dict[str, Any]:
    if rows.empty:
        return {}

    recent = rows.sort_values(["match_date", "match_id"]).tail(5)
    defaults: dict[str, Any] = {}
    for col in [
        "age",
        "minutes_played",
        "rating",
        "goals",
        "assists",
        "shots_total",
        "shots_on_target",
        "key_passes",
        "passes_completed",
        "passes_total",
        "pass_accuracy",
        "tackles",
        "interceptions",
        "clearances",
        "aerial_won",
        "dribbles_won",
        "fouls_committed",
    ]:
        if col in recent:
            defaults[col] = _json_number(recent[col].mean(skipna=True))
    return defaults


def _feature_row(match: MatchData, player: PlayerStats) -> dict[str, Any]:
    rows = _player_history(player)
    recent = rows.sort_values(["match_date", "match_id"]).tail(5)

    passes_total = float(player.passes_total or 0)
    pass_accuracy = player.pass_accuracy
    if pass_accuracy is None:
        pass_accuracy = (
            (float(player.passes_completed) / passes_total) * 100
            if passes_total > 0
            else 0
        )

    is_home = int(player.is_home)
    score_margin = (
        match.home_score - match.away_score
        if is_home == 1
        else match.away_score - match.home_score
    )

    row: dict[str, Any] = {
        "season": match.season or _latest_season(),
        "home_team": match.home_team,
        "away_team": match.away_team,
        "home_score": match.home_score,
        "away_score": match.away_score,
        "team": player.team,
        "is_home": is_home,
        "position": _clean_position(player.position),
        "is_first_eleven": int(player.is_first_eleven),
        "age": player.age,
        "minutes_played": player.minutes_played,
        "goals": player.goals,
        "assists": player.assists,
        "shots_total": player.shots_total,
        "shots_on_target": player.shots_on_target,
        "key_passes": player.key_passes,
        "passes_completed": player.passes_completed,
        "passes_total": passes_total,
        "pass_accuracy": pass_accuracy,
        "tackles": player.tackles,
        "interceptions": player.interceptions,
        "clearances": player.clearances,
        "aerial_won": player.aerial_won,
        "dribbles_won": player.dribbles_won,
        "fouls_committed": player.fouls_committed,
        "position_group": _position_group(player.position),
        "score_margin": score_margin,
        "goal_involvement": player.goals + player.assists,
        "shot_accuracy": (
            player.shots_on_target / player.shots_total
            if player.shots_total > 0
            else 0.0
        ),
        "minutes_ratio": min(max(player.minutes_played / 90.0, 0), 1.3),
    }

    for output_col, source_col in ROLLING_SOURCE_COLUMNS.items():
        row[output_col] = (
            float(recent[source_col].mean(skipna=True))
            if not recent.empty and source_col in recent
            else np.nan
        )

    return row


def _result_payload(player: PlayerStats, probability: float) -> dict[str, Any]:
    return {
        "name": player.name,
        "team": player.team,
        "position": _clean_position(player.position),
        "probability": round(probability, 6),
        "score": round(probability * 100, 2),
        "stats": {
            "rating": _json_number(player.rating),
            "goals": _json_number(player.goals),
            "assists": _json_number(player.assists),
            "shots_on_target": _json_number(player.shots_on_target),
            "key_passes": _json_number(player.key_passes),
            "tackles": _json_number(player.tackles),
            "interceptions": _json_number(player.interceptions),
            "minutes_played": _json_number(player.minutes_played),
        },
    }


@app.get("/api/health")
async def health():
    try:
        bundle = model_bundle()
        return {
            "ok": True,
            "model_loaded": True,
            "model_name": bundle["meta"].get("model_name"),
        }
    except RuntimeError as exc:
        return {"ok": False, "model_loaded": False, "error": str(exc)}


@app.get("/api/model-info")
async def model_info():
    try:
        bundle = model_bundle()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "model_name": bundle["meta"].get("model_name", "unknown"),
        "metrics": bundle["meta"],
        "feature_count": len(bundle["feature_columns"]),
    }


@app.get("/api/teams")
async def get_teams():
    df = history_df()
    teams = sorted(df["team"].dropna().astype(str).unique().tolist())
    return {"teams": teams}


@app.get("/api/players/{team}")
async def get_players(team: str):
    df = history_df()
    rows = df[df["team"].astype(str).str.casefold() == team.casefold()]
    if rows.empty:
        return {"players": []}

    players = []
    for name, group in rows.groupby("name", sort=False):
        ordered = group.sort_values(["match_date", "match_id"])
        latest = ordered.iloc[-1]
        position_values = ordered["position"].dropna().astype(str)
        position = (
            position_values[position_values != "Sub"].iloc[-1]
            if not position_values[position_values != "Sub"].empty
            else str(latest.get("position") or "MC")
        )
        players.append(
            {
                "name": name,
                "position": position,
                "position_group": _position_group(position),
                "freq": int(len(group)),
                "default_stats": _recent_defaults(ordered),
            }
        )

    players.sort(key=lambda item: item["freq"], reverse=True)
    return {"players": players}


@app.post("/api/predict")
async def predict_motm(match: MatchData):
    eligible = [p for p in match.players if p.minutes_played >= 1]
    if not eligible:
        raise HTTPException(status_code=400, detail="No eligible players")

    try:
        bundle = model_bundle()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    feature_rows = [_feature_row(match, player) for player in eligible]
    feature_df = pd.DataFrame(feature_rows)
    feature_df = feature_df.reindex(columns=bundle["feature_columns"])

    transformed = bundle["preprocessor"].transform(feature_df)
    probabilities = bundle["model"].predict_proba(transformed)[:, 1]

    results = [
        _result_payload(player, float(probability))
        for player, probability in zip(eligible, probabilities, strict=False)
    ]
    results.sort(key=lambda item: item["probability"], reverse=True)

    return {
        "motm": results[0],
        "top_contenders": results[1:6],
        "all_players": results,
        "top_score": results[0]["score"],
        "model": {
            "name": bundle["meta"].get("model_name", "unknown"),
            "probability_metric": "predict_proba[:, 1]",
        },
        "match_info": {
            "home_team": match.home_team,
            "away_team": match.away_team,
            "score": f"{match.home_score} - {match.away_score}",
            "season": match.season or _latest_season(),
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
