#!/usr/bin/env python3
import csv
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "read_write_results.csv")

if len(sys.argv) < 3:
    print("Sử dụng: python clean_csv.py <target> <suite|all>")
    sys.exit(1)

target, suite = sys.argv[1], sys.argv[2]

if not os.path.exists(p):
    print(f"File {p} không tồn tại.")
    sys.exit(0)

shutil.copy(p, p + ".bak")

with open(p, newline="", encoding="utf-8") as f:
    rd = csv.DictReader(f)
    fields = rd.fieldnames
    rows = list(rd)

keep = [r for r in rows if not (r["target"] == target and (suite == "all" or r["suite"] == suite))]

with open(p, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(keep)

print(f"Đã xóa {len(rows) - len(keep)} dòng ({target}/{suite}); bản sao lưu: {p}.bak")
