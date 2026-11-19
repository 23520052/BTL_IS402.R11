# Checklist kiểm thử Power BI

Cập nhật 19/11/2026. Run kiểm: `integration-261117`, toàn thời gian, không lọc brand/event trừ khi nêu khác. PASS ghi theo phạm vi được kiểm; PENDING là mục chưa đủ bằng chứng.

| ID | Tiêu chí | Kết quả và phạm vi |
|---|---|---|
| S201 | Mở dự án DirectQuery | PASS Desktop và Service, bốn trang và KPI hiển thị |
| S202 | KPI | PASS 8 truy vấn DAX: 10.000 event, 9.785 view, 97 cart, 118 purchase, remove=0, value 35.757,22 |
| S203 | Hai fact | PASS DAX, purchase count/value khớp, sai số ≤0,01 |
| S204 | RLS Manager | PASS engine, Desktop View as và Service Test as role; nhiều brand, 118 purchase |
| S205 | RLS Analyst | PASS engine, Desktop View as và Service Test as role; chỉ Apple, 25 purchase và value 19.415,91 |
| S206 | Chặn aggregate không có brand | PASS, Analyst không đọc raw event hoặc tổng event |
| S207 | Thử vượt RLS | PASS, REMOVEFILTERS không làm lộ Samsung hoặc event |
| S208 | Mobile bốn trang | PASS schema/bounds, 44 visual mobile, không chồng lấn; kiểm preview Desktop |
| S209 | Navigation/sync run | PASS chuyển tab Desktop và Page Navigator Service, đủ bốn trang và cùng run; PENDING Ctrl+click Page Navigator trong Desktop |
| S210 | APR | PASS cấu hình 30 giây và Window Age tự tăng sau 32,9 giây không thao tác; PENDING live E2E với run mới |
| S211 | PBIX cuối | PASS đóng/mở lại Desktop, 4 trang/44 mobile khớp source, 8 DAX và 6 RLS đạt trên engine PBIX |
| S212 | Service/thiết bị thật | Đã publish và kiểm Test as role; hai role có 0 thành viên. PENDING tài khoản Viewer riêng và điện thoại vật lý |
| S213 | Quyền SQL | PENDING kiểm lại SELECT=1 và INSERT/UPDATE/DELETE=0 trên cả hai fact bằng tài khoản BI |
| S214 | Slicer view | PASS UI: Total=9.785, Purchase=118, trend chỉ có view; khớp DAX |
| S215 | Không có dữ liệu | PASS DAX với run không tồn tại: count/value=0, ratio/last window=BLANK; PENDING khoảng thời gian rỗng trên UI |

Bằng chứng: [Desktop ngày 18/11](evidence/sprint2/README.md), [Service ngày 19/11](evidence/service_validation.json), [cấu trúc PBIP](evidence/project_validation.json). Hướng dẫn chạy lại tại [QA](qa/README.md), [RLS/mobile](rls_mobile.md) và [quy trình E2E](e2e_test_guide.md).
