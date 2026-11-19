# Event Hubs và Azure Stream Analytics — TV2

Module streaming tiếp nhận event từ Python Producer, chuẩn hóa dữ liệu, tính thống kê theo cửa sổ thời gian và ghi kết quả vào Azure SQL để Power BI đọc.

```text
CSV → Python Producer → Event Hubs sales-events
                              ↓
                       ASA asa-sales-gr03
                         ├─ 30s → dbo.event_metrics_30s
                         └─ 1m  → dbo.brand_sales_1m
                                      ↓
                              Power BI DirectQuery
```

## Bộ bàn giao

| File | Nội dung |
|---|---|
| [queries.sql](queries.sql) | Hai nhánh xử lý của ASA, dùng làm bản SQL duy nhất trong module |
| [sql_validation.sql](sql_validation.sql) | Kiểm tra database/schema, xem kết quả, tính tổng, kiểm tra trùng và liệt kê run |
| [azure_config.json](azure_config.json) | Thông số cấu hình được ghi lại từ bằng chứng triển khai |
| [azure_setup.md](azure_setup.md) | Thiết lập, quyền truy cập, kiểm tra kết nối và Start/Stop |
| [stream_test.md](stream_test.md) | Kết quả smoke 8 event và tích hợp 10.000 event |
| [tools/smoke_tv2.py](tools/smoke_tv2.py) | Tạo fixture 8 event hoặc gửi live khi có `--send` |
| [requirements.txt](requirements.txt) | Thư viện cho công cụ smoke của TV2 |
| [benchmark/stream_metrics.csv](benchmark/stream_metrics.csv) | Số liệu hiện có của các run |
| [benchmark/README.md](benchmark/README.md) | Định nghĩa cột và nguồn số liệu CSV |
| [benchmark/stream_benchmark.md](benchmark/stream_benchmark.md) | Phạm vi đo, kết quả hiện có và phần benchmark ASA cần bổ sung |
| [02_streaming_azure.md](../docs/project_report/02_streaming_azure.md) | Phần báo cáo streaming của đồ án |

`azure_config.json` là bản ghi cấu hình, không phải ARM template. Job hiện dùng cấu hình đã lưu trên Azure Portal; sửa JSON trên Git không tự cập nhật job. Giá trị `null` là thông số chưa xác nhận trong ảnh đã lưu. Các thông số có chữ `observed` mô tả cấu hình tại lúc chụp, không khẳng định tài nguyên hiện vẫn giữ cấu hình đó.

`queries.sql` được lưu theo query tham chiếu trong hướng dẫn TV2, phù hợp contract và kết quả kiểm thử đã có. Chưa có bản export trực tiếp query Portal ở thời điểm bàn giao; trước khi dùng để cập nhật job, đối chiếu với query đang lưu trên Portal.

## Kết quả đã ghi nhận

| Run | Event được ghi nhận trong SQL | Purchase | Revenue | Dòng 30s / 1m | Nhóm khóa trùng |
|---|---:|---:|---:|---|---|
| `smoke-3433042d611a` | 8 | 4 | 650.00 | 5 / 3 | 0 / 0 |
| `integration-261113` | 10000 | 118 | 35757.22 | 28 / 61 | 0 / 0 |

Số 10.000, 118 purchase và revenue 35.757,22 của integration khớp payload đã gửi trên Git. Số dòng nhóm kỳ vọng cũng khớp 28/61; chưa có file export toàn bộ dòng SQL của run này để đối chiếu từng cửa sổ.

Bộ ảnh và dữ liệu kiểm chứng nằm tại [evidence/stream-analytics](../evidence/stream-analytics/), [evidence/event-hubs](../evidence/event-hubs/) và [evidence/azure-sql](../evidence/azure-sql/). [File HTML tổng hợp](../evidence/stream-analytics/BANG_CHUNG_STREAMING.html) mở offline được.

## Chạy kiểm tra

Mở `queries.sql` trong **ASA → Query**. Đây là query xử lý luồng, chạy khi job được Start.

Mở `sql_validation.sql` trong **salesdb → Query editor**, thay `@run_id` bằng run cần kiểm tra. File chỉ có truy vấn đọc, không sửa dữ liệu. Để chạy một phần, chọn dòng `DECLARE` cùng câu `SELECT` cần xem; các editor có thể chỉ hiển thị một result set tại một thời điểm.

Để tạo fixture offline, chạy tại thư mục gốc repository:

```powershell
python -m pip install -r .\stream-analytics\requirements.txt
python .\stream-analytics\tools\smoke_tv2.py
```

Script in đường dẫn `smoke-results/<run_id>/sample_events.json` để upload vào input của ASA Query Test. Cách gửi live và lấy khóa qua biến môi trường được mô tả trong [azure_setup.md](azure_setup.md).

## Phần chờ bổ sung

Benchmark ASA ở ít nhất ba mức tải vẫn cần số đo Input/Output, backlog, watermark, tài nguyên và lỗi trong đúng khoảng chạy. Người hỗ trợ đo có thể bổ sung vào CSV và báo cáo benchmark của module này. [Benchmark Producer](../producer/benchmark_producer.md) đã có số đo riêng; tài liệu đó ghi ASA được dừng khi đo, nên không thay cho kết quả benchmark ASA.
