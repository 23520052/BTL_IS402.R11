#!/usr/bin/env python3
"""TV3 - Benchmark đọc/ghi SQL: Azure SQL vs SQL local (cùng một script, cùng workload).

Kết quả được APPEND vào read_write_results.csv (mỗi lần lặp 1 dòng) - không ước lượng, chỉ ghi số đo.
Bảng test nằm trong schema `bench` (không đụng dbo.event_metrics_30s / dbo.brand_sales_1m).

Ví dụ:
  python sql_benchmark.py --target azure --suite read     --sizes 10,100,1024 --note "S1 20DTU, SEA, laptop i5/16GB, wifi"
  python sql_benchmark.py --target azure --suite write    --note "..."
  python sql_benchmark.py --target azure --suite optimize --note "..."     # sau khi suite read xong
  python sql_benchmark.py --target local --suite read ...                  # lặp lại cho local
  python sql_benchmark.py --target azure --suite reset                     # xóa bảng bench

Chuỗi kết nối lấy từ database/.env: SQL_<TARGET>_CONN (azure | local | far).
"""
import argparse
import csv
import os
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone

import pyodbc
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, "..", ".env"))
CSV_PATH = os.path.join(HERE, "read_write_results.csv")
FIELDS = ["timestamp_utc", "target", "suite", "test", "size_label", "size_mb", "rows", "repeat",
          "duration_s", "rows_per_s", "mb_per_s", "dtu_cpu_max", "dtu_io_max", "dtu_log_max", "note"]

CHUNK = 250_000          # số dòng sinh mỗi lần INSERT phía server
R = "ABS(CAST(CHECKSUM(NEWID()) AS BIGINT))"   # random an toàn (tránh tràn ABS(int min))
ARGS = None


# ---------------------------------------------------------------- DDL / SQL
DDL = [
    "IF SCHEMA_ID('bench') IS NULL EXEC('CREATE SCHEMA bench')",
    """IF OBJECT_ID('bench.read_events','U') IS NULL
       CREATE TABLE bench.read_events (
           id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT pk_bench_read_events PRIMARY KEY CLUSTERED,
           event_time DATETIME2 NOT NULL, event_type VARCHAR(20) NOT NULL, product_id INT NOT NULL,
           brand VARCHAR(50) NOT NULL, price FLOAT NOT NULL, user_id INT NOT NULL,
           user_session CHAR(36) NOT NULL, payload CHAR(72) NOT NULL)""",
    """IF OBJECT_ID('bench.write_noidx','U') IS NULL
       CREATE TABLE bench.write_noidx (window_end DATETIME2 NOT NULL, run_id NVARCHAR(50) NOT NULL,
           event_type NVARCHAR(30) NOT NULL, event_count BIGINT NOT NULL, revenue FLOAT NOT NULL)""",
    """IF OBJECT_ID('bench.write_idx','U') IS NULL
       CREATE TABLE bench.write_idx (window_end DATETIME2 NOT NULL, run_id NVARCHAR(50) NOT NULL,
           event_type NVARCHAR(30) NOT NULL, event_count BIGINT NOT NULL, revenue FLOAT NOT NULL)""",
    """IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_bench_write_idx' AND object_id=OBJECT_ID('bench.write_idx'))
       CREATE INDEX ix_bench_write_idx ON bench.write_idx (window_end, run_id)""",
]

GEN_SQL = f"""
INSERT INTO bench.read_events (event_time, event_type, product_id, brand, price, user_id, user_session, payload)
SELECT TOP (?)
    DATEADD(SECOND, CAST({R} % 2678400 AS INT), '2019-10-01'),
    CHOOSE(1 + (ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) % 100) / 33, 'view', 'view', 'view', 'purchase'),
    CAST(1000978 + {R} % 59500000 AS INT),
    CHOOSE(1 + ((ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) / 7) % 10), 'samsung','apple','xiaomi','huawei','lenovo','acer','sony','lg','hp','bosch'),
    CAST(ROUND({R} % 257407 / 100.0, 2) AS FLOAT),
    CAST(33869381 + {R} % 530000000 AS INT),
    CONVERT(CHAR(36), NEWID()),
    CONVERT(CHAR(36), NEWID()) + CONVERT(CHAR(36), NEWID())
FROM sys.all_columns a CROSS JOIN sys.all_columns b
"""

READ_TESTS = [  # (tên, sql, là full-scan? -> tính MB/s)
    ("scan_count_sum", "SELECT COUNT_BIG(*), SUM(price) FROM bench.read_events", True),
    ("filter_range", "SELECT COUNT_BIG(*), SUM(price) FROM bench.read_events "
                     "WHERE event_time >= '2019-10-10' AND event_time < '2019-10-11'", False),
    ("group_by_brand", "SELECT brand, COUNT_BIG(*), SUM(price) FROM bench.read_events "
                       "WHERE event_type = 'purchase' GROUP BY brand", True),
]
FILTER_SQL = READ_TESTS[1][1]
SCAN_SQL = READ_TESTS[0][1]
INS_SQL = "INSERT INTO bench.{t} (window_end, run_id, event_type, event_count, revenue) VALUES (?,?,?,?,?)"


# ---------------------------------------------------------------- helpers
def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def connect(autocommit=True, retries=3):
    env = f"SQL_{ARGS.target.upper()}_CONN"
    cs = os.environ.get(env)
    if not cs:
        sys.exit(f"Thiếu biến {env} trong database/.env (xem database/.env.tv3.example)")
    for i in range(retries):
        try:
            return pyodbc.connect(cs, autocommit=autocommit)
        except pyodbc.Error as e:
            if i == retries - 1:
                raise
            print(f"  kết nối lỗi ({e.args[0] if e.args else e}), thử lại...", flush=True)
            time.sleep(3)


def note(extra=""):
    base = f"{ARGS.note}; py={platform.python_version()}; os={platform.system()}"
    return f"{extra}; {base}" if extra else base


def record(suite, test, label, mb, rows, repeat, dur, mb_s=None, dtu=(None, None, None), extra=""):
    row = {
        "timestamp_utc": utcnow().strftime("%Y-%m-%d %H:%M:%S"), "target": ARGS.target, "suite": suite,
        "test": test, "size_label": label, "size_mb": None if mb is None else round(mb, 1), "rows": rows,
        "repeat": repeat, "duration_s": round(dur, 4),
        "rows_per_s": round(rows / dur) if rows and dur > 0 else None,
        "mb_per_s": None if mb_s is None else round(mb_s, 2),
        "dtu_cpu_max": dtu[0], "dtu_io_max": dtu[1], "dtu_log_max": dtu[2], "note": note(extra),
    }
    new = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"  [{ARGS.target}] {test} {label or ''} #{repeat}: {dur:.3f}s"
          + (f", {row['rows_per_s']:,} rows/s" if row["rows_per_s"] else ""), flush=True)


def finish_dtu(conn, since):
    """Đỉnh CPU/IO/Log (%) từ sys.dm_db_resource_stats (chỉ có trên Azure SQL; local -> None)."""
    if ARGS.no_dtu:
        return (None, None, None)
    time.sleep(16)  # DMV cập nhật mỗi 15 giây
    try:
        cur = conn.cursor()
        cur.execute("SELECT MAX(avg_cpu_percent), MAX(avg_data_io_percent), MAX(avg_log_write_percent) "
                    "FROM sys.dm_db_resource_stats WHERE end_time >= ?", since)
        r = cur.fetchone()
        return tuple(None if x is None else round(float(x), 1) for x in r)
    except pyodbc.Error:
        return (None, None, None)


def timed(conn, sql, params=()):
    cur = conn.cursor()
    t = time.perf_counter()
    cur.execute(sql, *params)
    if cur.description:
        cur.fetchall()
    return time.perf_counter() - t


def pct(vals, p):
    s = sorted(vals)
    return s[max(0, -(-len(s) * p // 100) - 1)]


def label_of(mb):
    return f"{int(mb)}MB" if mb < 1024 else f"{mb / 1024:g}GB"


def setup(conn):
    for stmt in DDL:
        conn.cursor().execute(stmt)


def table_size(conn):
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(used_page_count),0)*8.0/1024, COALESCE(SUM(row_count),0) "
                "FROM sys.dm_db_partition_stats "
                "WHERE object_id = OBJECT_ID('bench.read_events') AND index_id IN (0,1)")
    mb, rows = cur.fetchone()
    return float(mb), int(rows)


def grow_to(conn, target_mb, label):
    mb, rows = table_size(conn)
    n = 0
    while mb < target_mb:
        n += 1
        if rows > 0:
            need = int((target_mb - mb) * rows / mb) + 1
            chunk = max(1000, min(CHUNK, need))
        else:
            chunk = 20_000 if target_mb < 50 else CHUNK
        t = time.perf_counter()
        conn.cursor().execute(GEN_SQL, chunk)
        dur = time.perf_counter() - t
        mb, rows = table_size(conn)
        record("read", "load_generate_chunk", label, mb, chunk, n, dur,
               extra=f"server-side generate; table now {mb:.0f}MB/{rows}rows")
    return mb, rows


# ---------------------------------------------------------------- suites
def suite_read():
    conn = connect()
    setup(conn)
    for s in [float(x) for x in ARGS.sizes.split(",")]:
        label = label_of(s)
        print(f"\n== Mốc {label}: nạp dữ liệu tới >= {s:.0f}MB ==", flush=True)
        mb, rows = grow_to(conn, s, label)
        print(f"== Kích thước thật: {mb:.1f}MB, {rows:,} dòng ==", flush=True)
        for name, sql, full in READ_TESTS:
            since, durs = utcnow(), [timed(conn, sql) for _ in range(ARGS.reps)]
            dtu = finish_dtu(conn, since)
            for i, d in enumerate(durs, 1):
                record("read", name, label, mb, rows, i, d, mb / d if full else None, dtu,
                       "warm cache; rows=số dòng của bảng")
        n = min(rows, 500_000)
        since, durs = utcnow(), []
        for _ in range(ARGS.reps):
            cur = conn.cursor()
            cur.arraysize = 10_000
            t = time.perf_counter()
            cur.execute("SELECT TOP (?) id,event_time,event_type,product_id,brand,price,user_id,user_session,payload "
                        "FROM bench.read_events ORDER BY id", n)
            got = 0
            while True:
                r = cur.fetchmany(10_000)
                if not r:
                    break
                got += len(r)
            durs.append(time.perf_counter() - t)
        dtu = finish_dtu(conn, since)
        for i, d in enumerate(durs, 1):
            record("read", "fetch_to_app", label, mb, got, i, d, (mb * got / rows) / d, dtu,
                   "rows kéo về client; MB/s ước theo kích thước lưu trữ trung bình/dòng")


def suite_optimize():
    conn = connect()
    setup(conn)
    mb, rows = table_size(conn)
    if rows == 0:
        sys.exit("Bảng bench.read_events trống: chạy --suite read trước.")
    label = label_of(mb)
    cur = conn.cursor()
    cur.execute("DROP INDEX IF EXISTS ix_bench_read_event_time ON bench.read_events")

    def run(test, sql, full=False, extra=""):
        since, durs = utcnow(), [timed(conn, sql) for _ in range(ARGS.reps)]
        dtu = finish_dtu(conn, since)
        _, r = table_size(conn)
        m, _ = table_size(conn)
        for i, d in enumerate(durs, 1):
            record("optimize", test, label_of(m), m, r, i, d, m / d if full else None, dtu, extra)

    print("\n== 1) Index: truy vấn lọc theo khoảng thời gian ==", flush=True)
    run("filter_range_noindex", FILTER_SQL)
    t = time.perf_counter()
    cur.execute("CREATE INDEX ix_bench_read_event_time ON bench.read_events (event_time) INCLUDE (price)")
    dur = time.perf_counter() - t
    cur.execute("SELECT SUM(used_page_count)*8.0/1024 FROM sys.dm_db_partition_stats "
                "WHERE object_id = OBJECT_ID('bench.read_events') AND index_id > 1")
    idx_mb = float(cur.fetchone()[0] or 0)
    record("optimize", "create_index", label, mb, rows, 1, dur, extra=f"index size={idx_mb:.1f}MB")
    run("filter_range_indexed", FILTER_SQL, extra=f"index size={idx_mb:.1f}MB")
    cur.execute("DROP INDEX ix_bench_read_event_time ON bench.read_events")

    print("\n== 2) Nén PAGE: dung lượng + tốc độ quét ==", flush=True)
    cur.execute("SELECT TOP 1 data_compression_desc FROM sys.partitions "
                "WHERE object_id = OBJECT_ID('bench.read_events') AND index_id = 1")
    state = cur.fetchone()[0]
    if state != "NONE":
        print(f"  Bảng đã nén ({state}); chạy --suite reset rồi nạp lại nếu cần đo lại.")
        return
    run("scan_uncompressed", SCAN_SQL, True, f"size before={mb:.1f}MB")
    t = time.perf_counter()
    cur.execute("ALTER TABLE bench.read_events REBUILD WITH (DATA_COMPRESSION = PAGE)")
    dur = time.perf_counter() - t
    mb2, _ = table_size(conn)
    record("optimize", "rebuild_page_compression", label, mb2, rows, 1, dur,
           extra=f"size {mb:.1f}MB -> {mb2:.1f}MB")
    run("scan_page_compressed", SCAN_SQL, True, f"size after={mb2:.1f}MB")


def gen_rows(n):
    base = datetime(2026, 11, 1)
    types = ("view", "cart", "remove_from_cart", "purchase")
    return [(base + timedelta(seconds=30 * (i // 4)), "bench-write", types[i % 4],
             random.randint(1, 2000), round(random.random() * 5000, 2)) for i in range(n)]


def get_done_tests():
    done = set()
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("target") == ARGS.target and row.get("suite") == "write":
                    done.add((row.get("test"), int(row.get("repeat") or 1)))
    return done


def run_with_retry(fn, tries=3):
    for k in range(1, tries + 1):
        try:
            return fn()
        except pyodbc.OperationalError as e:
            if k == tries:
                raise
            print(f"  [retry {k}/{tries - 1}] mất kết nối ({e.args[0] if e.args else e}), thử lại sau 10s...", flush=True)
            time.sleep(10)


def suite_write():
    ac = connect(autocommit=True)
    setup(ac)
    ac.close()
    done = get_done_tests()
    plan = [("write_noidx", 10_000, 1000), ("write_noidx", 100_000, 1000), ("write_noidx", 100_000, 100),
            ("write_noidx", 100_000, 10_000), ("write_idx", 10_000, 1000), ("write_idx", 100_000, 1000)]

    # 1) ghi từng dòng (autocommit)
    if ("write_single_n1000_noidx", 1) not in done:
        def one_single():
            c = connect(autocommit=True)
            try:
                c.cursor().execute("TRUNCATE TABLE bench.write_noidx")
                rows = gen_rows(1000)
                cur, lat, since = c.cursor(), [], utcnow()
                t0 = time.perf_counter()
                for r in rows:
                    t = time.perf_counter()
                    cur.execute(INS_SQL.format(t="write_noidx"), r)
                    lat.append((time.perf_counter() - t) * 1000)
                dur = time.perf_counter() - t0
                dtu = finish_dtu(c, since)
                record("write", "write_single_n1000_noidx", None, None, 1000, 1, dur, dtu=dtu,
                       extra=f"1 INSERT/dòng, autocommit; lat_p50_ms={statistics.median(lat):.2f}; lat_p95_ms={pct(lat, 95):.2f}")
            finally:
                c.close()
        run_with_retry(one_single)
    else:
        print("  [skip] write_single_n1000_noidx đã có kết quả trong CSV", flush=True)

    # 2) ghi theo batch: mỗi lần đo một kết nối riêng, tự thử lại nếu rớt mạng
    for table, n, batch in plan:
        tag = "idx" if table == "write_idx" else "noidx"
        test_name = f"write_b{batch}_n{n}_{tag}"
        for rep in range(1, ARGS.reps + 1):
            if (test_name, rep) in done:
                print(f"  [skip] {test_name} #{rep} đã có trong CSV", flush=True)
                continue

            def one_rep(table=table, n=n, batch=batch, rep=rep, test_name=test_name):
                conn = connect(autocommit=False)
                try:
                    conn.cursor().execute(f"TRUNCATE TABLE bench.{table}")
                    conn.commit()
                    rows = gen_rows(n)
                    cur = conn.cursor()
                    cur.fast_executemany = True
                    lat, since = [], utcnow()
                    t0 = time.perf_counter()
                    for i in range(0, n, batch):
                        t = time.perf_counter()
                        cur.executemany(INS_SQL.format(t=table), rows[i:i + batch])
                        conn.commit()
                        lat.append((time.perf_counter() - t) * 1000)
                    dur = time.perf_counter() - t0
                    dtu = finish_dtu(conn, since)
                    record("write", test_name, None, None, n, rep, dur, dtu=dtu,
                           extra=f"batch={batch}; batch_lat_p50_ms={statistics.median(lat):.1f}; batch_lat_p95_ms={pct(lat, 95):.1f}")
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

            run_with_retry(one_rep)


def suite_reset():
    conn = connect()
    conn.cursor().execute("DROP TABLE IF EXISTS bench.read_events, bench.write_noidx, bench.write_idx")
    print("Đã xóa bảng bench.*")


def main():
    global ARGS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True, help="azure | local | far")
    ap.add_argument("--suite", required=True, choices=["setup", "read", "optimize", "write", "reset"])
    ap.add_argument("--sizes", default="10,100,1024", help="mốc dung lượng MB cho suite read (1024 = 1GB)")
    ap.add_argument("--reps", type=int, default=3, help="số lần lặp mỗi phép đo")
    ap.add_argument("--note", default="", help="BẮT BUỘC: cấu hình đo (tier/CPU/RAM/mạng/vị trí client)")
    ap.add_argument("--no-dtu", action="store_true", help="bỏ qua chờ + đọc sys.dm_db_resource_stats")
    ARGS = ap.parse_args()
    if ARGS.target == "local":
        ARGS.no_dtu = True  # sys.dm_db_resource_stats chỉ có trên Azure SQL
    if ARGS.suite in ("read", "optimize", "write") and not ARGS.note:
        ap.error("--note là bắt buộc (ghi cấu hình để báo cáo nêu rõ điều kiện đo)")
    try:
        if ARGS.suite == "setup":
            setup(connect())
            print("Đã tạo bảng bench.*")
        else:
            {"read": suite_read, "optimize": suite_optimize, "write": suite_write, "reset": suite_reset}[ARGS.suite]()
    except KeyboardInterrupt:
        print("\nĐã dừng. Các dòng đã ghi vẫn nằm trong read_write_results.csv.")


if __name__ == "__main__":
    main()
