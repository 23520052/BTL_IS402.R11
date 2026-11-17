# Thiết kế dashboard Power BI — Sprint 1

## Dữ liệu và mô hình

Server: `sqlsrv-sales-gr03-tram01.database.windows.net`; database: `salesdb`; user: `pbi_reader`.
Mật khẩu nhập riêng trong Desktop; không đặt trong source, PBIP, M hay tài liệu.

| Bảng | Grain | Sử dụng |
|---|---|---|
| `event_metrics_30s` | run, window_end UTC 30s, event_type | Overview, Monitoring, Behavior |
| `brand_sales_1m` | run, window_end UTC 1m, brand | Brand Performance |
| `DimRun` | run_id duy nhất từ fact event | Lọc một chiều tới cả hai fact; slicer sync giữa 4 trang |
| `DimEvent` | event_type duy nhất từ fact event | Lọc một chiều tới fact event |

Tất cả partition dùng **DirectQuery** qua `Sql.Database`. Hai fact liên kết qua dimension, giữ riêng grain 30 giây và 1 phút. DimRun lấy từ fact event nên run chỉ có ở fact brand sẽ chưa xuất hiện trong slicer.

## Wireframe và nội dung 4 trang

Canvas 1280 × 800. Mỗi trang: tiêu đề → Page Navigator → run/time slicer → KPI → biểu đồ → nhãn Data Scope → chú thích nguồn.

| Trang | KPI | Visual chính | Bộ lọc |
|---|---|---|---|
| Sales Overview | Purchase Events, Purchase Value, View Events, Purchase/View | Line purchase value theo 30s; column event mix | Run chung; window_end của fact event |
| Real-time Monitoring | Total Events, Purchase Events, Last Window UTC, Window Age Seconds | Line event count theo 30s và event_type; chú thích refresh | Run chung; thời gian fact event; event type |
| Brand Performance | Brand Purchase Value, Brand Purchase Events | Bar brand ranking; bảng count/value/share | Run chung; thời gian fact brand; brand |
| Customer Behavior | View, Cart, Remove, Purchase Events | Column event counts; line Cart/View và Purchase/View | Run chung; thời gian fact event |

Navigation: Page Navigator có đủ 4 trang. Trong chế độ chỉnh sửa Desktop dùng **Ctrl+click** để theo nút; tab dưới cùng chuyển trực tiếp. Run slicer đồng bộ; time slicer độc lập vì grain khác nhau. Brand slicer chỉ ảnh hưởng trang Brand.

## Quy tắc KPI

- Count là `SUM(event_count)`, không phải số dòng aggregate, số đơn hay unique users.
- Value chỉ cộng revenue của purchase; giữ đơn vị gốc, không tự gắn VND/USD.
- Purchase/View và Cart/View là tỷ lệ số event. Mẫu số 0 → BLANK.
- KPI theo loại event bỏ slicer DimEvent; Total Events và trend vẫn nhận slicer.
- Brand share là share trong các brand được chọn (`ALLSELECTED`). Sắp xếp value giảm dần để xem top brand; không cộng value brand vào value fact event.
- `Window Age Seconds` = thời gian hiện tại UTC trừ cửa sổ cuối đang chọn. Đây là độ cũ dữ liệu, không phải đo latency từ producer đến màn hình.
- Chỉ chọn một run. `mock-seed` hiển thị nhãn MOCK. Không mặc định xem tổng nhiều run là kết quả tích hợp.
- Nguồn gốc CSV không có remove_from_cart; measure Remove Events = 0 ở run thật không có loại này. Mock có thể có 4 loại.

## Refresh và giới hạn

Overview và Monitoring cấu hình APR 30 giây, đã kiểm trong UI và lưu dưới dạng `APR`/`PT30S`. Độ trễ quan sát gồm cửa sổ ASA, xử lý/ghi SQL và truy vấn/render Power BI; chu kỳ refresh không đại diện cho độ trễ toàn luồng. Trạng thái nghiệm thu nằm trong [checklist](dashboard_test_cases.md).

Tài liệu Microsoft: [PBIP report definition](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report), [semantic model TMSL](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset), [Automatic Page Refresh](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-automatic-page-refresh).

RLS, mobile và publish Power BI Service nằm ngoài phạm vi triển khai Sprint 1.

Trend giữ BLANK ở cửa sổ không có dữ liệu của run đang chọn để không vẽ thêm các điểm 0 thuộc run khác.
