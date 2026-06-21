# Phân tích các trường dữ liệu — MOTM Predictor


---

## 1. Nhóm: Định danh & ngữ cảnh trận đấu

| Trường | Ý nghĩa | Cần cho MOTM? |
|---|---|---|
| `match_id` | ID trận đấu (WhoScored internal) | Chỉ dùng làm key join |
| `match_date` | Ngày thi đấu | ✅ Cần để tính rolling form |
| `season` | Mùa giải (vd: `2025/2026`) | ✅ Cần để lọc / group dữ liệu |
| `home_team` | Đội chủ nhà | ⚠️ Có thể encode sức mạnh đội |
| `away_team` | Đội khách | ⚠️ Có thể encode sức mạnh đội |
| `home_score` | Số bàn đội chủ nhà | ⚠️ Dùng tính score margin (gián tiếp) |
| `away_score` | Số bàn đội khách | ⚠️ Dùng tính score margin (gián tiếp) |

---

## 2. Nhóm: Định danh cầu thủ

| Trường | Ý nghĩa | Cần cho MOTM? |
|---|---|---|
| `player_id` | ID cầu thủ | ✅ Cần để join & tính rolling stats |
| `name` | Tên cầu thủ | ⚠️ Chỉ dùng debug / display |
| `team` | Đội của cầu thủ | ✅ Cần cho team context |


---

## 3. Nhóm: Trạng thái ra sân

| Trường | Ý nghĩa | Cần cho MOTM? |
|---|---|---|
| `is_home` | Cầu thủ đá sân nhà không (0/1) | ✅ Giữ — lợi thế sân nhà |
| `position` | Vị trí (`GK`, `DC`, `MC`, `FW`...) | ✅ **Rất quan trọng** — normalize stats theo vị trí |
| `is_first_eleven` | Đá chính không (0/1) | ✅ **Quan trọng** — Sub hiếm khi được MOTM |
| `minutes_played` | Số phút thi đấu | ✅ **Quan trọng** — phải đá đủ phút mới eligible |


---

## 4. Nhóm: Chỉ số kỹ thuật (Features chính)

| Trường | Ý nghĩa | Cần cho MOTM? |
|---|---|---|
| `rating` | Rating WhoScored (0–10) | ✅ **Cực quan trọng** — tương quan cao nhất với MOTM |
| `goals` | Số bàn thắng | ✅ **Rất quan trọng** |
| `assists` | Số kiến tạo | ✅ **Rất quan trọng** |
| `shots_total` | Tổng số cú sút | ✅ Quan trọng (tấn công) |
| `shots_on_target` | Số cú sút trúng đích | ✅ Quan trọng |
| `key_passes` | Đường chuyền tạo cơ hội | ✅ Quan trọng |
| `passes_completed` | Số đường chuyền thành công | ✅ Giữ |
| `passes_total` | Tổng đường chuyền | ✅ Giữ |
| `pass_accuracy` | % chuyền thành công | ⚠️ **Có thể bỏ** — bị derive từ `passes_completed / passes_total` |
| `tackles` | Số lần tắc bóng | ✅ Quan trọng (hậu vệ / tiền vệ) |
| `interceptions` | Số lần cắt bóng | ✅ Quan trọng |
| `clearances` | Số lần phá bóng | ✅ Quan trọng (trung vệ) |
| `aerial_won` | Duel trên không thắng | ✅ Giữ |
| `aerial_lost` | Duel trên không thua | ⚠️ Nên tính `aerial_win_rate` rồi bỏ 2 cột gốc |
| `dribbles_won` | Số lần dribble thành công | ✅ Quan trọng (tiền đạo / tiền vệ) |
| `dribbles_attempted` | Tổng số lần dribble | ⚠️ Nên tính `dribble_success_rate` rồi bỏ |
| `fouls_committed` | Số lần phạm lỗi | ✅ Giữ (negative signal) |
| `saves` | Số lần cứu thua | ⚠️ Chỉ cần thiết cho `GK` |

---

## 5. Nhóm: Trường RỖNG HOÀN TOÀN ❌

> Các trường này có **mean = 0, std = 0, max = 0** — không crawl được dữ liệu. Cần xóa.

| Trường | Vấn đề |
|---|---|
| `big_chances_created` | Toàn số 0 |
| `big_chances_missed` | Toàn số 0 |



## 6. Tóm tắt: Nên xử lý thế nào?

### ❌ Bỏ hoàn toàn (vô ích)
```
big_chances_created, big_chances_missed,
yellow_cards, red_cards,
competition, shirt_no, fouls_drawn
```

### 🔄 Tạo derived feature rồi bỏ cột gốc
| Cột gốc | Derived feature |
|---|---|
| `aerial_won`, `aerial_lost` | `aerial_win_rate = aerial_won / (aerial_won + aerial_lost)` |
| `dribbles_won`, `dribbles_attempted` | `dribble_success_rate = dribbles_won / dribbles_attempted` |
| `passes_completed`, `passes_total` | Đã có `pass_accuracy`, bỏ 1 trong 3 |

### ✅ Giữ nguyên làm features
```
rating, goals, assists,
shots_total, shots_on_target, key_passes,
passes_completed, passes_total,
tackles, interceptions, clearances,
aerial_won, aerial_lost, dribbles_won,
fouls_committed, saves,
minutes_played, is_first_eleven,
position, is_home, age
```

### 🎯 Target label
```
is_man_of_match
```

---

## 7. Phân phối vị trí cầu thủ

| Position | Số lượng |
|---|---|
| Sub (dự bị) | 6.828 |
| DC (trung vệ) | 1.695 |
| DMC (tiền vệ phòng ngự) | 856 |
| MC (tiền vệ) | 832 |
| FW (tiền đạo) | 815 |
| GK (thủ môn) | 760 |
| AMC (tiền vệ tấn công) | 672 |
| DR / DL (hậu vệ cánh) | 605 / 605 |
| AMR / AML (tiền vệ lệch cánh) | 411 / 411 |
| Khác (DMR, DML, FWR, FWL, MR, ML) | < 150 mỗi loại |

> **Lưu ý:** Sub chiếm 45% dữ liệu — nên lọc `minutes_played >= 45` hoặc `is_first_eleven == 1` trước khi train.
