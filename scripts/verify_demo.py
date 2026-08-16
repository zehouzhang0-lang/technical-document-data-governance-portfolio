#!/usr/bin/env python3
"""Validate the fully synthetic portfolio demonstration.

This verifier was created during portfolio archiving. It demonstrates an
improved two-level duplicate check (raw bytes and canonical JSON) and does not
claim to be the original project pipeline.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "synthetic"
FORMAL = DEMO / "01_formal_json"
NOTES = DEMO / "02_review_notes"

TOP_LEVEL_FIELDS = {
    "source_path",
    "spec_code",
    "spec_code_key",
    "revision",
    "title",
    "references",
}
REFERENCE_FIELDS = {
    "code",
    "code_key",
    "title",
    "revision",
    "order",
    "source_line",
    "source_path",
    "source_page",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def duplicate_group_count(values: list[str]) -> int:
    return sum(1 for count in Counter(values).values() if count > 1)


def validate_document(path: Path, value: Any) -> None:
    require(isinstance(value, dict), f"{path.name}: document must be an object")
    require(set(value) == TOP_LEVEL_FIELDS, f"{path.name}: top-level field mismatch")
    require(isinstance(value["references"], list), f"{path.name}: references must be a list")
    require(
        isinstance(value["source_path"], str)
        and value["source_path"].startswith("synthetic://"),
        f"{path.name}: source_path must be synthetic",
    )
    require(isinstance(value["spec_code"], str), f"{path.name}: invalid spec_code")
    require(isinstance(value["spec_code_key"], str), f"{path.name}: invalid spec_code_key")
    require(isinstance(value["revision"], str), f"{path.name}: invalid revision")
    require(isinstance(value["title"], str), f"{path.name}: invalid title")

    orders: list[int] = []
    for index, reference in enumerate(value["references"]):
        require(isinstance(reference, dict), f"{path.name}: reference {index} must be an object")
        require(set(reference) == REFERENCE_FIELDS, f"{path.name}: reference {index} field mismatch")
        require(isinstance(reference["order"], int), f"{path.name}: reference {index} invalid order")
        require(
            isinstance(reference["source_page"], int) and reference["source_page"] >= 1,
            f"{path.name}: reference {index} invalid page",
        )
        require(
            isinstance(reference["source_path"], str)
            and reference["source_path"].startswith("synthetic://"),
            f"{path.name}: reference {index} source_path must be synthetic",
        )
        for key in ("code", "code_key", "title", "revision", "source_line"):
            require(isinstance(reference[key], str), f"{path.name}: reference {index} invalid {key}")
        orders.append(reference["order"])
    require(orders == list(range(len(orders))), f"{path.name}: reference order is not contiguous")


def main() -> int:
    expected = json.loads((DEMO / "expected_metrics.json").read_text(encoding="utf-8"))
    files = sorted(FORMAL.glob("*.json"))
    require(len(files) == expected["formal_json_files"], "formal JSON count mismatch")

    documents: dict[str, dict[str, Any]] = {}
    raw_hashes: dict[str, str] = {}
    canonical_hashes: dict[str, str] = {}
    for path in files:
        value = json.loads(path.read_text(encoding="utf-8"))
        validate_document(path, value)
        documents[path.name] = value
        raw_hashes[path.name] = raw_sha256(path)
        canonical_hashes[path.name] = canonical_sha256(value)

    raw_duplicate_groups = duplicate_group_count(list(raw_hashes.values()))
    canonical_duplicate_groups = duplicate_group_count(list(canonical_hashes.values()))
    require(raw_duplicate_groups == expected["duplicate_raw_byte_groups"], "raw duplicate count mismatch")
    require(
        canonical_duplicate_groups == expected["duplicate_canonical_json_groups"],
        "canonical duplicate count mismatch",
    )

    manifest = read_csv(NOTES / "formal_json_manifest.csv")
    require(len(manifest) == expected["manifest_rows"], "manifest row count mismatch")
    manifest_names = [row["delivered_filename"] for row in manifest]
    require(len(manifest_names) == len(set(manifest_names)), "manifest filenames are not unique")
    require(set(manifest_names) == set(documents), "manifest/file set mismatch")
    for row in manifest:
        name = row["delivered_filename"]
        document = documents[name]
        require(row["sha256"] == raw_hashes[name], f"{name}: manifest hash mismatch")
        require(row["spec_code"] == document["spec_code"], f"{name}: manifest code mismatch")
        require(row["revision"] == document["revision"], f"{name}: manifest revision mismatch")
        require(int(row["reference_count"]) == len(document["references"]), f"{name}: reference count mismatch")

    coverage = read_csv(NOTES / "tree_input_record_coverage.csv")
    require(len(coverage) == expected["coverage_rows"], "coverage row count mismatch")
    coverage_keys: set[tuple[str, str]] = set()
    for row in coverage:
        key = (row["source_tree"], row["source_filename"])
        require(key not in coverage_keys, f"duplicate coverage key: {key}")
        coverage_keys.add(key)
        name = row["delivered_filename"]
        require(name in documents, f"coverage points to missing file: {name}")
        require(row["source_sha256"] == row["delivered_sha256"], f"coverage source/delivery hash mismatch: {key}")
        require(row["delivered_sha256"] == raw_hashes[name], f"coverage delivered hash mismatch: {key}")
        require(row["coverage_status"] == "COVERED_BY_BYTE_HASH_SELECTION", f"coverage status mismatch: {key}")

    variants = read_csv(NOTES / "same_filename_candidate_variants.csv")
    require(len(variants) == expected["variant_rows"], "variant row count mismatch")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in variants:
        grouped[row["source_filename"]].append(row)
        name = row["delivered_filename"]
        require(name in documents, f"variant points to missing file: {name}")
        require(row["raw_sha256"] == raw_hashes[name], f"variant hash mismatch: {name}")
    require(len(grouped) == expected["same_name_candidate_groups"], "variant group count mismatch")
    for source_name, rows in grouped.items():
        require(len(rows) >= 2, f"candidate group has fewer than two rows: {source_name}")
        require(
            len({row["raw_sha256"] for row in rows}) == len(rows),
            f"candidate group raw hashes are not unique: {source_name}",
        )

    recursive_trees = json.loads((DEMO / "recursive_trees.json").read_text(encoding="utf-8"))
    require(isinstance(recursive_trees, list) and len(recursive_trees) == 2, "recursive tree demo mismatch")

    summary = {
        "status": "PASS",
        "formal_json_files": len(files),
        "manifest_rows": len(manifest),
        "coverage_rows": len(coverage),
        "same_name_candidate_groups": len(grouped),
        "raw_duplicate_groups": raw_duplicate_groups,
        "canonical_duplicate_groups": canonical_duplicate_groups,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
