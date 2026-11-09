# Hướng dẫn Thiết lập và Vận hành Cơ sở Dữ liệu Azure SQL (TV3)

Tài liệu kỹ thuật mô tả cấu hình hạ tầng, lược đồ dữ liệu, quy trình thiết lập lại từ đầu (reproduction), phân quyền bảo mật và quy chuẩn vận hành hệ thống cơ sở dữ liệu cho đồ án *Hệ thống trực quan dữ liệu bán hàng – xử lý luồng & phân tích thời gian thực trên Azure*.

---

## 1. Thông số Tài nguyên Đám mây
| Hạng mục | Giá trị Cấu hình | Ghi chú Kỹ thuật |
|---|---|---|
| **Subscription / Resource Group** | Azure for Students / `rg-sales-stream-gr03` | Tài nguyên dùng chung của nhóm đồ án |
| **Logical SQL Server** | `sqlsrv-sales-gr03-tram01.database.windows.net` | Cổng 1433, xác thực SQL Server Authentication |
| **Database Name** | `salesdb` | Cơ sở dữ liệu quan hệ chính |
| **Region** | **East Asia** (Hồng Kông) | Cùng region với Event Hubs và Stream Analytics |
| **Service Tier** | Basic (5 DTU, 2 GB) $\rightarrow$ Standard S1 (20 DTU, 32 GB) | Basic cho Sprint 1; nâng S1 khi thực hiện đo benchmark |
| **Sao lưu & Dự phòng** | Locally-Redundant Storage (LRS) | Dự phòng cục bộ tối ưu hóa chi phí |
| **Phân quyền Cơ sở dữ liệu** | `sqladmin_gr03` (Admin), `asa_writer` (Ghi), `pbi_reader` (Đọc) | Nguyên tắc đặc quyền tối thiểu (Least Privilege) |
| **Chính sách Tường lửa** | Public Endpoint + Whitelist IP + Allow Azure Services | Mở cổng nội bộ cho ASA và IP nhà phát triển |
| **Blob Storage / Container** | `stsalesgr03tram01` / `benchmark-data` | Lưu trữ file kết quả đo lường và artifact |

---

## 2. Cơ sở Thiết kế & Lựa chọn Kiến trúc
* **Lựa chọn mô hình DTU thay vì Serverless:**
  - Mô hình DTU (Provisioned Compute) duy trì tài nguyên hoạt động liên tục, không xảy ra hiện tượng tự động tạm dừng (auto-pause / cold start) như mô hình Serverless. Điều này đảm bảo tính ổn định cho đường ống truyền dữ liệu thời gian thực của Azure Stream Analytics và kết nối DirectQuery của Power BI, đồng thời cho phép dự toán chi phí cố định chính xác theo ngày.
* **Chiến lược lưu trữ theo tầng (Tiered Storage Strategy):**
  - Không lưu trữ toàn bộ dữ liệu sự kiện thô (raw events) vào SQL Database. Dữ liệu được tổng hợp theo các cửa sổ thời gian (tumbling window 30 giây và 1 phút) tại tầng Stream Analytics trước khi nạp vào cơ sở dữ liệu quan hệ, giúp giảm thiểu đáng kể số lượng I/O ghi và tối ưu hóa chi phí điện toán đám mây.
* **Tối ưu hóa truy vấn thông qua chỉ mục (Indexing Strategy):**
  - Cả hai bảng aggregate được đánh chỉ mục phức hợp trên cặp khóa `(window_end, run_id)`. Đây là điều kiện lọc chính của các câu truy vấn thời gian thực từ bảng điều khiển BI và các tập lệnh kiểm định tính đúng đắn (validation queries).

---

## 3. Quy chuẩn Hợp đồng Dữ liệu (Data Contract)
Dữ liệu đích gồm 2 bảng quan hệ chuẩn hóa tại schema `dbo`:
1. **`dbo.event_metrics_30s`:**
   - `window_end` (`DATETIME2`, NOT NULL): Mốc thời gian kết thúc cửa sổ 30 giây theo chuẩn UTC.
   - `run_id` (`NVARCHAR(50)`, NOT NULL): Định danh của phiên phát luồng streaming.
   - `event_type` (`NVARCHAR(30)`, NOT NULL): Loại sự kiện (`view`, `cart`, `remove_from_cart`, `purchase`).
   - `event_count` (`BIGINT`, NOT NULL): Tổng số lượng sự kiện ghi nhận trong cửa sổ.
   - `revenue` (`FLOAT`, NOT NULL): Tổng giá trị giá bán (`price`) của các sự kiện mua hàng (`purchase`).
2. **`dbo.brand_sales_1m`:**
   - `window_end` (`DATETIME2`, NOT NULL): Mốc thời gian kết thúc cửa sổ 1 phút theo chuẩn UTC.
   - `run_id` (`NVARCHAR(50)`, NOT NULL): Định danh của phiên phát luồng streaming.
   - `brand` (`NVARCHAR(200)`, NOT NULL): Tên thương hiệu. Giá trị rỗng được chuẩn hóa thành `'unknown'` thông qua hàm `COALESCE`.
   - `purchase_events` (`BIGINT`, NOT NULL): Số sự kiện mua hàng của thương hiệu trong 1 phút.
   - `revenue` (`FLOAT`, NOT NULL): Tổng doanh thu tương ứng của thương hiệu trong 1 phút.

---

## 4. Quy trình Tái tạo Hệ thống từ Đầu (Step-by-Step Reproduction)
Quy trình thực thi tuần tự các tập lệnh SQL thông qua Azure Portal Query Editor, Azure Data Studio hoặc SQLCMD bằng tài khoản quản trị `sqladmin_gr03`:

1. **Khởi tạo bảng (`database/schema.sql`):**
   - Thực thi tạo 2 bảng `dbo.event_metrics_30s` và `dbo.brand_sales_1m`. Script có tính chất idempotent (`IF OBJECT_ID ... IS NULL`), đảm bảo an toàn khi chạy lại.
2. **Khởi tạo chỉ mục (`database/indexes.sql`):**
   - Tạo 2 chỉ mục `ix_metrics_window` và `ix_brand_window` trên cột `(window_end, run_id)`.
3. **Khởi tạo người dùng và phân quyền (`database/create_users.sql`):**
   - Tạo 2 tài khoản cơ sở dữ liệu độc lập (contained database users):
     - `asa_writer`: Được cấp quyền `SELECT, INSERT` trên schema `dbo`.
     - `pbi_reader`: Chỉ được cấp quyền `SELECT` trên schema `dbo`.
4. **Nạp dữ liệu giả lập ban đầu (`database/seed_data.sql`):**
   - Sinh dữ liệu mẫu mô phỏng cho 60 phút gần nhất với `run_id = 'mock-seed'` phục vụ kiểm thử giao diện Power BI trước khi kết nối luồng streaming thật.
5. **(Tùy chọn) Cấu hình Row-Level Security (`database/rls_support.sql`):**
   - Áp dụng chính sách bảo mật cấp dòng nếu dashboard yêu cầu phân quyền hiển thị theo thương hiệu.
6. **Kiểm tra tính toàn vẹn (`database/sql_validation.sql`):**
   - Thực thi các khối kiểm định [1], [4], [5] để xác nhận số lượng bản ghi, không có khóa trùng lặp và không có dữ liệu dị biệt.

---

## 5. Phương thức Kết nối và Tích hợp Thành phần
| Thành phần Tích hợp | Phương thức Kết nối | Cơ chế Xác thực & Phân quyền | Ghi chú Triển khai |
|---|---|---|---|
| **Azure Stream Analytics (ASA)** | Azure SQL Database Output Adapter | SQL Authentication (`asa_writer`) | Yêu cầu kích hoạt *Allow Azure services* |
| **Power BI Desktop** | SQL Server Connector (DirectQuery) | SQL Authentication (`pbi_reader`) | Yêu cầu thêm IP máy trạm vào Firewall |
| **Tập lệnh Đo tải & Benchmark** | Python `pyodbc` / Microsoft `sqlcmd` | SQL Authentication (`asa_writer` / Admin) | Yêu cầu ODBC Driver 18 và chuỗi kết nối an toàn |

---

## 6. Hướng dẫn Vận hành và Dọn dẹp Tài nguyên
* **Xóa dữ liệu kiểm thử (Mock Data Cleanup):**
  - Trước khi tiến hành tiếp nhận luồng dữ liệu thật hoặc chạy demo chính thức, thực thi script `database/cleanup_runs.sql` để xóa sạch các bản ghi mang mã `run_id = 'mock-seed'`. Tuyệt đối không xóa các run chứa dữ liệu đối chiếu thật (`integration-*`, `demo-*`).
* **Theo dõi giám sát tài nguyên (Monitoring):**
  - Định kỳ giám sát tỷ lệ tiêu thụ DTU, CPU percentage và Data IO percentage thông qua Azure Monitor Metrics và Dynamic Management View `sys.dm_db_resource_stats`.
* **Kế hoạch giải phóng tài nguyên (Decommissioning):**
  - Toàn bộ cơ sở dữ liệu và tài khoản lưu trữ được duy trì đến khi hoàn tất việc đánh giá và nghiệm thu đồ án. Sau thời điểm nghiệm thu, thực hiện xóa bỏ Resource Group `rg-sales-stream-gr03` để chấm dứt hoàn toàn chi phí phát sinh.
