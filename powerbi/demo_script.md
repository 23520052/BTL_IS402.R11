# Kịch bản demo Power BI — khoảng 6 phút

1. **Chuẩn bị:** mở PBIX chính, kết nối Azure SQL và chọn `integration-261117`. Bỏ bộ lọc thời gian để xem toàn run.
2. **Overview:** trình bày 118 purchase event, value 35.757,22, 9.785 view và Purchase/View khoảng 1,21%. Count là số event; số liệu thuộc run đã hoàn tất.
3. **Bốn trang:** chuyển trang và kiểm run đồng bộ. Ở Brand chọn Apple: 25 purchase, value 19.415,91; xóa lọc để về tổng. Ở Behavior giải thích Remove=0 do dữ liệu nguồn không có loại event này.
4. **RLS:** Modeling → View as → Manager: mọi brand. Stop viewing, chọn riêng Brand Analyst: chỉ Apple, share 100%; các chỉ số event bị chặn. Stop viewing sau khi kiểm.
5. **Mobile:** mở preview điện thoại, chuyển đủ bốn trang và cuộn xem KPI/biểu đồ.
6. **Cập nhật dữ liệu:** khi Producer/ASA phát run mới, chọn run đó, giữ Monitoring active và đối chiếu SQL trước/sau theo [quy trình E2E](e2e_test_guide.md). Nếu SQL không truy cập được, dùng snapshot có nhãn offline để giới thiệu báo cáo.

Phạm vi đã kiểm và các mục còn chờ nằm trong [checklist](dashboard_test_cases.md); quy tắc phân quyền tại [RLS/mobile](rls_mobile.md).
