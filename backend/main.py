"""
MOTM Predictor FastAPI backend.

Run from backend:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
PROCESSED_DATA = ROOT / "data" / "processed" / "motm_model_ready.csv"

MODEL_PATH = ARTIFACTS_DIR / "best_model.joblib"
PREPROCESSOR_PATH = ARTIFACTS_DIR / "preprocessor.joblib"
FEATURES_PATH = ARTIFACTS_DIR / "feature_columns.json"
META_PATH = ARTIFACTS_DIR / "best_model_meta.json"

ROLLING_SOURCE_COLUMNS = {
    "rolling_rating_5": "rating",
    "rolling_minutes_5": "minutes_played",
    "rolling_starts_5": "is_first_eleven",
    "rolling_goals_5": "goals",
    "rolling_assists_5": "assists",
    "rolling_shots_5": "shots_total",
    "rolling_shots_on_target_5": "shots_on_target",
    "rolling_key_passes_5": "key_passes",
    "rolling_pass_accuracy_5": "pass_accuracy",
    "rolling_tackles_5": "tackles",
    "rolling_interceptions_5": "interceptions",
    "rolling_clearances_5": "clearances",
    "rolling_aerial_won_5": "aerial_won",
    "rolling_dribbles_won_5": "dribbles_won",
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

TEAM_ALIASES = {
    "man utd": "Manchester United",
    "manchester united": "Manchester United",
    "man city": "Manchester City",
    "manchester city": "Manchester City",
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


class MatchData(BaseModel):
    home_team: str
    away_team: str
    prediction_date: date
    season: str | None = None
    players: list[PlayerStats]


def _json_number(value: Any) -> float | int | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if number.is_integer():
        return int(number)
    return round(number, 4)


def _normalize_match_probabilities(probabilities: np.ndarray) -> np.ndarray:
    """Convert independent binary scores into one-winner match probabilities."""
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-9, 1 - 1e-9)
    odds = clipped / (1 - clipped)
    total = odds.sum()
    if not np.isfinite(total) or total <= 0:
        return np.full(len(clipped), 1 / len(clipped))
    return odds / total


def _clean_position(position: str | None) -> str:
    return (position or "MC").strip() or "MC"


def _position_group(position: str | None) -> str:
    return POSITION_GROUP.get(_clean_position(position), "Other")


def _canonical_team(team: str) -> str:
    cleaned = team.strip()
    return TEAM_ALIASES.get(cleaned.casefold(), cleaned)


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

    try:
        model = joblib.load(MODEL_PATH)
        preprocessor = joblib.load(PREPROCESSOR_PATH)
    except (AttributeError, ImportError, ModuleNotFoundError, ValueError) as exc:
        raise RuntimeError(
            "Model artifacts are incompatible with the installed scikit-learn. "
            "Rebuild them with the same Python environment used by the backend: "
            "`python src/transform_motm_data.py --input PlayerCrawl.xlsx "
            "--out-dir data/processed --artifacts-dir artifacts` then "
            "`python src/train_models.py`."
        ) from exc

    return {
        "model": model,
        "preprocessor": preprocessor,
        "feature_columns": feature_meta["feature_columns"],
        "meta": meta,
    }


def _latest_season() -> str:
    values = history_df()["season"].dropna().astype(str)
    if values.empty:
        return "2025/2026"
    return sorted(values.unique())[-1]


def _history_before(prediction_date: date) -> pd.DataFrame:
    cutoff = pd.Timestamp(prediction_date)
    df = history_df()
    return df[df["match_date"] < cutoff]


def _season_before(prediction_date: date) -> str:
    rows = _history_before(prediction_date)
    if rows.empty:
        return _latest_season()
    latest_date = rows["match_date"].max()
    seasons = rows.loc[rows["match_date"] == latest_date, "season"].dropna().astype(str)
    return seasons.iloc[-1] if not seasons.empty else _latest_season()


def _player_history(player: PlayerStats, prediction_date: date) -> pd.DataFrame:
    df = _history_before(prediction_date)
    name_key = player.name.lower().strip()
    canonical_team = _canonical_team(player.team)
    team_matches = df["team"].astype(str).map(_canonical_team) == canonical_team
    rows = df[(df["name_key"] == name_key) & team_matches]
    if rows.empty:
        rows = df[df["name_key"] == name_key]
    return rows


def _recent_form(rows: pd.DataFrame) -> dict[str, Any]:
    if rows.empty:
        return {}

    recent = rows.sort_values(["match_date", "match_id"]).tail(5)
    defaults: dict[str, Any] = {}
    for col in [
        "rating",
        "goals",
        "assists",
        "shots_total",
        "key_passes",
        "tackles",
    ]:
        if col in recent:
            defaults[col] = _json_number(recent[col].mean(skipna=True))
    return defaults


def _feature_row(match: MatchData, player: PlayerStats) -> dict[str, Any]:
    rows = _player_history(player, match.prediction_date)
    recent = rows.sort_values(["match_date", "match_id"]).tail(5)

    is_home = int(player.is_home)

    row: dict[str, Any] = {
        "season": match.season or _season_before(match.prediction_date),
        "home_team": _canonical_team(match.home_team),
        "away_team": _canonical_team(match.away_team),
        "team": _canonical_team(player.team),
        "name": player.name,
        "is_home": is_home,
        "position": _clean_position(player.position),
        "is_first_eleven": int(player.is_first_eleven),
        "age": player.age,
        "position_group": _position_group(player.position),
    }

    for output_col, source_col in ROLLING_SOURCE_COLUMNS.items():
        row[output_col] = (
            float(recent[source_col].mean(skipna=True))
            if not recent.empty and source_col in recent
            else np.nan
        )
    row["rolling_motm_rate_10"] = (
        float(rows.sort_values(["match_date", "match_id"]).tail(10)["is_man_of_match"].mean())
        if not rows.empty
        else np.nan
    )

    return row


def _result_payload(
    player: PlayerStats, probability: float, feature_row: dict[str, Any]
) -> dict[str, Any]:
    return {
        "name": player.name,
        "team": player.team,
        "position": _clean_position(player.position),
        "probability": round(probability, 6),
        "score": round(probability * 100, 2),
        "recent_form": {
            "rating": _json_number(feature_row.get("rolling_rating_5")),
            "minutes": _json_number(feature_row.get("rolling_minutes_5")),
            "start_rate": _json_number(feature_row.get("rolling_starts_5")),
            "goals": _json_number(feature_row.get("rolling_goals_5")),
            "assists": _json_number(feature_row.get("rolling_assists_5")),
            "shots": _json_number(feature_row.get("rolling_shots_5")),
            "shots_on_target": _json_number(
                feature_row.get("rolling_shots_on_target_5")
            ),
            "key_passes": _json_number(feature_row.get("rolling_key_passes_5")),
            "pass_accuracy": _json_number(
                feature_row.get("rolling_pass_accuracy_5")
            ),
            "tackles": _json_number(feature_row.get("rolling_tackles_5")),
            "interceptions": _json_number(
                feature_row.get("rolling_interceptions_5")
            ),
            "clearances": _json_number(feature_row.get("rolling_clearances_5")),
            "aerial_won": _json_number(feature_row.get("rolling_aerial_won_5")),
            "dribbles_won": _json_number(
                feature_row.get("rolling_dribbles_won_5")
            ),
            "motm_rate": _json_number(feature_row.get("rolling_motm_rate_10")),
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
    teams = sorted({_canonical_team(team) for team in df["team"].dropna().astype(str)})
    return {"teams": teams}


@app.get("/api/players/{team}")
async def get_players(team: str, prediction_date: date | None = None):
    target_date = prediction_date or date.today()
    df = _history_before(target_date)
    canonical_team = _canonical_team(team)
    team_mask = df["team"].astype(str).map(_canonical_team) == canonical_team
    team_rows = df[team_mask]
    if team_rows.empty:
        return {"players": []}
    latest_season = sorted(team_rows["season"].dropna().astype(str).unique())[-1]
    rows = team_rows[team_rows["season"].astype(str) == latest_season]
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
                "age": _json_number(ordered["age"].dropna().iloc[-1])
                if "age" in ordered and not ordered["age"].dropna().empty
                else None,
                "recent_form": _recent_form(ordered),
            }
        )

    players.sort(key=lambda item: item["freq"], reverse=True)
    return {"players": players}


@app.post("/api/predict")
async def predict_motm(match: MatchData):
    eligible = match.players
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
    raw_probabilities = bundle["model"].predict_proba(transformed)[:, 1]
    probabilities = _normalize_match_probabilities(raw_probabilities)

    results = [
        _result_payload(player, float(probability), feature_row)
        for player, probability, feature_row in zip(
            eligible, probabilities, feature_rows, strict=False
        )
    ]
    results.sort(key=lambda item: item["probability"], reverse=True)

    return {
        "motm": results[0],
        "top_contenders": results[1:6],
        "all_players": results,
        "top_score": results[0]["score"],
        "model": {
            "name": bundle["meta"].get("model_name", "unknown"),
            "probability_metric": "match-normalized odds",
        },
        "match_info": {
            "home_team": match.home_team,
            "away_team": match.away_team,
            "season": match.season or _season_before(match.prediction_date),
            "prediction_date": match.prediction_date.isoformat(),
            "prediction_type": "pre-match",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
