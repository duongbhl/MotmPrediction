# Dự án: Dự đoán cầu thủ xuất sắc nhất trận đấu Premier League

## Mục tiêu
Xây dựng hệ thống dự đoán MVP (cầu thủ xuất sắc nhất) cho từng trận đấu Premier League, cung cấp web app nhập thông tin trận đấu và trả về dự đoán cầu thủ.

## Quy trình & các bước phát triển

### 1. Tiền xử lý dữ liệu
- Crawl, làm sạch và chuẩn hóa dữ liệu (đã xong).
- Feature engineering: tạo thêm các đặc trưng giúp mô hình học tốt hơn (VD: phong độ, vị trí, thống kê cá nhân/trận,...). KHÔI

### 2. Xây dựng & đánh giá AI Model: NHI
- Chia tập train/val/test.
- Lựa chọn mô hình học máy phù hợp (Logistic, Random Forest, XGBoost, Neural Network,...).
- Đánh giá và chọn ra mô hình tốt nhất.
- Lưu lại mô hình (pickle/joblib).

### 3. API hóa mô hình: KHÔI
- Dùng Flask hoặc FastAPI tạo API endpoint `/predict`, nhận thông tin trận đấu, trả về dự đoán (cầu thủ xuất sắc nhất).
- Ví dụ request:
    ```json
    {
      "home_team": "...",
      "away_team": "...",
      "player_stats": [...],
      ... (các trường cần thiết khác)
    }
    ```
- Response: trả về tên cầu thủ xuất sắc nhất trận đấu.

### 4. Xây dựng giao diện web (UI): BÁCH
- Giao diện đơn giản với các thành phần:
    - Form nhập đội hình thi đấu, thông số trận.
    - Nút [Dự đoán].
    - Kết quả dự đoán: tên cầu thủ MVP, thông tin nổi bật, hình ảnh (nếu có).
- Có thể dùng:  
    - **Streamlit/Dash:** kết hợp trực tiếp với Python/API.
    - **Tách backend (Python API) & frontend (ReactJS/VueJS/HTML).**

### 5. Kết nối AI Model với UI: DƯƠNG VS DUKKU
- UI gửi yêu cầu dự đoán (HTTP POST/GET) tới endpoint của API.
- Nhận kết quả và hiển thị đẹp mắt cho người dùng.
- Xử lý hợp lệ, thông báo lỗi khi cần.

### 6. Triển khai hệ thống
- Deploy toàn bộ hệ thống (API + UI) lên cloud (Heroku, Render, Vercel, ...).
- Hướng dẫn sử dụng, demo, link trải nghiệm (nếu có).

---

## Chức năng Web App

- Nhập thông tin trận đấu (đội, cầu thủ, thống kê, tỉ số).
- Gửi, nhận và hiển thị kết quả dự đoán MVP.
- Giao diện đơn giản, dễ dùng.
- Sẵn sàng mở rộng cho nhiều giải đấu khác nếu muốn.

## Hướng dẫn cài đặt & chạy thử

1. Clone repo:
    ```
    git clone https://github.com/duongbhl/MotmPrediction.git
    cd MotmPrediction
    ```

2. Cài đặt môi trường:
    ```
    pip install -r requirements.txt
    ```

3. Train model/dùng model mẫu.

4. Chạy API server dự đoán:
    ```
    python api_server.py
    ```

5. (Tùy chọn) Chạy UI (Streamlit hoặc web front-end riêng).

6. Truy cập app, nhập thông tin trận đấu và trải nghiệm dự đoán cầu thủ xuất sắc nhất trận!

---

## Contributing & License
- Mọi đóng góp, phản hồi xin gửi Issue hoặc Pull Request.
- License: MIT (hoặc khác tùy dự án).
