# Kiểm thử toàn luồng — Producer → Azure → Power BI

Mục tiêu: kiểm tra tính đúng của dữ liệu qua toàn bộ pipeline và khả năng tự cập nhật của Power BI Desktop. Đây là quy trình thực hiện; kết quả đã lưu nằm trong [evidence/](evidence/README.md).

```text
CSV → Producer → Event Hubs → Stream Analytics
                               ├─ 30s/event → event_metrics_30s
                               └─ 1m/brand → brand_sales_1m
                            → Azure SQL → Power BI DirectQuery
```

## 1. Chuẩn bị

| Phụ trách | Công việc |
|---|---|
| TV1 | CSV/manifest, cấu hình Sender, chạy Producer, lưu log và JSONL |
| TV2 | Kiểm Event Hubs, input/output/query ASA và trạng thái job |
| TV3 | Kiểm dữ liệu SQL và đối chiếu JSONL |
| TV4 | Chọn run/filter, đối chiếu KPI, ghi bằng chứng Automatic Page Refresh (APR) |

Thống nhất một run mới, tối đa 50 ký tự; ví dụ `e2e-20261117-140000`. Thay nhất quán mã này trong lệnh Producer, SQL, Power BI và thư mục bằng chứng. Mỗi lần nghiệm thu dùng run riêng để tránh cộng dữ liệu từ lần trước.

Kết nối SQL theo [README](README.md), chạy [qa/e2e_observe.sql](qa/e2e_observe.sql) với `@RunId` mới. Trước khi phát, run phải có 0 dòng ở cả hai fact. Mở PBIX chính hoặc PBIP, kiểm DirectQuery, APR 30 giây trên Overview/Monitoring và bỏ bộ lọc thời gian cũ. Timestamp dữ liệu dùng UTC.

## 2. Kiểm tra Stream Analytics

1. Input trỏ đúng Event Hub/consumer group, định dạng JSON khớp payload Producer.
2. Hai output ghi vào `salesdb.dbo.event_metrics_30s` và `salesdb.dbo.brand_sales_1m`, dùng tài khoản có quyền ghi.
3. Query nhóm theo `run_id`, cửa sổ event 30 giây và brand 1 phút; value chỉ cộng purchase, brand thiếu chuẩn hóa thành `unknown`.
4. Xác nhận quy tắc timestamp. Bài replay dùng `stream_event_time`; thời gian gốc năm 2019 không đại diện cho thời điểm phát hiện tại. Nếu job dùng enqueue time hoặc quy tắc khác, ghi rõ khi đối chiếu cửa sổ.
5. Job cần ở trạng thái **Running trước khi Producer gửi**. Với job chưa chạy, chọn **Start → Now** rồi chờ Running; giữ job ổn định suốt bài test.

Lưu cấu hình input/output/query thực tế của job và che thông tin xác thực. Tham khảo Microsoft: [Start ASA job](https://learn.microsoft.com/en-us/azure/stream-analytics/start-job), [timestamp và watermark](https://learn.microsoft.com/en-us/azure/stream-analytics/stream-analytics-time-handling).

## 3. Phát 10.000 event

Ví dụ trên Kaggle Notebook, dùng partition `dev` và các tham số Producer hiện có. Sửa đường dẫn CSV/project theo môi trường; dependencies nằm trong `requirements.txt`. Nếu dùng partition `demo`, giữ manifest gốc và tính thêm thời gian đọc qua nửa đầu CSV.

```python
import os
import subprocess
import sys
from pathlib import Path
from kaggle_secrets import UserSecretsClient

RUN_ID = "e2e-20261117-140000"  # Mã mới, dùng thống nhất cho SQL và Power BI
PROJECT = Path("/kaggle/working/BTL_IS402.R11")
INPUT_CSV = Path("/kaggle/input/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store/2019-Oct.csv")
MANIFEST = PROJECT / "producer/manifest.json"
OUT_DIR = Path("/kaggle/working") / RUN_ID
OUT_DIR.mkdir(parents=True, exist_ok=False)

secrets = UserSecretsClient()
os.environ["EVENTHUB_CONNECTION_STR"] = secrets.get_secret("EVENTHUB_CONNECTION_STR")
os.environ["EVENTHUB_NAME"] = secrets.get_secret("EVENTHUB_NAME")

assert INPUT_CSV.is_file(), "Sửa INPUT_CSV thành đường dẫn có thật"
assert MANIFEST.is_file(), "Kiểm tra manifest của TV1"
assert (PROJECT / "producer/producer.py").is_file(), "Kiểm tra PROJECT"
```

Sau khi ASA và các màn hình quan sát sẵn sàng:

```python
command = [
    sys.executable, str(PROJECT / "producer/producer.py"),
    "--input", str(INPUT_CSV),
    "--manifest", str(MANIFEST),
    "--mode", "dev",
    "--run-id", RUN_ID,
    "--max-events", "10000",
    "--batch-size", "50",
    "--chunk-size", "10000",
    "--rate", "50",
    "--max-retries", "5",
    "--base-backoff", "1",
    "--max-backoff", "30",
    "--checkpoint", str(OUT_DIR / "checkpoint.json"),
    "--jsonl-output", str(OUT_DIR / "events.jsonl"),
]
subprocess.run(command, cwd=OUT_DIR, check=True)
```

Với 50 event/giây, thời gian phát tối thiểu khoảng 200 giây, chưa tính đọc CSV, gửi batch và retry. Kỳ vọng `Events sent: 10000`, `Events error: 0`. JSONL chứa payload của các batch gửi thành công và là đầu vào đối chiếu.

Nếu lần chạy lỗi hoặc retry có trạng thái gửi không rõ, giữ log để kiểm tra trùng. Resume có thể gửi lại batch đã tới hub nhưng chưa ghi checkpoint; bài nghiệm thu mới dùng run mới.

## 4. Quan sát dữ liệu và APR

| Chặng | Nội dung quan sát |
|---|---|
| Producer | Events sent tăng, log gửi batch |
| Event Hubs | Incoming Messages/Bytes trong khoảng chạy |
| ASA | Input/Output Events, Runtime/Conversion errors, backlog và Watermark Delay |
| SQL | Chạy lại SQL quan sát sau 30–60 giây; count và window_end thay đổi |
| Power BI | Chọn run mới, giữ Monitoring active và ghi KPI/window trước–sau |

Metrics Portal có thể cập nhật trễ và chứa traffic từ run khác. Trong SQL, số event là `SUM(event_count)`; `COUNT(*)` là số dòng tổng hợp. [Microsoft: kiểm tra ASA output](https://learn.microsoft.com/en-us/azure/stream-analytics/stream-analytics-troubleshoot-output).

Để ghi nhận tự cập nhật:

1. Khi run xuất hiện trong SQL, Refresh danh sách nếu cần, chọn đúng run rồi bỏ bộ lọc phụ.
2. Giữ Monitoring active với APR 30 giây. Ghi UTC, Total Events, Purchase Events và Last Window UTC tại t0.
3. Trong đoạn ghi bằng chứng, giữ nguyên trang/slicer và không bấm Refresh. Chụp hoặc quay ít nhất hai trạng thái KPI/window tự thay đổi khi Producer còn gửi.
4. Đối chiếu SQL cùng giai đoạn. Tổng có thể khác giữa hai thời điểm chụp khi dữ liệu vẫn đang đến.

APR 30 giây là chu kỳ truy vấn. Độ trễ quan sát còn phụ thuộc cửa sổ ASA, watermark, SQL và thời gian render; Window Age là độ cũ cửa sổ, không phải latency từng event. [Microsoft: Automatic Page Refresh](https://learn.microsoft.com/power-bi/create-reports/desktop-automatic-page-refresh).

## 5. Đối chiếu sau khi phát xong

Giữ ASA chạy đến khi output ổn định; quan sát watermark/backlog và cửa sổ cuối trước khi chốt tổng. Bỏ time/brand/event filters khi đối chiếu toàn run.

| Tiêu chí | Kỳ vọng |
|---|---|
| Tổng event và phân bố event_type | SQL khớp JSONL; bài này là 10.000 event |
| Purchase count/value | JSONL = fact event = fact brand; sai số value ≤ 0,01 |
| Khóa grain trùng, giá trị âm, brand chưa chuẩn hóa | 0 |
| KPI và tỷ lệ trên Power BI | Khớp SQL cùng run/phạm vi |

KPI của run mới lấy từ JSONL mới; 118 purchase và value 35.757,22 chỉ là mốc của run lịch sử `integration-261113`.

TV3 đối chiếu bằng script hiện có, với dependencies/driver SQL và `SQL_AZURE_CONN` được cấu hình riêng:

```powershell
python database/validate_against_sample.py --events "powerbi/evidence/e2e-20261117-140000/events.jsonl" --run-id "e2e-20261117-140000" --out "powerbi/evidence/e2e-20261117-140000/sample_vs_sql.txt"
```

Chạy kết nối DB thật để nghiệm thu. Tùy chọn `--windows` kiểm count theo cửa sổ khi timestamp, brand và quy ước ranh giới khớp ASA; chưa thay thế kiểm revenue từng cửa sổ.

TV4 chạy thêm QA SQL/DAX theo [hướng dẫn kỹ thuật](qa/README.md), truyền run và thư mục kết quả:

```powershell
& ./powerbi/qa/validate_sql.ps1 -RunId 'e2e-20261117-140000' -OutputDirectory './powerbi/evidence/e2e-20261117-140000'
& ./powerbi/qa/validate_model.ps1 -Port <port_model_dang_mo> -RunId 'e2e-20261117-140000' -OutputDirectory './powerbi/evidence/e2e-20261117-140000'
```

Thay `<port_model_dang_mo>` bằng port thật của đúng model Desktop. Hoàn thành các thao tác navigation, slicer, trường hợp dữ liệu rỗng và đóng/mở lại PBIX theo [checklist](dashboard_test_cases.md).

## 6. Bằng chứng và tiêu chí đạt

Lưu trong `powerbi/evidence/<RUN_ID>/`: log Producer, JSONL, cấu hình/metrics Azure, SQL trước–trong–sau, kết quả đối chiếu, ảnh/video APR, ảnh bốn trang và biên bản kết quả. Biên bản ghi run, mốc UTC, cấu hình timestamp, số gửi/lỗi/retry và trạng thái từng tiêu chí.

E2E đạt khi dữ liệu mới đi hết pipeline, SQL khớp JSONL, Power BI khớp SQL và có bằng chứng tự cập nhật. Nếu mới đối chiếu số liệu, ghi rõ APR còn chờ nghiệm thu.

## 7. Khoanh vùng lỗi

| Hiện tượng | Kiểm tra |
|---|---|
| Producer không gửi | Secrets, quyền Sender, hub, CSV/manifest và log |
| Hub có dữ liệu nhưng ASA không đọc | Input, consumer group, job, start time và timestamp |
| ASA đọc nhưng SQL chưa có run | Output errors, quyền ghi, mapping và watermark |
| SQL có event nhưng thiếu brand | Purchase, cửa sổ 1 phút và output brand |
| SQL đúng nhưng report cũ | File DirectQuery, run/filter và APR trang active |
| SQL lỗi 40615 | Client IP trong lỗi và firewall |
| Cannot load model | Kết nối SQL và nội dung See details của Desktop |
| Tổng lớn hơn JSONL hoặc lệch cuối run | Replay/retry, grain trùng, watermark và cửa sổ cuối |

Giữ nguyên dữ liệu và cấu hình dùng chung trong khi kiểm tra để bảo toàn kết quả đối chiếu.
