
import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_CSV = (
    "/kaggle/input/datasets/"
    "mkechinov/ecommerce-behavior-data-from-multi-category-store/"
    "2019-Oct.csv"
)

QUOTAS = {
    "view": 17,
    "cart": 17,
    "purchase": 16,
}

COLUMNS = [
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


def is_null(value):
    return pd.isna(value)


def to_int(value):
    return int(value)


def to_float(value):
    return float(value)


def to_utc_string(value):
    timestamp = pd.to_datetime(value, utc=True)
    return timestamp.isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def build_event(row, run_id, stream_time):
    original_time = to_utc_string(row["event_time"])

    return {
        "event_id": str(uuid.uuid4()),
        "run_id": run_id,
        "original_event_time": original_time,
        "stream_event_time": stream_time,
        "event_type": str(row["event_type"]),
        "product_id": to_int(row["product_id"]),
        "category_id": to_int(row["category_id"]),
        "category_code": (
            None if is_null(row["category_code"])
            else str(row["category_code"])
        ),
        "brand": (
            None if is_null(row["brand"])
            else str(row["brand"])
        ),
        "price": to_float(row["price"]),
        "user_id": to_int(row["user_id"]),
        "user_session": (
            None if is_null(row["user_session"])
            else str(row["user_session"])
        ),
    }


def create_sample(csv_path, output_path, chunksize):
    if not Path(csv_path).is_file():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    selected = {event_type: [] for event_type in QUOTAS}

    total_rows_scanned = 0

    reader = pd.read_csv(
        csv_path,
        usecols=COLUMNS,
        chunksize=chunksize,
        dtype={
            "event_type": "string",
            "category_code": "string",
            "brand": "string",
            "user_session": "string",
        },
    )

    for chunk in reader:
        total_rows_scanned += len(chunk)

        for event_type, quota in QUOTAS.items():
            remaining = quota - len(selected[event_type])

            if remaining <= 0:
                continue

            candidates = chunk[
                chunk["event_type"] == event_type
            ]

            needed = candidates.head(remaining)

            selected[event_type].extend(
                needed.to_dict(orient="records")
            )

        if all(
            len(selected[event_type]) == quota
            for event_type, quota in QUOTAS.items()
        ):
            break

    missing = {
        event_type: quota - len(selected[event_type])
        for event_type, quota in QUOTAS.items()
        if len(selected[event_type]) < quota
    }

    if missing:
        raise ValueError(
            f"Not enough source events for quotas: {missing}"
        )

    run_id = "sample-01"
    stream_time = datetime.now(timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")

    events = []

    for event_type in QUOTAS:
        for row in selected[event_type]:
            events.append(
                build_event(row, run_id, stream_time)
            )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            events,
            file,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

    print("=== SAMPLE GENERATION ===")
    print(f"Source: {csv_path}")
    print(f"Rows scanned: {total_rows_scanned:,}")
    print(f"Events generated: {len(events)}")
    print(f"Run ID: {run_id}")
    print(f"Output: {output_path.resolve()}")

    print("\n=== EVENT DISTRIBUTION ===")
    for event_type, quota in QUOTAS.items():
        print(f"{event_type}: {quota}")

    print("\nSample generation completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help="Path to 2019-Oct.csv",
    )

    parser.add_argument(
        "--output",
        default="sample_events.json",
        help="Output JSON file",
    )

    parser.add_argument(
        "--chunksize",
        type=int,
        default=250_000,
    )

    args = parser.parse_args()

    create_sample(
        args.csv,
        args.output,
        args.chunksize,
    )
