"""
TV3 | test_asa_writer.py
Kiểm tra quyền ghi (INSERT) của user 'asa_writer' vào dbo.event_metrics_30s.
Mục tiêu: Chứng minh nguyên tắc đặc quyền tối thiểu (Least Privilege) trước khi bàn giao cho TV2 (ASA).
Log kết quả được lưu tại: evidence/azure-sql/13_asa_writer_test.txt.
Hỗ trợ cả pyodbc lẫn sqlcmd (tự động điều hướng nếu môi trường bị chặn DLL).
"""

import os
import sys
import datetime
import subprocess
import getpass

SERVER = os.getenv("SQL_AZURE_SERVER", "sqlsrv-sales-gr03-tram01.database.windows.net")
DATABASE = os.getenv("SQL_AZURE_DB", "salesdb")
USER = os.getenv("SQL_ASA_USER", "asa_writer")
PASSWORD = os.getenv("SQL_ASA_PASSWORD")

def run_via_sqlcmd(pwd, log_print):
    log_print("[*] Phương thức kết nối: Microsoft SQLCMD Utility.")
    test_run_id = "tv3-writetest"
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    insert_ok = False
    select_ok = False
    delete_denied = False

    # 1. Kiểm tra quyền INSERT
    insert_query = (
        f"INSERT INTO dbo.event_metrics_30s (window_end, run_id, event_type, event_count, revenue) "
        f"VALUES ('{now_utc}', '{test_run_id}', 'view', 1, 0.0);"
    )
    cmd_insert = ["sqlcmd", "-S", SERVER, "-d", DATABASE, "-U", USER, "-P", pwd, "-Q", insert_query, "-b"]
    res_insert = subprocess.run(cmd_insert, capture_output=True, text=True)
    if res_insert.returncode == 0:
        log_print(f"[+] INSERT thành công 1 dòng thử nghiệm (run_id='{test_run_id}').")
        insert_ok = True
    else:
        log_print(f"[-] Lỗi INSERT: {res_insert.stderr or res_insert.stdout}".strip())
        return False, False, False

    # 2. Kiểm tra quyền SELECT (xác nhận dòng vừa ghi)
    select_query = (
        f"SET NOCOUNT ON; "
        f"SELECT window_end, run_id, event_type, event_count, revenue "
        f"FROM dbo.event_metrics_30s WHERE run_id = '{test_run_id}';"
    )
    cmd_select = ["sqlcmd", "-S", SERVER, "-d", DATABASE, "-U", USER, "-P", pwd, "-Q", select_query, "-s", ",", "-W"]
    res_select = subprocess.run(cmd_select, capture_output=True, text=True)
    lines = [line.strip() for line in res_select.stdout.strip().splitlines() if line.strip() and not line.startswith("---")]
    if lines:
        log_print(f"[+] SELECT xác nhận dòng vừa ghi: {lines[-1]}")
        select_ok = True
    else:
        log_print("[-] Không đọc lại được dòng vừa ghi.")

    # 3. Kiểm tra ràng buộc quyền DELETE (kỳ vọng bị từ chối)
    delete_query = f"DELETE FROM dbo.event_metrics_30s WHERE run_id = '{test_run_id}';"
    cmd_delete = ["sqlcmd", "-S", SERVER, "-d", DATABASE, "-U", USER, "-P", pwd, "-Q", delete_query, "-b"]
    res_delete = subprocess.run(cmd_delete, capture_output=True, text=True)
    if res_delete.returncode != 0:
        err_msg = (res_delete.stderr or res_delete.stdout).strip().replace("\n", " ")
        log_print(f"[+] CHỨNG MINH QUYỀN TỐI THIỂU: Lệnh DELETE bị từ chối thành công ({err_msg}).")
        delete_denied = True
    else:
        log_print("[-] CẢNH BÁO: Lệnh DELETE được thực thi thành công! Cần thu hồi quyền DELETE của asa_writer.")

    return insert_ok, select_ok, delete_denied

def run_via_pyodbc(pwd, log_print):
    import pyodbc
    log_print("[*] Phương thức kết nối: pyodbc Driver.")
    test_run_id = "tv3-writetest"
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    insert_ok = False
    select_ok = False
    delete_denied = False

    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server={SERVER},1433;"
        f"Database={DATABASE};"
        f"Uid={USER};"
        f"Pwd={pwd};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
    )

    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        log_print("[+] Kết nối Azure SQL Database thành công.")

        # 1. INSERT
        cursor.execute(
            "INSERT INTO dbo.event_metrics_30s (window_end, run_id, event_type, event_count, revenue) VALUES (?, ?, ?, ?, ?);",
            (now_utc, test_run_id, "view", 1, 0.0)
        )
        conn.commit()
        log_print(f"[+] INSERT thành công 1 dòng thử nghiệm (run_id='{test_run_id}').")
        insert_ok = True

        # 2. SELECT
        cursor.execute("SELECT window_end, run_id, event_type, event_count, revenue FROM dbo.event_metrics_30s WHERE run_id = ?;", (test_run_id,))
        row = cursor.fetchone()
        if row:
            log_print(f"[+] SELECT xác nhận dòng vừa ghi: {row}")
            select_ok = True

        # 3. DELETE
        try:
            cursor.execute("DELETE FROM dbo.event_metrics_30s WHERE run_id = ?;", (test_run_id,))
            conn.commit()
            log_print("[-] CẢNH BÁO: Lệnh DELETE được thực thi thành công! Cần thu hồi quyền DELETE của asa_writer.")
        except pyodbc.Error as del_err:
            log_print(f"[+] CHỨNG MINH QUYỀN TỐI THIỂU: Lệnh DELETE bị từ chối thành công: {del_err}")
            delete_denied = True

    return insert_ok, select_ok, delete_denied

def test_writer():
    # Nhập mật khẩu tương tác an toàn (không hiển thị mật khẩu trên terminal history)
    if not PASSWORD:
        try:
            pwd = getpass.getpass("Nhập mật khẩu của asa_writer (ẩn ký tự): ").strip()
        except Exception:
            pwd = input("Nhập mật khẩu của asa_writer: ").strip()
    else:
        pwd = PASSWORD

    if not pwd:
        print("[-] Mật khẩu không được để trống.")
        sys.exit(1)

    log_path = os.path.join(os.path.dirname(__file__), "..", "evidence", "azure-sql", "13_asa_writer_test.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as log_file:
        def log_print(msg):
            print(msg)
            log_file.write(msg + "\n")

        log_print(f"=== KIỂM THỬ QUYỀN TRUY CẬP ASA_WRITER - {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} ===")
        log_print(f"Máy chủ: {SERVER} | Cơ sở dữ liệu: {DATABASE} | Tài khoản: {USER}")

        insert_ok = False
        select_ok = False
        delete_denied = False

        # Ưu tiên pyodbc, tự động fallback sang sqlcmd nếu gặp hạn chế môi trường (DLL policy)
        try:
            import pyodbc  # noqa: F401
            insert_ok, select_ok, delete_denied = run_via_pyodbc(pwd, log_print)
        except (ImportError, Exception):
            insert_ok, select_ok, delete_denied = run_via_sqlcmd(pwd, log_print)

        # Đánh giá kết luận khách quan dựa trên kết quả thực tế của 3 bài test
        if insert_ok and select_ok and delete_denied:
            log_print("[*] KẾT LUẬN: User 'asa_writer' hoạt động đúng thiết kế (GHI ĐƯỢC, ĐỌC ĐƯỢC, KHÔNG XÓA ĐƯỢC).")
        else:
            log_print("[*] KẾT LUẬN: CÓ VẤN ĐỀ, xem các dòng cảnh báo/lỗi ở trên.")

    print(f"\n[+] Bằng chứng kiểm thử đã được lưu vào:\n    {log_path}")
    print(f"[*] Gợi ý: Dùng tài khoản admin trên Query Editor để xóa dòng test:\n    DELETE FROM dbo.event_metrics_30s WHERE run_id = 'tv3-writetest';")

if __name__ == "__main__":
    test_writer()
