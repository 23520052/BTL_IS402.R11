

import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from azure.eventhub import EventData, EventHubProducerClient

import random
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

DEFAULT_MAX_EVENTS = 100
DEFAULT_BATCH_SIZE = 50
DEFAULT_CHUNK_SIZE = 10_000
DEFAULT_RATE = 100          # events/second; 0 = khong gioi han 
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_BACKOFF = 1.0
DEFAULT_MAX_BACKOFF = 30.0

LOG_DIR = Path("logs")


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


def build_event(row, run_id: str) -> dict:
    event_type = str(row["event_type"])

    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(
            f"Unsupported event_type: {event_type}"
        )

    if pd.isna(row["product_id"]):
        raise ValueError("product_id cannot be null")

    if pd.isna(row["category_id"]):
        raise ValueError("category_id cannot be null")

    if pd.isna(row["user_id"]):
        raise ValueError("user_id cannot be null")

    if pd.isna(row["price"]):
        raise ValueError("price cannot be null")

    price = float(row["price"])

    if price < 0:
        raise ValueError(f"Invalid price: {price}")

    event = {
        "event_id": str(uuid.uuid4()),
        "run_id": run_id,
        "original_event_time": to_utc_iso(row["event_time"]),
        "stream_event_time": datetime.now(
            timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "event_type": event_type,
        "product_id": int(row["product_id"]),
        "category_id": int(row["category_id"]),
        "category_code": to_nullable_string(
            row["category_code"]
        ),
        "brand": to_nullable_string(row["brand"]),
        "price": price,
        "user_id": int(row["user_id"]),
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


# ============================================================
# EVENT HUB BATCH SENDING
# ============================================================

def is_transient_error(exc: Exception) -> bool:
    """
    Identify errors that may succeed when retried.
    """
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True

    if isinstance(exc, EventHubError):
        return bool(getattr(exc, "is_transient", False))

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

            # Full jitter: random delay between 0 and backoff.
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


def add_event_to_batch(
    producer,
    batch,
    event: dict,
    batch_event_count: int,
    logger: logging.Logger,
    max_retries: int,
    base_backoff: float,
    max_backoff: float,
):
    payload = json.dumps(
        event,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )

    event_data = EventData(payload)

    try:
        batch.add(event_data)
        return batch, batch_event_count + 1, None

    except ValueError:
        if batch_event_count == 0:
            raise ValueError(
                "A single event exceeds the Event Hubs "
                "batch size limit."
            )

        # Send the current batch before creating a new one.
        result = send_current_batch(
            producer,
            batch,
            batch_event_count,
            logger,
            max_retries,
            base_backoff,
            max_backoff,
        )

        new_batch = producer.create_batch()

        try:
            new_batch.add(event_data)
        except ValueError as exc:
            raise ValueError(
                "A single event exceeds the Event Hubs "
                "batch size limit."
            ) from exc

        return new_batch, 1, result


# ============================================================
# PRODUCER
# ============================================================

def run_producer(args, logger):
    connection_str, eventhub_name = get_eventhub_config()

    input_path = Path(args.input)

    validate_csv_columns(input_path)

    logger.info("Starting Producer MVP")
    logger.info("Input file: %s", input_path)
    logger.info("Event Hub: %s", eventhub_name)
    logger.info("Run ID: %s", args.run_id)
    logger.info("Maximum events: %d", args.max_events)
    logger.info("Batch event limit: %d", args.batch_size)
    logger.info("CSV chunk size: %d", args.chunk_size)
    logger.info("Rate limit: %.2f events/second", args.rate)
    logger.info("Maximum retries: %d", args.max_retries)
    logger.info("Base backoff: %.2f seconds", args.base_backoff)
    logger.info("Maximum backoff: %.2f seconds", args.max_backoff)

    producer = EventHubProducerClient.from_connection_string(
        conn_str=connection_str,
        eventhub_name=eventhub_name,
    )

    rate_limiter = RateLimiter(args.rate)

    total_read = 0
    total_sent = 0
    total_success = 0
    total_errors = 0
    total_retries = 0
    total_batches = 0

    batch = producer.create_batch()
    batch_event_count = 0

    start_time = time.perf_counter()

    try:
        chunks = read_csv_chunks(
            input_path,
            args.chunk_size,
        )

        for chunk in chunks:
            for _, row in chunk.iterrows():
                if total_read >= args.max_events:
                    break

                rate_limiter.wait()
                event = build_event(row, args.run_id)

                batch, batch_event_count, size_result = (
                    add_event_to_batch(
                        producer,
                        batch,
                        event,
                        batch_event_count,
                        logger,
                        args.max_retries,
                        args.base_backoff,
                        args.max_backoff,
                    )
                )

                if size_result is not None:
                    total_sent += size_result["sent"]
                    total_success += size_result["sent"]
                    total_errors += size_result["errors"]
                    total_retries += size_result["retries"]
                    total_batches += 1

                total_read += 1

                # Flush when the configured event count is reached.
                if batch_event_count >= args.batch_size:
                    result = send_current_batch(
                        producer,
                        batch,
                        batch_event_count,
                        logger,
                        args.max_retries,
                        args.base_backoff,
                        args.max_backoff,
                    )

                    total_sent += result["sent"]
                    total_success += result["sent"]
                    total_errors += result["errors"]
                    total_retries += result["retries"]
                    total_batches += 1
                    batch = producer.create_batch()
                    batch_event_count = 0

            if total_read >= args.max_events:
                break

        # Send the remaining events.
        if batch_event_count > 0:
            result = send_current_batch(
                producer,
                batch,
                batch_event_count,
                logger,
                args.max_retries,
                args.base_backoff,
                args.max_backoff,
            )

            total_sent += result["sent"]
            total_success += result["sent"]
            total_errors += result["errors"]
            total_retries += result["retries"]
            total_batches += 1

    finally:
        producer.close()

    elapsed = time.perf_counter() - start_time

    logger.info("========== PRODUCER SUMMARY ==========")
    logger.info("Events read and prepared: %d", total_read)
    logger.info("Events sent successfully: %d", total_sent)
    logger.info("Events success: %d", total_success)
    logger.info("Events error: %d", total_errors)
    logger.info("Total retries: %d", total_retries)
    logger.info("Batches processed: %d", total_batches)
    logger.info("Elapsed time: %.2f seconds", elapsed)

    if elapsed > 0:
        logger.info(
            "Average throughput: %.2f events/second",
            total_sent / elapsed,
        )

    logger.info("Producer MVP finished")


# ============================================================
# CLI
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Stream e-commerce events to Azure Event Hubs"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to 2019-Oct.csv",
    )

    parser.add_argument(
        "--max-events",
        type=int,
        default=DEFAULT_MAX_EVENTS,
        help="Maximum number of events to send",
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
        help="Maximum event rate per second; 0 disables rate limiting",
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

    args = parser.parse_args()

    if args.max_events <= 0:
        parser.error("--max-events must be greater than 0")

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than 0")

    if args.chunk_size <= 0:
        parser.error("--chunk-size must be greater than 0")

    if not args.run_id:
        args.run_id = (
            "run-" + uuid.uuid4().hex[:12]
        )

    if args.rate < 0:
        parser.error("--rate cannot be negative")

    if args.max_retries < 0:
        parser.error("--max-retries cannot be negative")

    if args.base_backoff <= 0:
        parser.error("--base-backoff must be greater than 0")

    if args.max_backoff <= 0:
        parser.error("--max-backoff must be greater than 0")

    if args.max_backoff < args.base_backoff:
        parser.error("--max-backoff must be >= --base-backoff")

    return args

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
