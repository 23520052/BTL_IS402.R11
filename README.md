# BTL_IS402.R11

Đồ án môn Điện toán đám mây: xây dựng luồng xử lý sự kiện thương mại điện tử và trực quan hóa kết quả trên Power BI.

Luồng dữ liệu: CSV → Python Producer → Azure Event Hubs → Azure Stream Analytics → Azure SQL → Power BI DirectQuery.

| Thành phần | Tài liệu |
|---|---|
| Chuẩn bị dữ liệu và Producer | [Hướng dẫn Producer](producer/README_producer.md) |
| Cơ sở dữ liệu Azure SQL | [Schema, quyền và thiết lập](database/README.md) |
| Dashboard Power BI | [Mở báo cáo và kết nối SQL](powerbi/README.md) |
| Hợp đồng dữ liệu | [Data contract](docs/data_contract.md) |
| Kết quả tích hợp | [Bằng chứng](evidence/) |
| Báo cáo đồ án | [Tài liệu báo cáo](docs/project_report/) |

Để xem dashboard offline, mở [sales_dashboard_snapshot.pbix](powerbi/sales_dashboard_snapshot.pbix). Bản DirectQuery và hướng dẫn kiểm thử nằm trong [powerbi/](powerbi/README.md).

Sprint 2 của TV4: [RLS/mobile](powerbi/rls_mobile.md), [kết quả nghiệm thu](powerbi/evidence/sprint2/README.md), [báo cáo Power BI/QA](docs/project_report/04_powerbi_qa.md) và [nội dung slide TV4](docs/project_report/04_powerbi_slides.md).
