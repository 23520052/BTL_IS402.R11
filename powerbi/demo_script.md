# Kịch bản demo Power BI — khoảng 4 phút

1. **Giới thiệu nguồn:** mở PBIX/PBIP chính, xác nhận Azure SQL DirectQuery và chọn `integration-261113`. Bỏ bộ lọc thời gian để xem toàn run.
2. **Overview:** trình bày 118 purchase event, value 35.757,22, 9.785 view và purchase/view khoảng 1,21%. Đây là dữ liệu tích hợp lịch sử; count là số event.
3. **Khám phá bốn trang:** dùng Page Navigator, kiểm run đồng bộ. Ở Brand chọn apple: 25 purchase, value 19.415,91; xóa lọc để về tổng. Ở Behavior giải thích nguồn thật có view/cart/purchase, còn Remove=0.
4. **Minh họa cập nhật:** nếu Producer/ASA đang phát run mới, chọn run đó và ghi Monitoring tự đổi theo APR 30 giây, đối chiếu SQL cùng run. Quy trình đầy đủ ở [hướng dẫn E2E](e2e_test_guide.md).
5. **Trình bày kết quả:** phân biệt số liệu lịch sử với phần cập nhật mới đã quan sát. Nếu SQL không truy cập được, dùng snapshot để giới thiệu bố cục và nêu rõ chế độ offline.

Các tiêu chí và trạng thái nghiệm thu nằm trong [checklist](dashboard_test_cases.md). RLS và mobile nằm ngoài phạm vi Sprint 1.
