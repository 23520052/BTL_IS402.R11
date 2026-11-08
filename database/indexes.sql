-- TV3 | indexes.sql | Đúng theo plan: mỗi bảng 1 index (window_end, run_id).
-- Không thêm index khác khi chưa có số đo chứng minh (index làm chậm ghi của ASA).
-- Idempotent, không dùng GO.

IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE name = 'ix_metrics_window' AND object_id = OBJECT_ID('dbo.event_metrics_30s'))
    CREATE INDEX ix_metrics_window ON dbo.event_metrics_30s (window_end, run_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE name = 'ix_brand_window' AND object_id = OBJECT_ID('dbo.brand_sales_1m'))
    CREATE INDEX ix_brand_window ON dbo.brand_sales_1m (window_end, run_id);
