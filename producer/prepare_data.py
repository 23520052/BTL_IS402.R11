
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd


def count_csv_rows(input_path, chunk_size=100_000):
    total_rows = 0

    for chunk in pd.read_csv(
        input_path,
        chunksize=chunk_size,
        usecols=["event_time"],
    ):
        total_rows += len(chunk)

        if total_rows % 1_000_000 < chunk_size:
            print(f"Scanned: {total_rows:,} rows")

    return total_rows


def create_manifest(input_path, output_path, dev_ratio=0.5,
                    chunk_size=100_000):

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    if not 0 < dev_ratio < 1:
        raise ValueError("dev_ratio must be between 0 and 1")

    print("Counting CSV records...")

    total_rows = count_csv_rows(input_path, chunk_size)
    split_row = int(total_rows * dev_ratio)

    manifest = {
        "manifest_version": 1,
        "source_file": input_path.name,
        "total_data_rows": total_rows,
        "split_ratio": dev_ratio,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "row_indexing": "zero_based_data_rows",
        "range_convention": "start_inclusive_end_exclusive",
        "checksum": None,
        "partitions": {
            "dev": {
                "row_start": 0,
                "row_end": split_row,
                "row_count": split_row
            },
            "demo": {
                "row_start": split_row,
                "row_end": total_rows,
                "row_count": total_rows - split_row
            }
        }
    }

    assert (
        manifest["partitions"]["dev"]["row_end"]
        == manifest["partitions"]["demo"]["row_start"]
    )

    assert (
        manifest["partitions"]["dev"]["row_count"]
        + manifest["partitions"]["demo"]["row_count"]
        == total_rows
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.flush()

    temp_path.replace(output_path)

    print("\n=== PREPARE DATA SUMMARY ===")
    print(f"Source: {input_path}")
    print(f"Total data rows: {total_rows:,}")
    print(f"DEV rows: {split_row:,}")
    print(f"DEMO rows: {total_rows - split_row:,}")
    print(f"Manifest: {output_path}")
    print("Validation: PASSED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--output",
        default="/kaggle/working/manifest.json"
    )
    parser.add_argument("--dev-ratio", type=float, default=0.5)
    parser.add_argument("--chunk-size", type=int, default=100_000)

    args = parser.parse_args()

    create_manifest(
        args.input,
        args.output,
        args.dev_ratio,
        args.chunk_size
    )
