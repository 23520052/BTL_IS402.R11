-- ============================================================
-- TV3 | create_users.sql | Tạo 2 user DB quyền tối thiểu (contained users, SQL auth)
--   asa_writer : cho Stream Analytics ghi vào 2 bảng output (TV2)
--   pbi_reader : cho Power BI DirectQuery, CHỈ ĐỌC (TV4)
-- Chạy trong DB salesdb bằng tài khoản admin (Query editor).
-- !!! THAY 2 mật khẩu bên dưới trước khi chạy. KHÔNG lưu/commit bản đã thay mật khẩu. !!!
-- Mật khẩu: >= 12 ký tự, có hoa/thường/số/ký hiệu. Gửi cho TV2/TV4 qua kênh riêng, không đưa vào repo.
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'asa_writer')
    CREATE USER asa_writer WITH PASSWORD = '<<THAY_MAT_KHAU_ASA>>';

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'pbi_reader')
    CREATE USER pbi_reader WITH PASSWORD = '<<THAY_MAT_KHAU_PBI>>';

GRANT SELECT, INSERT ON SCHEMA::dbo TO asa_writer;
GRANT SELECT         ON SCHEMA::dbo TO pbi_reader;

-- Nếu TV2 báo "Test connection" của ASA bị lỗi quyền, bỏ comment dòng dưới (vẫn chỉ trong phạm vi DB này):
-- ALTER ROLE db_datawriter ADD MEMBER asa_writer;
