# Trực quan hóa dữ liệu và kiểm thử Power BI

**Phụ trách:** Thành viên 4, BI và QA Engineer. **Cập nhật:** 19/11/2026.

## Bài toán và kết quả triển khai

Dashboard giúp theo dõi sự kiện thương mại điện tử sau xử lý luồng trên Azure. Người quản lý xem tổng giá trị purchase, diễn biến sự kiện và hiệu suất brand. Bản triển khai có bốn trang Power BI Desktop, kết nối Azure SQL bằng DirectQuery, navigation, slicer đồng bộ run, Automatic Page Refresh, hai role RLS và bố cục điện thoại cho bốn trang.

Kết quả đối chiếu run `integration-261117`: 10.000 event, 9.785 view, 97 cart, 118 purchase, 0 remove và purchase value 35.757,22. Purchase/View bằng 118 / 9.785, khoảng 1,21%. Hai fact cùng trả về 118 purchase và 35.757,22. Đây là run đã hoàn tất, không phải một luồng đang phát tại thời điểm kiểm tra Sprint 2.

## Mô hình dữ liệu

`event_metrics_30s` có grain run, cửa sổ 30 giây và loại event. `brand_sales_1m` có grain run, cửa sổ 1 phút và brand. DimRun lọc một chiều tới cả hai fact, DimEvent lọc tới bảng event. Không nối trực tiếp hai fact khác grain. Tất cả bốn partition dùng DirectQuery; dữ liệu được truy vấn từ `salesdb` trên Azure SQL.

Tách grain tránh nhân bản revenue khi join bảng brand với bảng event. Run slicer dùng một sync group trên cả bốn trang. Bộ lọc thời gian là riêng từng trang vì cửa sổ 30 giây và 1 phút khác nhau. Brand slicer chỉ tác động trang Brand Performance.

## Bốn trang báo cáo

| Trang | Mục đích | Nội dung chính |
|---|---|---|
| Sales Overview | Tổng quan hoạt động mua | Purchase count/value, view, Purchase/View và trend |
| Real-time Monitoring | Theo dõi cửa sổ dữ liệu | Tổng event, phân bố event, cửa sổ cuối và độ cũ dữ liệu |
| Brand Performance | So sánh brand | Xếp hạng, purchase count/value và tỷ trọng |
| Customer Behavior | Phân tích cơ cấu hành vi | View/cart/remove/purchase, Cart/View và Purchase/View |

Count là tổng `event_count`, không phải số dòng aggregate. Dataset không có order_id nên purchase event không đồng nghĩa một đơn hàng. Tỷ lệ Purchase/View là tỷ lệ event, không phải tỷ lệ chuyển đổi unique customer. Value giữ đơn vị nguồn, không tự đổi tiền tệ. Mẫu số bằng 0 trả BLANK. Remove=0 của run thật phản ánh dữ liệu nguồn, không phải lỗi tính toán.

Công thức đầy đủ nằm trong `powerbi/dax_measures.md`. Các measure theo loại event bỏ filter DimEvent để card purchase không biến thành 0 khi Monitoring chọn view. Total Events và biểu đồ cơ cấu vẫn nhận filter này. Brand share sử dụng ALLSELECTED và luôn nằm trong quyền RLS hiện tại.

## DirectQuery và cập nhật dữ liệu

Overview và Monitoring bật APR 30 giây trong Desktop. Độ trễ nhìn thấy còn gồm cửa sổ ASA, watermark, thời gian ghi SQL và truy vấn/render báo cáo. Window Age tính từ UTC hiện tại tới cửa sổ cuối, chỉ biểu diễn độ cũ dữ liệu. Không dùng nó thay cho số đo độ trễ từng event.

Kiểm DAX trên model DirectQuery đang mở đạt với dữ liệu Azure của run `integration-261117`. Nghiệm thu live cần giữ Producer/ASA phát run mới trong lúc ghi ảnh SQL và KPI trước/sau, không bấm Refresh trong đoạn quan sát. Quy trình có trong `powerbi/e2e_test_guide.md`. Chưa có bằng chứng run mới đang phát trong lần nghiệm thu này.

Quan sát bổ sung trên chính PBIX sau mở lại: giữ nguyên Monitoring 32,9 giây, không thao tác hoặc bấm Refresh, Window Age tự tăng từ 35.007 lên 35.037 giây. Tổng event và cửa sổ cuối giữ nguyên vì run đã hoàn tất. Hai ảnh và timestamp lưu trong `apr_observation.json`; phép thử xác nhận visual được đánh giá lại theo chu kỳ, không thay cho live E2E. Slicer view trên UI cho Total=9.785, Purchase=118 và trend chỉ view, khớp truy vấn DAX.

## Row Level Security

Manager có quyền đọc toàn bộ. Brand Analyst dùng role mẫu tĩnh chỉ cho phép Apple trong `brand_sales_1m`. Bảng event tổng hợp không có brand nên bị chặn bằng FALSE() cho Analyst. Vì vậy trang Brand thể hiện được 25 purchase và value 19.415,91 của Apple; các trang dựa trên event không cung cấp chỉ số toàn hệ thống cho Analyst.

Kiểm bằng Modeling → View as và ADOMD với `Roles=...` xác nhận Manager đọc mọi brand, Analyst chỉ thấy Apple, bảng event bị chặn và REMOVEFILTERS không vượt qua RLS. Ngày 19/11, **Test as role trên Power BI Service** cũng xác nhận Manager có 118 purchase/value 35.757,22 và 10.000 event; Analyst chỉ có Apple, 25 purchase/value 19.415,91, event=0. Hai role hiện có 0 thành viên; chưa kiểm bằng tài khoản Viewer riêng. Kết quả tại [service_validation.json](../../powerbi/evidence/service_validation.json).

## Bố cục mobile

Cả bốn trang có bố cục mobile rộng 324 px, cuộn dọc, navigation 2 × 2 và KPI chia hai cột. Đã kiểm tra bằng preview trong Power BI Desktop; chưa kiểm trên thiết bị vật lý hoặc Power BI Mobile Service.

## Phương pháp QA và bằng chứng

| Kiểm tra | Cách làm | Kết quả |
|---|---|---|
| Cấu trúc dự án | Schema JSON, binding, relationship, bounds, mobile overlap và role | 103/103 file đạt kiểm schema tương thích, không có lỗi cấu trúc |
| KPI DirectQuery | 8 truy vấn DAX trên engine Desktop | Đạt, hai fact khớp count/value |
| RLS | Kết nối theo role, kiểm raw rows và thử gỡ filter | 6 kiểm tra đạt |
| UI RLS | View as Manager và Brand Analyst | Ảnh dữ liệu được phép và bảng event bị chặn |
| Power BI Service | Bốn trang, Page Navigator, slicer và Test as role | KPI khớp; Manager/Analyst đọc đúng phạm vi |
| Mobile | Preview điện thoại Desktop, cuộn xem KPI | Có layout bốn trang và ảnh kiểm tra |
| Live E2E | Run mới với Producer/ASA đang chạy | Chờ thực hiện |

Desktop khai báo schema visualContainer 2.14.0 chưa được Microsoft công bố tại URL tương ứng. Validator dùng schema công khai 2.13.0 và ghi rõ ánh xạ tương thích, không tuyên bố đã kiểm schema chính xác 2.14.0. Các file mobile dùng schema công khai 2.8.0.

Mã QA trong `powerbi/qa/`. Kết quả mới trong `powerbi/evidence/sprint2/`, ảnh tại thư mục screenshots bên trong. Bản snapshot offline của Sprint 1 giữ nhãn offline và không dùng để chứng minh DirectQuery, APR hoặc RLS Sprint 2.

## Demo và bàn giao

Mở PBIX chính, chọn run, trình bày bốn trang và KPI. Chuyển View as Manager rồi Brand Analyst, kiểm Apple và chặn event, sau đó Stop viewing. Mở mobile preview, chuyển bốn trang và cuộn xuống biểu đồ. Với bài live, làm theo quy trình E2E và lưu run_id cùng timestamp UTC. Khi mạng lỗi, dùng snapshot có nhãn offline và nói rõ phạm vi.

Bộ bàn giao gồm PBIX chính, PBIP cùng Report/SemanticModel, tài liệu DAX/spec, checklist QA, hướng dẫn RLS/mobile, kịch bản demo và bằng chứng.

## Tài liệu tham khảo

1. [Microsoft DirectQuery](https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-use-directquery).
2. [Microsoft Automatic Page Refresh](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-automatic-page-refresh).
3. [Microsoft Row Level Security](https://learn.microsoft.com/en-us/fabric/security/service-admin-row-level-security).
4. [Microsoft Power BI Project report](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report).
