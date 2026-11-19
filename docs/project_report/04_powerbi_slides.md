# Nội dung trình bày Power BI và QA

Thời lượng khoảng 6 phút gồm demo. Tham chiếu [báo cáo kỹ thuật](04_powerbi_qa.md) và [kết quả kiểm thử](../../powerbi/evidence/sprint2/README.md).

## Slide 1 Dashboard có bốn trang

Sales Overview trình bày tổng giá trị purchase và tỷ lệ event. Real-time Monitoring theo dõi cửa sổ 30 giây. Brand Performance so sánh brand theo cửa sổ 1 phút. Customer Behavior thể hiện view/cart/remove/purchase.

Hình: ảnh bốn trang DirectQuery trong `powerbi/evidence/sprint2/screenshots/`. Khi demo, chọn một run và chuyển Page Navigator để giữ cùng phạm vi dữ liệu.

## Slide 2 KPI hai fact khớp nhau

Run `integration-261117`: 10.000 event, 9.785 view, 97 cart, 118 purchase. Purchase value 35.757,22 và Purchase/View 1,21%. Bảng brand cũng có 118 purchase và cùng value.

Count là số event. Nguồn thiếu order_id và không hỗ trợ xác định tỷ lệ chuyển đổi unique customer. Số liệu trên thuộc run đã hoàn tất.

## Slide 3 DirectQuery và Automatic Page Refresh

Azure SQL phục vụ bốn partition DirectQuery. Overview và Monitoring đặt APR 30 giây. Thời gian hiển thị còn phụ thuộc cửa sổ ASA, watermark, ghi SQL và render. Window Age thể hiện độ cũ cửa sổ.

Demo live cần Producer/ASA phát run mới, giữ Monitoring active và đối chiếu SQL trước/sau. Lần QA Sprint 2 chưa ghi nhận run mới đang phát.

## Slide 4 RLS giới hạn Analyst theo brand

Manager xem mọi brand. Brand Analyst chỉ xem Apple: 25 purchase, value 19.415,91. RLS chặn bảng event không giữ brand, nên Analyst dùng trang Brand Performance.

Hình: `rls_manager_all_brands.png`, `rls_analyst_apple.png`, `rls_analyst_events_denied.png`. Trình diễn Modeling → View as từng role, sau đó Stop viewing. Không gán hai role cùng lúc cho người cần giới hạn.

## Slide 5 Mobile Layout và kết quả QA

Bốn trang có canvas mobile 324px, cuộn dọc và KPI chia hai cột. Đã kiểm bằng preview điện thoại Desktop. Kiểm schema tương thích của 103 file JSON, 8 truy vấn DAX và 6 kiểm tra RLS đều đạt.

Hình: chọn ảnh mobile tổng quan và mobile KPI. Bản Service đã kiểm đủ bốn trang và hai role bằng Test as role; tài khoản Viewer riêng và điện thoại vật lý chưa kiểm.

## Slide 6 Demo và phần còn cần nghiệm thu

Mở PBIX cuối, chọn run, trình bày bốn trang. Thử hai role rồi mobile. Khi Producer/ASA chạy run mới, bổ sung bằng chứng count/window tự đổi và SQL trước/sau. Snapshot offline là phương án dự phòng có nhãn riêng.

