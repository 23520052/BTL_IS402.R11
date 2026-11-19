WITH Normalized AS
(
    SELECT
        event_id,
        run_id,
        LOWER(LTRIM(RTRIM(event_type))) AS event_type,
        CASE
            WHEN brand IS NULL OR LTRIM(RTRIM(brand)) = ''
                THEN 'unknown'
            ELSE LOWER(LTRIM(RTRIM(brand)))
        END AS brand,
        TRY_CAST(price AS float) AS price
    FROM [eh-sales] TIMESTAMP BY stream_event_time
),
ValidEvents AS
(
    SELECT *
    FROM Normalized
    WHERE event_id IS NOT NULL
      AND LTRIM(RTRIM(event_id)) <> ''
      AND run_id IS NOT NULL
      AND LTRIM(RTRIM(run_id)) <> ''
      AND event_type IN ('view', 'cart', 'purchase')
      AND price IS NOT NULL
      AND price >= 0
)

SELECT
    System.Timestamp() AS window_end,
    run_id,
    event_type,
    COUNT(*) AS event_count,
    SUM(CASE WHEN event_type = 'purchase' THEN price ELSE 0.0 END) AS revenue
INTO [sql-event-metrics]
FROM ValidEvents
GROUP BY run_id, event_type, TumblingWindow(second, 30);

SELECT
    System.Timestamp() AS window_end,
    run_id,
    brand,
    COUNT(*) AS purchase_events,
    SUM(price) AS revenue
INTO [sql-brand-sales]
FROM ValidEvents
WHERE event_type = 'purchase'
GROUP BY run_id, brand, TumblingWindow(minute, 1);
