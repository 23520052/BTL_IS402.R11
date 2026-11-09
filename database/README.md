# database/ – Azure SQL (TV3)

Tài liệu quản lý cơ sở dữ liệu và bàn giao kỹ thuật cho nhóm (TV2, TV4, TV1).

## 1. Thông tin kết nối Azure SQL
| Mục | Giá trị |
|---|---|
| **Server** | `sqlsrv-sales-gr03-tram01.database.windows.net` |
| **Database** | `salesdb` |
| **Region** | **East Asia** (Cả nhóm thống nhất dùng chung region này) |
| **Cấu hình (Tier)** | Basic (5 DTU) – Giai đoạn Sprint 1; nâng S1 khi benchmark |
| **Mật khẩu & User** | TV3 gửi qua kênh riêng an toàn, không commit lên repo |

---

## 2. Hợp đồng dữ liệu (Data Contract – Freeze 08/11/2026)
> *Quy ước bất biến: Không tự ý đổi tên bảng, tên cột, kiểu dữ liệu nếu chưa có sự đồng thuận của TV2 + TV4.*

* **Bảng 1:** `dbo.event_metrics_30s`
  - `window_end` (`DATETIME2`, NOT NULL): Giờ UTC kết thúc cửa sổ (System.Timestamp() từ ASA).
  - `run_id` (`NVARCHAR(50)`, NOT NULL): Mã đợt chạy (ví dụ `mock-seed`, `integration-01`).
  - `event_type` (`NVARCHAR(30)`, NOT NULL): Loại sự kiện (`view`, `cart`, `remove_from_cart`, `purchase`).
  - `event_count` (`BIGINT`, NOT NULL): Số lượng sự kiện trong cửa sổ 30s.
  - `revenue` (`FLOAT`, NOT NULL): Tổng price của purchase event (không gọi là đơn hàng, không đổi đơn vị tiền).

* **Bảng 2:** `dbo.brand_sales_1m`
  - `window_end` (`DATETIME2`, NOT NULL): Giờ UTC kết thúc cửa sổ 1 phút.
  - `run_id` (`NVARCHAR(50)`, NOT NULL): Mã đợt chạy.
  - `brand` (`NVARCHAR(200)`, NOT NULL): Tên thương hiệu. Brand thiếu bắt buộc phải thành `'unknown'` (TV2 xử lý bằng `COALESCE(brand, 'unknown')` trong query ASA).
  - `purchase_events` (`BIGINT`, NOT NULL): Số sự kiện purchase của brand trong 1 phút.
  - `revenue` (`FLOAT`, NOT NULL): Doanh thu của brand trong 1 phút.

* **Index:** Cả 2 bảng đã được đánh index `(window_end, run_id)` để tối ưu hóa truy vấn DirectQuery cho Power BI và validation.
* **Mock data:** Đã nạp sẵn dữ liệu giả lập 60 phút gần nhất (`run_id = 'mock-seed'`). TV4 có thể kết nối kiểm tra dashboard ngay.

---

## 3. Phân quyền người dùng (User Roles)
* **`asa_writer` (Dành cho Huy - TV2):** 
  - Quyền: `SELECT`, `INSERT` trên schema `dbo`.
  - Mục đích: Stream Analytics ghi dữ liệu đầu ra vào 2 bảng aggregate.
  - Trạng thái: **Đã tạo trên DB, sẵn sàng kết nối.**
* **`pbi_reader` (Dành cho Nam - TV4):**
  - Quyền: `SELECT` (Chỉ đọc) trên schema `dbo`.
  - Mục đích: Power BI Desktop kết nối DirectQuery vẽ biểu đồ.
  - Trạng thái: **Đã tạo trên DB, chờ TV4 gửi IP public để mở Firewall.**

---

## 4. Tiến độ TV3 (Database & Cloud Engineer)
| Ngày | Hạng mục | Trạng thái | Minh chứng |
|---|---|---|---|
| **08/11** | Khởi tạo Budget alert, Usage & Quotas | **Hoàn thành** | `01_budget_alert.png`, `02_usage_quotas.png` |
| **08/11** | Dựng Azure SQL (`salesdb`, East Asia, Basic 5 DTU) | **Hoàn thành** | `03_sql_overview.png`, `04_sql_compute_tier.png` |
| **08/11** | Chạy Schema, Index, tạo User (`asa_writer`, `pbi_reader`), nạp Seed data | **Hoàn thành** | `06_tables_created.png`, `07_seed_check.png` |
| **08/11** | Phân quyền thành viên nhóm Contributor trên RG (IAM) | **Hoàn thành** | `08_iam_role_assignments.png` |
| **09/11** | Mở Firewall IP cho thành viên nhóm (TV3, TV4, TV2) | **Hoàn thành** | `05_firewall_rules.png` |
| **09/11** | Kiểm tra quyền chỉ đọc của `pbi_reader` (SELECT OK, DELETE Denied) | **Hoàn thành** | `12_pbi_reader_readonly.png` |
| **09/11** | Làm mới dữ liệu mock `seed_data.sql` (cửa sổ thời gian hiện tại) & kiểm thử `sql_validation.sql` | **Hoàn thành** | Query validation test passed |
| **09/11** | Đối chiếu Data Contract với TV1 (`data_contract.json`, `sample_events.json`) | **Hoàn thành** | Schema freeze, tương thích 100% |
| **09/11** | Tạo Blob Storage Account (`stsalesgr03tram01`) & container `benchmark-data` | **Hoàn thành** *(Vượt tiến độ 10/11)* | `09_storage_container.png` |
| **10/11** | Bàn giao kết nối ghi cho TV2 (ASA) & script test quyền ghi `asa_writer` | Đúng tiến độ | Theo plan |
