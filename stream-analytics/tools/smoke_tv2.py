import argparse
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


def iso(value):
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    run_id = "smoke-" + uuid.uuid4().hex[:12]
    client = None

    if args.send:
        from azure.eventhub import EventHubProducerClient, EventData, TransportType
        connection_string = os.environ["EVENTHUB_CONNECTION_STRING"]
        hub = os.environ["EVENTHUB_NAME"]
        client = EventHubProducerClient.from_connection_string(
            conn_str=connection_string,
            eventhub_name=hub,
            transport_type=TransportType.AmqpOverWebsocket,
        )

    base = (datetime.now(timezone.utc) + timedelta(seconds=10))
    base = base.replace(second=0, microsecond=0) + timedelta(minutes=1)
    specs = [
        (5, "view", "samsung", 100.0),
        (8, "view", "apple", 300.0),
        (12, "cart", "samsung", 100.0),
        (15, "purchase", "samsung", 100.0),
        (20, "purchase", "samsung", 200.0),
        (25, "purchase", "apple", 300.0),
        (35, "purchase", None, 50.0),
        (40, "view", "samsung", 100.0),
    ]
    events = []
    for index, (offset, event_type, brand, price) in enumerate(specs, 1):
        events.append({
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "original_event_time": "2019-10-01T00:00:04Z",
            "stream_event_time": iso(base + timedelta(seconds=offset)),
            "event_type": event_type,
            "product_id": 100000 + index,
            "category_id": 2053013555631882655,
            "category_code": "electronics.smartphone",
            "brand": brand,
            "price": price,
            "user_id": 123450 + index,
            "user_session": f"{run_id}-session-{index:04d}",
        })

    folder = Path("smoke-results") / run_id
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "sample_events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    expected = {
        "run_id": run_id,
        "base_utc": iso(base),
        "window_30s_first_end": iso(base + timedelta(seconds=30)),
        "window_1m_end": iso(base + timedelta(minutes=1)),
        "input_count": 8,
        "metrics_rows": 5,
        "brand_rows": 3,
        "purchase_events": 4,
        "revenue": 650.0,
        "live_send_requested": args.send,
    }
    (folder / "expected.json").write_text(
        json.dumps(expected, indent=2), encoding="utf-8"
    )
    print(json.dumps(expected, indent=2), flush=True)
    print(f"Files: {folder.resolve()}", flush=True)
    if not args.send:
        print("OFFLINE ONLY: upload sample_events.json to ASA query test.")
        return

    try:
        with client:
            for event in events:
                target = datetime.fromisoformat(
                    event["stream_event_time"].replace("Z", "+00:00")
                )
                while True:
                    wait = (target - datetime.now(timezone.utc)).total_seconds()
                    if wait <= 0:
                        break
                    time.sleep(min(wait, 0.5))
                lag = (datetime.now(timezone.utc) - target).total_seconds()
                if lag > 3:
                    raise RuntimeError("Local schedule missed >3s; rerun with a new run_id")
                batch = client.create_batch()
                batch.add(EventData(json.dumps(event, allow_nan=False)))
                client.send_batch(batch)
                ack = {"event_id": event["event_id"], "ack_utc": iso(datetime.now(timezone.utc))}
                with (folder / "acknowledged.jsonl").open("a", encoding="utf-8") as log:
                    log.write(json.dumps(ack) + "\n")
                print("ACK", event["event_id"], flush=True)
    except Exception as exc:
        print(f"FAILED ({type(exc).__name__}); run may be partial. Do not claim PASS.")
        raise SystemExit(1) from None
    print("8 sends acknowledged. Next: verify both SQL tables; this is not yet PASS.")


if __name__ == "__main__":
    main()
