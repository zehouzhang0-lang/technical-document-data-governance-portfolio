# Synthetic demonstration

Every identifier, title, source line, path, and relationship in this directory
is fictional. The files demonstrate the delivery structure and QA rules without
reproducing source material.

The example contains two root trees and five tree-level formal JSON records.
Both trees contain a source file named `SPEC_ALPHA.json`, but the two versions
have different normalized content. The delivery therefore keeps one ordinary
filename and renames the second variant. A missing mapped file remains a
terminal leaf in `recursive_trees.json` and does not receive a formal JSON file.

`scripts/verify_demo.py` checks both raw-byte SHA-256 and canonical JSON hashes,
so formatting-only duplicates would be detected in a future extension.
