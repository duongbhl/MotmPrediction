"""Transform WhoScored player data into model-ready MOTM datasets.

This script intentionally uses PlayerCrawl.xlsx as the source of truth and
does not consume previously normalized/cleaned Excel outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


NUMERIC_COLUMNS = [
    "home_score",
    "away_score",
    "is_home",
    "is_first_eleven",
    "is_man_of_match",
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
]

TEXT_COLUMNS = [
    "season",
    "home_team",
    "away_team",
    "name",
    "team",
    "position",
]

ID_COLUMNS = ["match_id", "player_id"]

ZERO_FILL_STAT_COLUMNS = [
    "goals",
    "assists",
    "shots_total",
    "shots_on_target",
    "key_passes",
    "passes_completed",
    "passes_total",
    "tackles",
    "interceptions",
    "clearances",
    "aerial_won",
    "dribbles_won",
    "fouls_committed",
]

POSITION_GROUP = {
    "GK": "GK",
    "DC": "DEF",
    "DR": "DEF",
    "DL": "DEF",
    "DMC": "MID",
    "DMR": "MID",
    "DML": "MID",
    "MC": "MID",
    "MR": "MID",
    "ML": "MID",
    "AMC": "ATT",
    "AMR": "ATT",
    "AML": "ATT",
    "FW": "ATT",
    "FWR": "ATT",
    "FWL": "ATT",
    "Sub": "Sub",
}

CURRENT_MATCH_EXCLUDE_COLUMNS = {
    "match_id",
    "match_date",
    "player_id",
    "name",
    "is_man_of_match",
    "rating",
    "source_sheet",
}


@dataclass
class QualityReport:
    raw_rows: int = 0
    raw_matches: int = 0
    rows_after_required_fields: int = 0
    rows_after_eligibility: int = 0
    rows_after_dedupe: int = 0
    final_rows: int = 0
    final_matches: int = 0
    invalid_rating_rows: int = 0
    invalid_pass_accuracy_rows: int = 0
    negative_minutes_rows: int = 0
    invalid_binary_rows: dict[str, int] | None = None
    dropped_matches_zero_motm: int = 0
    dropped_matches_multi_motm: int = 0
    dropped_rows_bad_match_target: int = 0
    train_rows: int = 0
    validation_rows: int = 0
    test_rows: int = 0
    train_matches: int = 0
    validation_matches: int = 0
    test_matches: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build model-ready MOTM datasets from PlayerCrawl.xlsx."
    )
    parser.add_argument("--input", default="PlayerCrawl.xlsx", help="Input Excel file.")
    parser.add_argument(
        "--out-dir",
        default="data/processed",
        help="Directory for processed CSV/report outputs.",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts",
        help="Directory for fitted preprocessors and metadata.",
    )
    parser.add_argument(
        "--min-minutes",
        type=float,
        default=1.0,
        help="Minimum minutes_played required for supervised rows.",
    )
    return parser.parse_args()


def normalize_id(value: object) -> str | pd.NA:
    if pd.isna(value):
        return pd.NA

    if isinstance(value, (int, np.integer)):
        return str(int(value))

    if isinstance(value, (float, np.floating)):
        if np.isfinite(value) and float(value).is_integer():
            return str(int(value))
        return str(value).strip()

    text = str(value).strip()
    if not text:
        return pd.NA

    as_number = pd.to_numeric(text, errors="coerce")
    if pd.notna(as_number) and float(as_number).is_integer():
        return str(int(as_number))

    return text


def parse_match_date(value: object) -> pd.Timestamp | pd.NaT:
    if pd.isna(value):
        return pd.NaT

    if isinstance(value, pd.Timestamp):
        return value.normalize()

    if hasattr(value, "date") and not isinstance(value, str):
        return pd.to_datetime(value, errors="coerce").normalize()

    numeric = pd.to_numeric(value, errors="coerce")
    if pd.notna(numeric) and 20000 <= float(numeric) <= 60000:
        return pd.to_datetime(float(numeric), unit="D", origin="1899-12-30")

    text = str(value).strip()
    if not text:
        return pd.NaT

    date_formats = [
        "%Y-%m-%d",
        "%a, %d-%b-%y",
        "%a, %d-%b-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]
    for date_format in date_formats:
        parsed = pd.to_datetime(text, format=date_format, errors="coerce")
        if pd.notna(parsed):
            return parsed.normalize()

    return pd.to_datetime(text, errors="coerce").normalize()


def to_numeric_series(series: pd.Series) -> pd.Series:
    without_datetime = series.mask(series.map(lambda value: hasattr(value, "date")))
    return pd.to_numeric(without_datetime, errors="coerce")


def read_input(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    frames = []
    for sheet_name, sheet_df in sheets.items():
        sheet_df = sheet_df.copy()
        sheet_df["source_sheet"] = sheet_name
        frames.append(sheet_df)

    if not frames:
        raise ValueError(f"No sheets found in {path}")

    return pd.concat(frames, ignore_index=True)


def ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column not in df.columns:
            df[column] = np.nan
    return df


def clean_base_data(df: pd.DataFrame, report: QualityReport) -> pd.DataFrame:
    df = ensure_columns(df, ID_COLUMNS + TEXT_COLUMNS + NUMERIC_COLUMNS + ["match_date"])
    report.raw_rows = len(df)
    report.raw_matches = df["match_id"].dropna().map(normalize_id).nunique()
    raw_present = {
        column: df[column].notna() & (df[column].astype("string").str.strip() != "")
        for column in NUMERIC_COLUMNS
    }

    for column in ID_COLUMNS:
        df[column] = df[column].map(normalize_id).astype("string")

    for column in TEXT_COLUMNS:
        df[column] = df[column].astype("string").str.strip()
        df[column] = df[column].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    df["match_date"] = df["match_date"].map(parse_match_date)

    for column in NUMERIC_COLUMNS:
        df[column] = to_numeric_series(df[column])

    required_mask = (
        df["match_id"].notna()
        & df["player_id"].notna()
        & df["match_date"].notna()
        & df["is_man_of_match"].isin([0, 1])
    )
    df = df.loc[required_mask].copy()
    report.rows_after_required_fields = len(df)

    invalid_rating = raw_present["rating"] & (
        df["rating"].isna() | ~df["rating"].between(0.000001, 10)
    )
    report.invalid_rating_rows = int(invalid_rating.sum())
    df.loc[invalid_rating, "rating"] = np.nan

    invalid_pass_accuracy = raw_present["pass_accuracy"] & (
        df["pass_accuracy"].isna() | ~df["pass_accuracy"].between(0, 100)
    )
    report.invalid_pass_accuracy_rows = int(invalid_pass_accuracy.sum())
    df.loc[invalid_pass_accuracy, "pass_accuracy"] = np.nan

    negative_minutes = df["minutes_played"].notna() & (df["minutes_played"] < 0)
    report.negative_minutes_rows = int(negative_minutes.sum())
    df.loc[negative_minutes, "minutes_played"] = 0

    report.invalid_binary_rows = {}
    for column in ["is_home", "is_first_eleven"]:
        invalid_binary = df[column].notna() & ~df[column].isin([0, 1])
        report.invalid_binary_rows[column] = int(invalid_binary.sum())
        df.loc[invalid_binary, column] = np.nan

    df[ZERO_FILL_STAT_COLUMNS] = df[ZERO_FILL_STAT_COLUMNS].fillna(0)

    return df


def apply_eligibility(df: pd.DataFrame, report: QualityReport, min_minutes: float) -> pd.DataFrame:
    eligible = df[
        (df["minutes_played"] >= min_minutes)
        & df["rating"].notna()
        & (df["rating"] > 0)
    ].copy()
    report.rows_after_eligibility = len(eligible)

    eligible = eligible.drop_duplicates(subset=["match_id", "player_id"], keep="first")
    report.rows_after_dedupe = len(eligible)

    target_per_match = eligible.groupby("match_id")["is_man_of_match"].sum()
    valid_match_ids = target_per_match[target_per_match == 1].index
    report.dropped_matches_zero_motm = int((target_per_match == 0).sum())
    report.dropped_matches_multi_motm = int((target_per_match > 1).sum())

    before_rows = len(eligible)
    eligible = eligible[eligible["match_id"].isin(valid_match_ids)].copy()
    report.dropped_rows_bad_match_target = before_rows - len(eligible)
    report.final_rows = len(eligible)
    report.final_matches = eligible["match_id"].nunique()

    return eligible


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["position_group"] = df["position"].map(POSITION_GROUP).fillna("Other")

    df["score_margin"] = np.where(
        df["is_home"] == 1,
        df["home_score"] - df["away_score"],
        df["away_score"] - df["home_score"],
    )

    df["goal_involvement"] = df["goals"] + df["assists"]
    df["shot_accuracy"] = np.where(
        df["shots_total"] > 0,
        df["shots_on_target"] / df["shots_total"],
        0.0,
    )
    df["minutes_ratio"] = (df["minutes_played"] / 90.0).clip(0, 1.3)

    df = df.sort_values(["player_id", "match_date", "match_id"]).reset_index(drop=True)

    rolling_sources = {
        "rolling_rating_5": "rating",
        "rolling_goals_5": "goals",
        "rolling_assists_5": "assists",
        "rolling_shots_5": "shots_total",
        "rolling_key_passes_5": "key_passes",
        "rolling_tackles_5": "tackles",
    }
    grouped = df.groupby("player_id", sort=False)
    for output_col, source_col in rolling_sources.items():
        df[output_col] = grouped[source_col].transform(
            lambda series: series.shift(1).rolling(5, min_periods=1).mean()
        )

    return df


def split_by_match_time(
    df: pd.DataFrame, report: QualityReport
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    match_dates = (
        df.groupby("match_id", as_index=False)["match_date"]
        .min()
        .sort_values(["match_date", "match_id"])
        .reset_index(drop=True)
    )
    match_count = len(match_dates)
    train_end = max(1, int(match_count * 0.70))
    validation_end = max(train_end + 1, int(match_count * 0.85))
    validation_end = min(validation_end, match_count)

    train_ids = set(match_dates.iloc[:train_end]["match_id"])
    validation_ids = set(match_dates.iloc[train_end:validation_end]["match_id"])
    test_ids = set(match_dates.iloc[validation_end:]["match_id"])

    train = df[df["match_id"].isin(train_ids)].copy()
    validation = df[df["match_id"].isin(validation_ids)].copy()
    test = df[df["match_id"].isin(test_ids)].copy()

    report.train_rows = len(train)
    report.validation_rows = len(validation)
    report.test_rows = len(test)
    report.train_matches = len(train_ids)
    report.validation_matches = len(validation_ids)
    report.test_matches = len(test_ids)

    return train, validation, test


def build_feature_lists(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    feature_columns = [
        column for column in df.columns if column not in CURRENT_MATCH_EXCLUDE_COLUMNS
    ]
    numeric_features = [
        column
        for column in feature_columns
        if pd.api.types.is_numeric_dtype(df[column])
        and column != "is_man_of_match"
    ]
    categorical_features = [
        column
        for column in feature_columns
        if column not in numeric_features and column != "is_man_of_match"
    ]
    return feature_columns, numeric_features, categorical_features


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_preprocessor(
    numeric_features: list[str], categorical_features: list[str]
) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", make_one_hot_encoder()),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )


def validate_outputs(
    df: pd.DataFrame,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
) -> None:
    if "rating" in feature_columns:
        raise AssertionError("Primary feature set must not include current rating.")

    target_counts = df.groupby("match_id")["is_man_of_match"].sum()
    if not (target_counts == 1).all():
        raise AssertionError("Every final match must have exactly one MOTM target.")

    split_ids = [
        set(train["match_id"]),
        set(validation["match_id"]),
        set(test["match_id"]),
    ]
    if split_ids[0] & split_ids[1] or split_ids[0] & split_ids[2] or split_ids[1] & split_ids[2]:
        raise AssertionError("Match IDs must not overlap across splits.")

    if not set(df["is_man_of_match"].dropna().unique()).issubset({0, 1}):
        raise AssertionError("Target must remain binary 0/1.")


def write_report(
    output_path: Path,
    report: QualityReport,
    feature_columns: list[str],
    numeric_features: list[str],
    categorical_features: list[str],
) -> None:
    invalid_binary = report.invalid_binary_rows or {}
    lines = [
        "# Báo Cáo Chất Lượng Dữ Liệu",
        "",
        "## Nguồn Dữ Liệu",
        "",
        "- Nguồn input: `PlayerCrawl.xlsx`",
        "- Không dùng làm input: `motm_clean.xlsx`, `PlayerCrawl_normalized_standard.xlsx`",
        "- Chính sách target: giữ nguyên `is_man_of_match` gốc; không gán lại nhãn theo rating cao nhất",
        "- Chính sách feature chính: loại `rating` của trận hiện tại để giảm leakage",
        "",
        "## Số Lượng Dòng",
        "",
        f"- Dòng dữ liệu thô: {report.raw_rows:,}",
        f"- Số trận thô: {report.raw_matches:,}",
        f"- Dòng sau khi kiểm tra các trường bắt buộc: {report.rows_after_required_fields:,}",
        f"- Dòng sau khi lọc điều kiện minutes/rating: {report.rows_after_eligibility:,}",
        f"- Dòng sau khi loại trùng theo `match_id + player_id`: {report.rows_after_dedupe:,}",
        f"- Dòng cuối cùng: {report.final_rows:,}",
        f"- Số trận cuối cùng: {report.final_matches:,}",
        "",
        "## Kiểm Soát Chất Lượng",
        "",
        f"- Dòng có rating không hợp lệ được chuyển thành missing: {report.invalid_rating_rows:,}",
        f"- Dòng có pass accuracy không hợp lệ được chuyển thành missing: {report.invalid_pass_accuracy_rows:,}",
        f"- Dòng có minutes âm được đặt về 0 trước khi lọc điều kiện hợp lệ: {report.negative_minutes_rows:,}",
        f"- Dòng có `is_home` không hợp lệ được chuyển thành missing: {invalid_binary.get('is_home', 0):,}",
        f"- Dòng có `is_first_eleven` không hợp lệ được chuyển thành missing: {invalid_binary.get('is_first_eleven', 0):,}",
        f"- Số trận bị loại vì có 0 MOTM sau khi lọc điều kiện hợp lệ: {report.dropped_matches_zero_motm:,}",
        f"- Số trận bị loại vì có hơn 1 MOTM sau khi lọc điều kiện hợp lệ: {report.dropped_matches_multi_motm:,}",
        f"- Số dòng bị loại do thuộc các trận có target không hợp lệ: {report.dropped_rows_bad_match_target:,}",
        "",
        "## Số Lượng Theo Tập Dữ Liệu",
        "",
        f"- Train: {report.train_rows:,} dòng / {report.train_matches:,} trận",
        f"- Validation: {report.validation_rows:,} dòng / {report.validation_matches:,} trận",
        f"- Test: {report.test_rows:,} dòng / {report.test_matches:,} trận",
        "",
        "## Tóm Tắt Feature",
        "",
        f"- Số cột feature chính: {len(feature_columns):,}",
        f"- Feature dạng số: {len(numeric_features):,}",
        f"- Feature dạng phân loại: {len(categorical_features):,}",
        "",
        "### Feature Dạng Số",
        "",
        ", ".join(f"`{column}`" for column in numeric_features),
        "",
        "### Feature Dạng Phân Loại",
        "",
        ", ".join(f"`{column}`" for column in categorical_features),
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_feature_metadata(
    output_path: Path,
    feature_columns: list[str],
    numeric_features: list[str],
    categorical_features: list[str],
) -> None:
    metadata = {
        "target_column": "is_man_of_match",
        "feature_columns": feature_columns,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "excluded_columns": sorted(CURRENT_MATCH_EXCLUDE_COLUMNS),
        "notes": [
            "Current-match rating is excluded from the primary feature set.",
            "Use preprocessor.joblib fitted on train only before model training.",
        ],
    }
    output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    artifacts_dir = Path(args.artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    report = QualityReport()
    raw_df = read_input(input_path)
    clean_df = clean_base_data(raw_df, report)
    eligible_df = apply_eligibility(clean_df, report, args.min_minutes)
    model_ready = add_features(eligible_df)
    train, validation, test = split_by_match_time(model_ready, report)

    feature_columns, numeric_features, categorical_features = build_feature_lists(model_ready)
    validate_outputs(model_ready, train, validation, test, feature_columns)

    preprocessor = build_preprocessor(numeric_features, categorical_features)
    preprocessor.fit(train[feature_columns])

    model_ready.to_csv(out_dir / "motm_model_ready.csv", index=False, encoding="utf-8-sig")
    train.to_csv(out_dir / "train.csv", index=False, encoding="utf-8-sig")
    validation.to_csv(out_dir / "validation.csv", index=False, encoding="utf-8-sig")
    test.to_csv(out_dir / "test.csv", index=False, encoding="utf-8-sig")

    joblib.dump(preprocessor, artifacts_dir / "preprocessor.joblib")
    write_feature_metadata(
        artifacts_dir / "feature_columns.json",
        feature_columns,
        numeric_features,
        categorical_features,
    )
    write_report(
        out_dir / "data_quality_report.md",
        report,
        feature_columns,
        numeric_features,
        categorical_features,
    )

    print("Transform complete.")
    print(f"Model-ready rows: {len(model_ready):,} / matches: {model_ready['match_id'].nunique():,}")
    print(f"Train: {len(train):,}, validation: {len(validation):,}, test: {len(test):,}")
    print(f"Outputs written to: {out_dir}")
    print(f"Artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
