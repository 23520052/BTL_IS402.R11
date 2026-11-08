#!/usr/bin/env python3
"""TV3 - Đo độ trễ tới các SQL server đặt ở region khác nhau, từ CÙNG một client.

Round-robin giữa các target (xen kẽ từng mẫu) để cùng điều kiện mạng. Mỗi mẫu đo:
  tcp   : thời gian TCP connect tới server:1433 (xấp xỉ RTT; Azure SQL không trả lời ICMP ping)
  ping  : SELECT 1 trên kết nối đang mở (1 round trip SQL)
  query : SELECT TOP 20 * FROM dbo.event_metrics_30s ORDER BY window_end DESC (truy vấn kiểu ứng dụng)
  login : mở kết nối mới + đăng nhập (đo ít mẫu hơn vì chậm)
Kết quả (min/p50/p95/max/mean, ms) APPEND vào region_latency_results.csv.

Ví dụ:
  python region_latency.py --targets azure,far --regions azure=southeastasia,far=eastus \
         --client "Laptop HCMC, wifi nhà" --samples 100
Chạy lại từ client khác (vd VM ở region khác) với --client khác để có thêm góc nhìn.
Mỗi DB đích phải có bảng dbo.event_metrics_30s (chạy schema.sql + indexes.sql + seed_data.sql trên DB đó).
"""
import argparse
import csv
import math
import os
import re
import socket
import statistics
import sys
import time
from datetime import datetime, timezone

import pyodbc
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, "..", ".env"))
CSV_PATH = os.path.join(HERE, "region_latency_results.csv")
FIELDS = ["timestamp_utc", "client", "target", "server_host", "server_region", "metric", "n",
          "min_ms", "p50_ms", "p95_ms", "max_ms", "mean_ms", "note"]
QUERY = "SELECT TOP 20 * FROM dbo.event_metrics_30s ORDER BY window_end DESC"


def pct(vals, p):
    s = sorted(vals)
    return s[max(0, math.ceil(len(s) * p / 100) - 1)]


def parse_server(cs):
    m = re.search(r"Server=(?:tcp:)?([^,;]+)(?:,(\d+))?", cs, re.I)
    return m.group(1), int(m.group(2) or 1433)


def ms(t0):
    return (time.perf_counter() - t0) * 1000


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--targets", required=True, help="vd azure,far (đọc SQL_<TARGET>_CONN trong database/.env)")
    ap.add_argument("--regions", default="", help="vd azure=southeastasia,far=eastus")
    ap.add_argument("--client", required=True, help="mô tả client: máy/vị trí/mạng")
    ap.add_argument("--samples", type=int, default=100)
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    targets = [t.strip() for t in a.targets.split(",") if t.strip()]
    regions = dict(kv.split("=", 1) for kv in a.regions.split(",") if "=" in kv)
    cs, host, port, conn, cur = {}, {}, {}, {}, {}
    for t in targets:
        cs[t] = os.environ.get(f"SQL_{t.upper()}_CONN") or sys.exit(f"Thiếu SQL_{t.upper()}_CONN trong database/.env")
        host[t], port[t] = parse_server(cs[t])
        conn[t] = pyodbc.connect(cs[t], autocommit=True)
        cur[t] = conn[t].cursor()
    data = {t: {"tcp": [], "ping": [], "query": [], "login": []} for t in targets}

    print(f"Đo {a.samples} mẫu (+{a.warmup} khởi động) tới {targets} ...", flush=True)
    for i in range(a.warmup + a.samples):
        for t in targets:
            t0 = time.perf_counter()
            s = socket.create_connection((host[t], port[t]), timeout=10)
            v_tcp = ms(t0)
            s.close()
            t0 = time.perf_counter()
            cur[t].execute("SELECT 1")
            cur[t].fetchone()
            v_ping = ms(t0)
            t0 = time.perf_counter()
            cur[t].execute(QUERY)
            cur[t].fetchall()
            v_q = ms(t0)
            if i >= a.warmup:
                data[t]["tcp"].append(v_tcp)
                data[t]["ping"].append(v_ping)
                data[t]["query"].append(v_q)
    for _ in range(min(a.samples, 30)):
        for t in targets:
            t0 = time.perf_counter()
            c = pyodbc.connect(cs[t], autocommit=True)
            data[t]["login"].append(ms(t0))
            c.close()

    new = not os.path.exists(CSV_PATH)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'target':8} {'region':16} {'metric':6} {'n':>4} {'min':>8} {'p50':>8} {'p95':>8} {'max':>8}  (ms)")
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for t in targets:
            for metric, v in data[t].items():
                row = {"timestamp_utc": now, "client": a.client, "target": t, "server_host": host[t],
                       "server_region": regions.get(t, ""), "metric": metric, "n": len(v),
                       "min_ms": round(min(v), 2), "p50_ms": round(pct(v, 50), 2), "p95_ms": round(pct(v, 95), 2),
                       "max_ms": round(max(v), 2), "mean_ms": round(statistics.mean(v), 2), "note": a.note}
                w.writerow(row)
                print(f"{t:8} {row['server_region']:16} {metric:6} {row['n']:>4} {row['min_ms']:>8} "
                      f"{row['p50_ms']:>8} {row['p95_ms']:>8} {row['max_ms']:>8}")


if __name__ == "__main__":
    main()
