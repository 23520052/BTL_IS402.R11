# Kết quả kiểm thử Power BI

## Kết quả mới nhất

[Kết quả ngày 18/11/2026](sprint2/README.md) xác nhận DirectQuery trên run `integration-261117`, KPI hai fact khớp, RLS đạt bằng engine và View as, mobile có đủ bốn trang. PBIX đã đóng/mở lại và kiểm DAX/RLS. [Kiểm cấu trúc PBIP](project_validation.json) đạt 103/103 file với ánh xạ schema tương thích được ghi trong kết quả.

[Kiểm Service ngày 19/11](service_validation.json): bốn trang và KPI khớp, Page Navigator giữ run, Test as role đạt với Manager và Brand Analyst. Hai role hiện có 0 thành viên. Các mục còn chờ: live E2E, kiểm lại quyền SQL trên cả hai fact, tài khoản Viewer riêng và điện thoại vật lý. Trạng thái từng tiêu chí tại [checklist](../dashboard_test_cases.md).

## Bằng chứng trước đó

| Bằng chứng | Phạm vi |
|---|---|
| [Kiểm artifact ngày 17/11](artifact_validation.json) | Cấu trúc ZIP/DataModel, bốn trang và SHA256 của phiên bản tại thời điểm kiểm |
| [SQL và DAX ngày 17/11](hotspot_recheck_20261117_103543/README.md) | 11 truy vấn SQL và 8 truy vấn DAX trên run `integration-261113` |
| [Snapshot DAX](snapshot/model_validation.json) | Offline: 10.000 event, 118 purchase, value 35.757,22 |
| [Ảnh snapshot](../screenshots/) | Bốn trang của bản offline |

Bằng chứng lịch sử giữ nguyên phiên bản và thời điểm kiểm; hash của PBIX bàn giao nằm trong [artifact_validation.json mới](sprint2/artifact_validation.json).
