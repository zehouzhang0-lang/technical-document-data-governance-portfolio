# Verification record

## Original delivery: local read-only audit

| Check | Result |
| --- | --- |
| Root-tree directories | Tens; exact source-derived count withheld |
| Tree-level formal JSON occurrences | Hundreds; exact count withheld |
| Delivered formal JSON files | More than one hundred; exact count withheld |
| JSON parse checks | PASS for all delivered files |
| Top-level field-set checks | PASS for all delivered files |
| Reference-record field-set checks | PASS for all recorded references |
| Delivered filename uniqueness | PASS |
| Raw-byte SHA-256 duplicate check | PASS |
| Manifest reconciliation | PASS |
| Coverage reconciliation | PASS |
| Same-name, byte-different candidates | Multiple groups retained |
| Normalized semantic duplicate review | Multiple groups identified |

These checks establish file integrity and mapping behavior. They do not prove
item-level semantic accuracy.

## Portfolio archive

The portfolio archive is verified independently by:

```bash
python scripts/security_scan.py
python scripts/verify_demo.py
```

The first command rejects forbidden source artifacts and common secret/PII/path
patterns. The second validates the synthetic JSON, manifest, coverage, and
variant example. The synthetic demo demonstrates the method without revealing
source data or exact source-derived project statistics.
