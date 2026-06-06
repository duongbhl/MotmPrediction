# Hướng Dẫn Chạy Trên Google Colab

Sử dụng `PlayerCrawl.xlsx` làm file dữ liệu nguồn. Không dùng
`motm_clean.xlsx` hoặc `PlayerCrawl_normalized_standard.xlsx` làm input cho
bước transform vì các file này đang có lỗi numeric/normalization.

## Cách 1: Upload File Zip Của Project

Upload file zip lên Colab:

```python
from google.colab import files
uploaded = files.upload()
```

Nếu bạn upload file zip của project, hãy giải nén và chuyển vào thư mục project:

```bash
!unzip -q MotmPrediction.zip
%cd MotmPrediction
```

Chạy pipeline transform:

```bash
!pip install -r requirements.txt
!python src/transform_motm_data.py --input PlayerCrawl.xlsx --out-dir data/processed --artifacts-dir artifacts
```

## Cách 2: Dùng Google Drive

Mount Google Drive và chuyển vào thư mục project:

```python
from google.colab import drive
drive.mount('/content/drive')
%cd /content/drive/MyDrive/MotmPrediction
```

Chạy pipeline transform:

```bash
!pip install -r requirements.txt
!python src/transform_motm_data.py --input PlayerCrawl.xlsx --out-dir data/processed --artifacts-dir artifacts
```

## Cách 3: Clone Project Từ GitHub

Cách này dùng khi project đã được push lên GitHub. Trước khi chạy, hãy đảm bảo
`requirements.txt`, `src/`, `docs/`, `tests/` và `PlayerCrawl.xlsx` đã được
commit/push lên repo.

```bash
!git clone https://github.com/duongbhl/MotmPrediction.git
%cd MotmPrediction
!pip install -r requirements.txt
!python src/transform_motm_data.py --input PlayerCrawl.xlsx --out-dir data/processed --artifacts-dir artifacts
```

Nếu repo là private, bạn cần dùng GitHub token, SSH key, hoặc chọn cách upload
file zip/mount Google Drive thay vì clone public bằng HTTPS.

## Kiểm Tra Output

```python
import pandas as pd

train = pd.read_csv("data/processed/train.csv")
val = pd.read_csv("data/processed/validation.csv")
test = pd.read_csv("data/processed/test.csv")

print(train.shape, val.shape, test.shape)
print(train["is_man_of_match"].value_counts())
```

Các file output kỳ vọng:

- `data/processed/motm_model_ready.csv`
- `data/processed/train.csv`
- `data/processed/validation.csv`
- `data/processed/test.csv`
- `data/processed/data_quality_report.md`
- `artifacts/preprocessor.joblib`
- `artifacts/feature_columns.json`
