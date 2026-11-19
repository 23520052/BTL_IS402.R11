# Xử lý luồng bằng Azure Event Hubs và Azure Stream Analytics

## 1. Mục tiêu và vị trí trong hệ thống

Module streaming tiếp nhận các sự kiện hành vi thương mại điện tử từ Python Producer, xử lý và tổng hợp liên tục thành các chỉ số để Power BI truy vấn qua Azure SQL. Phạm vi TV2 gồm Event Hubs, Stream Analytics, input/output, query ETL, kiểm chứng dữ liệu và theo dõi vận hành.

```text
Python Producer → Event Hubs → Stream Analytics → Azure SQL → Power BI
```

Dataset lịch sử được Producer phát lại bằng `stream_event_time` của lần chạy. `original_event_time` giữ thời điểm gốc trong dataset. Mỗi run có `run_id` để phân biệt dữ liệu test, tích hợp và demo.

## 2. Vai trò của hai dịch vụ

Event Hubs tiếp nhận message và lưu trong thời gian retention. Hub `sales-events` có hai partition để hỗ trợ đọc/ghi song song. Consumer group `cg-asa-sales` phục vụ ứng dụng ASA; consumer group là ngữ cảnh đọc độc lập, khác với partition lưu trữ.

Stream Analytics thực thi query đã lưu khi job Running. Job đọc event từ Event Hubs, chuẩn hóa và lọc dữ liệu, gom cửa sổ rồi ghi kết quả ra hai bảng SQL. Bản SQL được lưu tại [queries.sql](../../stream-analytics/queries.sql).

SQL lưu các dòng aggregate; số dòng SQL không bằng số event nguồn. Power BI đọc các bảng kết quả này bằng DirectQuery. Trong bộ kiểm chứng đã có, 10.000 event tạo 28 dòng bảng 30s và 61 dòng bảng brand.

## 3. Cấu hình triển khai

| Thành phần | Cấu hình ghi nhận |
|---|---|
| Resource group | `rg-sales-stream-gr03` |
| Region | East Asia |
| Event Hubs namespace | `evhns-sales-gr03-1110` |
| Event Hub | `sales-events`, 2 partition |
| Tier/capacity Event Hubs | Standard, baseline 1 TU, auto-inflate tắt |
| Consumer group ASA | `cg-asa-sales` |
| Policy Producer | `producer-send`, quyền Send |
| ASA job | `asa-sales-gr03`, Cloud, pricing plan StandardV2 |
| ASA input | `eh-sales`, JSON, UTF-8 |
| Xác thực input | System-assigned Managed Identity, role Azure Event Hubs Data Receiver |
| SQL | `sqlsrv-sales-gr03-tram01.database.windows.net`, database `salesdb` |
| Xác thực output | SQL Server authentication, user `asa_writer` |

Các giá trị trên được ghi từ ảnh triển khai. Tier SQL ban đầu là Basic 5 DTU. Chưa có bằng chứng số SU, compatibility level, retention giờ và Capture cuối để điền các giá trị đó. Cấu hình được lưu ở [azure_config.json](../../stream-analytics/azure_config.json); JSON này là bản ghi bàn giao, không tự triển khai hoặc cập nhật Azure.

## 4. Hợp đồng dữ liệu và ETL

Contract hiện tại quy định ba loại event `view`, `cart`, `purchase`. Query dùng đúng ba loại trong [data contract](../data_contract.md), thay vì đưa `remove_from_cart` từ mô tả kế hoạch ban đầu vào bộ kiểm thử mới.

### 4.1. Chuẩn hóa

CTE `Normalized` cắt khoảng trắng và chuyển `event_type` thành chữ thường. Brand null hoặc rỗng được đổi thành `unknown`; brand có giá trị cũng được cắt khoảng trắng và chuyển về chữ thường. `TRY_CAST(price AS float)` chuyển giá thành số để tổng hợp; giá không chuyển được trở thành null.

### 4.2. Lọc hợp lệ

CTE `ValidEvents` giữ các event có `event_id` và `run_id` không null/rỗng, event type được hỗ trợ, price là số không âm. Đây là bộ lọc cho các trường query sử dụng, không thay toàn bộ việc kiểm tra JSON Schema của Producer. Gán timestamp xảy ra trước các điều kiện WHERE nên timestamp sai không được tự sửa bởi bộ lọc này.

### 4.3. Tổng hợp 30 giây

Nhánh `sql-event-metrics` nhóm theo `run_id`, `event_type` và `TumblingWindow(second, 30)`. `COUNT(*)` là số event hợp lệ trong nhóm. Revenue chỉ cộng price của purchase; các event khác đóng góp 0. Kết quả ghi vào `dbo.event_metrics_30s` với các cột `window_end`, `run_id`, `event_type`, `event_count`, `revenue`.

### 4.4. Tổng hợp theo brand 1 phút

Nhánh `sql-brand-sales` lọc purchase, nhóm theo `run_id`, `brand` và `TumblingWindow(minute, 1)`. Kết quả có `purchase_events` và tổng price trong mỗi nhóm, ghi vào `dbo.brand_sales_1m`.

Purchase là sự kiện mua trong dataset, không khẳng định là số đơn hàng vì dữ liệu không có order ID.

## 5. Thời gian và chính sách xử lý

Query chọn event time bằng `TIMESTAMP BY stream_event_time`. Cửa sổ tumbling có kích thước cố định, liên tiếp và không chồng lấp. Mặc định ASA dùng biên `(start, end]`; event nằm đúng mốc kết thúc thuộc cửa sổ kết thúc tại mốc đó. `System.Timestamp()` trong kết quả aggregate biểu diễn thời điểm kết thúc cửa sổ. [Microsoft Learn](https://learn.microsoft.com/en-us/stream-analytics-query/tumbling-window-azure-stream-analytics).

Cấu hình đã lưu cho late arrival là 10 giây, out-of-order là 5 giây, action Drop; output error policy là Retry. Các policy này ảnh hưởng event được chấp nhận, tiến độ cửa sổ và khả năng ghi output. Khi đối chiếu run, phải kiểm tra metric late/out-of-order/lỗi trước khi kết luận thiếu dữ liệu.

Khi start Now, mốc bắt đầu output là lúc start; ASA có thể đọc lùi lượng input cần thiết để tạo đầy đủ cửa sổ đầu. Dữ liệu gửi trước khi start không mặc nhiên được xử lý toàn bộ. Việc đọc lại cần chọn mốc start phù hợp và Event Hubs vẫn còn giữ input. [Microsoft Learn](https://learn.microsoft.com/en-us/azure/stream-analytics/start-job).

## 6. Kết quả kiểm chứng

### 6.1. Live smoke 8 event

Run `smoke-3433042d611a` có 8 ACK phía gửi. Event Hubs Incoming Messages và ASA Input Events đều là 8; ASA Output Events là 8 dòng aggregate. SQL có 5 dòng bảng 30s và 3 dòng bảng brand, tổng 4 purchase và revenue 650 ở mỗi bảng. Kiểm tra nhóm khóa aggregate trùng trả về 0 ở cả hai bảng.

Ảnh chi tiết từng cửa sổ, từng brand, tổng và truy vấn kiểm tra trùng được giữ trong [evidence TV2](../../evidence/stream-analytics/). Kết quả smoke khớp fixture đã biết đáp án.

### 6.2. Tích hợp 10.000 event

Run `integration-261113` có log Producer báo 10.000 event gửi thành công, 0 event lỗi, 0 retry và 200 batch. Summary ghi elapsed 251,20 giây, target 50 event/s và actual 39,81 event/s.

| Chỉ tiêu | Nguồn độc lập từ payload | Actual SQL trong ảnh |
|---|---:|---:|
| Event hợp lệ | 10000 | 10000 |
| Purchase event | 118 | 118 ở hai bảng |
| Revenue purchase | 35757.22 | 35757.22 khi làm tròn hai chữ số |
| Nhóm 30s | 28 | 28 dòng |
| Nhóm brand 1m | 61 | 61 dòng |

Payload gồm 9785 view, 97 cart, 118 purchase và 10.000 event_id duy nhất. SQL không có nhóm khóa aggregate trùng trong run này. Các số tổng và số nhóm khớp; chưa có export đầy đủ từng dòng SQL để đối chiếu mọi khóa và giá trị từng cửa sổ.

Revenue SQL là FLOAT nên có thể hiển thị đuôi như `35757.219999…`; kiểm chứng tổng dùng mức làm tròn hai chữ số. Không thay đổi số liệu đầu vào theo giá trị SQL quan sát được. Nguồn log, payload và ảnh nằm trong [stream_test.md](../../stream-analytics/stream_test.md).

## 7. Monitoring và giới hạn benchmark

Số đo đã ghi trong [stream_metrics.csv](../../stream-analytics/benchmark/stream_metrics.csv). Input/Output và lỗi dùng Sum; backlog/watermark dùng Max; memory dùng Average/Max. Các metric khác đơn vị được đọc riêng và phải gắn với cùng khoảng chạy.

Ảnh backlog của integration hiển thị cực đại 46 ở từng partition trong khung 12 giờ. Không dùng ảnh đó để kết luận max riêng của run kéo dài khoảng bốn phút và không cộng hai cực đại thành backlog đồng thời. Watermark trong ảnh bị cắt nên chưa có số đo.

[Benchmark Producer](../../producer/benchmark_producer.md) trên Git có bốn mức tải, mỗi mức ba lần, nhưng ghi rõ ASA đã dừng lúc đo. Kết quả đó không chứng minh năng lực xử lý của ASA. Phần đo ít nhất ba mức tải khi ASA Running còn chờ thành viên hỗ trợ bổ sung theo [stream_benchmark.md](../../stream-analytics/benchmark/stream_benchmark.md).

## 8. Giới hạn và hướng hoàn thiện

Query chưa khử trùng input theo `event_id`; gửi lại cùng event có thể làm count tăng. Kiểm tra SQL không thấy khóa output trùng ở hai run đã thử không chứng minh không trùng trong mọi tình huống retry/restart. Exactly-once delivery tới SQL cần natural key và unique constraint phù hợp; cấu hình bảng hiện tại phải được người phụ trách database xác nhận trước khi tuyên bố bảo đảm đó. [Microsoft Learn](https://learn.microsoft.com/en-us/stream-analytics-query/event-delivery-guarantees-azure-stream-analytics).

Độ trễ quan sát của toàn pipeline còn gồm chờ cửa sổ, watermark, ghi SQL và refresh/render Power BI. Module hiện chứng minh xử lý gần thời gian thực qua run thử; chưa có phép đo độ trễ end-to-end hoặc benchmark tải cao hoàn chỉnh.

Các bước hoàn thiện là lưu export query/config thực tế, bổ sung số SU/retention/compatibility, export metrics theo đúng run, đối chiếu đầy đủ từng cửa sổ và đo ba mức tải có cấu hình nhất quán.

## Tài liệu và bằng chứng

- [Module streaming](../../stream-analytics/README.md).
- [Query xử lý](../../stream-analytics/queries.sql) và [query kiểm chứng SQL](../../stream-analytics/sql_validation.sql).
- [Biên bản kiểm chứng](../../stream-analytics/stream_test.md).
- [Bằng chứng Event Hubs](../../evidence/event-hubs/) và [ASA/SQL](../../evidence/stream-analytics/).
- [ASA monitoring reference](https://learn.microsoft.com/en-us/azure/stream-analytics/monitor-azure-stream-analytics-reference).
