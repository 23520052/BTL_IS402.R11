#!/usr/bin/env python3
"""TV3 - Đối chiếu aggregate trong Azure SQL với tập event TV1 đã gửi (đúng run_id).

Input (--events): file các event đã gửi của run đó, định dạng JSON array / JSON Lines / CSV,
cần có event_type, brand, price (và stream_event_time nếu muốn so theo cửa sổ với --windows).
Mặc định so TỔNG (theo event_type, purchase theo brand) - không phụ thuộc cách ASA cắt cửa sổ.

Ví dụ:
  python validate_against_sample.py --events ../data/samples/integration-01.jsonl --run-id integration-01
  python validate_against_sample.py --events ... --run-id integration-01 --windows --out ../evidence/azure-sql/validation_integration-01.txt
Kết nối dùng biến SQL_AZURE_CONN trong database/.env (đổi bằng --conn-env). Exit code 1 nếu có lệch.
Lưu ý: đợi ~2 phút sau khi producer gửi xong để ASA đóng cửa sổ cuối rồi hãy chạy.
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--events", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--windows", action="store_true", help="so thêm theo từng cửa sổ (cần stream_event_time)")
    ap.add_argument("--conn-env", default="SQL_AZURE_CONN")
    ap.add_argument("--out", help="ghi báo cáo ra file (làm bằng chứng)")
    a = ap.parse_args()

    import pyodbc
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, ".env"))
    cs = os.environ.get(a.conn_env) or sys.exit(f"Thiếu {a.conn_env} trong database/.env")
    cur = pyodbc.connect(cs).cursor()

    lines, bad = [], 0

    def out(s=""):
        lines.append(s)
        print(s)

    def cmp(label, exp, act, money=False):
        nonlocal bad
        ok = abs(exp - act) <= TOL if money else exp == act
        bad += 0 if ok else 1
        out(f"  {'OK  ' if ok else 'LỆCH'} {label:38} sample={exp:>14,.2f}  sql={act:>14,.2f}")

    n, by_type, rev, by_brand, w30, w60, has_ts = expected(load_events(a.events), a.windows)
    out(f"Run: {a.run_id} | events trong file: {n:,}")

    cur.execute("SELECT event_type, SUM(event_count) FROM dbo.event_metrics_30s WHERE run_id=? GROUP BY event_type", a.run_id)
    sql_type = {r[0]: int(r[1]) for r in cur.fetchall()}
    out("\n[1] Số event theo loại")
    for et in sorted(set(by_type) | set(sql_type)):
        cmp(et, by_type.get(et, 0), sql_type.get(et, 0))
    cmp("TỔNG event", n, sum(sql_type.values()))

    cur.execute("SELECT COALESCE(SUM(revenue),0) FROM dbo.event_metrics_30s WHERE run_id=? AND event_type='purchase'", a.run_id)
    out("\n[2] Tổng revenue purchase (event_metrics_30s)")
    cmp("revenue purchase", rev, float(cur.fetchone()[0]), money=True)

    cur.execute("SELECT brand, SUM(purchase_events), SUM(revenue) FROM dbo.brand_sales_1m WHERE run_id=? GROUP BY brand", a.run_id)
    sql_brand = {r[0]: (int(r[1]), float(r[2])) for r in cur.fetchall()}
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
            cur.execute("SELECT window_end, event_type, event_count FROM dbo.event_metrics_30s WHERE run_id=?", a.run_id)
            s30 = {(r[0], r[1]): int(r[2]) for r in cur.fetchall()}
            diff = [(k, w30.get(k, 0), s30.get(k, 0)) for k in set(w30) | set(s30) if w30.get(k, 0) != s30.get(k, 0)]
            out(f"  30s: {len(set(w30) | set(s30)) - len(diff)} khớp, {len(diff)} lệch")
            for k, e, s in sorted(diff)[:20]:
                out(f"    LỆCH {k[0]} {k[1]}: sample={e} sql={s}")
            bad += len(diff)
            cur.execute("SELECT window_end, brand, purchase_events FROM dbo.brand_sales_1m WHERE run_id=?", a.run_id)
            s60 = {(r[0], r[1]): int(r[2]) for r in cur.fetchall()}
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
