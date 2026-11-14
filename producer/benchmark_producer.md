# Producer Benchmark

## 1. Mục đích

Đo hiệu năng của Producer khi gửi dữ liệu hành vi thương mại điện tử từ CSV lên Azure Event Hubs ở nhiều mức tải cấu hình. Benchmark sử dụng lại `producer.py` hiện tại, không thay thế logic đọc CSV, chuyển đổi event, batching, retry, checkpoint hoặc rate limiter.

Các mức tải mặc định: 100, 500, 1.000 và 2.000 events/second. Mỗi mức tải chạy tối thiểu 3 lần.

## 2. Phạm vi đo

Benchmark chỉ đo phía Python Producer và quá trình gửi tới Azure Event Hubs. Không đo Azure Stream Analytics, Azure SQL Database hoặc Power BI.

Mỗi lần chạy ghi nhận:

- Target rate và repetition.
- `run_id` duy nhất.
- Số event gửi thành công.
- Số event lỗi.
- Tổng số lần retry.
- Thời gian thực thi Producer.
- Throughput thực tế (events/second).
- Kích thước payload JSON thực tế (bytes) và throughput (MB/second).
- Batch size, CPU, RAM, runtime, Python/OS và Azure Event Hubs region.

`payload_MB_per_sec` dùng MB thập phân (1 MB = 1.000.000 bytes). Kích thước payload được tính từ các JSON payload UTF-8 đã ghi vào JSONL sau khi batch được Event Hubs xác nhận gửi thành công; ký tự xuống dòng phân tách JSONL không được tính vào payload.

## 3. Cách đo

1. `benchmark_producer.py` gọi `producer.py` bằng subprocess cho từng cặp target rate/repetition.
2. Mỗi lần chạy có `run_id`, checkpoint, log và JSONL riêng.
3. Producer dùng `--rate` để giới hạn tốc độ đầu vào theo mức tải cần thử.
4. Số event thành công, event lỗi và retry được tổng hợp từ log của Producer.
5. Payload bytes được tính từ JSONL của lần chạy tương ứng.
6. Throughput thực tế được tính bằng:

   `actual_events_per_sec = events_sent / duration_seconds`

   `payload_MB_per_sec = payload_bytes / 1.000.000 / duration_seconds`

7. Kết quả từng lần chạy được ghi thành một dòng trong `producer_metrics.csv`. Không tự điền hoặc suy đoán số liệu chưa chạy.

Thời gian chính dùng cho throughput là `Elapsed time` do Producer ghi nhận. Nếu Producer kết thúc lỗi trước khi in summary, benchmark dùng wall-clock duration của subprocess và đánh dấu trạng thái để người thực hiện kiểm tra log.

## 4. Môi trường thực nghiệm

| Thuộc tính | Giá trị thực tế |
|---|---|
| Runtime | Kaggle Notebook |
| CPU | Tự động ghi nhận khi chạy |
| RAM | Tự động ghi nhận khi chạy |
| Python version | Tự động ghi nhận khi chạy |
| Operating system | Tự động ghi nhận khi chạy |
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

### 5.5. Lấy kết quả

File kết quả chính:

```text
/kaggle/working/producer_metrics.csv
```

Thư mục `benchmark_runs/` chứa log và JSONL riêng của từng lần chạy. Giữ lại các file này làm bằng chứng và để kiểm tra những lần chạy lỗi hoặc lệch số lượng JSONL.

## 6. Bảng kết quả

Điền bảng sau từ số liệu thực tế trong `producer_metrics.csv`. Có thể báo cáo trung bình của 3 lần lặp cho mỗi mức tải; nên giữ cả độ lệch chuẩn hoặc min/max nếu có đủ dữ liệu.

| Target rate (events/s) | Repetitions | Events sent | Errors | Retries | Avg duration (s) | Avg actual throughput (events/s) | Avg payload throughput (MB/s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 3 | — | — | — | — | — | — |
| 500 | 3 | — | — | — | — | — | — |
| 1.000 | 3 | — | — | — | — | — | — |
| 2.000 | 3 | — | — | — | — | — | — |

## 7. Lưu ý và giới hạn

- Target rate là giới hạn tốc độ cấu hình cho Producer, không phải throughput thực tế được đảm bảo. Báo cáo phải dùng `actual_events_per_sec` đo được.
- Benchmark gửi message thật lên Event Hubs. Mỗi lần chạy tạo `run_id` mới và phát lại một đoạn dữ liệu nguồn; các message này có thể đi tiếp xuống Stream Analytics/SQL/Power BI nếu pipeline đang hoạt động. Nên dùng Event Hub hoặc môi trường kiểm thử riêng. Nếu buộc dùng Event Hub đang tích hợp, cần thống nhất trước cách nhận diện/lọc các `run_id` benchmark với thành viên phụ trách downstream.
- Mỗi repetition là một lần gửi mới, không phải resume checkpoint cũ. Điều này tránh checkpoint của lần trước làm thay đổi số event được đo.
- Kết quả phụ thuộc tài nguyên Kaggle tại thời điểm chạy, network, vị trí địa lý, cấu hình Event Hubs, batch size và tải của dịch vụ.
- `payload_MB_per_sec` là tốc độ payload JSON ở phía Producer, không phải network wire throughput; không bao gồm overhead giao thức, TLS hoặc framing của Event Hubs.
- Thời gian Producer bao gồm đọc/parse CSV, tạo event, rate limiting, gửi batch và cập nhật checkpoint; do đó đây là throughput end-to-end của Producer, không phải tốc độ riêng của Event Hubs.
- Nếu process thất bại hoặc `jsonl_event_count` khác `events_sent`, cần mở log tương ứng để kiểm tra trước khi dùng số liệu.
- Không ghi connection string, SAS key hoặc thông tin bí mật vào CSV, log, ảnh chụp hay tài liệu.
- Benchmark này không đo Stream Analytics, SQL hoặc Power BI.

## 8. Kết luận thực nghiệm

Chưa có kết luận định lượng trước khi chạy benchmark. Sau khi có kết quả, nhận xét mức tải mà Producer duy trì ổn định, chênh lệch giữa target rate và actual throughput, tỷ lệ lỗi/retry, và ảnh hưởng của batch size. Không suy rộng kết quả ngoài cấu hình môi trường đã ghi nhận.
