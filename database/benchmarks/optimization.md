# optimization.md – Tối ưu lưu trữ & tốc độ đọc/ghi (TV3)

> Quy tắc: mỗi dòng số liệu trích từ `read_write_results.csv` (ghi rõ `test`, `size_label`, `target`, median của n lần). Chưa đo = `[CHƯA ĐO]`, không điền số. Điều kiện đo: [ĐIỀN tier/region/client/mạng].

## Tóm tắt
| # | Giải pháp | Trước | Sau | Cải thiện | Đánh đổi | Áp dụng cho hệ thống? |
|---|---|---|---|---|---|---|
| 1 | Aggregate trước khi ghi (ASA window) | [ĐIỀN: số event thô] | [ĐIỀN: số dòng ghi] | [ĐIỀN] | Mất chi tiết từng event | Đã áp dụng |
| 2 | Index `(window_end, run_id)` khi đọc | `filter_range_noindex` [ĐIỀN] s | `filter_range_indexed` [ĐIỀN] s | [ĐIỀN] | Tốn [ĐIỀN] MB + chậm ghi | [ĐIỀN] |
| 3 | Index khi ghi (chi phí) | `write_b1000_n100000_noidx` [ĐIỀN] rows/s | `..._idx` [ĐIỀN] rows/s | [ĐIỀN] | – | [ĐIỀN] |
| 4 | Batch size khi ghi | `write_single_n1000_noidx` [ĐIỀN] rows/s | `write_b1000_...` [ĐIỀN] rows/s | [ĐIỀN] | Độ trễ cửa sổ | [ĐIỀN] |
| 5 | Nén PAGE | `scan_uncompressed` [ĐIỀN] s, [ĐIỀN] MB | `scan_page_compressed` [ĐIỀN] s, [ĐIỀN] MB | [ĐIỀN] | CPU, thời gian rebuild | [ĐIỀN] |
| 6 | Chọn tier phù hợp | [ĐIỀN: DTU% khi benchmark] | – | – | Chi phí/ngày | [ĐIỀN] |
| 7 | Blob cho dữ liệu thô/log (lý thuyết + số đo upload/download) | – | – | – | – | [ĐIỀN] |

## Chi tiết từng giải pháp
Mỗi mục: **Vấn đề → Thay đổi → Số đo (trích dòng CSV) → Vì sao (cơ chế) → Đánh đổi → Kết luận**.

### 1. Aggregate trước khi ghi
- Số liệu: khối [9] `sql_validation.sql` (run `integration-01`).
- Cơ chế: SQL chỉ nhận số tổng theo cửa sổ nên số dòng ghi ≪ số event; số nhóm brand được giới hạn bởi cardinality (brand thiếu → `unknown`).

### 2–3. Index (đọc nhanh hơn, ghi chậm hơn)
### 4. Batch size
### 5. Nén PAGE
### 6. Tier
### 7. Blob

## Khuyến nghị cuối cùng cho dự án
[ĐIỀN sau khi có số đo: giữ 2 index; batch ...; tier ...]

## Hạn chế của phép đo
- Dữ liệu benchmark do server sinh theo schema dataset (không phải 100% dữ liệu thật); warm cache; chạy từ 1 máy client; local vs Azure khác phần cứng/phiên bản ⇒ so sánh chỉ mang tính tham khảo cùng workload. [BỔ SUNG nếu có]
