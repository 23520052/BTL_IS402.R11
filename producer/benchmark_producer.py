#!/usr/bin/env python3
"""Benchmark the existing Producer CLI against Azure Event Hubs.

This script deliberately launches producer.py as a subprocess so the benchmark
uses the same CSV parsing, event conversion, batching, retry, checkpoint and
rate-limiting implementation as the team's current Producer.
"""

from __future__ import annotations

import argparse
import csv
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


SUCCESS_BATCH_RE = re.compile(
    r"Batch sent successfully \| events=(\d+) \| duration=([0-9.]+)s \| retries=(\d+)"
)
FAILED_BATCH_RE = re.compile(
    r"Batch failed permanently \| events=(\d+) \| duration=([0-9.]+)s \| retries=(\d+)"
)
ELAPSED_RE = re.compile(r"Elapsed time: ([0-9.]+) seconds")


def get_total_ram_gb() -> float | None:
    """Return total system RAM in GiB without requiring an extra dependency."""
    try:
        if hasattr(os, "sysconf"):
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return round((pages * page_size) / (1024 ** 3), 2)
    except (ValueError, OSError, AttributeError):
        pass

    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kib = int(line.split()[1])
                    return round(kib / (1024 ** 2), 2)
    except (OSError, ValueError, IndexError):
        pass

    try:
        import psutil  # Optional; Kaggle commonly has this installed.
        return round(psutil.virtual_memory().total / (1024 ** 3), 2)
    except Exception:
        return None


def get_runtime_location() -> str:
    if os.getenv("KAGGLE_KERNEL_RUN_TYPE") or Path("/kaggle").exists():
        return "Kaggle Notebook"
    return f"{platform.system()} ({platform.platform()})"


def count_payload_bytes(jsonl_path: Path) -> tuple[int, int]:
    """Count UTF-8 JSON payload bytes, excluding JSONL newline delimiters."""
    if not jsonl_path.exists():
        return 0, 0

    total_bytes = 0
    event_count = 0
    with jsonl_path.open("rb") as f:
        for line in f:
            payload = line.rstrip(b"\r\n")
            if payload:
                total_bytes += len(payload)
                event_count += 1
    return event_count, total_bytes


def parse_producer_log(log_path: Path) -> tuple[int, int, int, float | None]:
    """Return successful events, failed events, retries, producer elapsed."""
    sent = 0
    errors = 0
    retries = 0
    elapsed = None

    if not log_path.exists():
        return sent, errors, retries, elapsed

    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            success_match = SUCCESS_BATCH_RE.search(line)
            if success_match:
                sent += int(success_match.group(1))
                retries += int(success_match.group(3))
                continue

            failed_match = FAILED_BATCH_RE.search(line)
            if failed_match:
                errors += int(failed_match.group(1))
                retries += int(failed_match.group(3))
                continue

            elapsed_match = ELAPSED_RE.search(line)
            if elapsed_match:
                elapsed = float(elapsed_match.group(1))

    return sent, errors, retries, elapsed


def run_one(
    *,
    producer_script: Path,
    input_csv: Path,
    manifest: Path,
    mode: str,
    target_rate: int,
    repetition: int,
    max_events: int,
    batch_size: int,
    chunk_size: int,
    max_retries: int,
    base_backoff: float,
    max_backoff: float,
    run_dir: Path,
    eventhub_region: str,
) -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"bench-{stamp}-{uuid.uuid4().hex[:8]}"
    safe_run_id = re.sub(r"[^a-zA-Z0-9_-]", "_", run_id)

    log_path = run_dir / f"{safe_run_id}.log"
    jsonl_path = run_dir / f"{safe_run_id}.jsonl"
    checkpoint_path = run_dir / f"{safe_run_id}.checkpoint.json"

    command = [
        sys.executable,
        str(producer_script),
        "--input", str(input_csv),
        "--manifest", str(manifest),
        "--mode", mode,
        "--run-id", run_id,
        "--max-events", str(max_events),
        "--batch-size", str(batch_size),
        "--chunk-size", str(chunk_size),
        "--rate", str(target_rate),
        "--max-retries", str(max_retries),
        "--base-backoff", str(base_backoff),
        "--max-backoff", str(max_backoff),
        "--checkpoint", str(checkpoint_path),
        "--jsonl-output", str(jsonl_path),
    ]

    print(
        f"\n[Benchmark] rate={target_rate} events/s | "
        f"repeat={repetition} | run_id={run_id}"
    )
    start_wall = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as log_file:
        completed = subprocess.run(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(producer_script.parent),
            check=False,
        )
    wall_duration = time.perf_counter() - start_wall

    sent_from_log, errors, retries, producer_elapsed = parse_producer_log(log_path)
    jsonl_events, payload_bytes = count_payload_bytes(jsonl_path)

    # The producer's batch-success logs are the send acknowledgement count.
    # JSONL is an independent payload-size measurement for those sent events.
    events_sent = sent_from_log
    duration = producer_elapsed if producer_elapsed and producer_elapsed > 0 else wall_duration
    actual_eps = events_sent / duration if duration > 0 else 0.0
    throughput_mb_s = (payload_bytes / 1_000_000) / duration if duration > 0 else 0.0

    status = "completed" if completed.returncode == 0 else "failed"
    if jsonl_events != events_sent:
        status += "_jsonl_count_mismatch"

    print(
        f"[Result] status={status}, sent={events_sent}, errors={errors}, "
        f"retries={retries}, duration={duration:.2f}s, "
        f"actual={actual_eps:.2f} events/s, payload={payload_bytes:,} bytes"
    )

    return {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "mode": mode,
        "target_rate_events_per_sec": target_rate,
        "repetition": repetition,
        "max_events": max_events,
        "batch_size": batch_size,
        "chunk_size": chunk_size,
        "events_sent": events_sent,
        "events_error": errors,
        "retries": retries,
        "duration_seconds": round(duration, 4),
        "actual_events_per_sec": round(actual_eps, 4),
        "payload_bytes": payload_bytes,
        "payload_MB_per_sec": round(throughput_mb_s, 6),
        "jsonl_event_count": jsonl_events,
        "process_wall_seconds": round(wall_duration, 4),
        "process_return_code": completed.returncode,
        "status": status,
        "cpu_count": os.cpu_count(),
        "ram_total_GiB": get_total_ram_gb(),
        "runtime_location": get_runtime_location(),
        "python_version": platform.python_version(),
        "operating_system": platform.platform(),
        "eventhub_region": eventhub_region or "not_recorded",
        "log_file": str(log_path),
        "payload_jsonl_file": str(jsonl_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark the existing producer.py at multiple target event rates."
    )
    here = Path(__file__).resolve().parent
    parser.add_argument("--producer", type=Path, default=here / "producer.py")
    parser.add_argument("--input", type=Path, required=True, help="Path to 2019-Oct.csv")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to manifest.json")
    parser.add_argument("--mode", choices=["dev", "demo"], default="dev")
    parser.add_argument("--rates", type=int, nargs="+", default=[100, 500, 1000, 2000])
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--max-events", type=int, default=10000)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--chunk-size", type=int, default=10000)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--base-backoff", type=float, default=1.0)
    parser.add_argument("--max-backoff", type=float, default=30.0)
    parser.add_argument("--eventhub-region", default="", help="Azure region, e.g. Southeast Asia")
    parser.add_argument("--output", type=Path, default=Path("producer_metrics.csv"))
    parser.add_argument("--run-dir", type=Path, default=Path("benchmark_runs"))
    args = parser.parse_args()

    if args.repetitions < 1:
        parser.error("--repetitions must be at least 1")
    if args.max_events < 1 or args.batch_size < 1 or args.chunk_size < 1:
        parser.error("--max-events, --batch-size and --chunk-size must be positive")
    if not args.rates or any(rate <= 0 for rate in args.rates):
        parser.error("All target rates must be positive integers")
    if args.max_retries < 0 or args.base_backoff <= 0 or args.max_backoff < args.base_backoff:
        parser.error("Invalid retry/backoff configuration")
    return args


def main() -> int:
    args = parse_args()
    producer_script = args.producer.resolve()
    input_csv = args.input.resolve()
    manifest = args.manifest.resolve()

    for path, label in [
        (producer_script, "Producer script"),
        (input_csv, "Input CSV"),
        (manifest, "Manifest"),
    ]:
        if not path.is_file():
            raise FileNotFoundError(f"{label} not found: {path}")

    # Producer reads credentials from these environment variables.
    missing = [
        name for name in ("EVENTHUB_CONNECTION_STR", "EVENTHUB_NAME")
        if not os.getenv(name)
    ]
    if missing:
        raise EnvironmentError(
            "Missing environment variables: " + ", ".join(missing)
        )

    args.run_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    print("========== PRODUCER BENCHMARK ==========")
    print(f"Producer: {producer_script}")
    print(f"Input CSV: {input_csv}")
    print(f"Manifest: {manifest}")
    print(f"Rates: {args.rates}")
    print(f"Repetitions per rate: {args.repetitions}")
    print(f"Max events per run: {args.max_events}")
    print(f"Batch size: {args.batch_size}")
    print(f"Event Hubs region: {args.eventhub_region or 'not recorded'}")

    rows = []
    for rate in args.rates:
        for repetition in range(1, args.repetitions + 1):
            row = run_one(
                producer_script=producer_script,
                input_csv=input_csv,
                manifest=manifest,
                mode=args.mode,
                target_rate=rate,
                repetition=repetition,
                max_events=args.max_events,
                batch_size=args.batch_size,
                chunk_size=args.chunk_size,
                max_retries=args.max_retries,
                base_backoff=args.base_backoff,
                max_backoff=args.max_backoff,
                run_dir=args.run_dir.resolve(),
                eventhub_region=args.eventhub_region,
            )
            rows.append(row)

    fieldnames = list(rows[0].keys()) if rows else []
    with args.output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n========== BENCHMARK FINISHED ==========")
    print(f"Metrics CSV: {args.output.resolve()}")
    print(f"Individual logs and JSONL payloads: {args.run_dir.resolve()}")
    print(f"Total runs: {len(rows)}")
    print("Note: inspect failed runs and JSONL count mismatches before reporting results.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"BENCHMARK ERROR: {exc}", file=sys.stderr)
        raise
