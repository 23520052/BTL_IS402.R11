# optimization.md – Tối ưu lưu trữ & tốc độ đọc/ghi (TV3)

> **Điều kiện thực nghiệm:**
> - **Azure SQL Database:** Tier Standard S1 (20 DTU, 250 GB Storage, Region East Asia).
> - **Local SQL Server:** Microsoft SQL Server 2022 CU trên Docker `sqlbench` (Linux container, cấp 4 CPU, 8GB RAM).
> - **Client môi trường đo:** AMD Ryzen 7 16-cores, 32GB RAM, SSD NVMe, Windows 11 Pro, Python 3.11 (`.venv`), ODBC Driver 18 for SQL Server.
> - **Quy tắc số liệu:** Toàn bộ số liệu dưới đây được trích xuất từ giá trị trung vị (median) của các lần lặp thực tế trong file `database/benchmarks/read_write_results.csv` (chạy ngày 14/11/2026).

---

## Bảng tổng hợp các giải pháp tối ưu

| # | Giải pháp | Trước tối ưu | Sau tối ưu | Mức độ cải thiện | Đánh đổi (Trade-off) | Áp dụng cho hệ thống? |
|---|---|---|---|---|---|---|
| **1** | **Aggregate trước khi ghi (ASA Windowing)** | 10.000 raw events | 30 dòng (`event_metrics_30s`)<br>27 dòng (`brand_sales_1m`) | **Giảm 99.4% – 99.7%** số dòng ghi vào DB | Mất độ chi tiết cấp từng sự kiện (event-level) | **ĐÃ ÁP DỤNG** (Core kiến trúc) |
| **2** | **Tạo Nonclustered Index khi đọc** | `filter_range_noindex` 1GB:<br>**5.934 s** (989.287 rows/s) | `filter_range_indexed` 1GB:<br>**0.092 s** (63.985.593 rows/s) | **Nhanh gấp 64.7 lần** (giảm 98.4% thời gian) | Tốn thời gian tạo index (262.7s), tăng dung lượng đĩa và làm chậm tốc độ ghi | **ĐÃ ÁP DỤNG** (2 Index chính cho `window_end` và `brand`) |
| **3** | **Đo chi phí Index khi ghi (Write Overhead)** | `write_b1000_n100000_noidx`:<br>**26.903 s** (3.717 rows/s) | `write_b1000_n100000_idx`:<br>**27.932 s** (3.580 rows/s) | **Ghi chậm hơn 3.8%** (Azure)<br>*(Trên Local: chậm hơn 22.7%)* | Tốn thêm I/O và CPU để cập nhật cây B-Tree của Index | **CHẤP NHẬN ĐÁNH ĐỔI** (Chỉ tạo đúng 2 index tối thiểu cần cho truy vấn) |
| **4** | **Tối ưu Batch Size khi ghi** | `write_single_n1000_noidx`:<br>**58.503 s** (17 rows/s) | `write_b10000_n100000_noidx`:<br>**14.272 s** (7.007 rows/s) | **Tăng tốc 412 lần** thông lượng ghi | Tăng bộ nhớ đệm client, tăng độ trễ gom lô | **ĐÃ ÁP DỤNG** (Khuyến nghị batch 1.000 – 10.000) |
| **5** | **Nén dữ liệu PAGE Compression** | `scan_uncompressed` 1GB:<br>**9.143 s** (1024.0 MB) | `scan_page_compressed`:<br>**6.671 s** (918.3 MB) | **Giảm 10.3% dung lượng** (tiết kiệm 105.7 MB)<br>**Quét nhanh hơn 27.0%** | Tốn CPU nén/giải nén khi đọc ghi; thời gian rebuild nén mất 630.9s | **KHUYẾN NGHỊ DÙNG** cho bảng lịch sử (Archive) |
| **6** | **Lựa chọn Tier phù hợp (FinOps)** | Gói Standard S1 (20 DTU, ~$30/tháng): Log IO chạm trần 100% khi bulk load | Gói Basic (5 DTU, ~$4.99/tháng): Chạy ổn định cho streaming window 30s | **Tiết kiệm 83.3% chi phí** cloud hàng tháng | Giới hạn dung lượng 2GB và 5 DTU | **ĐÃ ÁP DỤNG** (Hạ về Basic sau khi hoàn thành đo đạc) |
| **7** | **Lưu trữ Blob Storage cho raw data / log** | Lưu toàn bộ event thô vào SQL: tốn dung lượng đắt tiền | Đẩy event thô / file backup CSV lên Azure Blob (Hot/Cool tier) | **Tiết kiệm >90% chi phí lưu trữ** so với SQL | Cần công cụ riêng (`azcopy`) để tra cứu | **ĐÃ ÁP DỤNG** (Container `benchmark-data`) |

---

## Chi tiết từng giải pháp kỹ thuật

### 1. Aggregate trước khi ghi (Stream Pre-aggregation)
- **Vấn đề:** Nếu đẩy toàn bộ luồng sự kiện thương mại điện tử thô vào Azure SQL Database (hàng trăm ngàn sự kiện/phút), database sẽ nhanh chóng cạn kiệt tài nguyên Log IO và DTU, gây nghẽn cổ chai nghiêm trọng và phình to chi phí lưu trữ.
- **Giải pháp:** Sử dụng Azure Stream Analytics để tổng hợp dữ liệu trước theo cửa sổ thời gian (Tumbling Window 30 giây cho `event_metrics_30s` và Hopping Window 1 phút cho `brand_sales_1m`).
- **Số liệu chứng minh:**
  * Dữ liệu chạy kiểm thử tích hợp thực tế `integration-01` (khối [9] trong `sql_validation.sql`):
  * **10.000 sự kiện thô** phát ra từ Producer được Stream Analytics gom nhóm và chỉ ghi **30 dòng** vào `dbo.event_metrics_30s` và **27 dòng** vào `dbo.brand_sales_1m`.
  * Giảm tải tới **99.4% – 99.7%** số lượng transaction ghi vào database.
- **Đánh đổi:** Mất khả năng truy vấn chi tiết từng lượt click của một người dùng cụ thể. Tuy nhiên, với mục tiêu của hệ thống là Dashboard phân tích luồng và giám sát doanh số thời gian thực, sự đánh đổi này là hoàn toàn đúng đắn.

---

### 2 & 3. Tạo Nonclustered Index: Tối ưu đọc & Đánh đổi chi phí ghi

#### 2. Tối ưu hóa truy vấn Đọc:
- **Vấn đề:** Truy vấn lọc dữ liệu theo khoảng thời gian (`filter_range`: lọc các sự kiện trong 1 ngày cụ thể trên bảng 1GB ~ 5.87 triệu dòng) khi chưa có Index phải thực hiện **Table Scan** toàn bộ 5.87 triệu dòng, gây nghẽn CPU và mất nhiều thời gian.
- **Giải pháp:** Tạo Nonclustered Index `IX_bench_read_events_time` trên cột thời gian `event_time` kèm theo các cột bao phủ (`INCLUDE`).
- **Số liệu chứng minh (trung vị 3 lần lặp):**
  * `filter_range_noindex` (1024.0 MB): **5.934 s** (tốc độ xử lý: 989.287 dòng/s).
  * Thời gian tạo Index trên bảng 1GB: `create_index` mất **262.693 s** (~4.38 phút).
  * `filter_range_indexed` (1024.0 MB): **0.092 s** (tốc độ xử lý: **63.985.593 dòng/s**).
  * **Kết quả:** Tốc độ truy vấn tăng vọt **gấp 64.7 lần** (từ gần 6 giây giảm xuống chưa đầy 0.1 giây!).

#### 3. Chi phí duy trì Index khi Ghi (Write Penalty):
- **Cơ chế:** Khi bảng có Index, mỗi thao tác `INSERT` ngoài việc ghi dữ liệu vào trang dữ liệu chính (Data Page/Heap) còn phải cập nhật các nút trên cây chỉ mục B-Tree và ghi thêm Transaction Log.
- **Số liệu chứng minh (trung vị ghi lô 100.000 dòng):**
  * **Trên Azure SQL (Standard S1):**
    * Không Index (`write_b1000_n100000_noidx`): **26.903 s** (3.717 dòng/s).
    * Có Index (`write_b1000_n100000_idx`): **27.932 s** (3.580 dòng/s).
    * *Đánh đổi:* Tốc độ ghi chậm hơn khoảng **3.8%** do chi phí cập nhật Index.
  * **Trên Local SQL Server (SSD NVMe):**
    * Không Index: **3.566 s** (28.044 dòng/s).
    * Có Index: **4.613 s** (21.676 dòng/s).
    * *Đánh đổi:* Tốc độ ghi chậm hơn khoảng **22.7%**.
- **Kết luận kiến trúc:** Chỉ tạo **đúng 2 index thiết yếu** phục vụ Dashboard Power BI (`IX_event_metrics_window` và `IX_brand_sales_window_brand`), không tạo thừa thãi index để bảo vệ hiệu năng ghi của Stream Analytics.

---

### 4. Tối ưu kích thước lô khi ghi (Batch Sizing)
- **Vấn đề:** Ghi từng dòng đơn lẻ (`Row-by-Row INSERT`) qua môi trường mạng Internet từ client tới Cloud Database chịu ảnh hưởng nặng nề bởi độ trễ khứ hồi của mạng (Network Round-Trip Time - RTT) và chi phí commit từng giao dịch độc lập.
- **Giải pháp:** Sử dụng kỹ thuật Batching (`executemany` gom nhiều dòng trong một lệnh INSERT hoặc khối giao dịch).
- **Số liệu chứng minh trên Azure SQL (East Asia, mạng WiFi):**
  * Ghi đơn lẻ 1.000 dòng (`write_single_n1000_noidx`): **58.503 s** $\rightarrow$ Thông lượng chỉ đạt **17 dòng/s**!
  * Ghi lô 100 dòng (`write_b100_n100000_noidx`): **223.607 s** $\rightarrow$ Đạt **447 dòng/s**.
  * Ghi lô 1.000 dòng (`write_b1000_n100000_noidx`): **26.903 s** $\rightarrow$ Đạt **3.717 dòng/s** (Nhanh gấp **218 lần** ghi đơn lẻ).
  * Ghi lô 10.000 dòng (`write_b10000_n100000_noidx`): **14.272 s** $\rightarrow$ Đạt **7.007 dòng/s** (Nhanh gấp **412 lần** ghi đơn lẻ).
- **Kết luận:** Trong kiến trúc Stream Analytics ghi vào Azure SQL, thiết lập cấu hình Output Batch Policy (Max batch count = 1.000 – 10.000 hoặc Max time = 30s) là yếu tố sống còn để đạt thông lượng cao mà không làm nghẽn database.

---

### 5. Nén dữ liệu cấp trang (PAGE Data Compression)
- **Vấn đề:** Bảng lịch sử sự kiện phình to chiếm nhiều không gian lưu trữ đĩa (Data Max Size) và làm tăng số lượng trang đĩa vật lý cần đọc khi thực hiện quét toàn bảng (Full Table Scan).
- **Giải pháp:** Áp dụng tính năng nén nâng cao `DATA_COMPRESSION = PAGE` của SQL Server (kết hợp nén tiền tố Prefix Compression và nén từ điển Dictionary Compression).
- **Số liệu chứng minh:**
  * Kích thước bảng trước khi nén: **1024.0 MB** (5.870.467 dòng).
  * Thời gian thực hiện rebuild nén bảng 1GB: `rebuild_page_compression` mất **630.876 s** (~10.5 phút).
  * Kích thước bảng sau khi nén: **918.3 MB** (Tiết kiệm được **105.7 MB**, tương đương giảm **10.3%** dung lượng).
  * **Tốc độ quét toàn bảng (Full Scan):**
    * Chưa nén (`scan_uncompressed`): **9.143 s** (642.041 dòng/s).
    * Sau khi nén (`scan_page_compressed`): **6.671 s** (880.043 dòng/s).
    * *Hiệu quả:* Thời gian quét giảm từ 9.14s xuống 6.67s (**Nhanh hơn 27.0%**).
- **Giải thích cơ chế:** Vì dữ liệu được nén chặt lại, số lượng Data Pages (8KB) trên đĩa giảm đi đáng kể. Do đó, SQL Server tốn ít thao tác I/O đọc trang hơn, dữ liệu nạp vào Buffer Pool trong RAM cũng chiếm ít không gian hơn, giúp tốc độ truy vấn tăng lên rõ rệt.
- **Đánh đổi:** Tốn CPU trong quá trình nén và giải nén.

---

### 6. Lựa chọn Service Tier theo nhu cầu (FinOps Strategy)
- Khi thực hiện tải dữ liệu cực lớn (bulk insert hàng triệu dòng trong bài benchmark), gói **Standard S1 (20 DTU)** bị chạm trần 100% tài nguyên ở chỉ số **Log IO** (do giới hạn Transaction Log Generation Rate của gói S1).
- Tuy nhiên, trong luồng vận hành thực tế của dự án, dữ liệu đã được Stream Analytics gom nhóm thành từng đợt nhỏ cách nhau 30 giây (chỉ vài chục dòng/lần). 
- Với lưu lượng này, gói **Basic (5 DTU)** hoàn toàn gánh tải mượt mà (DTU dao động < 10%), trong khi chi phí chỉ tốn **$4.99/tháng** thay vì ~$30/tháng của S1. Nhóm áp dụng chính sách co giãn: chỉ nâng tier khi bảo trì/nạp dữ liệu ban đầu, sau đó đưa về Basic để tiết kiệm ngân sách.

---

## Khuyến nghị kiến trúc cho dự án
1. **Index:** Duy trì đúng **2 Nonclustered Index** gồm `IX_event_metrics_window` trên `(window_end DESC, run_id)` và `IX_brand_sales_window_brand` trên `(window_end DESC, brand)`. Tuyệt đối không thêm các index phụ không dùng tới để bảo vệ tốc độ ghi của luồng streaming.
2. **Batching:** Phía các tiến trình nạp hoặc pipeline ETL, luôn đặt kích thước lô $\ge 1.000$ bản ghi để tránh suy giảm hiệu năng do độ trễ mạng RTT.
3. **Nén bảng:** Định kỳ sau mỗi Sprint hoặc cuối tháng, kích hoạt `PAGE Compression` cho các phân vùng (partition) hoặc bảng chứa dữ liệu lịch sử để tiết kiệm chi phí đĩa và tăng tốc báo cáo định kỳ.

---

## Hạn chế của phép đo thực nghiệm
- Dữ liệu đo Đọc/Ghi được sinh ngẫu nhiên từ server theo phân phối chuẩn mô phỏng schema của tập dữ liệu e-commerce (không hoàn toàn mang 100% tính chất tự nhiên của hành vi mua sắm người dùng thật).
- Môi trường đo Local và Azure SQL khác nhau về phần cứng nền tảng (AMD 16-cores/SSD NVMe trên máy vật lý so với máy ảo chia sẻ tài nguyên 20 DTU trên Cloud), do đó số đo so sánh mang ý nghĩa tham chiếu để làm rõ đặc tính khác biệt giữa On-premises và Cloud Storage.
