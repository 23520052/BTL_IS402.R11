# cloud_cost_report.md – Chi phí & quota Azure (TV3)

> Chi phí lấy từ *Cost Management → Cost analysis* (ảnh `evidence/azure-sql/30_cost_analysis_*.png`); phần chưa hiện ghi "ước tính" + công thức. Cost analysis có thể trễ vài giờ.

## 1. Tài nguyên TV3
| Tài nguyên | Tier/cấu hình | Region | Bắt đầu | Kết thúc/xóa | Giờ chạy | Chi phí thực (Cost analysis) | Ghi chú |
|---|---|---|---|---|---|---|---|
| Azure SQL `salesdb` (main) | [ĐIỀN] | [ĐIỀN] | 08/11 [giờ] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | |
| Azure SQL far (Basic) | Basic 5 DTU | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | chỉ để đo region |
| Storage account (Blob, LRS) | Standard | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | – | [ĐIỀN] | dung lượng [ĐIỀN] GB |
| VM benchmark (nếu có) | [ĐIỀN] | [ĐIỀN] | | | | | |
| **Tổng TV3** | | | | | | **[ĐIỀN]** | |

(Event Hubs, Stream Analytics: do TV2 báo cáo; Power BI: TV4.)

## 2. Chi phí cho đợt benchmark
Khoảng thời gian [ĐIỀN] → [ĐIỀN]; tài nguyên phát sinh: [ĐIỀN]; chi phí ước tính = giá/ngày × số ngày = [ĐIỀN] (nêu công thức, nguồn giá: Pricing calculator [ngày tra]).

## 3. Quota & ngân sách
- Budget alert: `budget-gr03`, ngưỡng [ĐIỀN]% (`01_budget_alert.png`).
- Quota/giới hạn subscription liên quan (`02_usage_quotas.png`): [ĐIỀN: vCore/DTU/region bị giới hạn nếu có].

## 4. Biện pháp tiết kiệm đã làm
- [ĐIỀN: chọn DTU Standard S1 thay vì tier cao; LRS; xóa server far ngay sau khi đo; dọn bảng `bench.*`]

## 5. Bài học / đề xuất
[ĐIỀN sau khi có số thực: tier phù hợp cho demo, khi nào nên scale, chi phí/ngày vận hành]
