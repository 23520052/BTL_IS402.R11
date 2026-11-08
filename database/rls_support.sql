-- ============================================================
-- TV3 | rls_support.sql | TÙY CHỌN – chỉ chạy sau khi TV4 đồng ý dùng bảng ánh xạ này
-- Rubric "Phân quyền dashboard" (1.0đ): TV4 cấu hình RLS trong Power BI; TV3 cung cấp
-- bảng role -> brand ở SQL để RLS đọc từ nguồn dữ liệu (không hard-code trong PBIX).
-- 'Manager' = brand '*' (xem tất cả). 'Brand Analyst' = chỉ các brand liệt kê.
-- user_email để NULL; TV4 điền email thật nếu dùng Power BI Service.
-- Idempotent, không dùng GO.
-- ============================================================

IF OBJECT_ID('dbo.rls_brand_access', 'U') IS NULL
CREATE TABLE dbo.rls_brand_access (
    role_name  NVARCHAR(50)  NOT NULL,
    user_email NVARCHAR(200) NULL,
    brand      NVARCHAR(200) NOT NULL      -- '*' = tất cả brand
);

DELETE FROM dbo.rls_brand_access;

INSERT INTO dbo.rls_brand_access (role_name, user_email, brand) VALUES
    (N'Manager',       NULL, N'*'),
    (N'Brand Analyst', NULL, N'samsung'),
    (N'Brand Analyst', NULL, N'apple');

SELECT * FROM dbo.rls_brand_access;
