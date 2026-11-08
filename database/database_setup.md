# database_setup.md – Azure SQL (TV3)

> Template: Agent/Trâm điền `[ĐIỀN ...]` từ thực tế. Không ghi mật khẩu/connection string.

## 1. Tài nguyên
| Mục | Giá trị |
|---|---|
| Subscription / Resource group | Azure for Students / `rg-sales-stream-gr03` |
| SQL server (logical) | `sqlsrv-sales-gr03-tram01.database.windows.net` |
| Database | `salesdb` |
| Region | East Asia (cùng region Event Hubs/ASA) |
| Tier | Basic (5 DTU) [Sprint 1] -> nâng Standard S1 (20 DTU) [T7 Benchmark], backup redundancy: LRS |
| Xác thực | SQL authentication; admin `sqladmin_gr03`; user `asa_writer` (INSERT/SELECT), `pbi_reader` (SELECT) |
| Network | Public endpoint + firewall theo IP; "Allow Azure services" = Yes |
| Storage account / container | [CHƯA TẠO - T4] / `benchmark-data` (private, LRS) |

## 2. Lý do chọn (ngắn)
- DTU Standard thay vì serverless: không tự ngủ ⇒ ASA/Power BI/benchmark ổn định, chi phí theo ngày dễ dự đoán.
- 2 bảng aggregate nhỏ (cửa sổ 30s/1m) thay vì lưu event thô: giảm số dòng ghi/đọc; Power BI DirectQuery nhẹ.
- 2 index `(window_end, run_id)` đúng theo truy vấn của dashboard/validation; không thêm index khi chưa có số đo.

## 3. Schema (Data Contract – freeze 08/11)
Xem `database/schema.sql`, `indexes.sql`. Quy ước: `window_end` UTC; `revenue` = tổng price của purchase event (không phải đơn hàng); brand thiếu = `unknown`.

## 4. Tái tạo từ đầu (thứ tự chạy trong Query editor)
1. `schema.sql` → 2. `indexes.sql` → 3. `create_users.sql` (đặt mật khẩu riêng, không commit) → 4. `seed_data.sql` (mock `mock-seed`) → 5. (tùy chọn) `rls_support.sql`.
Xác minh: `sql_validation.sql`. Xóa mock: `cleanup_runs.sql`.

## 5. Kết nối
| Bên dùng | Cách | Ghi chú |
|---|---|---|
| ASA (TV2) | Output SQL Database, SQL auth `asa_writer`, bảng `dbo.event_metrics_30s` / `dbo.brand_sales_1m` | cần "Allow Azure services" |
| Power BI Desktop (TV4) | Azure SQL database, DirectQuery, `pbi_reader` | thêm IP máy vào firewall |
| Script benchmark (TV3) | `pyodbc` + `database/.env` (không commit) | ODBC Driver 18 |

## 6. Vận hành
- Giới hạn đã biết: ASA ghi *at-least-once* ⇒ restart job có thể tạo dòng trùng; kiểm tra bằng `sql_validation.sql` [4].
- Dọn dẹp: xem Guide J; ghi ngày/giờ xóa: [ĐIỀN].
