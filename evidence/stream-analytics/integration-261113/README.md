# Bằng chứng tích hợp `integration-261113`

Đã nhận và lưu đủ bốn ảnh người thực hiện gửi ngày 13/11/2026, xác nhận thuộc run Producer mới. Ảnh được sao chép nguyên trạng; không sửa nội dung.

| File | Nội dung |
|---|---|
| `29a-integration-asa-backlog-max.png` | ASA Backlogged Input Events, Max, split theo partition: đỉnh mỗi partition 46. Phần watermark bị cắt. |
| `30a-integration-sql-totals-30s.png` | Run `integration-261113`: 28 dòng aggregate, accepted 10000, purchase 118, revenue 35757.22. |
| `30b-integration-sql-totals-1m.png` | 61 dòng aggregate, purchase 118, revenue làm tròn hai chữ số là 35757.22. |
| `30c-integration-sql-duplicate-check.png` | Hai bảng đều có `duplicate_groups = 0`. |

Đã đạt kiểm chứng tổng SQL và khóa trùng cho run này.

`expected_from_payload.json` được tính ngày 19/11/2026 từ payload độc lập trên Git: 10.000 event, 118 purchase, revenue 35757.22, 28 nhóm 30s và 61 nhóm brand 1m. File lưu SHA-256 nguồn và từng nhóm expected theo biên `(start, end]`; không phải export actual từ SQL.

Biên bản và phạm vi còn thiếu nằm trong [stream_test.md](../../../stream-analytics/stream_test.md). Các truy vấn dùng tạo kết quả nằm tại [sql_validation.sql](../../../stream-analytics/sql_validation.sql).
