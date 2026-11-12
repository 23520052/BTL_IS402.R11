
import argparse
import json
import uuid
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


def validate_sample(schema_path, sample_path):
    with open(schema_path, "r", encoding="utf-8") as file:
        schema = json.load(file)

    with open(sample_path, "r", encoding="utf-8") as file:
        events = json.load(file)

    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors = []

    if not isinstance(events, list):
        raise ValueError("Sample root must be a JSON array.")

    if len(events) != 50:
        errors.append(
            f"Expected 50 events, found {len(events)}."
        )

    event_ids = [
        event.get("event_id")
        for event in events
        if isinstance(event, dict)
    ]

    if len(event_ids) != len(set(event_ids)):
        errors.append("Duplicate event_id detected.")

    for index, event in enumerate(events):
        for error in validator.iter_errors(event):
            errors.append(
                f"Event #{index + 1}: "
                f"{error.json_path}: {error.message}"
            )

    event_counts = Counter(
        event.get("event_type")
        for event in events
        if isinstance(event, dict)
    )

    expected_types = {"view", "cart", "purchase"}

    if set(event_counts) != expected_types:
        errors.append(
            f"Unexpected event types: {dict(event_counts)}"
        )

    if any(
        event.get("run_id") != "sample-01"
        for event in events
        if isinstance(event, dict)
    ):
        errors.append("Invalid run_id. Expected sample-01.")

    print("=== DATA CONTRACT VALIDATION ===")
    print(f"Schema: {schema_path}")
    print(f"Sample: {sample_path}")
    print(f"Total events: {len(events)}")

    print("\n=== EVENT TYPE DISTRIBUTION ===")
    for event_type in sorted(expected_types):
        print(f"{event_type}: {event_counts[event_type]}")

    if errors:
        print(f"\nVALIDATION FAILED: {len(errors)} error(s)")

        for error in errors:
            print(f"- {error}")

        raise SystemExit(1)

    print("\nVALIDATION PASSED")
    print("All 50 events satisfy the data contract.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--schema",
        default="data_contract.json",
    )

    parser.add_argument(
        "--sample",
        default="sample_events.json",
    )

    args = parser.parse_args()

    validate_sample(
        args.schema,
        args.sample,
    )
