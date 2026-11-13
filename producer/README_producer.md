# Producer MVP

## 1. Overview

Producer MVP là chương trình Python đọc dữ liệu hành vi thương mại điện tử từ file CSV và gửi các sự kiện đến Azure Event Hubs.

Producer thuộc pipeline xử lý dữ liệu:

```text
Python Producer (Kaggle Notebook)
      |
      v
Azure Event Hubs
      |
      v
Azure Stream Analytics
      |
      v
Azure SQL Database
      |
      v
Power BI
```

Các chức năng chính:

- Đọc dữ liệu CSV theo từng chunk, không tải toàn bộ dataset vào RAM.
- Chuyển đổi dữ liệu nguồn thành event theo Data Contract.
- Chia dữ liệu thành hai partition DEV và DEMO.
- Gửi event theo batch đến Azure Event Hubs.
- Retry khi gặp lỗi gửi tạm thời.
- Lưu checkpoint sau khi batch được xác nhận gửi thành công.
- Hỗ trợ tiếp tục quá trình gửi bằng `--resume`.
- Ghi log quá trình xử lý và gửi dữ liệu.

## 2. Dataset

Dataset: **eCommerce Behavior Data from Multi-Category Store**

Nguồn: https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

File sử dụng:

```text
2019-Oct.csv
```

Thông tin dataset:

| Thuộc tính | Giá trị |
|---|---:|
| Tổng số dòng dữ liệu | 42,448,764 |
| DEV | 21,224,382 |
| DEMO | 21,224,382 |
| Tỷ lệ chia | 50% / 50% |

Dữ liệu được chia theo khoảng dòng, không tạo hai bản CSV riêng.

- DEV: `[0, 21224382)`
- DEMO: `[21224382, 42448764)`

Quy ước: khoảng bắt đầu được tính, khoảng kết thúc không được tính.

Hai partition không trùng lặp và không bỏ sót dòng dữ liệu.

File `manifest.json` lưu thông tin dataset, tổng số dòng và khoảng dòng của từng partition.

## 3. Project Structure

```text
BTL_IS402.R11/
├── .env.example
├── requirements.txt
└── producer/
    ├── prepare_data.py
    ├── producer.py
    ├── data_contract.json
    ├── manifest.json
    ├── README.md
    └── logs/
```

Các file được đưa vào Kaggle Notebook hoặc lấy từ repository của nhóm.

Các file sinh ra khi chạy:

```text
working/
├── manifest.json
└── checkpoints/
```

## 4. Environment Setup on Kaggle

### 4.1. Create Kaggle Notebook

1. Truy cập Kaggle.
2. Tạo Notebook mới.
3. Chọn dataset chứa `2019-Oct.csv` tại mục Add Input.
4. Kiểm tra đường dẫn dataset trong `/kaggle/input/`.

Ví dụ đường dẫn:

```python
INPUT_CSV = (
    "/kaggle/input/datasets/mkechinov/"
    "ecommerce-behavior-data-from-multi-category-store/"
    "2019-Oct.csv"
)
```

Đường dẫn thực tế phụ thuộc vào dataset được thêm vào Notebook.

### 4.2. Upload or clone project files

Đưa các file sau vào môi trường làm việc:

- `prepare_data.py`
- `producer.py`
- `data_contract.json`
- `requirements.txt`

Có thể lấy file từ GitHub repository hoặc upload trực tiếp vào Notebook.

Ví dụ sử dụng Git:

```python
!git clone https://github.com/23520052/BTL_IS402.R11.git
```

Sau đó xác định thư mục chứa các file Producer.

### 4.3. Install dependencies

```python
!pip install -r /kaggle/working/BTL_IS402.R11/requirements.txt
```

Dependencies:

```text
pandas==2.3.3
azure-eventhub==5.15.1
```

Nếu các file nằm trực tiếp trong `/kaggle/working/`, điều chỉnh đường dẫn tương ứng.

## 5. Configure Kaggle Secrets

Không ghi connection string trực tiếp vào Notebook hoặc Git repository.

Thêm hai Secrets trong mục Add-ons → Secrets:

| Secret name | Value |
|---|---|
| `EVENTHUB_CONNECTION_STR` | Azure Event Hubs connection string |
| `EVENTHUB_NAME` | `sales-events` |

Cho phép Notebook truy cập các Secrets đã tạo.

Đọc Secrets bằng:

```python
from kaggle_secrets import UserSecretsClient
import os

user_secrets = UserSecretsClient()

os.environ["EVENTHUB_CONNECTION_STR"] = (
    user_secrets.get_secret("EVENTHUB_CONNECTION_STR")
)

os.environ["EVENTHUB_NAME"] = (
    user_secrets.get_secret("EVENTHUB_NAME")
)
```

Không in giá trị connection string ra output của Notebook.

File `.env.example` chỉ dùng để mô tả tên biến môi trường, không chứa secret thật.

## 6. Prepare Dataset

Chạy `prepare_data.py` để kiểm tra dữ liệu và tạo manifest.

```python
!python /kaggle/working/BTL_IS402.R11/producer/prepare_data.py \
    --input "$INPUT_CSV" \
    --output /kaggle/working \
    --dev-ratio 0.5
```

Các tham số:

| Tham số | Ý nghĩa |
|---|---|
| `--input` | Đường dẫn file CSV nguồn |
| `--output` | Thư mục xuất manifest |
| `--dev-ratio` | Tỷ lệ dữ liệu dành cho DEV |
| `--chunk-size` | Số dòng đọc mỗi chunk |

Kiểm tra manifest:

```python
import json

with open("/kaggle/working/manifest.json", "r") as f:
    manifest = json.load(f)

print(json.dumps(manifest, indent=2))
```

Không cần tạo hai file CSV riêng cho DEV và DEMO.

## 7. Run Producer

Producer yêu cầu `--input` và hỗ trợ hai chế độ `dev` và `demo`.

### 7.1. Run DEV

Ví dụ gửi tối đa 10,000 valid events:

```python
!python /kaggle/working/BTL_IS402.R11/producer/producer.py \
    --input "$INPUT_CSV" \
    --manifest /kaggle/working/manifest.json \
    --mode dev \
    --run-id integration-01 \
    --max-events 10000
```

```!python /kaggle/working/producer.py \
    --input "/kaggle/input/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store/2019-Oct.csv" \
    --manifest "/kaggle/working/manifest.json" \
    --mode dev \
    --max-events 10000 \
    --batch-size 50 \
    --chunk-size 10000 \
    --run-id "integration-261113" \
    --rate 50 \
    --max-retries 5 \
    --base-backoff 1 \
    --max-backoff 30 \
    --jsonl-output "/kaggle/working/events_integration-20261113.jsonl"
```

### 7.2. Run DEMO

```python
!python /kaggle/working/BTL_IS402.R11/producer/producer.py \
    --input "$INPUT_CSV" \
    --manifest /kaggle/working/manifest.json \
    --mode demo \
    --run-id demo-01 \
    --max-events 10000
```

Lưu ý:

- `--max-events` giới hạn số event hợp lệ được gửi, không phải số dòng CSV được đọc.
- DEMO sử dụng partition thứ hai trong manifest.
- Với cách đọc tuần tự hiện tại, Producer cần đi qua phần DEV trước khi đến vị trí bắt đầu DEMO. Vì vậy thời gian khởi động DEMO có thể lâu hơn.

### 7.3. Producer options

| Tham số | Ý nghĩa |
|---|---|
| `--input` | Đường dẫn file CSV |
| `--manifest` | Đường dẫn manifest JSON |
| `--mode` | Partition `dev` hoặc `demo` |
| `--checkpoint` | Đường dẫn checkpoint tùy chỉnh |
| `--resume` | Tiếp tục từ checkpoint hiện có |
| `--max-events` | Giới hạn số valid events |
| `--batch-size` | Số event tối đa trong một batch |
| `--chunk-size` | Số dòng CSV đọc mỗi chunk |
| `--run-id` | Định danh lần chạy Producer |
| `--rate` | Giới hạn tốc độ gửi event; 0 là không giới hạn |
| `--max-retries` | Số lần retry tối đa |
| `--base-backoff` | Thời gian chờ retry ban đầu |
| `--max-backoff` | Thời gian chờ retry tối đa |

Xem các tùy chọn:

```python
!python /kaggle/working/BTL_IS402.R11/producer/producer.py --help
```

## 8. Checkpoint and Resume

Producer sử dụng checkpoint JSON để lưu vị trí xử lý dữ liệu.

Checkpoint chứa:

- `source_file`
- `mode`
- `run_id`
- `partition_start`
- `partition_end`
- `next_row`
- `last_confirmed_row`
- `updated_at`

Checkpoint chỉ được cập nhật sau khi batch gửi thành công.

Quá trình ghi sử dụng file tạm và thay thế file đích để hạn chế tình trạng checkpoint bị ghi dở.

### Resume

Khi cần tiếp tục quá trình gửi:

```python
!python /kaggle/working/producer/producer.py \
    --input "$INPUT_CSV" \
    --manifest /kaggle/working/manifest.json \
    --mode dev \
    --run-id integration-01 \
    --max-events 10000 \
    --resume
```

Cần sử dụng đúng `run_id`, `mode` và checkpoint tương ứng.

**Lưu ý về Kaggle session:**

Checkpoint nằm trong `/kaggle/working/` có thể mất khi môi trường Notebook bị khởi tạo lại. Nếu cần tiếp tục sau khi session bị reset, hãy tải checkpoint về máy hoặc lưu ở nơi có thể khôi phục, sau đó đưa lại vào đúng đường dẫn trước khi chạy `--resume`.

### Delivery semantics

Nếu Event Hubs đã nhận batch nhưng chương trình dừng trước khi cập nhật checkpoint, batch có thể được gửi lại khi resume.

Vì vậy, cơ chế hiện tại có thể tạo duplicate events trong một số tình huống lỗi.

`event_id` được tạo ổn định theo `run_id`, file nguồn và vị trí dòng để hỗ trợ nhận diện event trùng ở các bước xử lý sau.

## 9. Logging and Verification

Kiểm tra log sau mỗi lần chạy để theo dõi:

- Số event gửi thành công.
- Số event lỗi.
- Số lần retry.
- Số batch đã gửi.
- Thời gian thực thi.
- Tốc độ gửi event.

Đối chiếu số liệu Producer với Incoming Messages trên Azure Event Hubs.

Không in hoặc lưu connection string trong log.

## 10. Troubleshooting

### Missing environment variables

Kiểm tra Kaggle Secrets đã được thêm và Notebook đã được cấp quyền truy cập hay chưa.

### Event Hubs connection error

Kiểm tra:

- Connection string.
- Event Hub name.
- Quyền gửi dữ liệu.
- Kết nối mạng và trạng thái Azure service.

### Invalid manifest

Kiểm tra:

- Đúng file `manifest.json`.
- Tên file nguồn khớp với manifest.
- File CSV không bị thay thế hoặc thay đổi.
- Khoảng dòng DEV/DEMO hợp lệ.

### Resume error

Kiểm tra:

- Checkpoint có tồn tại không.
- `run_id` và `mode` có khớp không.
- File nguồn và partition có khớp checkpoint không.

### Event validation error

Đối chiếu dữ liệu với `data_contract.json`:

- `event_type`: `view`, `cart`, `purchase`.
- Các trường ID là số nguyên không âm.
- `price` là số không âm.
- Các trường timestamp đúng định dạng UTC.
- Các trường nullable được xử lý đúng.

---

**End of Producer MVP Documentation**
