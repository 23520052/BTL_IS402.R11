# Kết quả kiểm thử ngày 18/11/2026

Dữ liệu kiểm: run đã hoàn tất `integration-261117`. Timestamp trong JSON là UTC. PBIX được kiểm lại sau cập nhật mobile tối 18/11; ảnh desktop và quan sát APR giữ thời điểm kiểm ban đầu.

| File | Nội dung | Kết quả |
|---|---|---|
| `baseline/model_validation.json` | DirectQuery trước khi bổ sung RLS/mobile | PASS |
| `final-model/model_validation.json` | Model trước xuất PBIX | PASS |
| `reopened-pbix/model_validation.json` | Model của PBIX bàn giao sau đóng/mở lại | PASS, 8 truy vấn DAX |
| `rls_validation.json` | RLS của PBIX mở lại, kết nối theo từng role | PASS, 6 kiểm tra |
| `artifact_validation.json` | ZIP/DataModel, 4 trang, 44 mobile, APR và đối chiếu định nghĩa trang/visual với source | PASS, kèm SHA256 |
| [project_validation.json](../project_validation.json) | Schema/binding/model/RLS/mobile | PASS 103/103 file; visual 2.14.0 dùng schema tương thích 2.13.0 |
| `screenshots/rls_*` | Desktop View as Manager và Brand Analyst | Manager đọc mọi brand; Analyst chỉ Apple và bị chặn event |
| `screenshots/mobile_*` | Preview mobile bốn trang | Canvas 324px, cuộn dọc trong Desktop |
| `screenshots/desktop_*` | Bốn trang DirectQuery tại lần kiểm ban đầu | Cùng run `integration-261117` |
| `apr_observation.json` | Monitoring không thao tác/Refresh trong 32,9 giây | Window Age tăng 35.007 → 35.037; count/window giữ nguyên |
| `ui_review.json` | Phạm vi kiểm tra UI và cập nhật mobile | Ghi rõ các mục chưa kiểm |

KPI: 10.000 event; 9.785 view; 97 cart; 118 purchase; remove=0; value 35.757,22; Purchase/View ≈1,21%. Hai fact khớp purchase count/value. Analyst có Apple: 25 purchase, value 19.415,91. Event=0 dưới role này là kết quả chặn quyền vì bảng không có brand.

APR được quan sát qua Window Age tăng sau chu kỳ 30 giây; run đã hoàn tất nên phép thử chưa chứng minh event mới đi qua pipeline.

Báo cáo đã publish lên Power BI Service. Các kết quả engine/UI ở trên ghi nhận lần kiểm trong Desktop; [kiểm Service ngày 19/11](../service_validation.json) xác nhận bốn trang và RLS bằng Test as role.

## Mục còn chờ kiểm

- Live E2E: phát run mới, quan sát count/window tự đổi và đối chiếu SQL trước–sau theo [hướng dẫn](../../e2e_test_guide.md).
- Quyền SQL: kiểm trực tiếp cả hai fact bằng tài khoản BI.
- Ctrl+click Page Navigator, khoảng thời gian rỗng trên UI, RLS bằng tài khoản Viewer trên Service và điện thoại vật lý.

Snapshot offline giữ riêng và không dùng để chứng minh RLS/mobile của bản chính. Khi chỉnh PBIP, mở lại và xuất PBIX; chạy lại QA để cập nhật bằng chứng và hash.
