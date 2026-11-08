-- ============================================================
-- TV3 | schema.sql | DATA CONTRACT v1 (freeze 08/11/2026 22:00)
-- Chạy trên Azure SQL Database (DB: salesdb). Idempotent: chạy lại an toàn.
-- KHÔNG đổi tên bảng / tên cột / kiểu dữ liệu sau khi freeze nếu chưa báo TV2 + TV4.
-- Không dùng GO (để dán thẳng được vào Query editor của Azure Portal).
--
-- Quy ước:
--   * window_end  : giờ UTC (System.Timestamp() của Stream Analytics), KHÔNG có múi giờ.
--   * revenue     : tổng price của PURCHASE EVENT (không phải "đơn hàng"; dataset không có order_id),
--                   đơn vị tiền giữ nguyên như dataset (không gọi là VND).
--   * revenue FLOAT: khớp output float của ASA ở giai đoạn MVP; cân nhắc DECIMAL sau khi test.
--   * brand NOT NULL: brand thiếu phải được chuẩn hóa thành 'unknown' ở nguồn (TV1) hoặc trong query ASA (TV2).
-- ============================================================

IF OBJECT_ID('dbo.event_metrics_30s', 'U') IS NULL
CREATE TABLE dbo.event_metrics_30s (
    window_end  DATETIME2     NOT NULL,
    run_id      NVARCHAR(50)  NOT NULL,
    event_type  NVARCHAR(30)  NOT NULL,
    event_count BIGINT        NOT NULL,
    revenue     FLOAT         NOT NULL
);

IF OBJECT_ID('dbo.brand_sales_1m', 'U') IS NULL
CREATE TABLE dbo.brand_sales_1m (
    window_end      DATETIME2      NOT NULL,
    run_id          NVARCHAR(50)   NOT NULL,
    brand           NVARCHAR(200)  NOT NULL,
    purchase_events BIGINT         NOT NULL,
    revenue         FLOAT          NOT NULL
);
