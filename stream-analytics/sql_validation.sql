DECLARE @run_id nvarchar(50) = N'integration-261113';

SELECT DB_NAME() AS connected_database, @run_id AS run_id;

SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    ORDINAL_POSITION,
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo'
  AND TABLE_NAME IN ('event_metrics_30s', 'brand_sales_1m')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

SELECT run_id, window_end, event_type, event_count, revenue
FROM dbo.event_metrics_30s
WHERE run_id = @run_id
ORDER BY window_end, event_type;

SELECT run_id, window_end, brand, purchase_events, revenue
FROM dbo.brand_sales_1m
WHERE run_id = @run_id
ORDER BY window_end, brand;

SELECT
    @run_id AS run_id,
    COUNT_BIG(*) AS aggregate_rows,
    SUM(event_count) AS accepted_events,
    SUM(CASE WHEN event_type = 'purchase' THEN event_count ELSE 0 END) AS purchase_events,
    SUM(revenue) AS revenue
FROM dbo.event_metrics_30s
WHERE run_id = @run_id;

SELECT
    @run_id AS run_id,
    COUNT_BIG(*) AS aggregate_rows,
    SUM(purchase_events) AS purchase_events,
    SUM(revenue) AS revenue
FROM dbo.brand_sales_1m
WHERE run_id = @run_id;

SELECT
    event_type,
    SUM(event_count) AS event_count,
    SUM(revenue) AS revenue
FROM dbo.event_metrics_30s
WHERE run_id = @run_id
GROUP BY event_type
ORDER BY event_type;

SELECT
    @run_id AS run_id,
    (SELECT SUM(event_count)
     FROM dbo.event_metrics_30s
     WHERE run_id = @run_id AND event_type = 'purchase') AS purchase_events_30s,
    (SELECT SUM(purchase_events)
     FROM dbo.brand_sales_1m
     WHERE run_id = @run_id) AS purchase_events_1m,
    CAST(ROUND((SELECT SUM(revenue)
                FROM dbo.event_metrics_30s
                WHERE run_id = @run_id), 2) AS decimal(20, 2)) AS revenue_30s,
    CAST(ROUND((SELECT SUM(revenue)
                FROM dbo.brand_sales_1m
                WHERE run_id = @run_id), 2) AS decimal(20, 2)) AS revenue_1m;

SELECT
    @run_id AS run_id,
    'event_metrics_30s' AS table_name,
    COUNT_BIG(*) AS duplicate_groups
FROM (
    SELECT window_end, event_type
    FROM dbo.event_metrics_30s
    WHERE run_id = @run_id
    GROUP BY window_end, event_type
    HAVING COUNT_BIG(*) > 1
) AS d30

UNION ALL

SELECT @run_id, 'brand_sales_1m', COUNT_BIG(*)
FROM (
    SELECT window_end, brand
    FROM dbo.brand_sales_1m
    WHERE run_id = @run_id
    GROUP BY window_end, brand
    HAVING COUNT_BIG(*) > 1
) AS d60;

SELECT
    run_id,
    SUM(event_count) AS processed_events,
    COUNT_BIG(*) AS aggregate_rows,
    MIN(window_end) AS first_window,
    MAX(window_end) AS last_window
FROM dbo.event_metrics_30s
GROUP BY run_id
ORDER BY MAX(window_end) DESC;
