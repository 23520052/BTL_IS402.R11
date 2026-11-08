# 03 – Cơ sở dữ liệu, lưu trữ cloud & hiệu năng (TV3)

> Template bám rubric. Điền bằng số liệu thật từ repo. Mọi bảng/hình có số + chú thích; nguồn ở mục 8. Ảnh trong `evidence/azure-sql/`.

## 1. Loại dữ liệu và bài toán lưu trữ  *(rubric 1.2)*
- Dữ liệu nguồn: CSV 9 cột, [ĐIỀN] triệu event (TV1) → bán cấu trúc (JSON event) → **aggregate có cấu trúc** (2 bảng SQL) phục vụ Power BI.
- Vì sao cần cả SQL và Blob: [ĐIỀN – SQL cho truy vấn theo cửa sổ/dashboard; Blob cho file mẫu, log, benchmark].
- Giới hạn dữ liệu: không có `order_id` → "purchase event" ≠ đơn hàng.

## 2. Dịch vụ cloud TV3 thuộc nhóm nào  *(rubric 1.4)*
| Dịch vụ | Nhóm | Lý do |
|---|---|---|
| Azure SQL Database | PaaS | Azure quản lý hạ tầng, vá lỗi, sao lưu; người dùng quản lý schema/dữ liệu |
| Azure Blob Storage | PaaS (dịch vụ lưu trữ) | [ĐIỀN] |
| VM benchmark (nếu dùng) | IaaS | [ĐIỀN] |
| Power BI Service (TV4) | SaaS | [ĐIỀN] |

## 3. Cơ sở lý thuyết: định dạng lưu trữ  *(rubric 2.1)*
So sánh CSV / JSON / bảng quan hệ (SQL, index) / Blob object: cấu trúc, kích thước, tốc độ đọc theo truy vấn, ràng buộc, khi nào dùng. Bảng so sánh: [ĐIỀN]. Áp dụng vào dự án: [ĐIỀN].

## 4. Cơ sở lý thuyết: dịch vụ cloud sử dụng  *(rubric 2.3)*
- Azure SQL Database: mô hình DTU (CPU+IO+log), service tier Basic/Standard/Premium, backup & redundancy (LRS), firewall + user quyền tối thiểu, DMV `sys.dm_db_resource_stats`. [ĐIỀN – dẫn nguồn]
- Azure Blob Storage: storage account, container, access tier, redundancy, SAS. [ĐIỀN]
- Cost Management: budget, cost analysis, quota. [ĐIỀN]

## 5. Mô hình dữ liệu và kiến trúc lưu trữ
Sơ đồ bảng + quan hệ với ASA/Power BI: [HÌNH – ĐIỀN]. Schema: `dbo.event_metrics_30s`, `dbo.brand_sales_1m` (bảng + cột + ý nghĩa). Index và lý do. Dữ liệu mock vs thật (`run_id`).

## 6. Kết quả đo  *(rubric 3.1, 3.3)*
### 6.1 Tốc độ đọc/ghi theo dung lượng
Môi trường: [ĐIỀN]. Phương pháp: `sql_benchmark.py` (nêu suite, mốc dung lượng, số lần lặp). Bảng + biểu đồ `read_scan_time.png`, `write_throughput.png`: [ĐIỀN].
### 6.2 Máy chủ truyền thống (SQL Server local) vs cloud (Azure SQL)  *(rubric 1.3)*
Cấu hình hai bên (CPU/RAM/ổ đĩa/tier) và kết quả cùng workload: [ĐIỀN]. **Giới hạn khoa học**: khác phần cứng, phiên bản, mạng; không khẳng định chênh lệch thuần của "cloud vs on-premise".
### 6.3 Độ trễ khác region
Thiết kế phép đo (1 client, 2 server, xen kẽ; tcp/ping/query/login; p50/p95; n mẫu; ≥2 lượt): [ĐIỀN]. Bảng + `region_latency.png`. Hạn chế: [ĐIỀN].
### 6.4 Blob upload/download
`blob_transfer_results.csv`: [ĐIỀN].
### 6.5 Độ trễ cập nhật pipeline
`lag_seconds` (khối [7]) cho run [ĐIỀN]: [ĐIỀN]; phụ thuộc cửa sổ ASA 30s/1m + ghi SQL + refresh Power BI.

## 7. Tối ưu  *(rubric 3.4)*
Tóm tắt từ `database/benchmarks/optimization.md` (bảng trước/sau) + khuyến nghị. Chi phí & quota: tóm tắt từ `cloud_cost_report.md` (bảng + ảnh Cost analysis).
Đối chiếu tính đúng: `validation_integration-01.txt` [ĐIỀN: PASS / lệch + giải thích].

## 8. Quản lý tài nguyên nhóm
Resource group chung, IAM 4 thành viên (`08_iam_role_assignments.png`), budget alert, quy trình dọn dẹp.

## 9. Kết luận, hạn chế, hướng cải tiến
[ĐIỀN]

## Tài liệu tham khảo
- Azure SQL Database – DTU-based purchasing model (Microsoft Learn): [ĐIỀN URL đã mở]
- sys.dm_db_resource_stats: [ĐIỀN URL]
- Azure Blob Storage introduction / redundancy: [ĐIỀN URL]
- Azure Cost Management budgets: [ĐIỀN URL]
- Dataset Kaggle eCommerce Behavior Data (mkechinov)
