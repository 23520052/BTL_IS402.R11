# Producer Benchmark

## 1. Mục đích

Đo hiệu năng của Producer khi gửi dữ liệu hành vi thương mại điện tử từ CSV lên Azure Event Hubs ở nhiều mức tải cấu hình. Benchmark sử dụng lại `producer.py` hiện tại, không thay thế logic đọc CSV, chuyển đổi event, batching, retry, checkpoint hoặc rate limiter.

Benchmark chính thức được thực hiện ngày **14/11/2026**, với 4 mức tải mục tiêu: 100, 500, 1.000 và 2.000 events/second. Mỗi mức tải chạy 3 lần, tổng cộng 12 lần chạy.

## 2. Phạm vi đo

Benchmark chỉ đo phía Python Producer và quá trình gửi tới Azure Event Hubs. Không đo Azure Stream Analytics, Azure SQL Database hoặc Power BI.

Mỗi lần chạy ghi nhận:

-   Target rate và repetition.
-   `run_id` duy nhất.
-   Số event gửi thành công (`events_sent`).
-   Số event lỗi (`events_error`).
-   Tổng số lần retry (`retries`).
-   Thời gian thực thi Producer (`duration_seconds`).
-   Throughput thực tế (`actual_events_per_sec`).
-   Kích thước payload JSON thực tế (`payload_bytes`) và throughput
    (`payload_MB_per_sec`).
-   Số event trong JSONL (`jsonl_event_count`) để đối chiếu.
-   Batch size, chunk size, CPU, RAM, runtime, Python/OS và Azure Event
    Hubs region.
-   Exit code và trạng thái của tiến trình Producer.

`payload_MB_per_sec` dùng MB thập phân (1 MB = 1.000.000 bytes). Kích thước payload được tính từ các JSON payload UTF-8 đã ghi vào JSONL sau khi batch được Event Hubs xác nhận gửi thành công; ký tự xuống dòng phân tách JSONL không được tính vào payload.

## 3. Cách đo

1.  `benchmark_producer.py` gọi `producer.py` bằng subprocess cho từng cặp target rate/repetition.
2.  Mỗi lần chạy có `run_id`, checkpoint, log và JSONL riêng.
3.  Producer dùng `--rate` để giới hạn tốc độ đầu vào theo mức tải cần thử.
4.  Số event thành công, event lỗi và retry được tổng hợp từ log của Producer.
5.  Payload bytes được tính từ JSONL của lần chạy tương ứng.
6.  Throughput thực tế được tính bằng:
    `actual_events_per_sec = events_sent / duration_seconds`
    `payload_MB_per_sec = payload_bytes / 1.000.000 / duration_seconds`
7.  Kết quả từng lần chạy được ghi thành một dòng trong `producer_metrics.csv`.
8.  Kết quả chỉ được xem là hợp lệ khi tiến trình kết thúc thành công, trạng thái hoàn tất và số event JSONL khớp với số event gửi thành công.

Thời gian chính dùng cho throughput là `Elapsed time` do Producer ghi nhận. Nếu Producer kết thúc lỗi trước khi in summary, benchmark dùng wall-clock duration của subprocess và đánh dấu trạng thái để người thực hiện kiểm tra log.
## 4. Môi trường thực nghiệm

| Thuộc tính | Giá trị thực tế |
|---|---|
| Ngày thực hiện | 14/11/2026 |
| Runtime | Kaggle Notebook |
| CPU |4 |
| RAM | 31,35 GiB (Tự động ghi nhận khi chạy) |
| Python version | 3.13.18 |
| Operating system | Linux 6.18.55+ x86_64, glibc 2.39 |
| Azure Event Hubs region | Người chạy nhập bằng `--eventhub-region` |
| Event Hub name | Được cấu hình qua Kaggle Secret, không ghi secret vào báo cáo |
| Batch size | Mặc định 50 events/batch; có thể cấu hình |
| CSV chunk size | Mặc định 10.000 rows/chunk |
| Max events mỗi lần chạy | Mặc định 10.000 |
| Số lần lặp | Mặc định 3 lần/mức tải |
| Mức tải mục tiêu | 100, 500, 1.000, 2.000 events/second |

## 5. Cách chạy trên Kaggle

### 5.1. Chuẩn bị

- Kaggle Notebook đã Add Input dataset có file `2019-Oct.csv`.
- Repository đã được clone hoặc các file dự án đã được đưa vào `/kaggle/working/BTL_IS402.R11/`.
- Có `producer/producer.py`, `producer/benchmark_producer.py`, `producer/manifest.json`.
- Đã tạo manifest bằng `prepare_data.py` nếu chưa có manifest hợp lệ.
- Đã cài dependencies từ `requirements.txt`.
- Kaggle Secrets có `EVENTHUB_CONNECTION_STR` và `EVENTHUB_NAME`, Notebook được cấp quyền truy cập.
- Event Hub đã sẵn sàng nhận message và tài khoản có quyền gửi.

### 5.2. Cài dependencies

```python
!pip install -q -r /kaggle/working/BTL_IS402.R11/requirements.txt
```

### 5.3. Đọc Kaggle Secrets

```python
import os
from kaggle_secrets import UserSecretsClient

secrets = UserSecretsClient()
os.environ["EVENTHUB_CONNECTION_STR"] = secrets.get_secret("EVENTHUB_CONNECTION_STR")
os.environ["EVENTHUB_NAME"] = secrets.get_secret("EVENTHUB_NAME")
```

Không in hai biến môi trường này ra Notebook output hoặc đưa vào Git.

### 5.4. Chạy benchmark

Điều chỉnh `INPUT_CSV` theo đúng đường dẫn dataset trong Kaggle:

```python
INPUT_CSV = "/kaggle/input/<your-dataset-folder>/2019-Oct.csv"
PROJECT = "/kaggle/working/BTL_IS402.R11"

!python {PROJECT}/producer/benchmark_producer.py \
    --producer {PROJECT}/producer/producer.py \
    --input {INPUT_CSV} \
    --manifest {PROJECT}/producer/manifest.json \
    --mode dev \
    --rates 100 500 1000 2000 \
    --repetitions 3 \
    --max-events 10000 \
    --batch-size 50 \
    --chunk-size 10000 \
    --eventhub-region "Southeast Asia" \
    --output /kaggle/working/producer_metrics.csv \
    --run-dir /kaggle/working/benchmark_runs
```

Nếu muốn chạy thử ngắn trước, có thể đặt `--max-events 1000` và chỉ dùng một vài mức tải; kết quả chạy thử không nên gộp với kết quả benchmark chính thức.

### 5.5. Kết quả đầu ra

-   `/kaggle/working/producer_metrics.csv`: bảng tổng hợp 12 lần chạy.
-   `/kaggle/working/benchmark_runs/`: log, JSONL và checkpoint riêng của từng lần chạy.

Thư mục `benchmark_runs/` chứa log và JSONL riêng của từng lần chạy. Giữ lại các file này làm bằng chứng và để kiểm tra những lần chạy lỗi hoặc lệch số lượng JSONL.

## 6. Kết quả benchmark thực tế

### 6.1. Tổng quan

| Chỉ tiêu | Kết quả |
|---|---|
| Số mức tải | 4 |
| Số lần chạy mỗi mức | 3 |
| Tổng số lần chạy | 12 |
| Tổng số events gửi thành công | 120.000 |
| Tổng số events lỗi | 0 |
| Tổng số lần retry | 0 |
| Số lần chạy hoàn tất | 12/12 |
| Process return code | 0 ở cả 12 lần |
| JSONL event count | 10.000 ở cả 12 lần |
| Payload mỗi lần chạy | 4.044.364 bytes |

Tất cả 12 lần chạy có `status=completed`, `process_return_code=0`, `events_error=0`, `retries=0`. `jsonl_event_count` đều bằng `events_sent` (10.000 event/lần).

### 6.2. Kết quả trung bình theo mức tải

Các giá trị throughput và duration dưới đây là trung bình số học của 3 lần lặp ở mỗi mức tải. Events sent, errors và retries là tổng của 3 lần lặp.

| Target rate (events/s) | Repetitions | Events sent | Errors | Retries | Avg duration (s) | Avg actual throughput (events/s) | Avg payload throughput (MB/s) |
| 100 | 3 | 30.000 | 0 | 0 | 149,28 | 66,99 | 0,0271 |
| 500 | 3 | 30.000 | 0 | 0 | 47,99 | 208,39 | 0,0843 |
| 1.000 | 3 | 30.000 | 0 | 0 | 40,27 | 248,35 | 0,1004 |
| 2.000 | 3 | 30.000 | 0 | 0 | 39,90 | 250,61 | 0,1014 |

### 6.3. Nhận xét

-   Cả 12 lần chạy đều hoàn tất thành công, gửi đủ 10.000 events mỗi lần; không ghi nhận event lỗi hoặc retry.
-   Khi target rate tăng từ 100 lên 500 events/s, throughput thực tế trung bình tăng từ 66,99 lên 208,39 events/s.
-   Khi target rate tăng từ 500 lên 1.000 events/s, throughput thực tế tăng lên 248,35 events/s.
-   Khi target rate tăng tiếp từ 1.000 lên 2.000 events/s, throughput chỉ tăng nhẹ lên 250,61 events/s. Trong cấu hình thử nghiệm này, throughput có dấu hiệu bão hòa quanh 250 events/s.
-   Payload throughput trung bình tăng từ 0,0271 MB/s ở mức tải 100 lên khoảng 0,1014 MB/s ở mức tải 2.000.
-   Kết quả cho thấy Producer không đạt target rate đã cấu hình ở cả bốn mức. Target rate là tốc độ giới hạn đầu vào, không phải throughput được đảm bảo.

Không thể chỉ dựa trên kết quả này để xác định chính xác nguyên nhân giới hạn throughput. Muốn xác định bottleneck cần đo/profile riêng các công đoạn đọc CSV, chuyển đổi event, rate limiter, batching, gửi Event Hubs và cập nhật checkpoint.

## 7. Lưu ý và giới hạn

- Target rate là giới hạn tốc độ cấu hình cho Producer, không phải throughput thực tế được đảm bảo. Báo cáo phải dùng `actual_events_per_sec` đo được.
- Benchmark gửi message thật lên Event Hubs. Mỗi lần chạy tạo `run_id` mới và phát lại một đoạn dữ liệu nguồn. Trong lần thử này, nhóm đã stop Stream Analytics trước khi benchmark; do đó không có xử lý tiếp qua Stream Analytics trong thời gian thử nghiệm. Nếu pipeline được bật lại hoặc có consumer khác, cần xem xét khả năng các message benchmark được xử lý tiếp.
- Mỗi repetition là một lần gửi mới, không phải resume checkpoint cũ. Điều này tránh checkpoint của lần trước làm thay đổi số event được đo.
- Kết quả phụ thuộc tài nguyên Kaggle tại thời điểm chạy, network, vị trí địa lý, cấu hình Event Hubs, batch size và tải của dịch vụ.
- `payload_MB_per_sec` là tốc độ payload JSON ở phía Producer, không phải network wire throughput; không bao gồm overhead giao thức, TLS hoặc framing của Event Hubs.
- Thời gian Producer bao gồm đọc/parse CSV, tạo event, rate limiting, gửi batch và cập nhật checkpoint; do đó đây là throughput end-to-end của Producer, không phải tốc độ riêng của Event Hubs.
- Nếu process thất bại hoặc `jsonl_event_count` khác `events_sent`, cần mở log tương ứng để kiểm tra trước khi dùng số liệu.
- Không ghi connection string, SAS key hoặc thông tin bí mật vào CSV, log, ảnh chụp hay tài liệu.
- Benchmark này không đo Stream Analytics, SQL hoặc Power BI.
- Kết quả phản ánh một cấu hình thử nghiệm cụ thể: Kaggle Notebook, batch size 50, chunk size 10.000, tối đa 10.000 events mỗi lần và mode `dev`. Không nên suy rộng trực tiếp thành năng lực tối đa của Azure Event Hubs hoặc của hệ thống production.

## 8. Kết luận thực nghiệm

Benchmark Producer đã hoàn thành với 4 mức tải, mỗi mức lặp lại 3 lần. Cả 12 lần chạy đều gửi thành công 10.000 events, tổng cộng 120.000 events; không ghi nhận event lỗi hoặc retry. Số lượng event trong JSONL khớp với số event gửi thành công ở tất cả các lần chạy.

Throughput thực tế trung bình lần lượt là 66,99; 208,39; 248,35 và 250,61 events/s tương ứng với target rate 100; 500; 1.000 và 2.000 events/s. Throughput tăng khi nâng target rate từ 100 lên 1.000 events/s, nhưng gần như không tăng thêm khi target rate tăng từ 1.000 lên 2.000 events/s. Vì vậy, trong cấu hình thử nghiệm này, Producer thể hiện dấu hiệu bão hòa quanh 250 events/s.

Đây là kết quả đo end-to-end phía Producer trong môi trường Kaggle và cấu hình đã nêu, không phải phép đo throughput độc lập của Azure Event Hubs. Cần profiling bổ sung nếu muốn xác định nguyên nhân giới hạn hiệu năng.
