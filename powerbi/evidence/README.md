# Kết quả kiểm thử Power BI — 17/11/2026

| Bằng chứng | Kết quả và phạm vi |
|---|---|
| [artifact_validation.json](artifact_validation.json) | Hai PBIX có ZIP hợp lệ, DataModel và bốn trang; ghi SHA256 và cấu hình APR của bản chính |
| [project_validation.json](project_validation.json) | Binding/mô hình không ghi nhận lỗi; schema kiểm được 33/59 file, còn thiếu schema công khai 2.14.0 (HTTP 404) |
| [SQL và DAX ngày 17/11](hotspot_recheck_20261117_103543/README.md) | 11 truy vấn SQL và 8 truy vấn DAX thành công trên run lịch sử `integration-261113` |
| [Snapshot DAX](snapshot/model_validation.json) | Offline: 10.000 event, 118 purchase, value 35.757,22 |
| [Ảnh dashboard](../screenshots/) | Bốn trang của bản snapshot |

## Giới hạn kiểm chứng

Lần SQL/DAX thành công diễn ra lúc 10:35–10:36. Kết nối mới lúc 13:49–13:52 bị firewall từ chối (40615), đồng thời Desktop báo `Cannot load model`; chưa xác định lỗi chi tiết của Desktop. Bản lưu mới nhất chưa được kiểm mở lại đầy đủ qua UI với SQL ổn định.

Bằng chứng hiện tại xác nhận dữ liệu lịch sử, cấu trúc báo cáo và cấu hình refresh. Cập nhật live bằng run mới, RLS, mobile và publish Service chưa được nghiệm thu. Trạng thái từng tiêu chí nằm trong [checklist](../dashboard_test_cases.md).
