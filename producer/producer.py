import argparse
import json
import logging
import math
import os
import random
import re
import sys
import tempfile
import time
import uuid

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from azure.eventhub import EventData, EventHubProducerClient
from azure.eventhub.exceptions import EventHubError


# ============================================================
# CONFIGURATION
# ============================================================

SOURCE_COLUMNS = [
    "event_time",
    "event_type",
    "product_id",
    "category_id",
    "category_code",
    "brand",
    "price",
    "user_id",
    "user_session",
]

SUPPORTED_EVENT_TYPES = {"view", "cart", "purchase"}
SUPPORTED_MODES = {"dev", "demo"}

DEFAULT_MAX_EVENTS = 100
DEFAULT_BATCH_SIZE = 50
DEFAULT_CHUNK_SIZE = 10_000
DEFAULT_RATE = 100.0
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_BACKOFF = 1.0
DEFAULT_MAX_BACKOFF = 30.0

LOG_DIR = Path("logs")
CHECKPOINT_DIR = Path("checkpoints")


# ============================================================
# LOGGING
# ============================================================

def setup_logging(run_id: str) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    safe_run_id = re.sub(r"[^a-zA-Z0-9_-]", "_", run_id)
    log_file = LOG_DIR / f"producer_{safe_run_id}.log"

    logger = logging.getLogger("producer")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

def get_eventhub_config():
    connection_str = os.getenv("EVENTHUB_CONNECTION_STR")
    eventhub_name = os.getenv("EVENTHUB_NAME")

    missing = []

    if not connection_str:
        missing.append("EVENTHUB_CONNECTION_STR")

    if not eventhub_name:
        missing.append("EVENTHUB_NAME")

    if missing:
        raise EnvironmentError(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    return connection_str, eventhub_name


# ============================================================
# DATA CONVERSION
# ============================================================

def to_nullable_string(value):
    if pd.isna(value):
        return None

    return str(value)


def to_utc_iso(value) -> str:
    timestamp = pd.to_datetime(
        value,
        utc=True,
        errors="raise",
    )

    if pd.isna(timestamp):
        raise ValueError("event_time is empty or invalid")

    return timestamp.isoformat().replace("+00:00", "Z")



def build_event(
    row,
    run_id: str,
    source_file: str,
    source_row_index: int,
) -> dict:
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id cannot be empty")

    event_type = row["event_type"]

    if pd.isna(event_type):
        raise ValueError("event_type cannot be null")

    event_type = str(event_type)

    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(
            f"Unsupported event_type: {event_type}"
        )

    # Validate integer fields without silently truncating decimals.
    integer_fields = [
        "product_id",
        "category_id",
        "user_id",
    ]

    integer_values = {}

    for field in integer_fields:
        value = row[field]

        if pd.isna(value):
            raise ValueError(f"{field} cannot be null")

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"{field} must be an integer: {value}"
            )

        if not math.isfinite(numeric_value):
            raise ValueError(
                f"{field} must be finite: {value}"
            )

        if not numeric_value.is_integer():
            raise ValueError(
                f"{field} must be an integer: {value}"
            )

        integer_value = int(numeric_value)

        if integer_value < 0:
            raise ValueError(
                f"{field} cannot be negative"
            )

        integer_values[field] = integer_value

    price_value = row["price"]

    if pd.isna(price_value):
        raise ValueError("price cannot be null")

    price = float(price_value)

    if not math.isfinite(price) or price < 0:
        raise ValueError(f"Invalid price: {price}")

    event_identity = (
        f"{run_id}:{source_file}:{source_row_index}"
    )

    event_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        event_identity,
    )

    event = {
        "event_id": str(event_id),
        "run_id": run_id,
        "original_event_time": to_utc_iso(
            row["event_time"]
        ),
        "stream_event_time": datetime.now(
            timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "event_type": event_type,
        "product_id": integer_values["product_id"],
        "category_id": integer_values["category_id"],
        "category_code": to_nullable_string(
            row["category_code"]
        ),
        "brand": to_nullable_string(row["brand"]),
        "price": price,
        "user_id": integer_values["user_id"],
        "user_session": to_nullable_string(
            row["user_session"]
        ),
    }

    return event



# ============================================================
# CSV READING
# ============================================================

def validate_csv_columns(input_path: Path):
    if not input_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {input_path}"
        )

    header = pd.read_csv(input_path, nrows=0)

    missing_columns = [
        column
        for column in SOURCE_COLUMNS
        if column not in header.columns
    ]

    if missing_columns:
        raise ValueError(
            "CSV is missing required columns: "
            + ", ".join(missing_columns)
        )


def read_csv_chunks(input_path: Path, chunk_size: int):
    dtype = {
        "event_time": "string",
        "event_type": "string",
        "product_id": "Int64",
        "category_id": "Int64",
        "category_code": "string",
        "brand": "string",
        "price": "float64",
        "user_id": "Int64",
        "user_session": "string",
    }

    return pd.read_csv(
        input_path,
        usecols=SOURCE_COLUMNS,
        dtype=dtype,
        chunksize=chunk_size,
    )


def iter_partition_rows(
    input_path: Path,
    chunk_size: int,
    row_start: int,
    row_end: int,
):
    """
    Yield (global_row_index, row) within [row_start, row_end).

    The CSV is read in chunks. Rows before row_start are parsed
    but not yielded. This avoids loading the entire CSV into RAM.
    """

    global_row_index = 0

    for chunk in read_csv_chunks(input_path, chunk_size):
        chunk_length = len(chunk)

        chunk_start = global_row_index
        chunk_end = chunk_start + chunk_length

        if chunk_end <= row_start:
            global_row_index = chunk_end
            continue

        if chunk_start >= row_end:
            break

        local_start = max(0, row_start - chunk_start)
        local_end = min(chunk_length, row_end - chunk_start)

        for local_index in range(local_start, local_end):
            source_row_index = chunk_start + local_index

            yield (
                source_row_index,
                chunk.iloc[local_index],
            )

        global_row_index = chunk_end

        if chunk_end >= row_end:
            break


# ============================================================
# MANIFEST
# ============================================================

def load_manifest(manifest_path: Path, input_path: Path):
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest not found: {manifest_path}"
        )

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    source_file = manifest.get("source_file")

    if source_file != input_path.name:
        raise ValueError(
            "Manifest source_file does not match input CSV. "
            f"Manifest={source_file}, input={input_path.name}"
        )

    total_rows = manifest.get("total_data_rows")
    partitions = manifest.get("partitions")

    if not isinstance(total_rows, int) or total_rows < 0:
        raise ValueError(
            "Manifest total_data_rows is invalid"
        )

    if not isinstance(partitions, dict):
        raise ValueError(
            "Manifest partitions is invalid"
        )

    for mode in SUPPORTED_MODES:
        if mode not in partitions:
            raise ValueError(
                f"Manifest is missing partition: {mode}"
            )

        partition = partitions[mode]

        row_start = partition.get("row_start")
        row_end = partition.get("row_end")
        row_count = partition.get("row_count")

        if not all(
            isinstance(value, int)
            for value in (row_start, row_end, row_count)
        ):
            raise ValueError(
                f"Invalid row range for partition: {mode}"
            )

        if row_start < 0 or row_end < row_start:
            raise ValueError(
                f"Invalid row boundaries for partition: {mode}"
            )

        if row_end > total_rows:
            raise ValueError(
                f"Partition {mode} exceeds total_data_rows"
            )

        if row_count != row_end - row_start:
            raise ValueError(
                f"row_count does not match row range: {mode}"
            )

    return manifest


# ============================================================
# CHECKPOINT
# ============================================================

def save_checkpoint(
    checkpoint_path: Path,
    checkpoint_data: dict,
):
    """
    Write checkpoint atomically.

    A temporary file is written first, then replaced using
    os.replace() so a partially written checkpoint is avoided.
    """

    checkpoint_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=checkpoint_path.parent,
            prefix=checkpoint_path.name,
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

            json.dump(
                checkpoint_data,
                temp_file,
                ensure_ascii=False,
                indent=2,
            )

            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, checkpoint_path)

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def load_checkpoint(checkpoint_path: Path):
    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Checkpoint not found: {checkpoint_path}"
        )

    with checkpoint_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def validate_checkpoint(
    checkpoint: dict,
    input_path: Path,
    mode: str,
    run_id: str,
    row_start: int,
    row_end: int,
):
    expected_values = {
        "source_file": input_path.name,
        "mode": mode,
        "run_id": run_id,
        "partition_start": row_start,
        "partition_end": row_end,
    }

    for key, expected in expected_values.items():
        actual = checkpoint.get(key)

        if actual != expected:
            raise ValueError(
                f"Checkpoint mismatch for {key}: "
                f"expected={expected}, actual={actual}"
            )

    next_row = checkpoint.get("next_row")

    if not isinstance(next_row, int):
        raise ValueError(
            "Checkpoint next_row is invalid"
        )

    if not row_start <= next_row <= row_end:
        raise ValueError(
            "Checkpoint next_row is outside partition boundaries"
        )

    return next_row


def create_initial_checkpoint(
    input_path: Path,
    mode: str,
    run_id: str,
    row_start: int,
    row_end: int,
):
    return {
        "checkpoint_version": 1,
        "source_file": input_path.name,
        "mode": mode,
        "run_id": run_id,
        "partition_start": row_start,
        "partition_end": row_end,
        "next_row": row_start,
        "last_confirmed_row": None,
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# ============================================================
# EVENT HUB BATCH SENDING
# ============================================================

def is_transient_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (TimeoutError, ConnectionError, OSError),
    ):
        return True

    if isinstance(exc, EventHubError):
        return bool(
            getattr(exc, "is_transient", False)
        )

    return False


def send_current_batch(
    producer,
    batch,
    event_count: int,
    logger: logging.Logger,
    max_retries: int,
    base_backoff: float,
    max_backoff: float,
):
    if event_count == 0:
        return {
            "sent": 0,
            "retries": 0,
            "errors": 0,
            "duration": 0.0,
        }

    retries = 0
    start_time = time.perf_counter()

    while True:
        try:
            producer.send_batch(batch)

            duration = time.perf_counter() - start_time

            logger.info(
                "Batch sent successfully | events=%d | "
                "duration=%.3fs | retries=%d",
                event_count,
                duration,
                retries,
            )

            return {
                "sent": event_count,
                "retries": retries,
                "errors": 0,
                "duration": duration,
            }

        except Exception as exc:
            if (
                not is_transient_error(exc)
                or retries >= max_retries
            ):
                duration = time.perf_counter() - start_time

                logger.exception(
                    "Batch failed permanently | events=%d | "
                    "duration=%.3fs | retries=%d",
                    event_count,
                    duration,
                    retries,
                )

                return {
                    "sent": 0,
                    "retries": retries,
                    "errors": event_count,
                    "duration": duration,
                }

            retries += 1

            backoff = min(
                base_backoff * (2 ** (retries - 1)),
                max_backoff,
            )

            delay = random.uniform(0, backoff)

            logger.warning(
                "Transient send error | retry=%d/%d | "
                "backoff=%.2fs | error=%s",
                retries,
                max_retries,
                delay,
                exc,
            )

            time.sleep(delay)


# ============================================================
# RATE LIMITER
# ============================================================

class RateLimiter:
    def __init__(self, rate: float):
        self.rate = rate
        self.interval = 1.0 / rate if rate > 0 else 0
        self.next_time = time.monotonic()

    def wait(self):
        if self.rate <= 0:
            return

        now = time.monotonic()

        if now < self.next_time:
            time.sleep(self.next_time - now)

        self.next_time = max(
            self.next_time + self.interval,
            time.monotonic(),
        )

def append_jsonl_batch(output_path: Path, payloads: list[str]):
    if output_path is None or not payloads:
        return

    with output_path.open("a", encoding="utf-8") as file:
        for payload in payloads:
            file.write(payload + "\n")

        file.flush()
        os.fsync(file.fileno())


# ============================================================
# PRODUCER
# ============================================================

def run_producer(args, logger):
    input_path = Path(args.input)
    manifest_path = Path(args.manifest)

    validate_csv_columns(input_path)

    manifest = load_manifest(
        manifest_path,
        input_path,
    )

    partition = manifest["partitions"][args.mode]

    row_start = partition["row_start"]
    row_end = partition["row_end"]

    safe_run_id = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        args.run_id,
    )

    checkpoint_path = (
        Path(args.checkpoint)
        if args.checkpoint
        else CHECKPOINT_DIR / (
            f"{args.mode}_{safe_run_id}.json"
        )
    )

    if args.resume:
        checkpoint = load_checkpoint(checkpoint_path)

        start_row = validate_checkpoint(
            checkpoint,
            input_path,
            args.mode,
            args.run_id,
            row_start,
            row_end,
        )

        logger.info(
            "Resuming from checkpoint | next_row=%d",
            start_row,
        )

    else:
        if checkpoint_path.exists():
            raise FileExistsError(
                f"Checkpoint already exists: {checkpoint_path}. "
                "Use --resume or choose another --run-id."
            )

        checkpoint = create_initial_checkpoint(
            input_path,
            args.mode,
            args.run_id,
            row_start,
            row_end,
        )

        save_checkpoint(
            checkpoint_path,
            checkpoint,
        )

        start_row = row_start

    jsonl_path = (
        Path(args.jsonl_output)
        if args.jsonl_output
        else None
    )

    if jsonl_path is not None:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        if jsonl_path.exists():
            raise FileExistsError(
                f"JSONL output already exists: {jsonl_path}"
            )

        jsonl_path.touch()

        logger.info("JSONL output: %s", jsonl_path)

    logger.info("Starting Producer MVP")
    logger.info("Input file: %s", input_path)
    logger.info("Manifest: %s", manifest_path)
    logger.info("Partition mode: %s", args.mode)
    logger.info(
        "Partition range: [%d, %d)",
        row_start,
        row_end,
    )
    logger.info("Checkpoint: %s", checkpoint_path)
    logger.info("Event Hub: configured from EVENTHUB_NAME environment variable")
    logger.info("Run ID: %s", args.run_id)
    logger.info("Maximum valid events: %d", args.max_events)
    logger.info("Batch event limit: %d", args.batch_size)
    logger.info("CSV chunk size: %d", args.chunk_size)
    logger.info("Rate limit: %.2f events/second", args.rate)
    logger.info("Maximum retries: %d", args.max_retries)

    if start_row >= row_end:
        logger.info(
            "Partition is already completed. No events to send."
        )
        return

    connection_str, eventhub_name = get_eventhub_config()

    producer = EventHubProducerClient.from_connection_string(
        conn_str=connection_str,
        eventhub_name=eventhub_name,
    )

    rate_limiter = RateLimiter(args.rate)

    stats = {
        "source_rows_scanned": 0,
        "events_prepared": 0,
        "events_sent": 0,
        "events_error": 0,
        "unsupported_skipped": 0,
        "retries": 0,
        "batches": 0,
    }

    batch = producer.create_batch()
    batch_event_count = 0
    batch_last_source_row = None
    batch_payloads = []

    start_time = time.perf_counter()
    partition_completed = False
    stop_at_max_events = False

    def confirm_batch(
        current_batch,
        event_count,
        last_source_row,
        payloads,
    ):
        """
        Send one batch and checkpoint only after success.
        """

        result = send_current_batch(
            producer,
            current_batch,
            event_count,
            logger,
            args.max_retries,
            args.base_backoff,
            args.max_backoff,
        )

        stats["retries"] += result["retries"]
        stats["batches"] += 1

        if result["errors"] > 0:
            stats["events_error"] += result["errors"]

            raise RuntimeError(
                "Batch could not be sent. "
                "Checkpoint was not advanced."
            )

        if jsonl_path is not None:
            if len(payloads) != result["sent"]:
                raise RuntimeError(
                    "JSONL payload count does not match sent events."
                )

            append_jsonl_batch(jsonl_path, payloads)

        stats["events_sent"] += result["sent"]

        checkpoint["next_row"] = last_source_row + 1
        checkpoint["last_confirmed_row"] = last_source_row
        checkpoint["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        save_checkpoint(
            checkpoint_path,
            checkpoint,
        )

        logger.info(
            "Checkpoint updated | next_row=%d | "
            "last_confirmed_row=%d",
            checkpoint["next_row"],
            last_source_row,
        )

    try:
        rows = iter_partition_rows(
            input_path,
            args.chunk_size,
            start_row,
            row_end,
        )

        for source_row_index, row in rows:

            if stats["events_prepared"] >= args.max_events:
                stop_at_max_events = True
                break

            stats["source_rows_scanned"] += 1

            event_type = row["event_type"]

            if (
                pd.isna(event_type)
                or str(event_type) not in SUPPORTED_EVENT_TYPES
            ):
                stats["unsupported_skipped"] += 1
                continue

            try:
                event = build_event(
                    row,
                    args.run_id,
                    input_path.name,
                    source_row_index,
                )

            except Exception as exc:
                raise ValueError(
                    f"Invalid source row {source_row_index}: {exc}"
                ) from exc

            rate_limiter.wait()

            payload = json.dumps(
                event,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )

            event_data = EventData(payload)

            # Try adding the event to the current batch.
            try:
                batch.add(event_data)

            except ValueError:
                if batch_event_count == 0:
                    raise ValueError(
                        "A single event exceeds the "
                        "Event Hubs batch size limit."
                    )

                # The current batch is full.
                # Confirm it before moving to the next event.
                confirm_batch(
                    batch,
                    batch_event_count,
                    batch_last_source_row,
                    batch_payloads,
                )

                batch = producer.create_batch()
                batch_event_count = 0
                batch_last_source_row = None
                batch_payloads = []

                try:
                    batch.add(event_data)

                except ValueError as exc:
                    raise ValueError(
                        "A single event exceeds the "
                        "Event Hubs batch size limit."
                    ) from exc

            batch_event_count += 1
            batch_last_source_row = source_row_index
            stats["events_prepared"] += 1
            batch_payloads.append(payload)

            # Flush when the configured event count is reached.
            if batch_event_count >= args.batch_size:
                confirm_batch(
                    batch,
                    batch_event_count,
                    batch_last_source_row,
                    batch_payloads,
                )

                batch = producer.create_batch()
                batch_event_count = 0
                batch_last_source_row = None
                batch_payloads = []

        else:
            # The iterator reached the end of the partition
            # without being interrupted by max_events.
            partition_completed = True

        # Flush remaining events.
        if batch_event_count > 0:
            confirm_batch(
                batch,
                batch_event_count,
                batch_last_source_row,
                batch_payloads,
            )

            batch = producer.create_batch()
            batch_event_count = 0
            batch_last_source_row = None
            batch_payloads = []

        # If all rows in the partition were scanned and all
        # batches were confirmed, mark the partition completed.
        if partition_completed and not stop_at_max_events:
            checkpoint["next_row"] = row_end
            checkpoint["last_confirmed_row"] = (
                row_end - 1 if row_end > row_start else None
            )
            checkpoint["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            save_checkpoint(
                checkpoint_path,
                checkpoint,
            )

            logger.info(
                "Partition completed | next_row=%d",
                row_end,
            )

    finally:
        producer.close()

    elapsed = time.perf_counter() - start_time

    logger.info("========== PRODUCER SUMMARY ==========")
    logger.info(
        "Source rows scanned: %d",
        stats["source_rows_scanned"],
    )
    logger.info(
        "Valid events prepared: %d",
        stats["events_prepared"],
    )
    logger.info(
        "Events sent successfully: %d",
        stats["events_sent"],
    )
    logger.info(
        "Events error: %d",
        stats["events_error"],
    )
    logger.info(
        "Unsupported events skipped: %d",
        stats["unsupported_skipped"],
    )
    logger.info(
        "Total retries: %d",
        stats["retries"],
    )
    logger.info(
        "Batches processed: %d",
        stats["batches"],
    )
    logger.info(
        "Checkpoint next_row: %d",
        checkpoint["next_row"],
    )
    logger.info(
        "Partition completed: %s",
        partition_completed,
    )
    logger.info(
        "Elapsed time: %.2f seconds",
        elapsed,
    )

    if elapsed > 0:
        logger.info(
            "Average throughput: %.2f events/second",
            stats["events_sent"] / elapsed,
        )

    logger.info("Producer MVP finished")


# ============================================================
# CLI
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Stream e-commerce events to Azure Event Hubs"
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to 2019-Oct.csv",
    )

    parser.add_argument(
        "--manifest",
        default="manifest.json",
        help="Path to manifest.json",
    )

    parser.add_argument(
        "--mode",
        choices=sorted(SUPPORTED_MODES),
        default="dev",
        help="Dataset partition: dev or demo",
    )

    parser.add_argument(
        "--checkpoint",
        default=None,
        help=(
            "Checkpoint JSON path. "
            "Default: checkpoints/<mode>_<run_id>.json"
        ),
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from an existing checkpoint",
    )

    parser.add_argument(
        "--max-events",
        type=int,
        default=DEFAULT_MAX_EVENTS,
        help="Maximum number of valid events to send",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Maximum number of events in one batch",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Number of CSV rows read per chunk",
    )

    parser.add_argument(
        "--run-id",
        default=None,
        help="Producer execution identifier",
    )

    parser.add_argument(
        "--rate",
        type=float,
        default=DEFAULT_RATE,
        help=(
            "Maximum event rate per second; "
            "0 disables rate limiting"
        ),
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help="Maximum retries for transient send errors",
    )

    parser.add_argument(
        "--base-backoff",
        type=float,
        default=DEFAULT_BASE_BACKOFF,
        help="Initial retry backoff in seconds",
    )

    parser.add_argument(
        "--max-backoff",
        type=float,
        default=DEFAULT_MAX_BACKOFF,
        help="Maximum retry backoff in seconds",
    )

    parser.add_argument(
        "--jsonl-output",
        default=None,
        help="Path to JSONL file containing successfully sent events",
    )

    args = parser.parse_args()

    if args.max_events <= 0:
        parser.error("--max-events must be greater than 0")

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than 0")

    if args.chunk_size <= 0:
        parser.error("--chunk-size must be greater than 0")

    if args.resume and not args.run_id:
        parser.error(
            "--run-id is required when using --resume"
        )

    if not args.run_id:
        args.run_id = "run-" + uuid.uuid4().hex[:12]

    if args.rate < 0:
        parser.error("--rate cannot be negative")

    if args.max_retries < 0:
        parser.error("--max-retries cannot be negative")

    if args.base_backoff <= 0:
        parser.error("--base-backoff must be greater than 0")

    if args.max_backoff <= 0:
        parser.error("--max-backoff must be greater than 0")

    if args.max_backoff < args.base_backoff:
        parser.error(
            "--max-backoff must be >= --base-backoff"
        )

    return args


# ============================================================
# MAIN
# ============================================================

def main():
    args = parse_args()
    logger = setup_logging(args.run_id)

    try:
        run_producer(args, logger)

    except Exception:
        logger.exception("Producer failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
