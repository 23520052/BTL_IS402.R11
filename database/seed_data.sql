-- ============================================================
-- TV3 | seed_data.sql | Dữ liệu MOCK cho TV4 làm dashboard (run_id = 'mock-seed')
-- * Mốc thời gian tính theo "bây giờ" (UTC): 60 phút gần nhất. Chạy lại để làm mới.
-- * Idempotent (xóa run 'mock-seed' rồi nạp lại). Không dùng GO.
-- * ĐÂY LÀ DỮ LIỆU GIẢ: không dùng làm số liệu báo cáo. Xóa trước demo bằng cleanup_runs.sql
-- * Tỉ lệ mô phỏng: view ~96%, cart ~2.2%, remove_from_cart ~0.5%, purchase ~1.75% (theo phân bố dataset).
-- ============================================================

DECLARE @run   NVARCHAR(50) = N'mock-seed';
DECLARE @now   DATETIME2    = SYSUTCDATETIME();
DECLARE @end30 DATETIME2    = DATEADD(SECOND, (DATEDIFF(SECOND, '2000-01-01', @now) / 30) * 30, '2000-01-01');
DECLARE @end60 DATETIME2    = DATEADD(SECOND, (DATEDIFF(SECOND, '2000-01-01', @now) / 60) * 60, '2000-01-01');

DELETE FROM dbo.event_metrics_30s WHERE run_id = @run;
DELETE FROM dbo.brand_sales_1m    WHERE run_id = @run;

-- ---------- event_metrics_30s: 120 cửa sổ 30 giây ----------
IF OBJECT_ID('tempdb..#w') IS NOT NULL DROP TABLE #w;

SELECT TOP (120)
    DATEADD(SECOND, CAST(-30 * (ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1) AS INT), @end30) AS window_end,
    400 + ABS(CAST(CHECKSUM(NEWID()) AS BIGINT)) % 400 AS v,     -- số view trong cửa sổ
    150 + ABS(CAST(CHECKSUM(NEWID()) AS BIGINT)) % 300 AS p      -- giá trung bình mỗi purchase
INTO #w
FROM sys.all_objects;

INSERT INTO dbo.event_metrics_30s (window_end, run_id, event_type, event_count, revenue)
SELECT w.window_end, @run, t.event_type, t.cnt, t.rev
FROM #w AS w
CROSS APPLY (VALUES
    (N'view',             w.v,                CAST(0.0 AS FLOAT)),
    (N'cart',             w.v * 22 / 1000,    CAST(0.0 AS FLOAT)),
    (N'remove_from_cart', w.v * 5 / 1000,     CAST(0.0 AS FLOAT)),
    (N'purchase',         w.v * 175 / 10000,  CAST(ROUND(w.v * 175 / 10000 * w.p, 2) AS FLOAT))
) AS t(event_type, cnt, rev)
WHERE t.cnt > 0;                                  -- ASA không phát hàng có count = 0

-- ---------- brand_sales_1m: 60 cửa sổ 1 phút x các brand ----------
IF OBJECT_ID('tempdb..#b')  IS NOT NULL DROP TABLE #b;
IF OBJECT_ID('tempdb..#bs') IS NOT NULL DROP TABLE #bs;

SELECT * INTO #b FROM (VALUES
    (N'samsung', 30, 350.0), (N'apple', 25, 700.0), (N'xiaomi', 10, 180.0), (N'huawei', 6, 200.0),
    (N'lenovo',   4, 400.0), (N'acer',   3, 450.0), (N'sony',    3, 300.0), (N'lg',     3, 350.0),
    (N'hp',       3, 500.0), (N'bosch',  2, 120.0), (N'unknown', 8, 150.0)
) AS x(brand, weight, base_price);

SELECT m.window_end, b.brand, b.base_price,
       ABS(CAST(CHECKSUM(NEWID()) AS BIGINT)) % (b.weight / 2 + 2)              AS pe,
       0.8 + (ABS(CAST(CHECKSUM(NEWID()) AS BIGINT)) % 40) / 100.0               AS k
INTO #bs
FROM (SELECT TOP (60)
             DATEADD(SECOND, CAST(-60 * (ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1) AS INT), @end60) AS window_end
      FROM sys.all_objects) AS m
CROSS JOIN #b AS b;

INSERT INTO dbo.brand_sales_1m (window_end, run_id, brand, purchase_events, revenue)
SELECT window_end, @run, brand, pe, CAST(ROUND(pe * base_price * k, 2) AS FLOAT)
FROM #bs
WHERE pe > 0;

-- ---------- kiểm tra nhanh ----------
SELECT 'event_metrics_30s' AS tbl, COUNT(*) AS n_rows, MIN(window_end) AS min_window, MAX(window_end) AS max_window
FROM dbo.event_metrics_30s WHERE run_id = @run
UNION ALL
SELECT 'brand_sales_1m', COUNT(*), MIN(window_end), MAX(window_end)
FROM dbo.brand_sales_1m WHERE run_id = @run;
