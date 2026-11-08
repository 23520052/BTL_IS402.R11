
# Data Contract - E-commerce Sales Events

## 1. Overview

This document defines the JSON event contract used by the
Python data preparation module before events are sent to
Azure Event Hubs.

Source dataset:
- Name: eCommerce behavior data from multi-category store
- File: 2019-Oct.csv
- Source: Kaggle
- Total records: 42,448,764

The actual dataset contains three event types:
- view
- cart
- purchase

Note: remove_from_cart is not present in the source CSV
and is excluded from this contract.

## 2. Event Structure

Each event contains 12 fields:

| Field | Data type | Nullable | Description |
|---|---|---|---|
| event_id | string (UUID) | No | Unique event identifier |
| run_id | string | No | Identifier of the execution |
| original_event_time | string (ISO 8601 UTC) | No | Original timestamp from event_time |
| stream_event_time | string (ISO 8601 UTC) | No | Timestamp when event is prepared for streaming |
| event_type | string (enum) | No | view, cart or purchase |
| product_id | integer | No | Product identifier |
| category_id | integer | No | Product category identifier |
| category_code | string | Yes | Product category code |
| brand | string | Yes | Product brand |
| price | number | No | Product price |
| user_id | integer | No | User identifier |
| user_session | string | Yes | User session identifier |

## 3. Nullable Fields

The following fields may contain null values:

| Field | Null count in source |
|---|---:|
| category_code | 13,515,609 |
| brand | 6,117,080 |
| user_session | 2 |

All other source fields have zero null values
according to data_profile.json.

Nullable fields must still be included in each JSON event.
Missing source values are represented by JSON null.

## 4. Timestamp Convention

All timestamps use ISO 8601 UTC format.

Example:

- original_event_time: 2019-10-01T00:00:00.000Z
- stream_event_time: 2026-11-08T09:00:00.000Z

original_event_time preserves the source event timestamp.

stream_event_time records when the event is prepared
for streaming.

## 5. Event Type Definition

| Event type | Meaning |
|---|---|
| view | Product viewing event |
| cart | Product added to cart |
| purchase | Purchase event |

The source dataset does not contain remove_from_cart.
Therefore, this event type is not supported.

A purchase event must not be interpreted as an order
because the source dataset does not provide order_id.

## 6. Event Identification

- event_id: generated as UUID for each event.
- run_id: shared by events in the same execution.
- Sample execution uses run_id = sample-01.

## 7. Validation Rules

The JSON Schema follows JSON Schema Draft 2020-12.

Validation requirements:

1. All 12 fields must be present.
2. event_id must be a valid UUID.
3. Both timestamps must be ISO 8601 UTC strings ending in Z.
4. event_type must belong to the supported enum.
5. category_code, brand and user_session may be null.
6. price must be a non-negative number.
7. No additional properties are allowed.

## 8. Sample Dataset

File: sample_events.json

- Total events: 50
- view: 17
- cart: 17
- purchase: 16
- run_id: sample-01

The sample is extracted from the original CSV
using chunk-based reading.

## 9. Related Files

- data_contract.json: JSON Schema
- prepare_sample.py: Sample generation
- validate_sample.py: Schema validation
- sample_events.json: Generated sample

## 10. Scope

This contract covers event preparation and data validation
for TV1 (Data Engineer).

Azure Stream Analytics queries, Azure SQL schema,
and Power BI implementation are outside this document's scope.
