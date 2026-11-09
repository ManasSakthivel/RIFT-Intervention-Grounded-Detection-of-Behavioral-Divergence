#!/usr/bin/env python3
"""Re-verify cross-split independence of the v2 datasets from the files on disk (Protocol v2 §12).

Reads only scenario *structure* (labels are stripped before analysis). Writes the result, bound to the held-out file
hash, into datasets/rift_v2/independence_report.json. Exit code 0 iff independent.

    python3 scripts/sprint430_verify_independence.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.scenarios.independence import strip_labels, verify_independence  # noqa: E402

V2 = REPO_ROOT / "datasets" / "rift_v2"
FILES = {"dev": "dev.json", "val": "val.json", "held_out": "heldout_candidate.json"}


def verify(root: Path = V2) -> dict:
    splits, hashes = {}, {}
    for sp, fn in FILES.items():
        raw = (root / fn).read_bytes()
        hashes[sp] = hashlib.sha256(raw).hexdigest()
        splits[sp] = [strip_labels(s) for s in json.loads(raw)["scenarios"]]
    rep = verify_independence(splits)
    rep["heldout_sha256"] = hashes["held_out"]
    rep["dataset_sha256"] = hashes
    rep["verified_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rep["labels_stripped_before_analysis"] = True
    return rep


def main() -> int:
    check = "--check" in sys.argv[1:]
    rep = verify()
    if check:   # read-only: safe after the freeze (the stored report is a frozen file)
        stored = json.loads((V2 / "independence_report.json").read_text())
        same = stored.get("ok") is True and stored.get("heldout_sha256") == rep["heldout_sha256"]
        print(json.dumps({"mode": "check(no write)", "recomputed_ok": rep["ok"], "stored_report_consistent": same,
                          "leaks_for_protected": rep["leaks_for_protected"]}, indent=1))
        return 0 if (rep["ok"] and same) else 1
    (V2 / "independence_report.json").write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"ok": rep["ok"], "leaks_for_protected": rep["leaks_for_protected"],
                      "group_integrity_violations": len(rep["group_integrity_violations"]),
                      "cross_split_near_duplicates": len(rep["near_duplicate_pairs_cross_split"]),
                      "distinct_keys_per_split": rep["distinct_keys_per_split"],
                      "unseen_in_heldout": rep["unseen_in_protected_vs_other_splits"],
                      "heldout_sha256": rep["heldout_sha256"]}, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
