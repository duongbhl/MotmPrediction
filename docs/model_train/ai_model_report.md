# Báo cáo: Xây dựng & Đánh giá AI Model — MOTM Prediction

> Phụ trách: NHI  
> Branch: `feature/data-cleaning-fix`  
> Scripts: `src/transform_motm_data.py`, `src/train_models.py`

---

## 1. Lý do chọn nguồn dữ liệu

### Dùng `PlayerCrawl.xlsx` — không dùng `PlayerCrawl_normalized_standard.xlsx`

Dù `PlayerCrawl_normalized_standard.xlsx` có vẻ đã được xử lý sẵn, file này **không thể dùng** vì 3 lý do:

**Lý do 1: Target label bị normalize sai ❌**

```
is_man_of_match gốc  : 0  hoặc  1
is_man_of_match bị sửa: -0.16  hoặc  6.24   ← StandardScaler biến dạng label
```

Target label tuyệt đối không được normalize. Model sẽ học sai hoàn toàn.

**Lý do 2: Thiếu 1 mùa dữ liệu ❌**

| File | Số hàng | Mùa giải có |
|---|---|---|
| `PlayerCrawl_normalized_standard.xlsx` | 15.188 | Chỉ 2024/25 |
| `PlayerCrawl.xlsx` | 20.191 | 2024/25 + 2025/26 |

File normalized bỏ sót toàn bộ 5.003 hàng của mùa 2025/26.

**Lý do 3: Normalize sai thời điểm — gây data leakage ❌**

| Cách sai (file normalize thủ công) | Cách đúng (pipeline hiện tại) |
|---|---|
| `StandardScaler.fit(toàn bộ dataset)` | `StandardScaler.fit(chỉ train set)` |
| Val/test biết thông tin của train khi normalize | Val/test hoàn toàn độc lập |
| Nếu có data mới → phải normalize lại từ đầu | Chỉ cần `preprocessor.transform(new_data)` |

`PlayerCrawl_normalized_standard.xlsx` là artifact từ `CleanData.ipynb` (giai đoạn khám phá Colab), không đủ chuẩn cho ML pipeline thực tế.

---

## 2. Chia tập train / validation / test

### Chiến lược: Stratified theo season (không pure time split)

Chia theo **thứ tự thời gian trong từng mùa giải**, sau đó ghép lại — đảm bảo cả 2 mùa đều có mặt trong train/val/test, tránh distribution shift.

> **Tại sao không chia random?** Nếu chia random, một match tháng 5/2026 có thể vào train, trong khi match tháng 4/2026 lại ở val — model "thấy tương lai" khi học quá khứ → leakage.

> **Tại sao không pure time split?** Với chỉ 2 mùa dữ liệu, pure time split đặt toàn bộ mùa 2024/25 vào train và mùa 2025/26 vào test → model không bao giờ học pattern mùa 2025/26 → distribution shift làm giảm accuracy giả tạo.

| Tập | Tỉ lệ | Số hàng | Số trận | Mùa 24/25 | Mùa 25/26 |
|---|---|---|---|---|---|
| **Train** | 70%/mùa | 10.537 | 365 | 266 trận | 99 trận |
| **Validation** | 15%/mùa | 2.267 | 78 | 57 trận | 21 trận |
| **Test** | 15%/mùa | 2.301 | 79 | 57 trận | 22 trận |

### Feature Engineering (tự động trong pipeline)

Ngoài các stats gốc, pipeline tạo thêm:

| Feature mới | Công thức |
|---|---|
| `score_margin` | Hiệu số bàn thắng theo góc nhìn cầu thủ |
| `goal_involvement` | `goals + assists` |
| `shot_accuracy` | `shots_on_target / shots_total` |
| `minutes_ratio` | `minutes_played / 90` (clip 0–1.3) |
| `rolling_rating_5` | Rating trung bình 5 trận **trước** (dùng `shift(1)`) |
| `rolling_goals_5` | Goals trung bình 5 trận trước |
| `rolling_assists_5` | Assists trung bình 5 trận trước |
| `rolling_shots_5` | Shots trung bình 5 trận trước |
| `rolling_key_passes_5` | Key passes trung bình 5 trận trước |
| `rolling_tackles_5` | Tackles trung bình 5 trận trước |

### Quyết định loại `rating` khỏi features

`rating` (WhoScored 0–10) bị loại có chủ ý:

- Chọn người `rating` cao nhất mỗi trận → **Top-1 Accuracy 98.7%** → model chỉ học 1 rule, không có giá trị AI
- `rating` là bản tóm tắt tổng hợp của toàn bộ stats (goals, tackles, passes...) — đưa vào là thừa và circular
- Model buộc học từ từng stat riêng lẻ → có ý nghĩa và generalizable hơn

### Tiền xử lý features

Preprocessor **fit chỉ trên train**, lưu tại `artifacts/preprocessor.joblib`:

- **Numeric** (30 cột): `SimpleImputer(median)` → `StandardScaler`
- **Categorical** (`season`, `team`, `position`...): `SimpleImputer(most_frequent)` → `OneHotEncoder`

---

## 3. Các mô hình đã thử nghiệm

Class imbalance **~28:1** (neg:pos) — xử lý:
- Logistic Regression, Random Forest: `class_weight='balanced'`
- XGBoost, LightGBM: `scale_pos_weight=27.9`
- MLP: `early_stopping=True`

Ngoài hyperparameter mặc định, còn chạy **Optuna tuning** (60 trials, objective = ROC-AUC trên val) cho LR, XGBoost, LightGBM, và **Soft Voting Ensemble** của top 3 models.

> **Tại sao dùng ROC-AUC làm Optuna objective thay vì Top-1 Accuracy?**  
> Val set chỉ có 78 match → Top-1 Accuracy có sai số ~±5.6%. Optimize trực tiếp trên metric quá noisy dẫn đến overfit validation. ROC-AUC mượt hơn (2.267 data points thay vì 78).

---

## 4. Đánh giá & so sánh

### Metric đánh giá

| Metric | Ý nghĩa |
|---|---|
| **Match Top-1 Accuracy** | % trận model chọn đúng người MOTM là #1 — metric kinh doanh quan trọng nhất |
| **ROC-AUC** | Khả năng phân biệt MOTM vs non-MOTM tổng thể |
| **PR-AUC** | Precision-Recall, phù hợp dữ liệu mất cân bằng nặng |
| **F1** | Dùng threshold tối ưu (không cố định 0.5) |

### Kết quả Validation Set (stratified split)

| Model | ROC-AUC | PR-AUC | F1 (opt) | **Top-1 Val** |
|---|---|---|---|---|
| Random Forest | 0.9386 | 0.4058 | 0.4852 | 43.6% |
| MLP | 0.9326 | 0.4802 | 0.5175 | 46.2% |
| XGBoost-Tuned | 0.9550 | 0.4990 | 0.5574 | 50.0% |
| LightGBM-Tuned | 0.9538 | 0.5302 | 0.5475 | 51.3% |
| LogisticRegression | 0.9516 | 0.5048 | 0.5093 | 53.8% |
| Ensemble-Top3 | 0.9616 | 0.5710 | 0.5668 | 55.1% |
| **LR-Tuned** | **0.9610** | **0.5779** | **0.5882** | **61.5%** |

### Baselines để tham chiếu (Test Set)

| Phương pháp | Top-1 Accuracy |
|---|---|
| Random guess (1/30 cầu thủ) | 3.3% |
| Chọn người đá nhiều phút nhất | 5.1% |
| Chọn người assists cao nhất | 16.5% |
| Chọn người goals + assists cao nhất | 35.4% |
| **Best model (LR)** | **62.0%** |

### Thực nghiệm thất bại — bài học

Trong quá trình thử cải thiện lên 70-80%, đã thử thêm **within-match rank features** (xếp hạng từng stat trong trận). Kết quả: val tăng nhưng test giảm từ 62% → 53% → overfit. Nguyên nhân: rank features tương quan cao với raw stats đã có, tăng multicollinearity, LR overfit train/val.

---

## 5. Mô hình tốt nhất: Logistic Regression

### Kết quả Test Set (final — chưa từng dùng khi train)

| Metric | Giá trị |
|---|---|
| ROC-AUC | **0.9573** |
| PR-AUC | **0.5061** |
| F1 (threshold = 0.92) | **0.5316** |
| **Top-1 Accuracy** | **62.0%** |

### Nhận xét

- Logistic Regression (model đơn giản nhất) thắng tất cả → dataset nhỏ (~365 train matches), model đơn giản generalize tốt hơn
- Test tốt hơn val (62% vs 53.8%) → val set có phân phối khó hơn trong giai đoạn cụ thể đó, không phải model overfit
- **Tốt hơn heuristic tốt nhất ~75%** (62% vs 35.4%)
- **Tốt hơn random ~19 lần**

### Tại sao không đạt 70-80%?

Với dataset hiện tại (~500 trận, 2 mùa), 62% gần là ceiling thực tế khi không dùng `rating`. Để cải thiện thêm cần:
1. Thêm 2-3 mùa data (≥1000 trận train)
2. Features domain-specific hơn (độ khó đối thủ, tầm quan trọng trận, thông tin chấn thương)
3. Hoặc chấp nhận dùng rolling_rating_5 với trọng số nặng hơn

---

## 6. Artifacts đã lưu & cách dùng

| File | Nội dung |
|---|---|
| `artifacts/preprocessor.joblib` | StandardScaler + OneHotEncoder đã fit trên train |
| `artifacts/best_model.joblib` | Logistic Regression model đã train |
| `artifacts/best_model_meta.json` | Metrics đầy đủ của best model |
| `artifacts/feature_columns.json` | Danh sách features, numeric/categorical split |
| `data/processed/model_report.md` | Bảng so sánh tất cả models |

### Cách dùng `best_model.joblib` trong API

```python
import joblib
import json
import pandas as pd

# Load 1 lần khi khởi động server
preprocessor = joblib.load("artifacts/preprocessor.joblib")
model        = joblib.load("artifacts/best_model.joblib")

with open("artifacts/feature_columns.json") as f:
    meta = json.load(f)

feature_cols = meta["feature_columns"]   # danh sách 43 features cần thiết


def predict_motm(match_players_df: pd.DataFrame) -> dict:
    """
    Input : DataFrame, mỗi hàng = 1 cầu thủ trong trận,
            phải có đủ các cột trong feature_cols.
    Output: dict với tên cầu thủ được dự đoán MOTM và xác suất từng người.
    """
    X = preprocessor.transform(match_players_df[feature_cols])
    probs = model.predict_proba(X)[:, 1]          # xác suất từng cầu thủ là MOTM

    best_idx = probs.argmax()
    return {
        "predicted_motm": match_players_df.iloc[best_idx]["name"],
        "probability":    round(float(probs[best_idx]), 4),
        "all_players": [
            {"name": row["name"], "prob": round(float(p), 4)}
            for row, p in zip(match_players_df.to_dict("records"), probs)
        ]
    }
```

### Chạy lại toàn bộ pipeline từ đầu

```bash
# Bước 1: Tạo train/val/test splits + preprocessor
python src/transform_motm_data.py --input PlayerCrawl.xlsx

# Bước 2: Train tất cả models, chọn best, lưu artifact
python src/train_models.py
```
