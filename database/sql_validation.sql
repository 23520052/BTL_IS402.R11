-- ============================================================
-- TV3 | sql_validation.sql | Đối chiếu / kiểm tra dữ liệu ASA ghi vào Azure SQL
-- Cách dùng: sửa @run; muốn chạy 1 khối thì bôi đen DÒNG DECLARE @run + khối đó -> Run. Không dùng GO.
-- Khối 6, 7 cũng là phần TV3 chiếu khi DEMO (xem docs/tv3/IMPLEMENTATION_PLAN.md).
-- ============================================================
DECLARE @run NVARCHAR(50) = N'integration-01';

-- [1] Có những run nào, bao nhiêu dòng, khoảng thời gian nào
SELECT 'event_metrics_30s' AS tbl, run_id, COUNT(*) AS n_rows, MIN(window_end) AS min_window, MAX(window_end) AS max_window
FROM dbo.event_metrics_30s GROUP BY run_id
UNION ALL
SELECT 'brand_sales_1m', run_id, COUNT(*), MIN(window_end), MAX(window_end)
FROM dbo.brand_sales_1m GROUP BY run_id
ORDER BY tbl, max_window DESC;

-- [2] Tổng event theo loại của 1 run -> so với số event TV1 đã gửi (vd 10.000 cho integration-01)
SELECT event_type, SUM(event_count) AS events, SUM(revenue) AS revenue
FROM dbo.event_metrics_30s WHERE run_id = @run
GROUP BY ROLLUP (event_type);

-- [3] Nhất quán giữa 2 output: purchase_events và revenue phải khớp (revenue lệch <= 0.01)
SELECT
  (SELECT SUM(event_count)     FROM dbo.event_metrics_30s WHERE run_id = @run AND event_type = N'purchase') AS purchase_events_30s,
  (SELECT SUM(purchase_events) FROM dbo.brand_sales_1m    WHERE run_id = @run)                            AS purchase_events_1m,
  (SELECT SUM(revenue)         FROM dbo.event_metrics_30s WHERE run_id = @run AND event_type = N'purchase') AS revenue_30s,
  (SELECT SUM(revenue)         FROM dbo.brand_sales_1m    WHERE run_id = @run)                            AS revenue_1m;
-- Lệch nhỏ ở cửa sổ cuối là bình thường nếu ASA chưa đóng cửa sổ: đợi ~2 phút (hoặc Stop job) rồi chạy lại.

-- [4] Trùng khóa (ASA ghi at-least-once; restart job có thể sinh dòng trùng). Kỳ vọng: 0 dòng
SELECT window_end, run_id, event_type, COUNT(*) AS dup
FROM dbo.event_metrics_30s WHERE run_id = @run
GROUP BY window_end, run_id, event_type HAVING COUNT(*) > 1;

SELECT window_end, run_id, brand, COUNT(*) AS dup
FROM dbo.brand_sales_1m WHERE run_id = @run
GROUP BY window_end, run_id, brand HAVING COUNT(*) > 1;

-- [5] Giá trị bất thường (âm / brand rỗng). Kỳ vọng: 0 dòng
SELECT 'event_metrics_30s' AS tbl, COUNT(*) AS bad_rows FROM dbo.event_metrics_30s
WHERE run_id = @run AND (event_count < 0 OR revenue < 0)
UNION ALL
SELECT 'brand_sales_1m', COUNT(*) FROM dbo.brand_sales_1m
WHERE run_id = @run AND (purchase_events < 0 OR revenue < 0 OR LTRIM(RTRIM(brand)) = N'');

-- [6] (DEMO) 20 dòng mới nhất
SELECT TOP 20 * FROM dbo.event_metrics_30s ORDER BY window_end DESC;
SELECT TOP 20 * FROM dbo.brand_sales_1m    ORDER BY window_end DESC;

-- [7] (DEMO) Độ trễ cập nhật: cửa sổ mới nhất cách "bây giờ" bao nhiêu giây (bằng chứng near-real-time)
SELECT MAX(window_end) AS last_window_end_utc, SYSUTCDATETIME() AS now_utc,
       DATEDIFF(SECOND, MAX(window_end), SYSUTCDATETIME()) AS lag_seconds
FROM dbo.event_metrics_30s WHERE run_id = @run;

-- [8] Top brand theo revenue của run
SELECT TOP 10 brand, SUM(purchase_events) AS purchase_events, SUM(revenue) AS revenue
FROM dbo.brand_sales_1m WHERE run_id = @run
GROUP BY brand ORDER BY SUM(revenue) DESC;

-- [9] Bằng chứng "aggregate trước khi ghi DB" (cho optimization.md): số event thô vs số dòng đã ghi
SELECT
  (SELECT SUM(event_count) FROM dbo.event_metrics_30s WHERE run_id = @run) AS raw_events_in,
  (SELECT COUNT(*)         FROM dbo.event_metrics_30s WHERE run_id = @run) AS rows_30s,
  (SELECT COUNT(*)         FROM dbo.brand_sales_1m    WHERE run_id = @run) AS rows_1m;
