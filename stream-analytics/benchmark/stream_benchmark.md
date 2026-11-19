# Kết quả đo streaming và bàn giao benchmark

Cập nhật ngày 19/11/2026. Bộ hiện có gồm một run smoke và một run tích hợp. Benchmark ASA ở ít nhất ba mức tải chưa có đầy đủ số đo và được để lại cho thành viên hỗ trợ đo bổ sung.

## 1. Kết quả hiện có

| Run | Loại | Target Producer | Actual Producer | SQL accepted | Purchase | Revenue |
|---|---|---:|---:|---:|---:|---:|
| `smoke-3433042d611a` | Smoke | Không áp dụng | Chưa ghi | 8 | 4 | 650.00 |
| `integration-261113` | Tích hợp | 50 event/s | 39.81 event/s | 10000 | 118 | 35757.22 |

Smoke có ảnh ASA Input = 8, Output = 8. Output là 5 dòng bảng 30s cộng 3 dòng bảng brand; việc bằng số input ở fixture này không áp dụng cho run khác.

Integration có 28 dòng bảng 30s và 61 dòng bảng brand, không có nhóm khóa trùng trong ảnh kiểm tra. Payload độc lập có đủ 10.000 event, 118 purchase và revenue 35.757,22. Hai tổng SQL khớp nguồn và nhau trong độ chính xác hai chữ số thập phân.

## 2. Phạm vi của các con số

39,81 event/s lấy từ summary Producer với elapsed 251,20 giây. Đây là tốc độ của quá trình đọc CSV, tạo event, rate limit, batch, gửi và checkpoint; không phải throughput tối đa đã chứng minh của ASA.

Ảnh backlog của integration có Max 46 ở mỗi partition trong khoảng 13/11 14:59 đến 14/11 02:59 UTC+7. Khoảng này rộng hơn run, chưa dùng làm `backlog_max` riêng run. Không cộng hai cực đại khác thời điểm thành backlog đồng thời. Phần Watermark Delay trong ảnh bị cắt nên chưa ghi số.

CSV lưu số liệu có nguồn; các ô thiếu để trống, không gán bằng 0. Cấu hình baseline lấy từ ảnh triển khai: 2 partition, 1 TU, SQL Basic 5 DTU; không có ảnh số SU và cấu hình đồng thời từng run để xác nhận tất cả tham số tại lúc đo.

## 3. Benchmark Producer đã có trên Git

[producer/benchmark_producer.md](../../producer/benchmark_producer.md) ghi ngày đo 14/11/2026, bốn mức target 100, 500, 1000 và 2000 event/s, mỗi mức lặp ba lần. Tài liệu đó xác nhận ASA đã dừng trong lúc đo. Vì vậy không chép các kết quả đó thành số đo backlog, watermark, Input/Output hoặc năng lực xử lý của ASA.

## 4. Bổ sung benchmark ASA

TV1 hoặc thành viên hỗ trợ có thể vận hành Producer; người đo streaming cần lưu metrics ASA trong cùng lần chạy. Giữ cấu hình query, TU/SU, partitions, payload và SQL tier ổn định để so sánh. Ghi target và actual Producer riêng.

| Bước | Thực hiện |
|---|---|
| Chuẩn bị | Ghi TU, SU, SQL tier, time policy, query version; kiểm tra input/output; dùng warm-up riêng |
| Phát | Ít nhất ba mức tải, run_id mới từng lần, lưu payload và summary; chọn mức phù hợp khả năng Producer |
| Theo dõi | Incoming Messages/Bytes, Input/Output, backlog, watermark, memory, errors, late/out-of-order và throttle khi có |
| Kết thúc run | Dừng phát, theo dõi drain, đợi cửa sổ cuối, đối chiếu SQL |
| Lưu | Export metrics, ảnh đúng time range, log Producer và một dòng CSV mỗi run |

Hướng dẫn thực hành đề xuất 100/300/500 event/s, khoảng 5 phút mỗi mức. Đây là thiết kế thử, không phải số đã đo hoặc capacity cam kết. Nếu chọn mức khác theo Producer thực tế, ghi rõ phương pháp trong báo cáo. Mỗi mức lặp được bao nhiêu lần thì báo đúng số lần đó.

## 5. Aggregation và đơn vị

| Metric | Aggregation | Đơn vị |
|---|---|---|
| Input/Output Events | Sum | Event/output record |
| Backlogged Input Events | Max | Event đang chờ |
| Watermark Delay | Max | Giây |
| SU (Memory) % Utilization | Average và Max | Phần trăm |
| Runtime/Conversion/Deserialization errors | Sum | Lỗi |
| Late Input/Out-of-Order Events | Sum | Event |

Metrics thông thường không có dimension run_id, nên cần traffic tách biệt và khoảng thời gian đúng run. Khi split partition, giữ tên chuỗi/dimension trong dữ liệu nguồn. Watermark delay là metric tiến độ ASA, không đại diện toàn bộ thời gian từ event đến hiển thị trên Power BI.

## 6. Tiêu chí báo cáo

Chỉ kết luận ở mức tải đã đo. Backlog hoặc delay tăng kéo dài cần đối chiếu CPU/memory, input và SQL trước khi thay capacity. Giữ bằng chứng trước/sau nếu thực sự thay cấu hình; không tự suy ra cần tăng SU chỉ từ một đỉnh backlog.

Kết quả hoàn thành ba mức tải chưa có trong bộ bàn giao này. Tài liệu hiện xác nhận pipeline và số liệu test/tích hợp đã lưu, không khẳng định nghiệm thu hiệu năng tải cao.

## Nguồn

- [stream_metrics.csv](stream_metrics.csv).
- [Định nghĩa cột và nguồn số đo](README.md).
- [Biên bản test](../stream_test.md).
- [ASA monitoring reference](https://learn.microsoft.com/en-us/azure/stream-analytics/monitor-azure-stream-analytics-reference).
