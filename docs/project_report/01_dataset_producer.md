# 01. KHẢO SÁT DATASET VÀ THIẾT KẾ PYTHON PRODUCER

## 1. Giới thiệu dataset

### 1.1. Nguồn dữ liệu

Đồ án sử dụng bộ dữ liệu **eCommerce behavior data from multi-category store** được công bố trên Kaggle.

Nguồn dữ liệu: https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

File được sử dụng là `2019-Oct.csv`, chứa dữ liệu hành vi người dùng trên nền tảng thương mại điện tử trong tháng 10/2019.

Theo kết quả khảo sát được lưu trong `producer/data_profile.json`, tập dữ liệu có các thông số:

| Thuộc tính | Giá trị |
|---|---:|
| Tên file | `2019-Oct.csv` |
| Dung lượng | 5.668.612.855 bytes |
| Dung lượng GB | 5,6686 GB |
| Dung lượng GiB | 5,2793 GiB |
| Tổng số bản ghi | 42.448.764 |
| Thời điểm bắt đầu | 01/10/2019 00:00:00 UTC |
| Thời điểm kết thúc | 31/10/2019 23:59:59 UTC |
| Phương pháp khảo sát | Pandas đọc CSV theo chunk |
| Số chunk khi khảo sát | 85 |
| Kích thước chunk khảo sát | 500.000 dòng |

Do dung lượng dữ liệu lớn hơn 5 GB, việc nạp toàn bộ CSV vào RAM không phù hợp với phương pháp triển khai của đồ án. Vì vậy, dữ liệu được xử lý tuần tự theo từng chunk.

### 1.2. Cấu trúc dữ liệu

File CSV có 9 trường dữ liệu chính:

| Trường | Ý nghĩa |
|---|---|
| `event_time` | Thời điểm phát sinh sự kiện |
| `event_type` | Loại hành vi |
| `product_id` | Mã sản phẩm |
| `category_id` | Mã danh mục |
| `category_code` | Mã phân cấp danh mục |
| `brand` | Thương hiệu sản phẩm |
| `price` | Giá sản phẩm |
| `user_id` | Mã người dùng |
| `user_session` | Mã phiên tương tác |

### 1.3. Các loại sự kiện

Theo kết quả khảo sát thực tế trong `data_profile.json`, dataset có ba loại sự kiện:

| Event type | Số lượng | Ý nghĩa |
|---|---:|---|
| `view` | 40.779.399 | Người dùng xem sản phẩm |
| `cart` | 926.516 | Người dùng thêm sản phẩm vào giỏ hàng |
| `purchase` | 742.849 | Người dùng thực hiện sự kiện mua sản phẩm |
| **Tổng** | **42.448.764** | |

**Lưu ý về `remove_from_cart`:**

Trong kế hoạch ban đầu, nhóm dự kiến sử dụng bốn loại sự kiện gồm `view`, `cart`, `remove_from_cart` và `purchase`. Tuy nhiên, kết quả khảo sát CSV và Data Contract hiện tại cho thấy file `2019-Oct.csv` chỉ chứa ba loại sự kiện: `view`, `cart` và `purchase`.

Do đó, `remove_from_cart` không được đưa vào Data Contract và không được hỗ trợ bởi phiên bản Producer hiện tại.

**Lưu ý về purchase event:**

Sự kiện `purchase` được hiểu là một **purchase event**, không đồng nghĩa với một đơn hàng hoàn chỉnh. Dataset không có trường `order_id` để xác định và nhóm các sự kiện thành đơn hàng.

Vì vậy, số lượng purchase event chỉ phản ánh số sự kiện mua hàng được ghi nhận. Tỷ lệ `purchase/view` là tỷ lệ giữa hai nhóm sự kiện, không phải tỷ lệ chuyển đổi của những khách hàng duy nhất.

### 1.4. Chất lượng và giới hạn dữ liệu

Kết quả thống kê giá trị thiếu từ `producer/data_profile.json`:

| Trường | Số lượng giá trị thiếu |
|---|---:|
| `event_time` | 0 |
| `event_type` | 0 |
| `product_id` | 0 |
| `category_id` | 0 |
| `category_code` | 13.515.609 |
| `brand` | 6.117.080 |
| `price` | 0 |
| `user_id` | 0 |
| `user_session` | 2 |

Một số giới hạn của dataset:

- Dữ liệu chỉ phản ánh hành vi được ghi nhận trong tháng 10/2019.
- Đây là dữ liệu lịch sử, không phải dữ liệu phát sinh trực tiếp tại thời điểm hệ thống chạy.
- Không có `order_id`, do đó không thể xác định chính xác số đơn hàng.
- Một người dùng có thể tạo nhiều sự kiện trong cùng một phiên hoặc nhiều phiên khác nhau.
- Trường `brand` và `category_code` có số lượng giá trị thiếu đáng kể.
- `purchase` không thể được sử dụng trực tiếp như số lượng đơn hàng thực tế.

Trong đồ án, dataset được sử dụng để mô phỏng nguồn phát sinh dữ liệu streaming. Python Producer đọc dữ liệu lịch sử và phát các sự kiện lên Azure Event Hubs nhằm kiểm thử khả năng xử lý luồng của hệ thống.

## 2. Cơ sở lý thuyết về CSV và JSON

### 2.1. CSV

CSV (Comma-Separated Values) là định dạng lưu trữ dữ liệu dạng bảng, trong đó mỗi dòng biểu diễn một bản ghi và các trường được phân cách bằng dấu phẩy.

Ưu điểm:

- Cấu trúc đơn giản, dễ đọc và dễ trao đổi dữ liệu.
- Được hỗ trợ bởi nhiều công cụ như Python, Excel và các hệ quản trị dữ liệu.
- Phù hợp với việc lưu trữ dữ liệu dạng bảng có quy mô lớn.

Hạn chế:

- Không mô tả trực tiếp cấu trúc dữ liệu phân cấp.
- Không quy định kiểu dữ liệu một cách chặt chẽ.
- Cần xác định quy tắc xử lý giá trị thiếu và chuyển đổi kiểu dữ liệu khi đọc.

Trong đồ án, CSV được sử dụng làm nguồn dữ liệu lịch sử. Python Producer sử dụng Pandas `read_csv()` với tham số `chunksize` để đọc từng phần dữ liệu, tránh nạp toàn bộ file vào bộ nhớ.

### 2.2. JSON

JSON (JavaScript Object Notation) là định dạng trao đổi dữ liệu có cấu trúc, sử dụng các cặp khóa – giá trị để biểu diễn thông tin.

Ví dụ một sự kiện sau khi chuyển đổi:

```json
{
  "event_id": "example-event-id",
  "run_id": "integration-01",
  "original_event_time": "2019-10-01T00:00:00Z",
  "stream_event_time": "2026-11-16T10:00:00Z",
  "event_type": "view",
  "product_id": 100001,
  "category_id": 2053013555631882655,
  "category_code": "electronics.smartphone",
  "brand": "example_brand",
  "price": 99.99,
  "user_id": 123456,
  "user_session": "example-session"
}
```

JSON có các ưu điểm:

- Cấu trúc rõ ràng, dễ mở rộng.
- Các trường dữ liệu được xác định bằng tên khóa.
- Phù hợp với việc trao đổi dữ liệu giữa các dịch vụ.
- Dễ dàng chuyển đổi từ bản ghi CSV thành đối tượng dữ liệu.

### 2.3. Lý do chuyển đổi CSV sang JSON

CSV phù hợp với lưu trữ dữ liệu dạng bảng, trong khi JSON phù hợp với việc truyền tải các sự kiện độc lập giữa những thành phần trong hệ thống.

Quá trình chuyển đổi được thực hiện như sau:

1. Đọc một phần dữ liệu từ CSV.
2. Kiểm tra các trường dữ liệu cần thiết.
3. Chuyển đổi bản ghi thành JSON event.
4. Bổ sung `event_id`, `run_id` và hai trường thời gian.
5. Đưa event vào batch.
6. Gửi batch lên Azure Event Hubs.

Việc chuyển đổi giúp chuẩn hóa cấu trúc dữ liệu truyền tải và tạo cơ sở thống nhất cho các thành phần xử lý phía sau.

## 3. Thiết kế Data Contract

### 3.1. Mục đích

Data Contract xác định cấu trúc JSON event được sử dụng trong quá trình chuyển đổi dữ liệu từ CSV sang định dạng truyền tải.

File Data Contract hiện tại:

`producer/data_contract.json`

Schema sử dụng JSON Schema Draft 2020-12.

### 3.2. Cấu trúc event

Mỗi event có 12 trường:

| Trường | Kiểu dữ liệu | Cho phép null | Mục đích |
|---|---|---|---|
| `event_id` | String (UUID) | Không | Định danh duy nhất |
| `run_id` | String | Không | Định danh lần chạy |
| `original_event_time` | String (ISO 8601 UTC) | Không | Thời điểm sự kiện gốc |
| `stream_event_time` | String (ISO 8601 UTC) | Không | Thời điểm chuẩn bị phát event |
| `event_type` | String | Không | Loại sự kiện |
| `product_id` | Integer | Không | Mã sản phẩm |
| `category_id` | Integer | Không | Mã danh mục |
| `category_code` | String | Có | Mã phân cấp danh mục |
| `brand` | String | Có | Thương hiệu |
| `price` | Number | Không | Giá sản phẩm |
| `user_id` | Integer | Không | Mã người dùng |
| `user_session` | String | Có | Mã phiên tương tác |

Các quy tắc chính:

- `event_id` được tạo dưới dạng UUID.
- `run_id` không được để trống.
- Hai trường thời gian sử dụng ISO 8601 UTC và kết thúc bằng `Z`.
- `event_type` chỉ nhận một trong ba giá trị `view`, `cart`, `purchase`.
- `product_id`, `category_id` và `user_id` phải là số nguyên không âm.
- `price` phải là số không âm.
- `category_code`, `brand` và `user_session` có thể nhận giá trị `null`.
- Không cho phép các trường ngoài Data Contract.

### 3.3. Quy tắc thời gian và định danh

`original_event_time` lưu lại thời điểm phát sinh sự kiện trong dataset gốc.

`stream_event_time` ghi nhận thời điểm Producer chuẩn bị sự kiện để truyền tải.

Việc duy trì hai trường thời gian giúp phân biệt dữ liệu lịch sử với thời điểm phát dữ liệu trong quá trình mô phỏng.

`event_id` được tạo bằng UUID phiên bản 5 dựa trên `run_id`, tên file nguồn và chỉ số dòng dữ liệu.

`run_id` được sử dụng để phân biệt các lần chạy Producer và hỗ trợ kiểm tra, đối chiếu dữ liệu.

## 4. Thiết kế Python Producer

### 4.1. Vai trò và kiến trúc

Python Producer chịu trách nhiệm đọc dữ liệu lịch sử, chuyển đổi thành JSON event và gửi lên Azure Event Hubs.

Kiến trúc xử lý:

```text
2019-Oct.csv
     |
     v
prepare_data.py
     |
     v
manifest.json
     |
     v
producer.py
     |
     +-- Đọc CSV theo chunk
     |
     +-- Kiểm tra event_type
     |
     +-- Chuyển đổi JSON
     |
     +-- Rate limiting
     |
     +-- Batch processing
     |
     +-- Retry khi gửi lỗi tạm thời
     |
     +-- Checkpoint sau batch thành công
     |
     v
Azure Event Hubs
```

Producer sử dụng Python, Pandas và thư viện `azure-eventhub`.

Các dependencies được khai báo trong `requirements.txt`:

- `pandas==2.3.3`
- `azure-eventhub==5.15.1`

### 4.2. Phân vùng dữ liệu bằng prepare_data.py

File `producer/prepare_data.py` có nhiệm vụ khảo sát tổng số dòng và tạo manifest phân vùng dữ liệu.

Chương trình đọc CSV theo chunk để đếm số bản ghi, sau đó chia dữ liệu thành hai phân vùng dựa trên tỷ lệ cấu hình.

Manifest hiện tại:

`producer/manifest.json`

Kết quả phân vùng:

| Phân vùng | Vị trí bắt đầu | Vị trí kết thúc | Số dòng |
|---|---:|---:|---:|
| dev | 0 | 21.224.382 | 21.224.382 |
| demo | 21.224.382 | 42.448.764 | 21.224.382 |
| Tổng |  |  | 42.448.764 |

Việc đánh chỉ số sử dụng quy ước bắt đầu từ 0 và khoảng dữ liệu có dạng `[start, end)`.

Manifest lưu tên file nguồn, tổng số dòng, tỷ lệ phân vùng, thời điểm tạo và thông tin các khoảng dữ liệu.

Chương trình không tạo hai file CSV vật lý riêng. Producer sử dụng các khoảng dòng trong manifest để xác định phần dữ liệu cần đọc và xử lý.

Kích thước chunk mặc định của `prepare_data.py` là 100.000 dòng.

### 4.3. Đọc CSV theo chunk

Producer sử dụng Pandas `read_csv()` với tham số `chunksize`.

Cấu hình mặc định trong `producer.py`:

`DEFAULT_CHUNK_SIZE = 10_000`

Các trường dữ liệu được chỉ định kiểu dữ liệu khi đọc:

- `event_time`: string.
- `event_type`: string.
- `product_id`: Int64.
- `category_id`: Int64.
- `category_code`: string.
- `brand`: string.
- `price`: float64.
- `user_id`: Int64.
- `user_session`: string.

Producer chỉ đọc các cột cần thiết, xử lý lần lượt từng chunk và sử dụng chỉ số dòng toàn cục để xác định vị trí bản ghi trong manifest.

Cách thực hiện này giúp hạn chế bộ nhớ sử dụng và tránh phải nạp toàn bộ CSV vào RAM.

Việc đọc bằng thư viện xử lý CSV giúp duy trì ranh giới bản ghi, không chia dữ liệu tùy tiện theo số byte làm cắt giữa dòng.

### 4.4. Batch processing

Producer nhóm nhiều event thành một batch trước khi gửi lên Event Hubs.

Cấu hình mặc định:

`DEFAULT_BATCH_SIZE = 50`

Batch processing giúp giảm số lần gọi gửi riêng lẻ và tận dụng khả năng gửi nhiều event trong cùng một lần truyền.

Trong quá trình xử lý, Producer tạo batch bằng `create_batch()` và thêm event bằng `batch.add()`.

Nếu batch không thể tiếp nhận thêm event, chương trình gửi batch hiện tại rồi tạo batch mới.

Kích thước batch được cấu hình thông qua tham số `--batch-size`.

### 4.5. Rate limiting

Rate limiting được sử dụng để giới hạn tốc độ gửi event theo số lượng event mỗi giây.

Producer triển khai lớp `RateLimiter` dựa trên `time.monotonic()` và khoảng thời gian giữa các event.

Cấu hình thông qua tham số:

`--rate`

Giá trị mặc định:

`DEFAULT_RATE = 100.0`

Các mức tải sử dụng trong benchmark:

- 100 events/second.
- 500 events/second.
- 1.000 events/second.
- 2.000 events/second.

Đây là tốc độ mục tiêu cấu hình, không phải throughput thực tế.

Throughput thực tế còn phụ thuộc vào tốc độ xử lý dữ liệu, chuyển đổi JSON, batching, kết nối mạng và khả năng gửi lên Event Hubs.

### 4.6. Retry mechanism

Producer triển khai retry nhằm xử lý các lỗi tạm thời khi gửi batch.

Chương trình phân biệt lỗi có thể thử lại và lỗi không thể thử lại.

Cấu hình mặc định:

| Tham số | Giá trị |
|---|---:|
| Số lần retry tối đa | 5 |
| Backoff ban đầu | 1 giây |
| Backoff tối đa | 30 giây |
| Chiến lược chờ | Exponential backoff kết hợp random jitter |

Khi gặp lỗi tạm thời, thời gian chờ được tăng theo số lần retry và không vượt quá giới hạn cấu hình.

Nếu vượt quá số lần retry hoặc gặp lỗi không thuộc nhóm lỗi tạm thời, batch được ghi nhận thất bại.

Cơ chế này giúp hạn chế việc mất dữ liệu do những lỗi kết nối tạm thời.

### 4.7. Checkpoint và Resume

Checkpoint lưu lại vị trí bản ghi đã được xác nhận gửi thành công.

File checkpoint có định dạng JSON và lưu các thông tin:

- `checkpoint_version`.
- `source_file`.
- `mode`.
- `run_id`.
- `partition_start`.
- `partition_end`.
- `next_row`.
- `last_confirmed_row`.
- `updated_at`.

Checkpoint được cập nhật sau khi batch gửi thành công.

Để hạn chế rủi ro ghi checkpoint không hoàn chỉnh, Producer ghi dữ liệu vào file tạm trước rồi sử dụng `os.replace()` để thay thế file checkpoint chính.

Khi chương trình được chạy với `--resume`, Producer kiểm tra checkpoint hiện tại và xác định vị trí tiếp tục.

Nếu batch gửi thất bại, checkpoint không được tiến lên.

Cần lưu ý rằng việc gửi batch và cập nhật checkpoint không phải một giao dịch nguyên tử. Nếu Event Hubs đã nhận batch nhưng chương trình bị gián đoạn trước khi checkpoint được ghi, batch đó có thể được gửi lại khi resume.

Vì vậy, cơ chế này hỗ trợ khôi phục quá trình gửi nhưng không tự đảm bảo exactly-once delivery.

### 4.8. Logging và bảo mật

Producer sử dụng Python logging để ghi nhận quá trình thực thi.

Thông tin được ghi nhận gồm:

- `run_id`.
- File CSV đầu vào.
- Phân vùng dữ liệu đang xử lý.
- Số lượng event đã chuẩn bị.
- Số event gửi thành công.
- Số event gửi thất bại.
- Số lần retry.
- Thời gian thực thi.
- Trạng thái checkpoint.

Log được ghi ra màn hình và file trong thư mục `logs/`.

Thông tin kết nối Event Hubs được lấy thông qua hai biến môi trường:

- `EVENTHUB_CONNECTION_STR`.
- `EVENTHUB_NAME`.

Trong Kaggle Notebook, các giá trị này được lấy từ Kaggle Secrets.

Không lưu connection string hoặc SAS key trực tiếp trong mã nguồn hay repository.

## 5. Benchmark hiệu năng Producer

### 5.1. Mục tiêu

Benchmark nhằm đánh giá hiệu năng của Python Producer khi gửi dữ liệu hành vi thương mại điện tử từ CSV lên Azure Event Hubs.

Các chỉ tiêu đánh giá:

- Số event gửi thành công.
- Số event gửi thất bại.
- Số lần retry.
- Thời gian thực thi.
- Throughput thực tế.
- Payload throughput.
- Trạng thái tiến trình và số lượng event trong JSONL.

Benchmark chỉ đo phía Producer và quá trình gửi tới Event Hubs, không đo hiệu năng của Stream Analytics, Azure SQL hoặc Power BI.

### 5.2. Môi trường thực nghiệm

Theo `producer_metrics.csv` và `benchmark_producer.md`:

| Thuộc tính | Giá trị |
|---|---|
| Ngày benchmark | 14/11/2026 |
| Runtime | Kaggle Notebook |
| CPU | 4 |
| RAM | 31,35 GiB |
| Python | 3.13.18 |
| Hệ điều hành | Linux 6.18.55+ x86_64, glibc 2.39 |
| Event Hubs Region | Southeast Asia |
| Batch size | 50 events |
| CSV chunk size | 10.000 rows |
| Số event tối đa mỗi lần chạy | 10.000 |
| Số lần lặp mỗi mức tải | 3 |
| Tổng số mức tải | 4 |

### 5.3. Phương pháp đo

Benchmark sử dụng file `producer/benchmark_producer.py`.

Chương trình gọi `producer.py` bằng subprocess để sử dụng lại toàn bộ logic đọc CSV, chuyển đổi event, batching, rate limiting, retry và checkpoint.

Bốn mức tải được kiểm thử:

| Lần thử | Target rate |
|---|---:|
| Test 1 | 100 events/s |
| Test 2 | 500 events/s |
| Test 3 | 1.000 events/s |
| Test 4 | 2.000 events/s |

Mỗi mức tải được thực hiện ba lần, tổng cộng 12 lần chạy.

Các công thức tính:

**Throughput thực tế:**

`actual_events_per_sec = events_sent / duration_seconds`

**Payload throughput:**

`payload_MB_per_sec = payload_bytes / 1.000.000 / duration_seconds`

Trong đó:

- `events_sent`: số event được xác nhận gửi thành công.
- `duration_seconds`: thời gian thực thi Producer.
- `payload_bytes`: tổng số byte của các JSON payload UTF-8.
- `payload_MB_per_sec`: tốc độ truyền tải payload theo MB/s.

Kết quả được ghi vào `producer/producer_metrics.csv`.

Ngoài ra, mỗi lần chạy có log, JSONL và checkpoint riêng để hỗ trợ kiểm tra kết quả.

### 5.4. Kết quả benchmark tổng quan

Theo dữ liệu thực tế trong `producer_metrics.csv`:

| Chỉ tiêu | Kết quả |
|---|---:|
| Số mức tải | 4 |
| Số lần chạy mỗi mức | 3 |
| Tổng số lần chạy | 12 |
| Tổng event gửi thành công | 120.000 |
| Tổng event lỗi | 0 |
| Tổng số lần retry | 0 |
| Số lần chạy hoàn tất | 12/12 |
| Process return code | 0 ở cả 12 lần |
| JSONL event count | 10.000 mỗi lần |
| Payload mỗi lần chạy | 4.044.364 bytes |

Cả 12 lần chạy đều có trạng thái `completed`.

Số event được ghi trong JSONL khớp với số event gửi thành công ở tất cả các lần chạy.

### 5.5. Kết quả theo từng mức tải

Các giá trị throughput và duration dưới đây là trung bình số học của ba lần chạy tại mỗi mức tải. Số event gửi thành công, event lỗi và retry là tổng của ba lần chạy.

| Target rate (events/s) | Số lần chạy | Events sent | Errors | Retries | Avg duration (s) | Avg throughput (events/s) | Avg payload (MB/s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 3 | 30.000 | 0 | 0 | 149,28 | 66,99 | 0,0271 |
| 500 | 3 | 30.000 | 0 | 0 | 47,99 | 208,39 | 0,0843 |
| 1.000 | 3 | 30.000 | 0 | 0 | 40,27 | 248,35 | 0,1004 |
| 2.000 | 3 | 30.000 | 0 | 0 | 39,90 | 250,61 | 0,1014 |

### 5.6. Nhận xét kết quả

**Thứ nhất, về khả năng gửi dữ liệu:**

Cả 12 lần chạy đều hoàn tất thành công. Mỗi lần gửi đủ 10.000 event, không ghi nhận event lỗi hoặc retry.

Tổng số event gửi thành công là 120.000. Số lượng event trong JSONL khớp với số lượng event gửi thành công.

**Thứ hai, về throughput:**

Khi tăng target rate từ 100 lên 500 events/s, throughput thực tế trung bình tăng từ 66,99 lên 208,39 events/s.

Khi tăng target rate từ 500 lên 1.000 events/s, throughput tiếp tục tăng lên 248,35 events/s.

Tuy nhiên, khi tăng target rate từ 1.000 lên 2.000 events/s, throughput chỉ tăng nhẹ từ 248,35 lên 250,61 events/s.

Kết quả cho thấy throughput của Producer trong cấu hình thử nghiệm có dấu hiệu bão hòa quanh mức 250 events/s.

**Thứ ba, về payload throughput:**

Payload throughput tăng từ 0,0271 MB/s ở mức tải 100 events/s lên 0,1014 MB/s ở mức tải 2.000 events/s.

Điều này phản ánh tốc độ truyền tải payload tăng khi tăng mức tải cấu hình, nhưng mức tăng cũng có xu hướng chậm lại ở hai mức tải cao.

**Thứ tư, về độ ổn định:**

Trong phạm vi 12 lần chạy, không ghi nhận event lỗi hoặc retry. Các tiến trình đều kết thúc với return code bằng 0.

Tuy nhiên, kết quả này chỉ phản ánh cấu hình và điều kiện thử nghiệm tại thời điểm benchmark, không chứng minh Producer không thể gặp lỗi trong những điều kiện tải khác.

### 5.7. Giới hạn benchmark

Benchmark có một số giới hạn cần được xem xét:

- Kết quả phụ thuộc vào tài nguyên Kaggle, network và cấu hình Event Hubs tại thời điểm thực nghiệm.
- Thời gian đo bao gồm đọc CSV, chuyển đổi dữ liệu, rate limiting, batching, gửi Event Hubs và cập nhật checkpoint.
- `payload_MB_per_sec` chỉ phản ánh tốc độ payload JSON ở phía Producer, không phải network wire throughput.
- Target rate là tốc độ giới hạn cấu hình, không phải throughput thực tế được đảm bảo.
- Benchmark không đo hiệu năng Stream Analytics, Azure SQL và Power BI.
- Không thể xác định chính xác bottleneck chỉ từ kết quả throughput tổng thể. Cần profiling riêng từng công đoạn nếu muốn xác định nguyên nhân giới hạn hiệu năng.
- Trong lần benchmark này, nhóm đã dừng Stream Analytics trước khi thử nghiệm. Do đó, kết quả không phản ánh khả năng xử lý end-to-end của toàn bộ pipeline.

## 6. Kết luận

Tập dữ liệu `2019-Oct.csv` có dung lượng 5,6686 GB và 42.448.764 bản ghi, phù hợp để sử dụng làm nguồn dữ liệu lịch sử cho bài toán mô phỏng xử lý luồng trong đồ án.

Qua khảo sát, dữ liệu thực tế chứa ba loại sự kiện là `view`, `cart` và `purchase`. Trường `remove_from_cart` không xuất hiện trong CSV nguồn nên không thuộc phạm vi hỗ trợ của Producer hiện tại.

Python Producer được triển khai với phương pháp đọc CSV theo chunk, chuyển đổi dữ liệu sang JSON, gửi theo batch và kiểm soát tốc độ bằng rate limiting. Các cơ chế retry, checkpoint và logging được sử dụng để hỗ trợ xử lý lỗi, theo dõi tiến trình và tiếp tục quá trình gửi sau khi bị gián đoạn.

Kết quả benchmark ngày 14/11/2026 cho thấy cả 12 lần chạy đều hoàn tất thành công, tổng cộng gửi 120.000 event, không ghi nhận event lỗi hoặc retry.

Throughput thực tế trung bình lần lượt đạt 66,99; 208,39; 248,35 và 250,61 events/s tương ứng với các mức target rate 100; 500; 1.000 và 2.000 events/s.

Trong cấu hình thử nghiệm, throughput có dấu hiệu bão hòa quanh 250 events/s khi tăng target rate lên mức cao hơn. Đây là kết quả đo end-to-end phía Producer trong môi trường Kaggle, không phải giới hạn throughput độc lập của Azure Event Hubs.

Nhìn chung, Python Producer đáp ứng được vai trò phát dữ liệu lịch sử lên Azure Event Hubs và cung cấp các số liệu thực nghiệm để đánh giá khả năng truyền tải dữ liệu trong phạm vi đồ án.

## 7. Tài liệu tham khảo

1. Kaggle, *eCommerce behavior data from multi-category store*: https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store
2. Python Documentation, *CSV File Reading and Writing*: https://docs.python.org/3/library/csv.html
3. Python Documentation, *JSON encoder and decoder*: https://docs.python.org/3/library/json.html
4. Microsoft Learn, *Send events to Azure Event Hubs using Python*: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-python-get-started-send
5. Microsoft Learn, *Azure Event Hubs documentation*: https://learn.microsoft.com/en-us/azure/event-hubs/

## 8. Các file minh chứng trong repository

| File | Nội dung |
|---|---|
| `producer/data_profile.json` | Kết quả khảo sát dataset |
| `producer/prepare_data.py` | Chương trình tạo manifest phân vùng |
| `producer/manifest.json` | Thông tin phân vùng dev/demo |
| `producer/producer.py` | Mã nguồn Python Producer |
| `producer/data_contract.json` | JSON Schema |
| `docs/data_contract.md` | Mô tả Data Contract |
| `producer/benchmark_producer.py` | Chương trình benchmark |
| `producer/producer_metrics.csv` | Số liệu benchmark thực tế |
| `producer/benchmark_producer.md` | Phương pháp và kết quả benchmark |
| `requirements.txt` | Dependencies |