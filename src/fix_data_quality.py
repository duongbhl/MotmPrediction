"""
Script sửa lỗi chất lượng dữ liệu trong motm_clean.xlsx:
  1. Cột `rating` bị Excel parse thành datetime → convert về float
  2. Cột `match_date` có 2 format hỗn hợp → chuẩn hóa về YYYY-MM-DD
  3. Cột `rolling_shots_5` có 719 null → fillna(0)
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE  = ROOT / "motm_clean.xlsx"
OUTPUT_FILE = ROOT / "motm_clean.xlsx"  # ghi đè luôn


# ─── helpers ──────────────────────────────────────────────────────────────────

def fix_rating(value):
    """
    Chuyển datetime (bị Excel auto-parse) về float rating.
    Pattern: datetime(2026, month, day) → float(f"{day}.{month:02d}")
    Ví dụ: 2026-09-06  →  6.09  |  2026-01-07  →  7.01
    """
    if isinstance(value, (int, float)):
        return float(value)
    if hasattr(value, "day") and hasattr(value, "month"):      # datetime-like
        return float(f"{value.day}.{value.month:02d}")
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def normalize_date(value):
    """
    Chuẩn hóa match_date về YYYY-MM-DD (string).
    Hỗ trợ: 'M/D/YYYY', 'YYYY-MM-DD', và datetime object.
    """
    if pd.isnull(value):
        return None
    parsed = pd.to_datetime(value, dayfirst=False, errors="coerce")
    if pd.isnull(parsed):
        return str(value)
    return parsed.strftime("%Y-%m-%d")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"Đọc file: {INPUT_FILE}")
    df = pd.read_excel(INPUT_FILE)
    print(f"  Shape ban đầu: {df.shape}")

    # ── 1. Fix cột rating ──────────────────────────────────────────────────────
    rating_bad_before = pd.to_numeric(df["rating"], errors="coerce").isnull().sum()
    df["rating"] = df["rating"].apply(fix_rating)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    rating_bad_after = df["rating"].isnull().sum()

    print(f"\n[1] rating:")
    print(f"  Rows bị lỗi trước fix : {rating_bad_before}")
    print(f"  Null còn lại sau fix  : {rating_bad_after}")
    print(f"  rating range          : {df['rating'].min():.2f} – {df['rating'].max():.2f}")

    # ── 2. Chuẩn hóa match_date ───────────────────────────────────────────────
    mixed_before = df["match_date"].astype(str).str.contains("-").sum()
    df["match_date"] = df["match_date"].apply(normalize_date)
    null_dates = df["match_date"].isnull().sum()

    print(f"\n[2] match_date:")
    print(f"  Rows dùng format YYYY-MM-DD trước : {mixed_before}")
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    print(f"  Tất cả sau fix đều là YYYY-MM-DD  : {df['match_date'].str.match(pattern).sum()}")
    print(f"  Null còn lại                       : {null_dates}")

    # ── 3. Fill null rolling_shots_5 ──────────────────────────────────────────
    null_shots_before = df["rolling_shots_5"].isnull().sum()
    df["rolling_shots_5"] = df["rolling_shots_5"].fillna(0.0)
    null_shots_after = df["rolling_shots_5"].isnull().sum()

    print(f"\n[3] rolling_shots_5:")
    print(f"  Null trước : {null_shots_before}")
    print(f"  Null sau   : {null_shots_after}")

    # ── Kiểm tra tổng null toàn bộ dataframe ──────────────────────────────────
    total_null = df.isnull().sum().sum()
    print(f"\n  Tổng null toàn bộ dataset sau fix: {total_null}")

    # ── Lưu file ──────────────────────────────────────────────────────────────
    print(f"\nGhi file: {OUTPUT_FILE}")
    df.to_excel(OUTPUT_FILE, index=False)
    print("  Done!")

    return df


if __name__ == "__main__":
    main()
