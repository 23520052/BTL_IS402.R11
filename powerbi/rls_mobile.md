# RLS và Mobile Layout

## Phân quyền trong semantic model

| Role | Dữ liệu được đọc | Quy tắc |
|---|---|---|
| Manager | Cả hai fact, mọi brand | Read, không lọc dòng |
| Brand Analyst | Chỉ Apple trong `brand_sales_1m` | `'brand_sales_1m'[brand] = "apple"` |
| Brand Analyst | Không đọc `event_metrics_30s` | `FALSE()` |

Đây là role mẫu tĩnh; semantic model không sử dụng bảng ánh xạ user.

Bảng event tổng hợp không giữ brand nên không thể tính view/cart hoặc Purchase/View riêng cho Apple. Analyst thấy card event bằng 0 và biểu đồ event trống; sử dụng trang Brand Performance để phân tích. Số 0 này thể hiện giới hạn quyền. Manager dùng đủ bốn trang.

Không dùng slicer làm RLS. Không cấp đồng thời Manager và Brand Analyst cho cùng một người cần giới hạn: nhiều role có quyền cộng dồn. Các measure `ALLSELECTED`/`REMOVEFILTERS` không gỡ bộ lọc bảo mật.

## Kiểm thử lại trong Desktop

1. Mở `sales_dashboard.pbip` hoặc PBIX cuối, chọn `integration-261117`, bỏ time/brand filter.
2. Modeling → View as → chỉ Manager → OK. Trang Brand có 118 purchase và value 35.757,22, nhiều brand.
3. Stop viewing. Modeling → View as → chỉ Brand Analyst → OK.
4. Brand Performance có Apple, 25 purchase và value 19.415,91, share 100% của phạm vi được cấp. Mở dropdown brand: không có Samsung.
5. Chuyển Monitoring: Total/Purchase=0, latest window trống. Stop viewing để trở lại tác giả.
6. Chạy `qa/validate_rls.ps1 -Port <port> -OutputDirectory powerbi/evidence/local-check` để kiểm thêm truy vấn raw và thử gỡ filter. Dùng đúng port engine theo `qa/README.md`.

Test engine dùng thuộc tính kết nối `Roles=...`, không thay RLS bằng một bộ lọc DAX mô phỏng. Kết quả thật nằm trong `evidence/sprint2/rls_validation.json` và ảnh View as ở `evidence/sprint2/screenshots/`.

## Mobile

Cả bốn trang có `visuals/<name>/mobile.json`, canvas rộng 324 px, cuộn dọc. Navigation dùng lưới 2 × 2; KPI chia hai cột, timestamp và biểu đồ chiếm chiều rộng trang; brand/event dùng dropdown. Bố cục desktop giữ nguyên.

Trong Desktop chọn biểu tượng điện thoại ở góc dưới trái, chuyển đủ bốn tab, cuộn để kiểm tra KPI và biểu đồ. Run slicer dùng cùng sync group với desktop. Layout này được kiểm trong trình thiết kế điện thoại Desktop; chưa có kiểm thử trên điện thoại vật lý hoặc Power BI Mobile Service.

## Power BI Service

Báo cáo đã publish lên Power BI Service. Ngày 19/11, **Security → Test as role** xác nhận Analyst chỉ thấy Apple (25 purchase, value 19.415,91), slicer chỉ có Apple và Monitoring bị chặn; Manager thấy nhiều brand, 118 purchase, value 35.757,22 và 10.000 event. [Kết quả kiểm Service](evidence/service_validation.json).

Cả hai role hiện có 0 thành viên. Chưa kiểm bằng tài khoản Viewer riêng được gán role. Admin/Member/Contributor có quyền chỉnh sửa không dùng để nghiệm thu giới hạn RLS.

Nguồn: [Microsoft RLS](https://learn.microsoft.com/en-us/fabric/security/service-admin-row-level-security), [hướng dẫn RLS](https://learn.microsoft.com/en-us/power-bi/guidance/rls-guidance), [PBIP report và mobile.json](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report).
