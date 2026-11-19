# TV2 — Kiểm chứng Event Hubs → ASA → Azure SQL

**Kết luận: PASS cho run 8 event `smoke-3433042d611a`.**

Kết quả SQL được đối chiếu từ ảnh Query editor, fixture, expected và log ACK đã lưu. Ngày 19/11/2026 bổ sung đối chiếu độc lập payload tích hợp từ Git; chưa thực hiện một lượt truy vấn Azure trực tiếp mới trong lần cập nhật tài liệu này.

## 1. Run và môi trường

| Mục | Giá trị |
|---|---|
| Run ID | `smoke-3433042d611a` |
| Ngày phát live | 11/11/2026 |
| Ngày đối chiếu SQL và chốt bằng chứng | 12/11/2026, Asia/Saigon |
| Base UTC của fixture | `2026-11-11T15:51:00.000Z` |
| Window end 30s | `2026-11-11T15:51:30Z`, `2026-11-11T15:52:00Z` |
| Window end 1m | `2026-11-11T15:52:00Z` |
| Thời điểm bắt đầu/kết thúc phát chính xác | Chưa ghi riêng; base UTC là mốc timestamp fixture, không phải số đo thời gian chạy |
| Resource group | `rg-sales-stream-gr03` |
| Region | `East Asia` |
| Namespace / Event Hub | `evhns-sales-gr03-1110` / `sales-events` |
| Event Hubs tier / TU / partitions | `Standard` / `1` / `2`, theo ảnh cấu hình |
| Consumer group | `cg-asa-sales` |
| ASA job / input | `asa-sales-gr03` / `eh-sales` |
| ASA pricing plan | `StandardV2`; chưa ghi số SU trong bộ bằng chứng này |
| Event time | `TIMESTAMP BY stream_event_time` |
| Time policy đã chụp | Late arrival 10s, out of order 5s, action Drop |
| Output error policy đã chụp | Retry |
| Azure SQL | `sqlsrv-sales-gr03-tram01` / `salesdb` |
| Hai bảng output | `dbo.event_metrics_30s`, `dbo.brand_sales_1m` |
| Query version | [queries.sql](queries.sql) lưu theo query tham chiếu của hướng dẫn đã dùng kiểm thử; chưa có export Portal độc lập để gán đúng phiên bản tại thời điểm run |

## 2. Expected và actual

| Kiểm tra | Expected | Actual | Kết quả |
|---|---:|---:|---|
| Input fixture | 8 event | 8 event | PASS |
| Producer ACK | 8 | 8 bản ghi trong `acknowledged.jsonl`, cùng ảnh 8 ACK | PASS |
| Event Hubs Incoming Messages | 8 | 8, theo ảnh metrics | PASS |
| ASA Input Events | 8 | 8, theo ảnh metrics | PASS |
| ASA Output Events | 8 dòng aggregate | 8, theo ảnh metrics | PASS |
| SQL bảng 30s: số dòng | 5 | 5 | PASS |
| SQL bảng 30s: accepted events | 8 | 8 | PASS |
| SQL bảng 30s: purchase events | 4 | 4 | PASS |
| SQL bảng 30s: revenue | 650 | 650 | PASS |
| SQL bảng 1m: số dòng | 3 | 3 | PASS |
| SQL bảng 1m: purchase events | 4 | 4 | PASS |
| SQL bảng 1m: revenue | 650 | 650 | PASS |
| Nhóm khóa trùng bảng 30s | 0 | 0 | PASS |
| Nhóm khóa trùng bảng 1m | 0 | 0 | PASS |

Output Events là số dòng tổng hợp: `5 + 3 = 8`. Việc bằng số input trong fixture này là trùng hợp; không dùng quy tắc output phải bằng input cho các run khác.

### Chi tiết bảng 30 giây

Các thời điểm dưới đây là UTC ngày 11/11/2026. Tất cả các dòng đều thuộc run đã nêu.

| window_end | event_type | event_count | revenue |
|---|---|---:|---:|
| 15:51:30 | cart | 1 | 0 |
| 15:51:30 | purchase | 3 | 600 |
| 15:51:30 | view | 2 | 0 |
| 15:52:00 | purchase | 1 | 50 |
| 15:52:00 | view | 1 | 0 |

### Chi tiết bảng theo brand

Mọi dòng có `window_end = 2026-11-11T15:52:00Z` và thuộc cùng run.

| brand | purchase_events | revenue |
|---|---:|---:|
| apple | 1 | 300 |
| samsung | 2 | 300 |
| unknown | 1 | 50 |

## 3. Bằng chứng

Thư mục ảnh: [`evidence/stream-analytics`](../evidence/stream-analytics/).

| File | Nội dung |
|---|---|
| `19-smoke-live-8-sends-acknowledged.png` | Run ID và đủ 8 ACK |
| `20-event-hubs-incoming-messages-8.png` | Event Hubs nhận 8 message |
| `21-smoke-asa-input-output.png` | ASA input/output metrics |
| `22-smoke-sql-30s.png` | Chi tiết 5 dòng bảng 30s |
| `23-smoke-sql-1m.png` | Chi tiết 3 dòng bảng brand |
| `24a-smoke-sql-totals-30s.png` | Tổng 5 dòng, 8 event, 4 purchase, revenue 650 |
| `24b-smoke-sql-totals-1m.png` | Tổng 3 dòng, 4 purchase, revenue 650 |
| `25-smoke-duplicate-check.png` | `duplicate_groups = 0` ở cả hai bảng |

Fixture và log gốc được sao chép nguyên trạng vào [`smoke-3433042d611a`](../evidence/stream-analytics/smoke-3433042d611a/): `sample_events.json`, `expected.json`, `acknowledged.jsonl`.

File [bằng chứng HTML](../evidence/stream-analytics/BANG_CHUNG_STREAMING.html) nhúng các ảnh để mở offline.

## 4. Phạm vi kết luận

- Đã xác minh live smoke 8 event chạy qua Event Hubs → ASA → hai bảng SQL; chi tiết, tổng và kiểm tra trùng output khớp expected.
- Kiểm tra khóa trùng chỉ xác nhận các dòng aggregate của run này; không chứng minh query có cơ chế khử event đầu vào trùng hoặc bảo đảm exactly-once cho mọi lần chạy.
- Chưa có số đo riêng về tổng lỗi input/output hoặc late/out-of-order drops trong bộ ảnh của run; không tự gán các metric chưa đo bằng 0. Số accepted khớp đủ 8 event của fixture.
- Tích hợp 10.000 event và benchmark tải là các bài riêng, chưa được nghiệm thu bằng run smoke này.

## 5. Tích hợp `integration-261113` — cập nhật 13/11/2026

**Đạt đối chiếu tổng nguồn → SQL và khóa trùng: 10.000 event, 118 purchase, revenue 35.757,22, 0 nhóm khóa trùng ở cả hai bảng. Đã bổ sung payload độc lập ngày 19/11/2026; còn thiếu đối chiếu từng dòng SQL và bộ metrics đầy đủ của run.**

Run thực tế là `integration-261113`.

Ngày 13/11/2026, người thực hiện xác nhận bốn ảnh gồm backlog và ba kết quả SQL thuộc run mới này. Bốn ảnh được lưu chung trong thư mục run.

### Số liệu quan sát trong SQL

| Bảng | Aggregate rows | Accepted events | Purchase events | Revenue |
|---|---:|---:|---:|---|
| `dbo.event_metrics_30s` | 28 | 10000 | 118 | 35757.22 |
| `dbo.brand_sales_1m` | 61 | Không áp dụng | 118 | Xấp xỉ 35757.219999…, làm tròn 2 chữ số thập phân là 35757.22 |

Kiểm tra nhóm khóa aggregate trùng trả về `duplicate_groups = 0` ở cả `event_metrics_30s` và `brand_sales_1m`.

Hai query đều lọc đúng `run_id = 'integration-261113'`. Số dòng aggregate khác nhau vì hai nhánh dùng khóa nhóm và cửa sổ khác nhau. Không so số dòng SQL với số event nguồn để kết luận thiếu dữ liệu.

`revenue` hiện dùng FLOAT theo schema bàn giao. FLOAT là kiểu số gần đúng; phần đuôi thập phân rất nhỏ ở hai tổng phù hợp với tính chất này. Hai tổng khớp ở mức hai chữ số thập phân; không thay kiểu dữ liệu hoặc cập nhật số lưu chỉ để sửa cách hiển thị. Nguồn: [Microsoft Learn — float and real](https://learn.microsoft.com/en-us/sql/t-sql/data-types/float-and-real-transact-sql).

### Bằng chứng hiện có

- [Tổng SQL bảng 30s](../evidence/stream-analytics/integration-261113/30a-integration-sql-totals-30s.png).
- [Tổng SQL bảng brand 1m](../evidence/stream-analytics/integration-261113/30b-integration-sql-totals-1m.png).
- [Kiểm tra trùng hai bảng](../evidence/stream-analytics/integration-261113/30c-integration-sql-duplicate-check.png): mỗi bảng có 0 nhóm khóa trùng.
- [Backlog ASA theo partition](../evidence/stream-analytics/integration-261113/29a-integration-asa-backlog-max.png): Max backlog = 46 ở từng partition. Người thực hiện xác nhận ảnh thuộc đợt run; chart bao phủ khung 12 giờ, rộng hơn khoảng phát xác định từ payload. Không dùng số này làm max riêng run hoặc cộng các cực đại thành backlog đồng thời. Phần Watermark Delay của ảnh bị cắt.

### Đối chiếu độc lập từ payload và log

Nguồn event là [events_integration-20261113.jsonl](../evidence/event-hubs/events_integration-20261113.jsonl), nguồn gửi là [producer_integration-261113.log](../producer/logs/producer_integration-261113.log).

| Chỉ tiêu | Expected từ nguồn | Actual trong ảnh SQL |
|---|---:|---:|
| Event hợp lệ | 10000 | 10000 |
| Purchase | 118 | 118 ở hai bảng |
| Revenue purchase | 35757.22 | 35757.22 sau làm tròn hai chữ số |
| Nhóm 30s | 28 | 28 dòng |
| Nhóm brand 1m | 61 | 61 dòng |

Payload có 9785 view, 97 cart, 118 purchase và 10.000 event_id duy nhất. Mốc `stream_event_time` từ `2026-11-13T13:37:27.895368Z` đến `2026-11-13T13:41:38.643197Z`, tương đương 20:37:27 đến 20:41:38 giờ Việt Nam.

Log báo 10.000 event gửi thành công, 0 event lỗi, 0 retry, 200 batch, elapsed 251,20 giây. Target là 50 event/s; actual throughput trong summary là 39,81 event/s.

[expected_from_payload.json](../evidence/stream-analytics/integration-261113/expected_from_payload.json) lưu kết quả tính độc lập, SHA-256 nguồn và các nhóm kỳ vọng theo biên cửa sổ `(start, end]`. Tính tổng revenue dùng Decimal từ giá trong payload. Đây là expected từ nguồn, không phải export thực tế của bảng SQL.

### Các kiểm chứng còn chờ theo mục 13 của hướng dẫn

- Export toàn bộ dòng SQL của hai bảng theo run để đối chiếu từng khóa, count và revenue với các nhóm trong `expected_from_payload.json`. Hiện đã khớp tổng và số nhóm; chưa xác nhận từng dòng SQL.
- Bổ sung metrics Event Hubs/ASA Input/Output, watermark với đúng khoảng chạy để hoàn thiện bằng chứng tích hợp. Số liệu phía gửi đã có từ log.

Các truy vấn dùng tạo ảnh chi tiết, tổng, kiểm tra trùng và liệt kê run được lưu tại [sql_validation.sql](sql_validation.sql).
