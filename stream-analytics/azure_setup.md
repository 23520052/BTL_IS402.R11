# Thiết lập Event Hubs và ASA

Thông số bàn giao nằm trong [azure_config.json](azure_config.json). Hướng dẫn này mô tả quy trình triển khai đã sử dụng; trước một lần chạy mới cần kiểm tra trạng thái, capacity và quyền hiện tại trong Portal.

## 1. Quyền và dữ liệu đầu vào

Đăng nhập đúng subscription nhóm và mở `rg-sales-stream-gr03`. Quyền Contributor tại RG cho phép quản lý tài nguyên trong phạm vi đó. Gán role dữ liệu cho Managed Identity cần người có quyền tạo role assignment hỗ trợ.

Đối chiếu event với [data contract](../docs/data_contract.md) và [JSON Schema](../producer/data_contract.json). Contract hiện tại có ba loại `view`, `cart`, `purchase`. Mỗi message chứa một JSON object với `event_id`, `run_id`, `original_event_time`, `stream_event_time`, `event_type`, `brand`, `price` và các trường nguồn khác.

Hai bảng SQL và user `asa_writer` được người phụ trách database chuẩn bị trong [database/README.md](../database/README.md). TV2 cấu hình output ghi vào các bảng này.

## 2. Event Hubs

1. Tạo hoặc mở namespace `evhns-sales-gr03-1110`, region East Asia, tier Standard. Baseline đã chụp là 1 TU, auto-inflate tắt.
2. Tạo hoặc mở hub `sales-events`, 2 partition, cleanup policy Delete.
3. Kiểm tra retention tại Properties. Bộ ảnh hiện chưa ghi giá trị retention; điền lại `retention_hours` sau khi xác nhận. Capture cũng chưa có ảnh giá trị cấu hình cuối.
4. Tạo consumer group `cg-asa-sales` dành cho ASA.
5. Tạo policy `producer-send` với quyền Send. Producer lấy connection string từ policy này qua kênh riêng.

Event Hubs tiếp nhận message ngay cả khi ASA chưa Running. Muốn đọc lại dữ liệu cũ cần dữ liệu vẫn còn trong retention và chọn mốc start ASA phù hợp.

## 3. ASA và input

1. Tạo hoặc mở `asa-sales-gr03`, East Asia, môi trường Cloud. Pricing plan đã chụp là StandardV2.
2. Xác nhận số SU tại Settings → Scale và compatibility level. Hai thông số này chưa có trong ảnh bàn giao, cần ghi vào JSON khi xác nhận.
3. Dùng System-assigned Managed Identity của job. Nhờ người có quyền gán `Azure Event Hubs Data Receiver` tại hub hoặc scope cha phù hợp.
4. Tạo input alias `eh-sales`, chọn namespace/hub/consumer group ở trên.
5. Chọn Managed Identity: System assigned, serialization JSON, encoding UTF-8. Partition key để trống theo cấu hình đã chụp.
6. Save và Test input; lưu bằng chứng connection test thành công.
7. Event ordering: late arrival tolerance 10 giây, out-of-order tolerance 5 giây, action Drop. Output error policy: Retry.

## 4. Hai output SQL

| Output alias | Database | Table |
|---|---|---|
| `sql-event-metrics` | `salesdb` | `[dbo].[event_metrics_30s]` |
| `sql-brand-sales` | `salesdb` | `[dbo].[brand_sales_1m]` |

Chọn SQL server `sqlsrv-sales-gr03-tram01`, xác thực SQL Server bằng user `asa_writer`. Mật khẩu nhập trên Portal từ thông tin bàn giao riêng. Save và Test cả hai output.

User cần quyền đọc bảng phục vụ kiểm tra và INSERT phục vụ output. Kết nối laptop → SQL và ASA → SQL là hai đường truy cập riêng; mở IPv4 laptop không tự giải quyết đường ASA → SQL. Khi có lỗi firewall/quyền, phối hợp người quản lý SQL theo [database_setup.md](../database/database_setup.md).

## 5. Query

Lưu query hiện tại của job trước khi thay đổi. Đối chiếu alias và schema, rồi dùng [queries.sql](queries.sql) trong ASA → Query. Các cột output phải khớp tên cột trong hai bảng SQL.

`queries.sql` là bản theo hướng dẫn đã dùng để kiểm thử, chưa có file export Portal độc lập. Nếu Portal khác file này, xác minh thay đổi trước khi Save; không thay query đang phục vụ demo chỉ để đồng bộ tên file.

## 6. Smoke offline và live

Cài thư viện và tạo fixture tại thư mục gốc repository:

```powershell
python -m pip install -r .\stream-analytics\requirements.txt
python .\stream-analytics\tools\smoke_tv2.py
```

Upload `sample_events.json` của run vừa tạo vào input `eh-sales` trong ASA Query Test. Xem kết quả cả hai output; expected là 5 dòng bảng 30s, 3 dòng bảng brand, 4 purchase và revenue 650.

Để kiểm tra live, Start job với Now, đợi Running rồi mới gửi fixture có timestamp mới. Nhập Send connection string qua lời nhắc ẩn:

```powershell
$env:EVENTHUB_CONNECTION_STRING = [System.Net.NetworkCredential]::new('', (Read-Host 'Event Hubs Send connection string' -AsSecureString)).Password
$env:EVENTHUB_NAME = 'sales-events'
python .\stream-analytics\tools\smoke_tv2.py --send
Remove-Item Env:EVENTHUB_CONNECTION_STRING -ErrorAction SilentlyContinue
```

Script smoke dùng biến `EVENTHUB_CONNECTION_STRING`. Producer chính của nhóm dùng `EVENTHUB_CONNECTION_STR`; hai script có tên biến riêng, cần đặt đúng biến cho chương trình đang chạy.

Sau 8 ACK, đợi cửa sổ cuối và output ổn định. Dùng `sql_validation.sql` trong Query editor của `salesdb`, chọn đúng run_id vừa in. Không dùng run offline để lọc kết quả của run live.

## 7. Tích hợp và lưu bằng chứng

1. Đảm bảo ASA Running trước khi người chạy Producer bắt đầu đợt mới.
2. Dùng run_id chưa sử dụng, giữ payload đã gửi và log summary của Producer.
3. Ghi giờ bắt đầu/kết thúc và cấu hình. Chọn đúng khoảng thời gian khi xem Event Hubs Incoming Messages, ASA Input/Output, backlog, watermark và lỗi.
4. Đối chiếu SQL bằng tổng `event_count`, purchase, revenue và khóa trùng; khi cần đối chiếu đầy đủ thì export toàn bộ dòng hai bảng theo run.
5. Lưu ảnh và export metrics trong thư mục evidence của run, cập nhật `stream_test.md` và `benchmark/stream_metrics.csv`.

## 8. Start và Stop

Với đợt phát mới, chọn Now và chỉ gửi sau khi job Running. Now chọn mốc bắt đầu output hiện tại; với query cửa sổ, ASA có thể đọc lùi phần input cần thiết để hoàn tất cửa sổ, không đồng nghĩa xử lý toàn bộ lịch sử đã lưu.

Custom cho phép chọn mốc output cũ nếu input vẫn còn giữ dữ liệu. When last stopped dùng mốc output cuối của lần chạy trước; cần kiểm tra khả năng phát lại và trùng output. Chọn chế độ theo mục tiêu run, không tự đổi khi cần đối chiếu bằng chứng.

Kết thúc buổi, dừng Producer trước, đợi output cuối hoàn tất và lưu kết quả, rồi Stop ASA khi nhóm không còn cần xử lý. Stop job không xóa các dòng đã ghi trong SQL.

## Tài liệu tham khảo

- [Start ASA job](https://learn.microsoft.com/en-us/azure/stream-analytics/start-job).
- [Tumbling window](https://learn.microsoft.com/en-us/stream-analytics-query/tumbling-window-azure-stream-analytics).
- [Event delivery guarantees](https://learn.microsoft.com/en-us/stream-analytics-query/event-delivery-guarantees-azure-stream-analytics).
