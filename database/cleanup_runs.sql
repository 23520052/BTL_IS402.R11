-- TV3 | cleanup_runs.sql | Xóa dữ liệu của 1 run (mặc định: mock-seed) trước demo / sau test.
-- Chỉ xóa run 'integration-*' / 'demo-*' khi CẢ NHÓM đồng ý (đó là bằng chứng). Không dùng GO.
DECLARE @run NVARCHAR(50) = N'mock-seed';

SELECT 'event_metrics_30s' AS tbl, COUNT(*) AS rows_to_delete FROM dbo.event_metrics_30s WHERE run_id = @run
UNION ALL
SELECT 'brand_sales_1m', COUNT(*) FROM dbo.brand_sales_1m WHERE run_id = @run;

DELETE FROM dbo.event_metrics_30s WHERE run_id = @run;
DELETE FROM dbo.brand_sales_1m    WHERE run_id = @run;
