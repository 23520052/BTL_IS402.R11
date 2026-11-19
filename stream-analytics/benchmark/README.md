# Cách điền stream_metrics.csv

`stream_metrics.csv` là bảng tổng hợp số đo streaming, mỗi dòng tương ứng một run. Đã ghi hai run từ bộ 37 ảnh đã lưu, log và payload hiện có: smoke 8 event và integration 10k. Đây là các quan sát test/tích hợp, chưa thay cho bộ benchmark T10 ba mức tải. Mở bằng Excel hoặc trình soạn thảo CSV; giữ dòng tiêu đề khi lưu.

## Số liệu đã điền ngày 13/11/2026

| Nội dung | `smoke-3433042d611a` | `integration-261113` |
|---|---|---|
| Khoảng `stream_event_time` UTC trong payload | 11/11 15:51:05 đến 15:51:40 | 13/11 13:37:27.895368 đến 13:41:38.643197 |
| Target rate Producer | Không cấu hình rate cố định; để trống | 50 event/s |
| Actual rate Producer | Không có summary throughput; để trống | 39.81 event/s, theo summary dùng elapsed 251.20s |
| Kích thước JSON UTF-8 trung bình | 409.75 byte, dựng lại đúng `json.dumps` của script smoke | 391.4364 byte, tính trực tiếp từ các dòng JSONL đã gửi, bỏ CR/LF |
| Cấu hình baseline đã chụp | 2 partition, 1 TU, SQL Basic 5 DTU | 2 partition, 1 TU, SQL Basic 5 DTU |
| ASA Input / Output | 8 / 8, ảnh metrics 21 | Chưa có ảnh/export Input và Output cho đúng run; để trống |
| Producer gửi thành công | 8 ACK | 10000; error = 0, retry = 0, 200 batch |
| SQL accepted / số dòng hai bảng | 8 event / 5 và 3 dòng | 10000 event / 28 và 61 dòng |
| SQL purchase / revenue | 4 / 650 | 118 / 35757.22 |
| Nhóm khóa output trùng | 0 ở cả hai bảng | 0 ở cả hai bảng |
| Backlog chart đã gửi | Không có số backlog riêng | Max 46 ở từng partition trên chart khung 12h; đã ghi trong notes, chưa gán thành `backlog_max` riêng run |

Hai cột `start_utc` / `end_utc` hiện dùng mốc nhỏ nhất/lớn nhất của `stream_event_time` trong payload, không phải timestamp bắt đầu/kết thúc tiến trình. `actual_eps` của integration giữ số trong log với elapsed 251.20s, không tính lại từ khoảng hai timestamp payload. Khi đo T10 cần ghi rõ khoảng phát đo và khoảng metrics/drain thực tế.

Cấu hình 2 partition / 1 TU / Basic 5 DTU được chép từ ảnh cấu hình baseline đã lưu; chưa có ảnh cấu hình đồng thời từng run. Số SU của ASA chưa có trong bộ ảnh nên để trống. Backlog 46 được giữ trong notes vì chart bao phủ 13/11 14:59 đến 14/11 02:59 giờ Việt Nam, rộng hơn đợt phát khoảng 20:37–20:41. Không cộng hai cực đại partition thành 92.

Các kết quả SQL và số ACK được ghi trong `notes`, không dùng thay metric ASA Input/Output. Các ô trống còn lại không có số đo xác nhận trong bộ ảnh: SU, watermark max, memory, late/out-of-order, lỗi ASA và drain time.

### Nguồn đã đối chiếu

- Ảnh cấu hình: `evidence/event-hubs/01-namespace-overview.png`, `02-eventhub-config.png`; `evidence/stream-analytics/02-sql-database.png`.
- Smoke: `evidence/stream-analytics/smoke-3433042d611a/sample_events.json`, `acknowledged.jsonl`; ảnh 19–25 trong `evidence/stream-analytics/`.
- Integration: `producer/logs/producer_integration-261113.log`, `evidence/event-hubs/events_integration-20261113.jsonl` và bốn ảnh trong `evidence/stream-analytics/integration-261113/`.
- Payload integration có 10000 event_id duy nhất: 9785 view, 97 cart, 118 purchase; tổng price purchase tính bằng Decimal = 35757.22. SHA-256: `61947fc32e6bbecf6c7cb347736f3f5d0e5d54b2acdd723a75473440b98e359c`.

## Lấy số liệu ở đâu?

| Cột | Nguồn và cách ghi |
|---|---|
| `run_id` | ID thật của lần phát, trùng Producer, thư mục bằng chứng và SQL. |
| `start_utc`, `end_utc` | Giờ bắt đầu/kết thúc khoảng phát đo, UTC ISO 8601 có `Z`. Ghi rõ nếu khoảng theo dõi metrics có thêm thời gian drain. |
| `target_eps` | Tốc độ mục tiêu cấu hình ở Producer, đơn vị event/giây. |
| `actual_eps` | Tốc độ gửi thành công thực đo của Producer; giữ đúng khoảng thời gian/cách tính trong log. Không tự điền bằng target. |
| `avg_payload_bytes` | Kích thước JSON UTF-8 trung bình của payload thật đã gửi, không tính dấu xuống dòng của JSONL. |
| `partitions` | Số partition của Event Hub khi đo. |
| `eventhub_tu` | TU namespace khi đo. |
| `asa_su_v2` | SU của ASA tại Settings → Scale khi đo. |
| `sql_tier` | Tier/cấu hình SQL thực tế trong lần đo. |
| `input_events` | ASA Metrics → Input Events, aggregation Sum, đúng khoảng chạy. |
| `output_events` | ASA Metrics → Output Events, aggregation Sum, theo khoảng phát/drain đã ghi. Đây là số dòng aggregate. |
| `backlog_max` | ASA Backlogged Input Events, Max, đúng khoảng chạy. Ghi phạm vi dimension trong notes. Nếu split partition, dùng cực đại lớn nhất trong các chuỗi và ghi rõ đó là max theo partition; không cộng các đỉnh khác thời điểm thành backlog đồng thời. |
| `watermark_delay_max_s` | ASA Watermark Delay, Max, đơn vị giây. |
| `su_memory_avg_pct`, `su_memory_max_pct` | ASA SU (Memory) % Utilization, lần lượt Average và Max. Ghi phạm vi dimension trong notes. |
| `late_events` | ASA Late Input Events, Sum. |
| `out_of_order_events` | ASA Out-of-Order Events, Sum. |
| `runtime_errors` | ASA Runtime Errors, Sum. |
| `conversion_errors` | ASA Data Conversion Errors, Sum. |
| `drain_seconds` | Thời gian thực đo từ khi ngừng phát đến khi backlog tiêu hết. Chưa theo dõi thì để trống. |
| `notes` | Nguồn log/ảnh/file export; khoảng thời gian metrics; timezone; time grain; aggregation/dimensions; trường chưa đo; query version và thay đổi cấu hình nếu có. |

Các cột số để trống khi chưa đo. Chỉ ghi `0` khi đã kiểm tra có số liệu và kết quả thực tế bằng 0. Không lấy số liệu mock làm benchmark. `SUM(event_count)` trong SQL là số event đã được query chấp nhận, không tự dùng thay metric ASA Input Events.

## Làm sau mỗi run

1. Chốt run_id, giờ phát, tốc độ mục tiêu và cấu hình TU/SU/SQL. Người chạy Producer giữ log và payload thực tế đã gửi.
2. Mở ASA → Monitoring → Metrics. Chọn Custom time range đúng lần chạy, ghi timezone và time grain; dùng khoảng theo dõi đủ cho cửa sổ/output cuối hoàn tất.
3. Lấy các metric với aggregation trong bảng trên. Các metric khác đơn vị nên để chart riêng. Nếu cần, xem thêm Event Hubs Incoming Messages/Bytes, Throttled Requests và Input Deserialization Errors; thêm cột có tên/đơn vị rõ ràng khi đo.
4. Trong Metrics explorer, dùng **Share → Download to Excel** nếu giao diện cung cấp. Lưu file export gốc và ảnh chart trong thư mục run. Nếu ghi thủ công từ chart/tooltip thì ghi cách thu thập trong notes.
5. Tổng hợp đúng Sum/Max/Average theo khoảng chạy vào một dòng CSV. File export Azure là dữ liệu nguồn theo thời gian; `stream_metrics.csv` này là bảng tổng hợp các lần đo, cần đối chiếu cột khi điền.
6. Lặp lại cho các mức tải. Hướng dẫn đề xuất 100/300/500 event/s, mỗi mức khoảng 5 phút; đây là target thử nghiệm. Báo cáo phải ghi actual từ Producer và thời gian thực tế.

`stream_metrics.csv` thuộc phần TV2. Log/tốc độ phát thuộc phần Producer của TV1; hai bên có thể đo trong cùng một buổi benchmark theo kế hoạch nhóm.

## Nguồn

- `HUONG_DAN_TV2_EVENT_HUBS_ASA.md`, mục 14.2–14.5: schema CSV và phương pháp thu thập.
- `Ke_hoach_Azure_07-19_11_2026.md`: deliverable `stream_metrics.csv` của TV2.
- [Azure Monitor metrics explorer — Share your charts](https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/metrics-getting-started#share-your-charts).
- [ASA monitoring data reference](https://learn.microsoft.com/en-us/azure/stream-analytics/monitor-azure-stream-analytics-reference).
