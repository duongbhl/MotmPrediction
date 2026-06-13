# Dự án: Dự đoán cầu thủ xuất sắc nhất trận đấu Premier League

## Mục tiêu

Xây dựng pipeline dữ liệu và mô hình dự đoán MOTM (Man of the Match) cho từng
trận đấu Premier League. Ở giai đoạn hiện tại, project tập trung vào bước
chuẩn hóa dữ liệu đầu vào và tạo dataset sẵn sàng cho modeling.

## Trạng thái hiện tại

- Dữ liệu nguồn chính: `PlayerCrawl.xlsx`.
- Pipeline transform chính: `src/transform_motm_data.py`.
- Output sinh ra sau transform:
  - `data/processed/motm_model_ready.csv`
  - `data/processed/train.csv`
  - `data/processed/validation.csv`
  - `data/processed/test.csv`
  - `data/processed/data_quality_report.md`
  - `artifacts/preprocessor.joblib`
  - `artifacts/feature_columns.json`

Lưu ý: không dùng `motm_clean.xlsx` hoặc
`PlayerCrawl_normalized_standard.xlsx` làm input cho pipeline transform vì các
file này có thể chứa lỗi numeric/normalization từ các bước thử nghiệm trước.

## Cài đặt và chạy local

Clone project:

```bash
git clone https://github.com/duongbhl/MotmPrediction.git
cd MotmPrediction
```

Cài đặt thư viện:

```bash
pip install -r requirements.txt
```

Chạy pipeline transform:

```bash
python src/transform_motm_data.py --input PlayerCrawl.xlsx --out-dir data/processed --artifacts-dir artifacts
```

Chạy unit test:

```bash
python -m unittest discover -s tests
```

## Chạy transform dữ liệu trên Google Colab

Project có thể chạy trực tiếp trên Google Colab sau khi đã được push lên GitHub.
Cách nhanh nhất là clone repo trong Colab:

```bash
!git clone https://github.com/duongbhl/MotmPrediction.git
%cd MotmPrediction
!pip install -r requirements.txt
!python src/transform_motm_data.py --input PlayerCrawl.xlsx --out-dir data/processed --artifacts-dir artifacts
```
Trong backend cai: pip install -r requirements.txt
Hướng dẫn đầy đủ, bao gồm cách upload zip, dùng Google Drive và clone từ
GitHub, nằm trong `docs/colab_run_guide.md`.

Trước khi chạy bằng cách clone từ GitHub, hãy đảm bảo các file mới như
`requirements.txt`, `src/`, `docs/`, `tests/` và `PlayerCrawl.xlsx` đã được
commit/push lên repo.

## Quy trình phát triển tiếp theo

1. Chuẩn hóa và transform dữ liệu.
2. Chọn mô hình phù hợp và đánh giá trên train/validation/test.
3. Lưu model tốt nhất bằng `joblib` hoặc `pickle`.
4. Xây API dự đoán bằng Flask hoặc FastAPI.
5. Xây UI để nhập thông tin trận đấu và hiển thị cầu thủ MOTM dự đoán.

## Contributing & License

- Mọi đóng góp, phản hồi xin gửi Issue hoặc Pull Request.
- License: MIT hoặc điều chỉnh theo quyết định của nhóm.
