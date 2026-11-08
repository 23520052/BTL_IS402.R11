#!/usr/bin/env python3
"""TV3 - Vẽ biểu đồ từ read_write_results.csv và region_latency_results.csv -> charts/*.png
Chạy: python make_charts.py   (chỉ vẽ biểu đồ nào có dữ liệu)"""
import csv
import os
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "charts")
os.makedirs(OUT, exist_ok=True)


def load(name):
    p = os.path.join(HERE, name)
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def med(rows, key):
    v = [num(r[key]) for r in rows if num(r[key]) is not None]
    return statistics.median(v) if v else None


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), dpi=150)
    plt.close(fig)
    print("Đã vẽ", name)


rw = load("read_write_results.csv")
lat = load("region_latency_results.csv")

# 1) Thời gian quét toàn bảng theo dung lượng, mỗi target một đường
g = defaultdict(list)
for r in rw:
    if r["suite"] == "read" and r["test"] == "scan_count_sum":
        g[(r["target"], r["size_label"])].append(r)
if g:
    fig, ax = plt.subplots(figsize=(6, 4))
    for tg in sorted({k[0] for k in g}):
        pts = sorted((med(v, "size_mb"), med(v, "duration_s"), k[1]) for k, v in g.items() if k[0] == tg)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", label=tg)
        for x, y, lb in pts:
            ax.annotate(lb, (x, y), textcoords="offset points", xytext=(4, 4), fontsize=8)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Dung lượng bảng (MB, thang log)"); ax.set_ylabel("Thời gian quét COUNT/SUM (s, median)")
    ax.set_title("Tốc độ đọc theo dung lượng"); ax.legend(); ax.grid(True, alpha=.3)
    save(fig, "read_scan_time.png")

# 2) Throughput ghi (rows/s) theo cấu hình
w = defaultdict(list)
for r in rw:
    if r["suite"] == "write":
        w[(r["test"], r["target"])].append(r)
if w:
    tests = sorted({k[0] for k in w})
    targets = sorted({k[1] for k in w})
    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.8 / len(targets)
    for i, tg in enumerate(targets):
        ys = [med(w.get((t, tg), []), "rows_per_s") or 0 for t in tests]
        ax.bar([x + i * width for x in range(len(tests))], ys, width, label=tg)
    ax.set_xticks([x + width * (len(targets) - 1) / 2 for x in range(len(tests))])
    ax.set_xticklabels(tests, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("rows/s (median)"); ax.set_title("Tốc độ ghi theo cấu hình"); ax.legend()
    save(fig, "write_throughput.png")

# 3) Tối ưu: trước/sau (index, nén PAGE)
o = defaultdict(list)
for r in rw:
    if r["suite"] == "optimize" and r["test"] in ("filter_range_noindex", "filter_range_indexed",
                                                  "scan_uncompressed", "scan_page_compressed"):
        o[(r["test"], r["target"])].append(r)
if o:
    tests = ["filter_range_noindex", "filter_range_indexed", "scan_uncompressed", "scan_page_compressed"]
    targets = sorted({k[1] for k in o})
    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.8 / len(targets)
    for i, tg in enumerate(targets):
        ys = [med(o.get((t, tg), []), "duration_s") or 0 for t in tests]
        ax.bar([x + i * width for x in range(len(tests))], ys, width, label=tg)
    ax.set_xticks([x + width * (len(targets) - 1) / 2 for x in range(len(tests))])
    ax.set_xticklabels(tests, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Thời gian (s, median)"); ax.set_title("Tối ưu: index và nén PAGE"); ax.legend()
    save(fig, "optimize_before_after.png")

# 4) Region latency: p50 + p95 theo target/metric
if lat:
    metrics = ["tcp", "ping", "query", "login"]
    targets = sorted({r["target"] for r in lat})
    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.8 / len(targets)
    for i, tg in enumerate(targets):
        rows = {r["metric"]: r for r in lat if r["target"] == tg}   # lấy lần đo mới nhất mỗi metric
        p50 = [num(rows[m]["p50_ms"]) if m in rows else 0 for m in metrics]
        p95 = [num(rows[m]["p95_ms"]) if m in rows else 0 for m in metrics]
        xs = [x + i * width for x in range(len(metrics))]
        ax.bar(xs, p50, width, label=f"{tg} p50")
        ax.scatter(xs, p95, marker="_", s=250, color="black", zorder=3, label="p95" if i == 0 else None)
    ax.set_xticks([x + width * (len(targets) - 1) / 2 for x in range(len(metrics))])
    ax.set_xticklabels(metrics)
    ax.set_ylabel("ms"); ax.set_title("Độ trễ tới SQL server theo region"); ax.legend()
    save(fig, "region_latency.png")

if not (rw or lat):
    print("Chưa có CSV kết quả để vẽ.")
