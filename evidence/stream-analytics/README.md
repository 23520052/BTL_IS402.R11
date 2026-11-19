# Bằng chứng xử lý luồng

| Tệp hoặc thư mục | Nội dung |
|---|---|
| [BANG_CHUNG_STREAMING.html](BANG_CHUNG_STREAMING.html) | Tổng hợp 37 ảnh, mở offline |
| [smoke-3433042d611a](smoke-3433042d611a/) | Fixture, expected và ACK của run smoke 8 event |
| [integration-261113](integration-261113/) | Ảnh SQL, backlog và expected độc lập của run 10.000 event |
| `06-asa-overview.png` đến `13-output-brand-sales-success.png` | Bằng chứng thiết lập ASA, input/output và quyền truy cập |
| `19-smoke-live-8-sends-acknowledged.png` đến `25-smoke-duplicate-check.png` | Kiểm chứng live smoke từ phía gửi đến SQL |

Ảnh giữ nguyên nội dung tại thời điểm chụp. Đối chiếu phạm vi và kết luận tại [stream_test.md](../../stream-analytics/stream_test.md). Query tạo các kết quả SQL nằm ở [sql_validation.sql](../../stream-analytics/sql_validation.sql).

Ảnh cấu hình Event Hubs nằm ở [event-hubs](../event-hubs/); ảnh schema output nằm ở [05-sql-output-schema.png](../azure-sql/05-sql-output-schema.png).
