"""
Train & evaluate multiple ML models for MOTM prediction.

Models   : Logistic Regression, Random Forest, XGBoost, LightGBM, MLP + Ensemble
Tuning   : Optuna hyperparameter search for XGBoost and LightGBM
Metrics  : ROC-AUC, PR-AUC, F1 (optimal threshold), Match Top-1 Accuracy
Output   : artifacts/best_model.joblib  +  artifacts/model_report.md
"""

from __future__ import annotations

import json
import platform
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.neural_network import MLPClassifier

warnings.filterwarnings("ignore")

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[WARN] xgboost not installed — skipping XGBoost.")

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    print("[WARN] lightgbm not installed — skipping LightGBM.")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    print("[WARN] optuna not installed — skipping hyperparameter tuning.")


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
ARTIFACTS_DIR = ROOT / "artifacts"

OPTUNA_TRIALS = 60


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_split(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"{name}.csv", low_memory=False)


def prepare_xy(
    df: pd.DataFrame,
    feature_cols: list[str],
    preprocessor,
) -> tuple[np.ndarray, np.ndarray]:
    X = preprocessor.transform(df[feature_cols])
    y = df["is_man_of_match"].values.astype(int)
    return X, y


# ─── Evaluation ───────────────────────────────────────────────────────────────

def match_top1_accuracy(df: pd.DataFrame, probs: np.ndarray) -> float:
    tmp = df[["match_id", "is_man_of_match"]].copy()
    tmp["prob"] = probs
    correct = (
        tmp.groupby("match_id")
        .apply(lambda g: int(g.loc[g["prob"].idxmax(), "is_man_of_match"] == 1))
        .sum()
    )
    return int(correct) / tmp["match_id"].nunique()


def best_f1_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> tuple[float, float]:
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    denom = np.where((precision + recall) == 0, 1, precision + recall)
    f1_scores = 2 * precision * recall / denom
    idx = np.argmax(f1_scores[:-1])
    return float(f1_scores[idx]), float(thresholds[idx])


def evaluate(
    name: str,
    model,
    X: np.ndarray,
    y: np.ndarray,
    df: pd.DataFrame,
) -> dict:
    probs = model.predict_proba(X)[:, 1]
    roc   = roc_auc_score(y, probs)
    pr    = average_precision_score(y, probs)
    f1, thr = best_f1_threshold(y, probs)
    top1  = match_top1_accuracy(df, probs)

    print(f"  {name:<26} ROC-AUC={roc:.4f}  PR-AUC={pr:.4f}  "
          f"F1={f1:.4f}(thr={thr:.2f})  Top-1={top1:.4f}")

    return {
        "name": name, "roc_auc": roc, "pr_auc": pr,
        "f1": f1, "threshold": thr, "top1_acc": top1,
        "model": model, "probs": probs,
    }


# ─── Optuna tuning ────────────────────────────────────────────────────────────

def tune_xgb(X_train, y_train, X_val, y_val, ratio: float) -> object:
    # Optimize ROC-AUC (smooth, ~2300 points) instead of Top-1 (noisy, 78 points)
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 200, 800),
            "max_depth": trial.suggest_int("max_depth", 3, 9),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0, 1),
            "scale_pos_weight": ratio,
            "eval_metric": "logloss",
            "random_state": 42,
            "verbosity": 0,
        }
        m = xgb.XGBClassifier(**params)
        m.fit(X_train, y_train)
        return roc_auc_score(y_val, m.predict_proba(X_val)[:, 1])

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=OPTUNA_TRIALS, show_progress_bar=False)
    best = xgb.XGBClassifier(**study.best_params, scale_pos_weight=ratio,
                              eval_metric="logloss", random_state=42, verbosity=0)
    best.fit(X_train, y_train)
    return best


def tune_lgb(X_train, y_train, X_val, y_val, ratio: float) -> object:
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 200, 800),
            "max_depth": trial.suggest_int("max_depth", 3, 9),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 20, 150),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "scale_pos_weight": ratio,
            "random_state": 42,
            "verbosity": -1,
        }
        m = lgb.LGBMClassifier(**params)
        m.fit(X_train, y_train)
        return roc_auc_score(y_val, m.predict_proba(X_val)[:, 1])

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=OPTUNA_TRIALS, show_progress_bar=False)
    best = lgb.LGBMClassifier(**study.best_params, scale_pos_weight=ratio,
                               random_state=42, verbosity=-1)
    best.fit(X_train, y_train)
    return best


def tune_lr(X_train, y_train, X_val, y_val) -> object:
    def objective(trial):
        C = trial.suggest_float("C", 1e-3, 100, log=True)
        penalty = trial.suggest_categorical("penalty", ["l1", "l2"])
        solver = "liblinear" if penalty == "l1" else "lbfgs"
        m = LogisticRegression(C=C, penalty=penalty, solver=solver,
                               class_weight="balanced", max_iter=1000, random_state=42)
        m.fit(X_train, y_train)
        return roc_auc_score(y_val, m.predict_proba(X_val)[:, 1])

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=40, show_progress_bar=False)
    p = study.best_params
    solver = "liblinear" if p["penalty"] == "l1" else "lbfgs"
    best = LogisticRegression(C=p["C"], penalty=p["penalty"], solver=solver,
                              class_weight="balanced", max_iter=1000, random_state=42)
    best.fit(X_train, y_train)
    return best


# ─── Base models (no tuning) ─────────────────────────────────────────────────

def build_base_models(neg: int, pos: int) -> list[tuple[str, object]]:
    ratio = neg / max(pos, 1)
    models: list[tuple[str, object]] = [
        (
            "LogisticRegression",
            LogisticRegression(C=1.0, class_weight="balanced",
                               max_iter=1000, random_state=42),
        ),
        (
            "RandomForest",
            RandomForestClassifier(n_estimators=300, max_depth=12,
                                   min_samples_leaf=5, class_weight="balanced",
                                   random_state=42, n_jobs=-1),
        ),
        (
            "MLP",
            MLPClassifier(hidden_layer_sizes=(128, 64, 32), activation="relu",
                          max_iter=300, early_stopping=True,
                          validation_fraction=0.1, random_state=42),
        ),
    ]
    if HAS_XGB and not HAS_OPTUNA:
        models.append(("XGBoost",
            xgb.XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.05,
                               subsample=0.8, colsample_bytree=0.8,
                               scale_pos_weight=ratio, eval_metric="logloss",
                               random_state=42, verbosity=0)))
    if HAS_LGB and not HAS_OPTUNA:
        models.append(("LightGBM",
            lgb.LGBMClassifier(n_estimators=400, max_depth=8, learning_rate=0.05,
                                num_leaves=63, subsample=0.8, colsample_bytree=0.8,
                                scale_pos_weight=ratio, random_state=42, verbosity=-1)))
    return models


# ─── Report ───────────────────────────────────────────────────────────────────

def write_report(results: list[dict], best: dict, test_metrics: dict) -> None:
    lines = [
        "# Model Evaluation Report — MOTM Prediction",
        "",
        "## Primary metric: Match Top-1 Accuracy",
        "> For each match, is the player with the highest predicted probability the actual MOTM?",
        "",
        "## Validation Results",
        "",
        "| Model | ROC-AUC | PR-AUC | F1 (opt) | Top-1 Acc |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: x["top1_acc"], reverse=True):
        lines.append(
            f"| {r['name']} | {r['roc_auc']:.4f} | {r['pr_auc']:.4f} "
            f"| {r['f1']:.4f} | {r['top1_acc']:.4f} |"
        )
    lines += [
        "",
        f"## Best Model: **{best['name']}** (by Top-1 Accuracy on validation)",
        "",
        "## Test Set Results (best model)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| ROC-AUC   | {test_metrics['roc_auc']:.4f} |",
        f"| PR-AUC    | {test_metrics['pr_auc']:.4f} |",
        f"| F1        | {test_metrics['f1']:.4f} |",
        f"| Top-1 Acc | {test_metrics['top1_acc']:.4f} |",
    ]
    path = DATA_DIR / "model_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {path}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading data...")
    train_df = load_split("train")
    val_df   = load_split("validation")
    test_df  = load_split("test")

    with open(ARTIFACTS_DIR / "feature_columns.json", encoding="utf-8") as f:
        meta = json.load(f)

    preprocessor = joblib.load(ARTIFACTS_DIR / "preprocessor.joblib")
    feature_cols = meta["feature_columns"]

    X_train, y_train = prepare_xy(train_df, feature_cols, preprocessor)
    X_val,   y_val   = prepare_xy(val_df,   feature_cols, preprocessor)
    X_test,  y_test  = prepare_xy(test_df,  feature_cols, preprocessor)

    neg, pos = int((y_train == 0).sum()), int((y_train == 1).sum())
    ratio = neg / max(pos, 1)
    print(f"Train: {len(y_train):,} rows | pos={pos} | neg={neg} | ratio={ratio:.1f}:1")
    print(f"Features: {X_train.shape[1]}\n")

    results: list[dict] = []

    # ── Base models ───────────────────────────────────────────────────────────
    print("=== Base Models ===")
    for name, model in build_base_models(neg, pos):
        print(f"  Training {name}...", end=" ", flush=True)
        model.fit(X_train, y_train)
        print("done.", end=" ", flush=True)
        results.append(evaluate(name, model, X_val, y_val, val_df))

    # ── Optuna tuning ─────────────────────────────────────────────────────────
    if HAS_OPTUNA:
        print(f"\n=== Optuna Tuning ({OPTUNA_TRIALS} trials each) ===")

        print(f"  Tuning LogisticRegression (40 trials)...", end=" ", flush=True)
        lr_tuned = tune_lr(X_train, y_train, X_val, y_val)
        print("done.", end=" ", flush=True)
        results.append(evaluate("LR-Tuned", lr_tuned, X_val, y_val, val_df))

        if HAS_XGB:
            print(f"  Tuning XGBoost ({OPTUNA_TRIALS} trials)...", end=" ", flush=True)
            xgb_tuned = tune_xgb(X_train, y_train, X_val, y_val, ratio)
            print("done.", end=" ", flush=True)
            results.append(evaluate("XGBoost-Tuned", xgb_tuned, X_val, y_val, val_df))

        if HAS_LGB:
            print(f"  Tuning LightGBM ({OPTUNA_TRIALS} trials)...", end=" ", flush=True)
            lgb_tuned = tune_lgb(X_train, y_train, X_val, y_val, ratio)
            print("done.", end=" ", flush=True)
            results.append(evaluate("LightGBM-Tuned", lgb_tuned, X_val, y_val, val_df))

    # ── Soft-vote Ensemble (top 3 by Top-1) ──────────────────────────────────
    print("\n=== Ensemble (Soft Voting, top 3 models) ===")
    top3 = sorted(results, key=lambda r: r["top1_acc"], reverse=True)[:3]
    estimators = [(r["name"].replace("-", "_"), r["model"]) for r in top3]
    ensemble = VotingClassifier(estimators=estimators, voting="soft")
    print(f"  Members: {[n for n, _ in estimators]}")
    print("  Fitting ensemble...", end=" ", flush=True)
    ensemble.fit(X_train, y_train)
    print("done.", end=" ", flush=True)
    results.append(evaluate("Ensemble-Top3", ensemble, X_val, y_val, val_df))

    # ── Pick best ─────────────────────────────────────────────────────────────
    best = max(results, key=lambda r: r["top1_acc"])
    print(f"\n=> Best model: {best['name']} (Top-1 val={best['top1_acc']:.4f})")

    # ── Test evaluation ───────────────────────────────────────────────────────
    print("\n=== Test Set (best model) ===")
    test_probs = best["model"].predict_proba(X_test)[:, 1]
    test_roc  = roc_auc_score(y_test, test_probs)
    test_pr   = average_precision_score(y_test, test_probs)
    test_f1, test_thr = best_f1_threshold(y_test, test_probs)
    test_top1 = match_top1_accuracy(test_df, test_probs)
    test_metrics = {"roc_auc": test_roc, "pr_auc": test_pr,
                    "f1": test_f1, "threshold": test_thr, "top1_acc": test_top1}
    print(f"  ROC-AUC={test_roc:.4f}  PR-AUC={test_pr:.4f}  "
          f"F1={test_f1:.4f}  Top-1={test_top1:.4f}")

    # ── Save ──────────────────────────────────────────────────────────────────
    model_path = ARTIFACTS_DIR / "best_model.joblib"
    joblib.dump(best["model"], model_path)
    print(f"\nSaved: {model_path}")

    meta_out = {
        "model_name": best["name"],
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "joblib_version": joblib.__version__,
        "val_roc_auc": best["roc_auc"], "val_pr_auc": best["pr_auc"],
        "val_f1": best["f1"], "val_threshold": best["threshold"],
        "val_top1_acc": best["top1_acc"],
        "test_roc_auc": test_roc, "test_pr_auc": test_pr,
        "test_f1": test_f1, "test_threshold": test_thr,
        "test_top1_acc": test_top1,
    }
    (ARTIFACTS_DIR / "best_model_meta.json").write_text(
        json.dumps(meta_out, indent=2), encoding="utf-8"
    )

    write_report(results, best, test_metrics)
    print("Done!")


if __name__ == "__main__":
    main()
