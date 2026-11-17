# Dashboard Power BI — Sprint 1

Dashboard gồm bốn trang: tổng quan bán hàng, giám sát sự kiện, hiệu suất thương hiệu và hành vi khách hàng. Bản chính truy vấn Azure SQL bằng DirectQuery; bản snapshot dùng để xem dữ liệu lịch sử offline.

## File chính

| File / thư mục | Nội dung |
|---|---|
| [sales_dashboard.pbix](sales_dashboard.pbix) | Báo cáo chính, cần kết nối Azure SQL |
| [sales_dashboard_snapshot.pbix](sales_dashboard_snapshot.pbix) | Bản offline của run `integration-261113` gồm 10.000 event, có nhãn OFFLINE SNAPSHOT |
| [sales_dashboard.pbip](sales_dashboard.pbip) | Điểm mở bộ nguồn; đi kèm `sales_dashboard.Report/` và `sales_dashboard.SemanticModel/` |
| [screenshots/](screenshots/) | Ảnh bốn trang của bản snapshot |
| [qa/](qa/README.md) | Script và hướng dẫn kiểm thử |
| [evidence/](evidence/README.md) | Kết quả kiểm tra và phạm vi đã xác nhận |

## Mở báo cáo

1. Mở `sales_dashboard.pbix` bằng Power BI Desktop. Để chỉnh sửa nguồn qua Git, mở `sales_dashboard.pbip` cùng hai thư mục Report và SemanticModel.
2. Nguồn SQL đã cấu hình: server `sqlsrv-sales-gr03-tram01.database.windows.net`, database `salesdb`.
3. Chọn xác thực **Database**, user `pbi_reader`, mật khẩu được cấp riêng. Có thể đổi tài khoản tại **File → Options and settings → Data source settings → Edit Permissions**.
4. IP kết nối phải được Azure SQL firewall cho phép. Nếu gặp lỗi 40615, người quản trị thêm đúng client IP trong thông báo lỗi tại **SQL server → Networking → Firewall rules**.
5. Refresh, chọn một `run_id` và xóa bộ lọc thời gian cũ trước khi đối chiếu dữ liệu.

Bản chính hiện lưu lựa chọn `integration-261117`; KPI mẫu và bằng chứng đã lưu thuộc `integration-261113`. Chọn lại run này để đối chiếu các số mẫu. `mock-seed` là dữ liệu mô phỏng.

Overview và Monitoring cấu hình Automatic Page Refresh 30 giây. Dữ liệu mới xuất hiện khi Producer/ASA đang ghi vào SQL; snapshot không tự cập nhật.

## Chỉnh sửa

Mở PBIP, chỉnh sửa trong Desktop rồi Save. Khi cập nhật bản bàn giao, chọn **File → Save as → Power BI file (.pbix)** và lưu `sales_dashboard.pbix`. Hai định dạng là các bản lưu riêng, cần xuất lại PBIX sau khi thay đổi PBIP.

Cache `.pbi/`, `local-preview/`, `evidence/local-check/` và môi trường chứa mật khẩu được bỏ qua bởi Git.

## Tài liệu

- [Mô hình dữ liệu, bố cục và quy tắc KPI](dashboard_spec.md)
- [Công thức DAX](dax_measures.md)
- [Kiểm thử kỹ thuật](qa/README.md) và [checklist nghiệm thu](dashboard_test_cases.md)
- [Quy trình kiểm thử toàn luồng](e2e_test_guide.md)
- [Kịch bản demo](demo_script.md)
- [Kết quả và giới hạn kiểm chứng](evidence/README.md)
