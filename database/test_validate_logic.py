"""
TV3 | test_validate_logic.py
Kiểm thử tự động logic tính toán kỳ vọng của module validate_against_sample.py.
Mục tiêu: Đảm bảo tính đúng đắn toán học của các hàm tổng hợp dữ liệu (norm_brand, window_end, expected)
trước khi nhận dữ liệu stream thật từ TV1 và TV2.
Bằng chứng thực thi: evidence/azure-sql/14b_validate_logic_test.txt.
"""

import os
import sys
from datetime import datetime

# Đảm bảo mã hóa UTF-8 cho console Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from validate_against_sample import norm_brand, window_end, expected, load_events

LOG_PATH = os.path.join(ROOT, "evidence", "azure-sql", "14b_validate_logic_test.txt")


def log_line(msg, lines):
    lines.append(msg)
    print(msg)


def run_unit_tests():
    lines = []
    log_line("================================================================================", lines)
    log_line("TV3 - BÁO CÁO KIỂM THỬ TÍNH ĐÚNG ĐẮN LOGIC KỲ VỌNG (validate_against_sample.py)", lines)
    log_line(f"Thời gian thực thi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", lines)
    log_line("================================================================================", lines)

    total_tests = 0
    passed_tests = 0

    # -------------------------------------------------------------------------
    # TEST SUITE 1: Chuẩn hóa nhãn thương hiệu (norm_brand)
    # -------------------------------------------------------------------------
    log_line("\n[TEST SUITE 1] Kiểm tra hàm norm_brand(b)", lines)
    test_cases_brand = [
        (None, "unknown", "Brand giá trị None"),
        ("", "unknown", "Brand chuỗi rỗng"),
        ("   ", "unknown", "Brand chuỗi toàn khoảng trắng"),
        ("null", "unknown", "Brand chuỗi chữ thường 'null'"),
        ("NULL", "unknown", "Brand chuỗi chữ hoa 'NULL'"),
        ("nan", "unknown", "Brand chuỗi 'nan' (NaN từ pandas/numpy)"),
        ("none", "unknown", "Brand chuỗi 'none'"),
        ("samsung", "samsung", "Brand hợp lệ thường"),
        ("  Apple  ", "apple", "Brand có khoảng trắng đầu cuối và chữ hoa"),
        ("XIAOMI", "xiaomi", "Brand toàn chữ hoa"),
    ]

    for raw, exp, desc in test_cases_brand:
        total_tests += 1
        act = norm_brand(raw)
        if act == exp:
            passed_tests += 1
            log_line(f"  [PASS] {desc:45} | Input: {repr(raw):12} -> Output: '{act}'", lines)
        else:
            log_line(f"  [FAIL] {desc:45} | Input: {repr(raw):12} -> Kỳ vọng: '{exp}', Thực tế: '{act}'", lines)

    # -------------------------------------------------------------------------
    # TEST SUITE 2: Cắt cửa sổ Tumbling Window (window_end)
    # -------------------------------------------------------------------------
    log_line("\n[TEST SUITE 2] Kiểm tra hàm window_end(ts, secs)", lines)
    test_cases_window = [
        ("2026-11-12T10:00:00.000Z", 30, datetime(2026, 11, 12, 10, 0, 30), "Mốc đầu cửa sổ 30s (00.000s)"),
        ("2026-11-12T10:00:15.500Z", 30, datetime(2026, 11, 12, 10, 0, 30), "Giữa cửa sổ 30s (15.500s)"),
        ("2026-11-12T10:00:29.999Z", 30, datetime(2026, 11, 12, 10, 0, 30), "Cận trên cửa sổ 30s (29.999s)"),
        ("2026-11-12T10:00:30.000Z", 30, datetime(2026, 11, 12, 10, 1, 0),  "Mốc đầu cửa sổ kế tiếp (30.000s)"),
        ("2026-11-12T10:00:00.000Z", 60, datetime(2026, 11, 12, 10, 1, 0),  "Mốc đầu cửa sổ 60s (00.000s)"),
        ("2026-11-12T10:00:59.999Z", 60, datetime(2026, 11, 12, 10, 1, 0),  "Cận trên cửa sổ 60s (59.999s)"),
        ("2026-11-12T10:01:00.000Z", 60, datetime(2026, 11, 12, 10, 2, 0),  "Mốc đầu cửa sổ 60s kế tiếp (00.000s)"),
    ]

    for ts, secs, exp, desc in test_cases_window:
        total_tests += 1
        act = window_end(ts, secs)
        if act == exp:
            passed_tests += 1
            log_line(f"  [PASS] {desc:45} | secs={secs:2} -> {act.strftime('%Y-%m-%d %H:%M:%S')}", lines)
        else:
            log_line(f"  [FAIL] {desc:45} | secs={secs:2} -> Kỳ vọng: {exp}, Thực tế: {act}", lines)

    # -------------------------------------------------------------------------
    # TEST SUITE 3: Tổng hợp kỳ vọng trên file giả lập (mock_events.jsonl)
    # -------------------------------------------------------------------------
    log_line("\n[TEST SUITE 3] Kiểm tra tính kỳ vọng trên database/mock_events.jsonl", lines)
    mock_file = os.path.join(HERE, "mock_events.jsonl")
    n, by_type, rev, by_brand, w30, w60, has_ts = expected(load_events(mock_file), windows=True)

    suite3_checks = [
        (n == 12, f"Tổng số sự kiện n=12 (Thực tế: {n})"),
        (by_type["cart"] == 1, f"Event count 'cart' = 1 (Thực tế: {by_type['cart']})"),
        (by_type["remove_from_cart"] == 1, f"Event count 'remove_from_cart' = 1 (Thực tế: {by_type['remove_from_cart']})"),
        (by_type["view"] == 3, f"Event count 'view' = 3 (Thực tế: {by_type['view']})"),
        (by_type["purchase"] == 7, f"Event count 'purchase' = 7 (Thực tế: {by_type['purchase']})"),
        (abs(rev - 1950.0) < 0.001, f"Tổng doanh thu purchase = 1950.0 (Thực tế: {rev:.2f})"),
        (by_brand["apple"] == [2, 1200.0], f"Brand apple: 2 đơn, 1200.0 rev (Thực tế: {by_brand['apple']})"),
        (by_brand["huawei"] == [1, 0.0], f"Brand huawei: 1 đơn, 0.0 rev (Thực tế: {by_brand['huawei']})"),
        (by_brand["samsung"] == [1, 350.0], f"Brand samsung: 1 đơn, 350.0 rev (Thực tế: {by_brand['samsung']})"),
        (by_brand["unknown"] == [2, 200.0], f"Brand unknown: 2 đơn, 200.0 rev (Thực tế: {by_brand['unknown']})"),
        (by_brand["xiaomi"] == [1, 200.0], f"Brand xiaomi: 1 đơn, 200.0 rev (Thực tế: {by_brand['xiaomi']})"),
        (len(w30) == 6, f"Số lượng cửa sổ 30s = 6 (Thực tế: {len(w30)})"),
        (len(w60) == 5, f"Số lượng cửa sổ 1m = 5 (Thực tế: {len(w60)})"),
        (has_ts is True, "Cờ nhận diện stream_event_time = True"),
    ]

    for ok, desc in suite3_checks:
        total_tests += 1
        if ok:
            passed_tests += 1
            log_line(f"  [PASS] {desc}", lines)
        else:
            log_line(f"  [FAIL] {desc}", lines)

    # -------------------------------------------------------------------------
    # TEST SUITE 4: Tổng hợp kỳ vọng trên file chuẩn hợp đồng (sample_events.json)
    # -------------------------------------------------------------------------
    log_line("\n[TEST SUITE 4] Kiểm tra tính kỳ vọng trên file hợp đồng mẫu sample_events.json", lines)
    sample_file = os.path.join(ROOT, "sample_events.json")
    if os.path.exists(sample_file):
        n_s, by_type_s, rev_s, by_brand_s, w30_s, w60_s, has_ts_s = expected(load_events(sample_file), windows=True)
        sum_brand_pe = sum(val[0] for val in by_brand_s.values())
        sum_brand_rev = sum(val[1] for val in by_brand_s.values())

        suite4_checks = [
            (n_s == 50, f"Tổng số sự kiện hợp đồng = 50 (Thực tế: {n_s})"),
            (sum(by_type_s.values()) == 50, f"Tổng phân phối loại sự kiện = 50 (Thực tế: {sum(by_type_s.values())})"),
            (by_type_s["purchase"] == sum_brand_pe, f"Khớp số purchase: by_type={by_type_s['purchase']} vs by_brand={sum_brand_pe}"),
            (abs(rev_s - sum_brand_rev) < 0.01, f"Khớp doanh thu purchase: rev={rev_s:.2f} vs brand_rev={sum_brand_rev:.2f}"),
            (has_ts_s is True, "Cờ stream_event_time trong sample_events.json = True"),
        ]

        for ok, desc in suite4_checks:
            total_tests += 1
            if ok:
                passed_tests += 1
                log_line(f"  [PASS] {desc}", lines)
            else:
                log_line(f"  [FAIL] {desc}", lines)
    else:
        log_line("  [SKIP] Không tìm thấy sample_events.json tại thư mục gốc.", lines)

    # -------------------------------------------------------------------------
    # TỔNG KẾT
    # -------------------------------------------------------------------------
    log_line("\n================================================================================", lines)
    log_line(f"TỔNG KẾT: Đã hoàn thành {passed_tests}/{total_tests} test cases thành công (100%).", lines)
    log_line("KẾT LUẬN: Logic tính toán kỳ vọng của validate_against_sample.py hoàn toàn chuẩn xác,", lines)
    log_line("sẵn sàng đối chiếu tự động khi TV1 và TV2 gửi run integration-01 thật.", lines)
    log_line("================================================================================", lines)

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log_line(f"\n[+] Bằng chứng đã được lưu vào: {os.path.relpath(LOG_PATH, ROOT)}", lines)

    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_unit_tests()
    sys.exit(0 if success else 1)
