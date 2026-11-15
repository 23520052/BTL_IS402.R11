# cloud_cost_report.md – Chi phí & Quota Azure (TV3)

> **Ghi chú:** Báo cáo chi phí được tổng hợp từ *Azure Portal → Cost Management + Billing → Cost analysis* (minh chứng `evidence/azure-sql/30_cost_analysis_20261114.png` và các mốc đối chiếu), kết hợp tính toán đơn giá thực tế từ *Azure Pricing Calculator* theo giờ vận hành thực tế của các tài nguyên.

---

## 1. Danh mục tài nguyên phụ trách bởi TV3 (Database & Storage)

| Tài nguyên | Tier / Cấu hình | Region | Bắt đầu | Kết thúc / Xóa | Giờ chạy | Chi phí thực / Ước tính | Ghi chú |
|---|---|---|---|---|---|---|---|
| **Azure SQL `salesdb` (Main)** | Basic (5 DTU) $\rightarrow$ Standard S1 (20 DTU) $\rightarrow$ Basic (5 DTU) | East Asia | 08/11/2026 21:30 | Duy trì demo | Chạy liên tục (~170 giờ tính đến 15/11) | ~$1.25 | Nâng lên S1 trong 3 giờ (11:00–14:00 ngày 14/11) để đo benchmark 1GB; sau đó hạ về Basic ($4.99/tháng = $0.166/ngày). |
| **Azure SQL Far (`sqlsrv-sales-far-gr03`)** | Basic (5 DTU) | UAE North | 15/11/2026 17:30 | 15/11/2026 21:55 | ~4.5 giờ | ~$0.04 | Khởi tạo làm server đối chứng đo độ trễ liên vùng (Region Latency). Đơn giá UAE North: $6.46/tháng (~$0.0089/giờ). Đã xóa sạch ngay sau đo. |
| **Storage Account (`stsalesgr03...`)** | Standard general-purpose v2, LRS, Hot | East Asia | 09/11/2026 13:46 | Duy trì lưu trữ | Chạy liên tục | ~$0.02 | Container `benchmark-data` (Private). Lưu file mẫu và 1GB dữ liệu `sample_1gb.csv` đo tốc độ AzCopy. |
| **VM Benchmark (`vm-bench-gr03`)** | Standard_B2ats_v2 (2 vCPU, 1 GiB RAM), Ubuntu 24.04 LTS Gen2, Premium SSD 30GB | East Asia | 15/11/2026 17:45 | 15/11/2026 21:55 | ~4.2 giờ | ~$0.08 | VM Client đo độ trễ chuẩn cùng datacenter với SQL Main. Đơn giá VM: $0.0131/giờ; OS Disk + Public IP: ~$0.006/giờ. Đã xóa sạch (cả VM, Disk, NIC, IP). |
| **TỔNG CỘNG TV3** | | | | | | **~$1.39** | Ngân sách hạ tầng TV3 cực kỳ tối ưu, chiếm ~1.4% hạn mức credit $100. |

*(Lưu ý: Các dịch vụ Event Hubs và Azure Stream Analytics do TV2 phụ trách; Báo cáo Power BI do TV4 phụ trách).*

---

## 2. Chi phí riêng cho đợt thực nghiệm Benchmark (14/11 – 15/11)

- **Khoảng thời gian thực hiện:** Từ 11:00 ngày 14/11/2026 đến 22:00 ngày 15/11/2026.
- **Các khoản chi phí phát sinh riêng cho đợt đo đạc:**
  1. *Nâng tier Azure SQL Main lên Standard S1:* 3 giờ $\times$ $0.041/giờ = **~$0.123**.
  2. *Chạy Azure SQL Far (UAE North):* 4.5 giờ $\times$ $0.0089/giờ = **~$0.040**.
  3. *Chạy VM Client B2ats_v2 + Disk + IP:* 4.2 giờ $\times$ $0.0191/giờ = **~$0.080**.
  4. *AzCopy 1GB dữ liệu thô (Egress download quốc tế + Blob write transactions):* **~$0.015**.
- **Tổng chi phí đợt Benchmark:** **~$0.26** (xấp xỉ **6.500 VNĐ**). Chi phí thực nghiệm được kiểm soát ở mức tối thiểu nhờ chiến lược xóa tài nguyên ngay lập tức sau khi đo xong.

---

## 3. Quota & Ngân sách (FinOps Governance)

- **Budget Alert (`01_budget_alert.png`):**
  - Tên cấu hình: `budget-gr03`.
  - Phạm vi áp dụng: Toàn bộ Subscription / Resource Group `rg-sales-stream-gr03`.
  - Chu kỳ đặt lại: Monthly.
  - Ngưỡng cảnh báo tự động: Thiết lập ở mức **50%** ($50) và **80%** ($80) trên tổng hạn mức $100 của tài khoản Azure for Students, gửi cảnh báo trực tiếp về email thành viên khi chi phí thực tế chạm ngưỡng.
- **Giới hạn Subscription & Quota liên quan (`02_usage_quotas.png`):**
  - Chính sách Subscription Azure for Students áp dụng giới hạn vùng địa lý (Region Policy), chỉ cho phép khởi tạo tài nguyên tại 5 khu vực: `eastasia`, `koreacentral`, `uaenorth`, `centralindia`, `indiasouthcentral`.
  - Giới hạn kích thước VM: Dòng máy ảo thế hệ cũ `Standard_B1s` đã bước vào lộ trình ngừng hỗ trợ (Retiring) và không cho phép tạo cùng Ubuntu 24.04 Gen2 tại East Asia. Nhóm đã linh hoạt chuyển sang dòng `Standard_B2ats_v2` (B-series v2, 2 vCPU, 1 GiB RAM) với chi phí thấp tương đương ($0.0131/giờ).
  - Giới hạn DTU Database: Hạn mức DTU cơ bản đáp ứng tốt cho các tier từ Basic (5 DTU) đến Standard S1 (20 DTU).

---

## 4. Các biện pháp tối ưu chi phí đã áp dụng (FinOps Best Practices)

1. **Chiến lược co giãn linh hoạt (Elastic Scaling):**
   - Chỉ nâng Database lên Standard S1 (20 DTU, ~$30/tháng) trong đúng 3 tiếng ngày 14/11 để phục vụ nạp tải nặng 1GB cho bài test đọc/ghi.
   - Ngay sau khi hoàn thành đo đạc, lập tức hạ Service Tier về **Basic (5 DTU, $4.99/tháng)** để phục vụ lưu trữ kết quả và demo, giúp tiết kiệm **~83.3%** chi phí duy trì hàng ngày.
2. **Lưu trữ cục bộ tiết kiệm (LRS):**
   - Storage Account cấu hình chế độ sao lưu `Locally Redundant Storage (LRS)` thay vì GRS hay ZRS, giảm 50% chi phí lưu trữ cho các tập dữ liệu benchmark.
3. **Chính sách xóa sạch tài nguyên tạm thời (Ephemeral Resource Teardown):**
   - Server SQL vùng xa (`sqlsrv-sales-far-gr03`) và máy ảo benchmark (`vm-bench-gr03`) cùng toàn bộ tài nguyên phụ thuộc (OS Disk Premium SSD, Network Interface, Public IP) được xóa hoàn toàn ngay sau khi hoàn tất 2 lượt đo và xác minh tính toàn vẹn của dữ liệu CSV. Không để tài nguyên nhàn rỗi chạy qua đêm.
4. **Dọn dẹp bảng đệm và thu hồi đĩa:**
   - Xóa bỏ toàn bộ schema `bench.*` và các bảng tạm dung lượng lớn sau khi benchmark, thực thi lệnh `DBCC SHRINKDATABASE (0)` để giải phóng không gian lưu trữ vật lý về cho Azure SQL.

---

## 5. Bài học kinh nghiệm & Đề xuất kiến trúc

- **Khuyến nghị Service Tier cho luồng Streaming:**
  - Đối với bài toán trực quan dữ liệu thời gian thực có Stream Analytics gom cụm (tumbling window 30 giây đổ dữ liệu về database một lần), lưu lượng ghi chỉ dao động vài chục bản ghi mỗi đợt. Gói **Basic (5 DTU)** hoạt động ổn định với mức DTU tiêu thụ thực tế `< 10%`, hoàn toàn không bị trễ hay nghẽn cổ chai.
  - Gói **Standard S1 (20 DTU)** chỉ nên được kích hoạt trong các kịch bản nạp dữ liệu lịch sử ban đầu (Initial Bulk Load) hoặc bảo trì hệ thống để vượt qua giới hạn Transaction Log IO.
- **Tối ưu hóa vị trí địa lý (Co-location Strategy):**
  - Thí nghiệm thực tế giữa Client và Server chứng minh: Việc đặt ứng dụng và cơ sở dữ liệu cùng một Data Center (East Asia) giúp giảm độ trễ Ping từ **110 ms** (UAE North) xuống **0.85 ms** (nhanh hơn **~129 lần**), và thời gian truy vấn giảm từ **111 ms** xuống **1.08 ms** (nhanh hơn **~102 lần**). Khuyến nghị toàn bộ các thành phần trong kiến trúc Cloud (Event Hubs, Stream Analytics, Azure SQL, Web App) bắt buộc phải đặt đồng nhất tại cùng Region `East Asia`.
- **Dự toán ngân sách vận hành dài hạn:**
  - Chi phí duy trì hạ tầng cơ sở dữ liệu của dự án sau khi hoàn tất benchmark ước tính chỉ tốn khoảng **$5.10 / tháng** (~$0.17 / ngày), hoàn toàn khả thi cho các doanh nghiệp vừa và nhỏ vận hành hệ thống giám sát kinh doanh thời gian thực.
