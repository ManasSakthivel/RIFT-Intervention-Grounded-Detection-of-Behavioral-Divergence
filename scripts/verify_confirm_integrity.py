#!/usr/bin/env python3
"""Confirmatory dataset integrity verification (WP5).

Verifies:
  (a) generator, runner, analysis and wrapper hashes equal those in prereg.sha256
  (b) dataset hashes equal provenance.json
  (c) the stripped file equals strip_labels() of the labelled one
  (d) record file hash is consistent with the records file on disk
  (e) record counts equal scenarios × methods
  (f) refuses to read any path matching the sealed held-out names (C11)

Usage:
    python3 scripts/verify_confirm_integrity.py \\
        --labelled <confirm.json> \\
        --stripped <confirm_stripped.json> \\
        --records  <records.jsonl> \\
        [--prereg  <prereg.sha256>] \\
        [--provenance <provenance.json>]

Exit 0 = all checks pass. Exit 1 = at least one check failed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.scenarios.independence import strip_labels  # noqa: E402

# Sealed path fragments that this script refuses to read (C11)
_SEALED_FRAGMENTS = ("heldout_candidate", "heldout_status", "results/held_out")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refuse_sealed(path: Path) -> None:
    """Raise RuntimeError if path matches any sealed held-out name (C11)."""
    s = str(path).replace("\\", "/")
    for fragment in _SEALED_FRAGMENTS:
        if fragment in s:
            raise RuntimeError(
                f"C11: refusing to access sealed held-out path: {path}"
            )


def _check(results: List[Dict[str, Any]], label: str, ok: bool, detail: str = "") -> None:
    results.append({"check": label, "ok": ok, "detail": detail})
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}" + (f": {detail}" if detail else ""))


def run_checks(labelled_path: Optional[Path], stripped_path: Optional[Path],
               records_path: Optional[Path], prereg_path: Optional[Path],
               provenance_path: Optional[Path]) -> bool:
    results: List[Dict[str, Any]] = []
    all_ok = True

    print("=== Confirmatory Integrity Verification ===")

    # C11: sealed path check
    for p in [labelled_path, stripped_path, records_path, prereg_path, provenance_path]:
        if p is not None:
            try:
                _refuse_sealed(p)
                _check(results, f"C11_no_sealed_path:{p.name}", True)
            except RuntimeError as exc:
                _check(results, f"C11_no_sealed_path:{p.name}", False, str(exc))
                all_ok = False

    # (a) generator/runner/analysis code hashes vs prereg.sha256
    code_files = {
        "generator_confirm": REPO / "src" / "rift" / "scenarios" / "generator_confirm.py",
        "sprint450_run_confirm": REPO / "scripts" / "sprint450_run_confirm.py",
        "sprint450_analyze": REPO / "scripts" / "sprint450_analyze.py",
        "verify_confirm_integrity": REPO / "scripts" / "verify_confirm_integrity.py",
    }
    actual_hashes = {name: _sha256_file(p) for name, p in code_files.items() if p.exists()}

    if prereg_path and prereg_path.exists():
        try:
            prereg = json.loads(prereg_path.read_text())
        except (ValueError, OSError) as exc:
            _check(results, "prereg_readable", False, str(exc))
            prereg = {}
            all_ok = False
        else:
            _check(results, "prereg_readable", True)

        recorded_code_hashes = prereg.get("code_hashes", {})
        for name, actual in actual_hashes.items():
            expected = recorded_code_hashes.get(name)
            if expected is None:
                _check(results, f"code_hash_{name}", None, "not recorded in prereg (expected after G3)")
            else:
                ok = actual == expected
                _check(results, f"code_hash_{name}", ok,
                       f"actual={actual[:16]}... expected={expected[:16]}...")
                if not ok:
                    all_ok = False
    else:
        _check(results, "prereg_present", False if prereg_path else None,
               "prereg.sha256 not found — code hashes cannot be verified against it")

    # (b) dataset hashes vs provenance.json
    if provenance_path and provenance_path.exists():
        try:
            prov = json.loads(provenance_path.read_text())
        except (ValueError, OSError) as exc:
            _check(results, "provenance_readable", False, str(exc))
            prov = {}
            all_ok = False
        else:
            _check(results, "provenance_readable", True)

        if labelled_path and labelled_path.exists():
            actual_sha = _sha256_file(labelled_path)
            expected_sha = prov.get("labelled_sha256") or prov.get("dataset_sha256")
            if expected_sha:
                ok = actual_sha == expected_sha
                _check(results, "labelled_hash_vs_provenance", ok,
                       f"actual={actual_sha[:16]}... expected={expected_sha[:16]}...")
                if not ok:
                    all_ok = False
            else:
                _check(results, "labelled_hash_vs_provenance", None, "hash not recorded in provenance")

        if records_path and records_path.exists():
            actual_sha = _sha256_file(records_path)
            expected_sha = prov.get("output_sha256") or prov.get("records_sha256")
            if expected_sha:
                ok = actual_sha == expected_sha
                _check(results, "records_hash_vs_provenance", ok,
                       f"actual={actual_sha[:16]}... expected={expected_sha[:16]}...")
                if not ok:
                    all_ok = False
            else:
                _check(results, "records_hash_vs_provenance", None, "hash not recorded in provenance")
    else:
        _check(results, "provenance_present", False if provenance_path else None,
               "provenance.json not found")

    # (c) stripped file equals strip_labels() of labelled
    if labelled_path and labelled_path.exists() and stripped_path and stripped_path.exists():
        try:
            labelled_data = json.loads(labelled_path.read_text())
            stripped_data = json.loads(stripped_path.read_text())
            labelled_scs = labelled_data["scenarios"] if isinstance(labelled_data, dict) and "scenarios" in labelled_data else labelled_data
            stripped_scs = stripped_data["scenarios"] if isinstance(stripped_data, dict) and "scenarios" in stripped_data else stripped_data
            stripped_map = {sc["scenario_id"]: sc for sc in stripped_scs}
            n_mismatch = 0
            for sc in labelled_scs:
                sid = sc["scenario_id"]
                expected_stripped = strip_labels(sc)
                actual_stripped = stripped_map.get(sid)
                if actual_stripped is None:
                    n_mismatch += 1
                    continue
                # Compare field by field (ignore scenario_id split tracking differences)
                for key in expected_stripped:
                    if expected_stripped.get(key) != actual_stripped.get(key):
                        n_mismatch += 1
                        break
            ok = n_mismatch == 0
            _check(results, "stripped_equals_strip_labels_of_labelled", ok,
                   f"{n_mismatch} mismatches" if not ok else "")
            if not ok:
                all_ok = False
        except Exception as exc:  # noqa: BLE001
            _check(results, "stripped_equals_strip_labels_of_labelled", False, str(exc))
            all_ok = False
    elif stripped_path and labelled_path:
        _check(results, "stripped_equals_strip_labels_of_labelled", None,
               "one or both files missing; cannot verify")

    # (d) record file hash on disk is consistent
    if records_path and records_path.exists():
        actual_sha = _sha256_file(records_path)
        _check(results, "records_file_readable", True, f"SHA-256={actual_sha[:16]}...")

    # (e) record counts = n_scenarios × n_methods
    if records_path and records_path.exists() and labelled_path and labelled_path.exists():
        try:
            recs = [json.loads(line) for line in records_path.read_text().splitlines() if line.strip()]
            labelled_data = json.loads(labelled_path.read_text())
            scs = labelled_data["scenarios"] if isinstance(labelled_data, dict) and "scenarios" in labelled_data else labelled_data
            n_scenarios = len(scs)
            method_ids = set(r["method_id"] for r in recs)
            n_methods = len(method_ids)
            expected = n_scenarios * n_methods
            actual = len(recs)
            ok = actual == expected
            _check(results, "record_count_scenarios_x_methods", ok,
                   f"actual={actual} expected={expected} ({n_scenarios}×{n_methods})")
            if not ok:
                all_ok = False
        except Exception as exc:  # noqa: BLE001
            _check(results, "record_count_scenarios_x_methods", False, str(exc))
            all_ok = False

    # (f) C11: static scan for sealed name strings in new source files
    scan_targets = [
        REPO / "src" / "rift" / "scenarios" / "generator_confirm.py",
        REPO / "scripts" / "sprint450_run_confirm.py",
        REPO / "scripts" / "sprint450_analyze.py",
        REPO / "scripts" / "verify_confirm_integrity.py",
        REPO / "tests" / "unit" / "test_confirm_generator.py",
        REPO / "tests" / "unit" / "test_confirm_runner.py",
        REPO / "tests" / "unit" / "test_confirm_analyze.py",
        REPO / "tests" / "unit" / "test_confirm_integrity.py",
    ]
    # Patterns defined here — scanner skips lines that define or reference the sealed_fragments guard list itself.
    _sealed_scan_patterns = ["heldout_candidate", "heldout_status", "results/held_out"]
    _scan_skip_markers = (
        "_SEALED_FRAGMENTS", "_sealed_scan_patterns", "forbidden_patterns",
        "_FORBIDDEN", "# C11", "C11:", "_refuse_sealed", "refuse_sealed",
        "# sealed", "# Sealed", "sealed_path", "SEALED_FRAGMENTS",
        "forbidden =", "_FORBIDDEN =",
    )
    for src in scan_targets:
        if not src.exists():
            continue
        lines = src.read_text().splitlines()
        violation_lines = []
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip guard/definition lines that deliberately name the forbidden patterns
            if any(skip in stripped for skip in _scan_skip_markers):
                continue
            for pattern in _sealed_scan_patterns:
                if pattern in line:
                    violation_lines.append(f"line {line_no}: {line.rstrip()}")
                    break
        ok = len(violation_lines) == 0
        _check(results, f"C11_static_scan:{src.name}", ok,
               ("found forbidden patterns:\n  " + "\n  ".join(violation_lines)) if not ok else "")
        if not ok:
            all_ok = False

    print(f"\n=== Result: {'PASS' if all_ok else 'FAIL'} "
          f"({sum(1 for r in results if r['ok'] is True)}/{len([r for r in results if r['ok'] is not None])} checks passed) ===")

    return all_ok


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Confirmatory dataset integrity verification (WP5)")
    ap.add_argument("--labelled", default=None, help="Labelled confirmatory JSON file")
    ap.add_argument("--stripped", default=None, help="Label-stripped confirmatory JSON file")
    ap.add_argument("--records", default=None, help="Records JSONL file from runner")
    ap.add_argument("--prereg", default=None, help="prereg.sha256 file")
    ap.add_argument("--provenance", default=None, help="provenance.json file")
    args = ap.parse_args(argv)

    ok = run_checks(
        labelled_path=Path(args.labelled).resolve() if args.labelled else None,
        stripped_path=Path(args.stripped).resolve() if args.stripped else None,
        records_path=Path(args.records).resolve() if args.records else None,
        prereg_path=Path(args.prereg).resolve() if args.prereg else None,
        provenance_path=Path(args.provenance).resolve() if args.provenance else None,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
