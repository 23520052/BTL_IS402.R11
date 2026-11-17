"""Validate official PBIR schemas and semantic bindings without touching SQL."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request
from urllib.error import HTTPError
import warnings

import jsonschema

warnings.filterwarnings("ignore", category=DeprecationWarning)
ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(tempfile.gettempdir()) / "tv4-json-schema-cache"
CACHE.mkdir(exist_ok=True)


def load_schema(url):
    # Some Microsoft embedded schemas advertise a dotted $id but are served
    # at the hyphenated URL used by their public referring schemas.
    url = url.replace('/schema.embedded.json', '/schema-embedded.json')
    path = CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(url, timeout=20).read())
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root
    model = json.loads((root / "sales_dashboard.SemanticModel/model.bim").read_text(encoding="utf-8"))["model"]
    tables = {t["name"]: t for t in model["tables"]}
    definitions = root / "sales_dashboard.Report/definition"
    errors = []
    unavailable_schemas = {}
    checked = 0
    schema_files = 0
    for path in definitions.rglob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if "$schema" not in value:
            continue
        schema_files += 1
        try:
            if value["$schema"] in unavailable_schemas:
                raise HTTPError(value["$schema"], 404, "Schema unavailable", None, None)
            schema = load_schema(value["$schema"])
            resolver = jsonschema.RefResolver(value["$schema"], schema, handlers={"https": load_schema})
            jsonschema.Draft7Validator(schema, resolver=resolver).validate(value)
            checked += 1
        except HTTPError as exc:
            if exc.code == 404:
                unavailable_schemas[value["$schema"]] = "HTTP 404 at the declared schema URL"
            else:
                errors.append(f"{path.relative_to(root)}: {str(exc)[:700]}")
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: {str(exc)[:700]}")
        if "visual" in value:
            for role, state in value["visual"].get("query", {}).get("queryState", {}).items():
                for p in state["projections"]:
                    field = p["field"]
                    kind = next(iter(field))
                    ref = field[kind]
                    table = ref["Expression"]["SourceRef"]["Entity"]
                    if table not in tables:
                        errors.append(f"{path.relative_to(root)}: unknown table {table}")
                        continue
                    names = {x["name"] for x in tables[table].get("measures" if kind == "Measure" else "columns", [])}
                    if ref["Property"] not in names:
                        errors.append(f"{path}: unknown {kind} {table}.{ref['Property']}")
            position = value["position"]
            if position["x"] < 0 or position["y"] < 0 or position["x"]+position["width"] > 1280 or position["y"]+position["height"] > 800:
                errors.append(f"{path}: visual outside 1280x800 canvas")
    pages = list((definitions / "pages").glob("*/page.json"))
    if len(pages) != 4:
        errors.append("Expected exactly four pages")
    expected_tables = {"event_metrics_30s", "brand_sales_1m", "DimRun", "DimEvent"}
    if set(tables) != expected_tables:
        errors.append("Expected two fact tables and DimRun/DimEvent")
    for name, table in tables.items():
        partitions = table.get("partitions", [])
        if len(partitions) != 1 or partitions[0].get("mode") != "directQuery":
            errors.append(f"{name}: expected one DirectQuery partition")
    expected_relationships = {
        ("event_metrics_30s", "run_id", "DimRun", "run_id"),
        ("brand_sales_1m", "run_id", "DimRun", "run_id"),
        ("event_metrics_30s", "event_type", "DimEvent", "event_type"),
    }
    actual_relationships = {
        (rel["fromTable"], rel["fromColumn"], rel["toTable"], rel["toColumn"])
        for rel in model["relationships"]
    }
    if actual_relationships != expected_relationships or len(model["relationships"]) != 3:
        errors.append("Unexpected relationship columns or missing relationships")
    for rel in model["relationships"]:
        # Desktop omits crossFilteringBehavior when it uses the oneDirection default.
        if rel.get("crossFilteringBehavior", "oneDirection") != "oneDirection" or rel["toTable"] not in ("DimRun", "DimEvent"):
            errors.append("Unexpected fact relationship")
    status = "failed" if errors else "incomplete" if unavailable_schemas else "pass"
    result = {"status": status, "schema_files_checked": checked, "schema_files_total": schema_files, "unavailable_schemas": unavailable_schemas, "pages": len(pages), "tables": len(tables), "measures": sum(len(t.get("measures", [])) for t in tables.values()), "errors": errors}
    (root / "evidence").mkdir(exist_ok=True)
    (root / "evidence/project_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(status != "pass")


if __name__ == "__main__":
    main()
