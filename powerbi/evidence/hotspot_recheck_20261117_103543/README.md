# Kiểm tra SQL và DAX — 17/11/2026

Thời điểm: 10:35–10:36 giờ Việt Nam. Mạng sử dụng: hotspot điện thoại.

| Nội dung | Kết quả |
|---|---|
| SQL trực tiếp | 11 truy vấn đọc thành công: metadata quyền/schema, KPI và tính toàn vẹn dữ liệu |
| Model Desktop | 8 truy vấn DAX thành công |
| Run `integration-261113` | 10.000 event = 9.785 view + 97 cart + 118 purchase; purchase value 35.757,22 |
| Đối chiếu hai fact | Tổng purchase count và value khớp |

Đây là kiểm tra trên dữ liệu lịch sử. Trạng thái kết nối và giới hạn nghiệm thu được tổng hợp tại [evidence/README.md](../README.md).

- [Kết quả SQL](sql_validation.json)
- [Kết quả DAX](model_validation.json)
