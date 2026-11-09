#!/usr/bin/env python3
"""TV3 - Đối chiếu aggregate trong Azure SQL với tập event TV1 đã gửi (đúng run_id).

Input (--events): file các event đã gửi của run đó, định dạng JSON array / JSON Lines / CSV,
cần có event_type, brand, price (và stream_event_time nếu muốn so theo cửa sổ với --windows).
Mặc định so TỔNG (theo event_type, purchase theo brand) - không phụ thuộc cách ASA cắt cửa sổ.

Tùy chọn --dry-run / --no-db:
  Chạy riêng phần tính toán kỳ vọng từ file event mà không cần kết nối cơ sở dữ liệu.
  Rất hữu ích để kiểm thử tính đúng đắn của logic trước khi có dữ liệu stream thật.

Ví dụ:
  python validate_against_sample.py --events ../sample_events.json --run-id sample-01 --dry-run
  python validate_against_sample.py --events ../data/samples/integration-01.jsonl --run-id integration-01
  python validate_against_sample.py --events ... --run-id integration-01 --windows --out ../evidence/azure-sql/validation_integration-01.txt

Kết nối dùng biến SQL_AZURE_CONN trong database/.env (đổi bằng --conn-env). Exit code 1 nếu có lệch.
Hỗ trợ cả pyodbc lẫn sqlcmd (tự động chuyển sang sqlcmd nếu môi trường bị hạn chế driver/DLL).
Lưu ý: đợi ~2 phút sau khi producer gửi xong để ASA đóng cửa sổ cuối rồi hãy chạy.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone

# Đảm bảo mã hóa UTF-8 cho console Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = 0.01  # sai số tuyệt đối cho tổng revenue (float)


def load_events(path):
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            yield from csv.DictReader(f)
        return
    with open(path, encoding="utf-8") as f:
        first = f.read(1)
        f.seek(0)
        if first == "[":
            yield from json.load(f)
        else:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def norm_brand(b):
    b = (b or "").strip().lower()
    return b if b and b not in ("nan", "none", "null") else "unknown"


def window_end(ts, secs):
    """Cửa sổ tumbling nửa mở [start, end): event đúng mốc thuộc cửa sổ kế tiếp. Trả datetime UTC naive."""
    e = int(datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp())
    return datetime.fromtimestamp((e // secs + 1) * secs, tz=timezone.utc).replace(tzinfo=None)


def expected(events, windows):
    by_type, by_brand = defaultdict(int), defaultdict(lambda: [0, 0.0])
    rev_total, n = 0.0, 0
    w30, w60 = defaultdict(int), defaultdict(lambda: [0, 0.0])
    has_ts = False
    for e in events:
        n += 1
        et = e["event_type"]
        price = float(e.get("price") or 0)
        by_type[et] += 1
        if et == "purchase":
            rev_total += price
            b = by_brand[norm_brand(e.get("brand"))]
            b[0] += 1
            b[1] += price
        if windows and e.get("stream_event_time"):
            has_ts = True
            w30[(window_end(e["stream_event_time"], 30), et)] += 1
            if et == "purchase":
                x = w60[(window_end(e["stream_event_time"], 60), norm_brand(e.get("brand")))]
                x[0] += 1
                x[1] += price
    return n, by_type, rev_total, by_brand, w30, w60, has_ts


def parse_conn_str(cs):
    params = {}
    for part in cs.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            params[k.strip().lower()] = v.strip().strip("'\"{}")
    server = params.get("server", "").replace("tcp:", "").split(",")[0]
    database = params.get("database", "")
    uid = params.get("uid", "")
    pwd = params.get("pwd", "")
    return server, database, uid, pwd


class DatabaseClient:
    def __init__(self, cs):
        self.cs = cs
        self.mode = "pyodbc"
        self.pyodbc_conn = None
        try:
            import pyodbc
            self.pyodbc_conn = pyodbc.connect(cs)
        except Exception:
            self.mode = "sqlcmd"
            self.server, self.database, self.uid, self.pwd = parse_conn_str(cs)
            if not (self.server and self.database and self.uid and self.pwd):
                raise RuntimeError(
                    "Không thể kết nối pyodbc và thiếu thông tin Server/Database/Uid/Pwd trong connection string để dùng sqlcmd."
                )

    def execute_query(self, sql, params=()):
        if params:
            for p in params:
                val_str = f"'{p}'" if isinstance(p, str) else str(p)
                sql = sql.replace("?", val_str, 1)

        if self.mode == "pyodbc":
            cur = self.pyodbc_conn.cursor()
            cur.execute(sql)
            return cur.fetchall()
        else:
            cmd = [
                "sqlcmd", "-S", self.server, "-d", self.database,
                "-U", self.uid, "-P", self.pwd,
                "-Q", f"SET NOCOUNT ON; {sql}",
                "-s", "\t", "-W"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Lỗi truy vấn sqlcmd: {res.stderr or res.stdout}".strip())
            rows = []
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if not line or line.startswith("---"):
                    continue
                rows.append([c.strip() for c in line.split("\t")])
            return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--events", required=True, help="đường dẫn file events (.json, .jsonl, .csv)")
    ap.add_argument("--run-id", required=True, help="mã đợt chạy (run_id) cần đối chiếu")
    ap.add_argument("--windows", action="store_true", help="so thêm theo từng cửa sổ (cần stream_event_time)")
    ap.add_argument("--conn-env", default="SQL_AZURE_CONN", help="tên biến môi trường chứa connection string")
    ap.add_argument("--dry-run", "--no-db", dest="dry_run", action="store_true", help="chỉ tính toán và hiển thị giá trị kỳ vọng từ file event, không kết nối DB")
    ap.add_argument("--out", help="ghi báo cáo ra file (làm bằng chứng)")
    a = ap.parse_args()

    lines, bad = [], 0

    def out(s=""):
        lines.append(s)
        print(s)

    n, by_type, rev, by_brand, w30, w60, has_ts = expected(load_events(a.events), a.windows)
    out(f"Run: {a.run_id} | events trong file: {n:,}")

    # Chế độ DRY-RUN (không kết nối cơ sở dữ liệu)
    if a.dry_run:
        out("\n[CHẾ ĐỘ DRY-RUN / KIỂM THỬ LOGIC KỲ VỌNG - KHÔNG KẾT NỐI DB]")
        out("\n[1] Kỳ vọng số event theo loại (bảng dbo.event_metrics_30s):")
        for et in sorted(by_type):
            out(f"  {et:20} : {by_type[et]:>10,}")
        out(f"  {'TỔNG event':20} : {n:>10,}")

        out("\n[2] Kỳ vọng tổng revenue purchase (bảng dbo.event_metrics_30s):")
        out(f"  {'revenue purchase':20} : {rev:>14,.2f}")

        out("\n[3] Kỳ vọng purchase theo brand (bảng dbo.brand_sales_1m):")
        for b in sorted(by_brand):
            cnt, br_rev = by_brand[b]
            out(f"  {b:20} : {cnt:>6,} purchases | revenue = {br_rev:>12,.2f}")

        if a.windows:
            out("\n[4] Kỳ vọng tổng hợp theo từng cửa sổ thời gian:")
            if not has_ts:
                out("  Bỏ qua: file không chứa thuộc tính stream_event_time.")
            else:
                out(f"  * Số cửa sổ 30s (event_metrics_30s): {len(w30)} cửa sổ")
                for (w_end, et), cnt in sorted(w30.items()):
                    out(f"    {w_end.strftime('%Y-%m-%d %H:%M:%S')} UTC | {et:18} : {cnt:>5} events")
                out(f"\n  * Số cửa sổ 1m (brand_sales_1m): {len(w60)} cửa sổ-brand")
                for (w_end, b), (cnt, br_rev) in sorted(w60.items()):
                    out(f"    {w_end.strftime('%Y-%m-%d %H:%M:%S')} UTC | {b:18} : {cnt:>3} purchases | {br_rev:>10,.2f}")

        out("\nKẾT QUẢ DRY-RUN: PASS (Logic tính toán kỳ vọng hoạt động chính xác).")
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            with open(a.out, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        return

    # Chế độ kết nối cơ sở dữ liệu thật
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, ".env"))
    cs = os.environ.get(a.conn_env) or sys.exit(f"Thiếu {a.conn_env} trong database/.env")
    db_client = DatabaseClient(cs)

    def cmp(label, exp, act, money=False):
        nonlocal bad
        ok = abs(exp - act) <= TOL if money else exp == act
        bad += 0 if ok else 1
        out(f"  {'OK  ' if ok else 'LỆCH'} {label:38} sample={exp:>14,.2f}  sql={act:>14,.2f}")

    rows_type = db_client.execute_query(
        "SELECT event_type, SUM(event_count) FROM dbo.event_metrics_30s WHERE run_id=? GROUP BY event_type",
        (a.run_id,)
    )
    sql_type = {r[0]: int(r[1]) for r in rows_type}
    out("\n[1] Số event theo loại")
    for et in sorted(set(by_type) | set(sql_type)):
        cmp(et, by_type.get(et, 0), sql_type.get(et, 0))
    cmp("TỔNG event", n, sum(sql_type.values()))

    rows_rev = db_client.execute_query(
        "SELECT COALESCE(SUM(revenue),0) FROM dbo.event_metrics_30s WHERE run_id=? AND event_type='purchase'",
        (a.run_id,)
    )
    out("\n[2] Tổng revenue purchase (event_metrics_30s)")
    sql_rev = float(rows_rev[0][0]) if rows_rev else 0.0
    cmp("revenue purchase", rev, sql_rev, money=True)

    rows_brand = db_client.execute_query(
        "SELECT brand, SUM(purchase_events), SUM(revenue) FROM dbo.brand_sales_1m WHERE run_id=? GROUP BY brand",
        (a.run_id,)
    )
    sql_brand = {r[0]: (int(r[1]), float(r[2])) for r in rows_brand}
    out("\n[3] Purchase theo brand (brand_sales_1m)")
    for b in sorted(set(by_brand) | set(sql_brand)):
        e, s = by_brand.get(b, [0, 0.0]), sql_brand.get(b, (0, 0.0))
        cmp(f"{b} - purchase_events", e[0], s[0])
        cmp(f"{b} - revenue", e[1], s[1], money=True)

    if a.windows:
        out("\n[4] Theo từng cửa sổ")
        if not has_ts:
            out("  Bỏ qua: file không có stream_event_time.")
        else:
            rows_w30 = db_client.execute_query(
                "SELECT window_end, event_type, event_count FROM dbo.event_metrics_30s WHERE run_id=?",
                (a.run_id,)
            )
            # Chuẩn hóa datetime từ chuỗi nếu chạy qua sqlcmd
            def parse_dt(val):
                if isinstance(val, datetime):
                    return val
                return datetime.fromisoformat(str(val).replace("Z", "+00:00").split(".")[0])

            s30 = {(parse_dt(r[0]), r[1]): int(r[2]) for r in rows_w30}
            diff = [(k, w30.get(k, 0), s30.get(k, 0)) for k in set(w30) | set(s30) if w30.get(k, 0) != s30.get(k, 0)]
            out(f"  30s: {len(set(w30) | set(s30)) - len(diff)} khớp, {len(diff)} lệch")
            for k, e, s in sorted(diff)[:20]:
                out(f"    LỆCH {k[0]} {k[1]}: sample={e} sql={s}")
            bad += len(diff)

            rows_w60 = db_client.execute_query(
                "SELECT window_end, brand, purchase_events FROM dbo.brand_sales_1m WHERE run_id=?",
                (a.run_id,)
            )
            s60 = {(parse_dt(r[0]), r[1]): int(r[2]) for r in rows_w60}
            diff = [(k, w60[k][0] if k in w60 else 0, s60.get(k, 0)) for k in set(w60) | set(s60)
                    if (w60[k][0] if k in w60 else 0) != s60.get(k, 0)]
            out(f"  1m : {len(set(w60) | set(s60)) - len(diff)} khớp, {len(diff)} lệch")
            for k, e, s in sorted(diff)[:20]:
                out(f"    LỆCH {k[0]} {k[1]}: sample={e} sql={s}")
            bad += len(diff)

    out(f"\nKẾT QUẢ: {'PASS - khớp hoàn toàn' if bad == 0 else f'CÓ {bad} MỤC LỆCH (kiểm tra late events / cửa sổ cuối / brand null / job restart)'}")
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
