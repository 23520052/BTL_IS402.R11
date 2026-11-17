# Checklist kiểm thử Power BI — Sprint 1

Cập nhật 17/11/2026. PASS ghi theo phạm vi SQL, DAX hoặc UI; PENDING là tiêu chí chưa đủ bằng chứng. Mốc số liệu bên dưới thuộc run `integration-261113`, với toàn bộ thời gian và không lọc event/brand trừ khi nêu riêng.

| ID | Tiêu chí | Kết quả mong đợi | Trạng thái |
|---|---|---|---|
| BI01 | Mở PBIP | Đủ bốn trang, model/report không lỗi | PENDING mở lại bản mới nhất với SQL ổn định; snapshot đã kiểm bốn trang |
| BI02 | Quyền `pbi_reader` | Cả hai fact: SELECT=1, INSERT/UPDATE/DELETE=0 | Đã kiểm đọc SQL và metadata quyền fact event; PENDING kiểm lại cả hai fact bằng script mới |
| BI03 | Chọn `mock-seed` | KPI mỗi fact khớp SQL, kiểm độc lập | PASS DAX/SQL; PENDING slicer UI |
| BI04 | Navigation và đồng bộ run | Chuyển đủ bốn trang, giữ run đã chọn | PENDING |
| BI05 | KPI toàn run | 10.000 event; view 9.785; cart 97; purchase 118; remove 0; value 35.757,22; purchase/view ≈ 1,21% | PASS SQL/DAX; PENDING ảnh đủ trang DirectQuery |
| BI06 | Lọc brand | Apple: 25 purchase/19.415,91; samsung: 26/6.677,27; Overview không chịu brand filter | PASS số liệu DAX; PENDING UI |
| BI07 | Tổng brand/share | 118 purchase, value 35.757,22; share toàn bộ 100% | PASS count/value SQL/DAX; PENDING share tổng và UI |
| BI08 | Monitoring lọc view | Total/trend chỉ view; Purchase Events vẫn 118 | PASS DAX Total=9.785/Purchase=118; PENDING trend/slicer UI |
| BI09 | Khoảng thời gian rỗng | Count/value=0; ratio/last window=BLANK | PASS DAX với run không tồn tại; PENDING khoảng thời gian rỗng trên UI |
| BI10 | Mô hình | Bốn bảng DirectQuery, hai fact không join trực tiếp, dimension lọc một chiều | Source đạt; PENDING kiểm runtime khi mở lại |
| BI11 | APR | Overview/Monitoring bật refresh 30 giây | PASS UI tại lần kiểm đã lưu; PBIX có APR/PT30S |
| BI12 | Run mới đang phát | Window/count tự đổi, đối chiếu SQL trước–sau | PENDING |
| BI13 | Đối chiếu hai fact | Purchase count bằng nhau, chênh value ≤ 0,01, grain trùng=0 | PASS SQL/DAX |
| BI14 | Đóng/mở lại PBIX | Bốn trang và kết nối DirectQuery hoạt động | PASS cấu trúc ZIP/DataModel; PENDING mở lại đầy đủ với SQL ổn định |

## Bằng chứng

- [SQL/DAX ngày 17/11](evidence/hotspot_recheck_20261117_103543/README.md): 11 truy vấn SQL và 8 truy vấn DAX trên run lịch sử.
- [Kiểm PBIX](evidence/artifact_validation.json), [kiểm PBIP](evidence/project_validation.json) và [snapshot DAX](evidence/snapshot/model_validation.json).
- [Mốc tích hợp SQL ngày 13/11](../evidence/azure-sql/validation_integration-01.txt).

Giới hạn kết nối, schema và phạm vi kiểm chứng nằm tại [evidence/README.md](evidence/README.md). Các bước nghiệm thu run mới nằm trong [quy trình E2E](e2e_test_guide.md).
