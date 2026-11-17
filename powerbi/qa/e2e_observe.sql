-- TV4/QA: read-only E2E observation. Run the entire script in salesdb.
-- Change this identifier to the SAME fresh run as Producer and Power BI.
-- Capture output before sending, during sending, and after final output settles.
DECLARE @RunId NVARCHAR(50) = N'e2e-20261117-140000';

SELECT SYSUTCDATETIME() AS observed_at_utc,
       DB_NAME() AS database_name, USER_NAME() AS database_user,
       @RunId AS run_id;

SELECT N'event_metrics_30s' AS source_table, COUNT_BIG(*) AS aggregate_rows,
       COALESCE(SUM(event_count), 0) AS source_events,
       MIN(window_end) AS first_window_utc, MAX(window_end) AS last_window_utc
FROM dbo.event_metrics_30s WHERE run_id = @RunId
UNION ALL
SELECT N'brand_sales_1m', COUNT_BIG(*), COALESCE(SUM(purchase_events), 0),
       MIN(window_end), MAX(window_end)
FROM dbo.brand_sales_1m WHERE run_id = @RunId;

SELECT event_type, SUM(event_count) AS events, SUM(revenue) AS purchase_value
FROM dbo.event_metrics_30s WHERE run_id = @RunId
GROUP BY event_type ORDER BY event_type;

SELECT
    COALESCE(SUM(event_count), 0) AS total_events,
    COALESCE(SUM(CASE WHEN event_type = N'view' THEN event_count ELSE 0 END), 0) AS view_events,
    COALESCE(SUM(CASE WHEN event_type = N'cart' THEN event_count ELSE 0 END), 0) AS cart_events,
    COALESCE(SUM(CASE WHEN event_type = N'purchase' THEN event_count ELSE 0 END), 0) AS purchase_events,
    COALESCE(SUM(CASE WHEN event_type = N'purchase' THEN revenue ELSE 0 END), 0) AS purchase_value,
    1.0 * SUM(CASE WHEN event_type = N'purchase' THEN event_count ELSE 0 END)
        / NULLIF(SUM(CASE WHEN event_type = N'view' THEN event_count ELSE 0 END), 0) AS purchase_to_view_ratio
FROM dbo.event_metrics_30s WHERE run_id = @RunId;

-- Compare after both outputs have settled, with NO extra time or brand filter.
SELECT e.purchase_events AS purchase_events_30s,
       b.purchase_events AS purchase_events_1m,
       e.purchase_value AS purchase_value_30s,
       b.purchase_value AS purchase_value_1m,
       e.purchase_events - b.purchase_events AS purchase_count_difference,
       ABS(e.purchase_value - b.purchase_value) AS purchase_value_difference
FROM (
    SELECT COALESCE(SUM(event_count), 0) AS purchase_events,
           COALESCE(SUM(revenue), 0) AS purchase_value
    FROM dbo.event_metrics_30s WHERE run_id = @RunId AND event_type = N'purchase'
) e
CROSS JOIN (
    SELECT COALESCE(SUM(purchase_events), 0) AS purchase_events,
           COALESCE(SUM(revenue), 0) AS purchase_value
    FROM dbo.brand_sales_1m WHERE run_id = @RunId
) b;

SELECT brand, SUM(purchase_events) AS purchase_events, SUM(revenue) AS purchase_value
FROM dbo.brand_sales_1m WHERE run_id = @RunId
GROUP BY brand ORDER BY purchase_value DESC, brand;

-- Both duplicate result sets must be empty.
SELECT window_end, run_id, event_type, COUNT_BIG(*) AS duplicate_count
FROM dbo.event_metrics_30s WHERE run_id = @RunId
GROUP BY window_end, run_id, event_type HAVING COUNT_BIG(*) > 1;

SELECT window_end, run_id, brand, COUNT_BIG(*) AS duplicate_count
FROM dbo.brand_sales_1m WHERE run_id = @RunId
GROUP BY window_end, run_id, brand HAVING COUNT_BIG(*) > 1;

SELECT N'event_metrics_30s' AS source_table, COUNT_BIG(*) AS invalid_rows
FROM dbo.event_metrics_30s
WHERE run_id = @RunId
  AND (event_count < 0 OR revenue < 0
       OR event_type NOT IN (N'view', N'cart', N'remove_from_cart', N'purchase')
       OR (event_type <> N'purchase' AND ABS(revenue) > 0.01))
UNION ALL
SELECT N'brand_sales_1m', COUNT_BIG(*)
FROM dbo.brand_sales_1m
WHERE run_id = @RunId
  AND (purchase_events < 0 OR revenue < 0 OR LTRIM(RTRIM(brand)) = N'');

SELECT TOP (10) window_end, run_id, event_type, event_count, revenue
FROM dbo.event_metrics_30s WHERE run_id = @RunId
ORDER BY window_end DESC, event_type;

SELECT TOP (10) window_end, run_id, brand, purchase_events, revenue
FROM dbo.brand_sales_1m WHERE run_id = @RunId
ORDER BY window_end DESC, brand;
