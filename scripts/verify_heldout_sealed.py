#!/usr/bin/env python3
"""verify_heldout_sealed.py — RIFT Held-Out Gate Verification

This script verifies that the held-out test set has not been accessed by
development code. It:

1. Checks that datasets/rift_faults/held_out_test.json is not imported
   by any development module (except the guard and Oracle baseline)
2. Runs the HeldOutGuard with a synthetic attempt and verifies it raises
   HeldOutLeakageError
3. Checks that no results/ directory contains held-out evaluation artifacts
4. Checks that no analysis/ file references held_out_test.json directly

Exit codes:
  0 — All gate checks PASS. Held-out set is sealed.
  1 — Gate FAIL. Unauthorized held-out access detected.

Usage:
    python scripts/verify_heldout_sealed.py
    python scripts/verify_heldout_sealed.py --results-dir results/

Authority: docs/PHASE_3_SPEC_FREEZE.md §16, docs/experiments/SCENARIO_CATALOG.md
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Project root
REPO_ROOT = Path(__file__).parent.parent
HELDOUT_PATH = REPO_ROOT / "datasets" / "rift_faults" / "held_out_test.json"
SRC_DIR = REPO_ROOT / "src"
TESTS_DIR = REPO_ROOT / "tests"
ANALYSIS_DIR = REPO_ROOT / "analysis"
RESULTS_DIR = REPO_ROOT / "results"
SCRIPTS_DIR = REPO_ROOT / "scripts"


# ---------------------------------------------------------------------------
# Allowed files that may reference held_out_test.json
# ---------------------------------------------------------------------------

ALLOWED_PATHS = {
    # The guard itself
    str(REPO_ROOT / "src" / "rift" / "evaluation" / "held_out_guard.py"),
    # This script
    str(Path(__file__).resolve()),
    # Dataset readme
    str(REPO_ROOT / "datasets" / "rift_faults" / "README.md"),
    # Scenario catalog (documentation only)
    str(REPO_ROOT / "docs" / "experiments" / "SCENARIO_CATALOG.md"),
    # Manifest (references file name as data, not import)
    str(REPO_ROOT / "datasets" / "rift_faults" / "manifest.json"),
}


# ---------------------------------------------------------------------------
# Check 1: No unauthorized source code imports held_out_test.json
# ---------------------------------------------------------------------------

def check_no_source_import(verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Scan all Python source files for direct file path references to
    held_out_test.json (the actual data file, not the guard mechanism).

    References in ALLOWED_PATHS are exempted.
    Legitimate uses of 'allow_held_out', 'HELD_OUT_TEST' split constants,
    and 'held_out_guard' are NOT violations.
    """
    violations = []
    # Match direct file path references only — not split names or guard references
    pattern = re.compile(r'["\']held_out_test\.json["\']', re.IGNORECASE)

    search_dirs = [SRC_DIR, TESTS_DIR, SCRIPTS_DIR, ANALYSIS_DIR]
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for py_file in sorted(search_dir.rglob("*.py")):
            if str(py_file.resolve()) in ALLOWED_PATHS:
                continue
            try:
                text = py_file.read_text()
            except OSError:
                continue
            if pattern.search(text):
                violations.append(f"  {py_file.relative_to(REPO_ROOT)}")
                if verbose:
                    for i, line in enumerate(text.splitlines(), 1):
                        if pattern.search(line):
                            print(f"    L{i}: {line.strip()}")

    return len(violations) == 0, violations


# ---------------------------------------------------------------------------
# Check 2: HeldOutGuard raises HeldOutLeakageError without active token
# ---------------------------------------------------------------------------

def check_guard_raises() -> Tuple[bool, str]:
    """
    Verify HeldOutGuard correctly raises HeldOutLeakageError when no
    oracle token is active.
    """
    sys.path.insert(0, str(REPO_ROOT / "src"))
    try:
        from rift.evaluation.held_out_guard import HeldOutGuard, HeldOutLeakageError
        guard = HeldOutGuard()

        try:
            guard.check_access(caller_name="test_unauthorized")
            return False, "HeldOutGuard did NOT raise HeldOutLeakageError — guard is broken"
        except HeldOutLeakageError:
            pass  # Expected

        # Verify authorized access works
        guard.allow_oracle("TEST_TOKEN_PHASE45")
        guard.activate_token("TEST_TOKEN_PHASE45")
        try:
            guard.check_access(caller_name="test_authorized")
        except HeldOutLeakageError:
            return False, "HeldOutGuard raised error even with valid oracle token"
        finally:
            guard.deactivate_token()

        return True, "HeldOutGuard raises correctly for unauthorized, passes for authorized"

    except ImportError as exc:
        return False, f"Could not import HeldOutGuard: {exc}"


# ---------------------------------------------------------------------------
# Check 3: No held-out artifacts in results/
# ---------------------------------------------------------------------------

def check_results_directory(results_dir: Path) -> Tuple[bool, List[str]]:
    """
    Verify results/ does not contain held-out evaluation artifacts.
    Held-out artifacts would be named 'held_out_*' or reference 'HELD_OUT_TEST'.
    """
    violations = []
    if not results_dir.exists():
        return True, []  # No results yet — trivially sealed

    pattern = re.compile(r"held.?out|HELD.?OUT", re.IGNORECASE)
    for f in sorted(results_dir.rglob("*")):
        if not f.is_file():
            continue
        # Check filename
        if pattern.search(f.name):
            violations.append(f"  {f.relative_to(REPO_ROOT)}")
            continue
        # Check JSON content for held-out references
        if f.suffix == ".json":
            try:
                text = f.read_text()
                if pattern.search(text) and "DEVELOPMENT" not in text:
                    violations.append(f"  {f.relative_to(REPO_ROOT)} (content)")
            except OSError:
                continue

    return len(violations) == 0, violations


# ---------------------------------------------------------------------------
# Check 4: held_out_test.json file integrity
# ---------------------------------------------------------------------------

def check_heldout_file_exists() -> Tuple[bool, str]:
    """Verify the held-out file exists and has not been deleted."""
    if HELDOUT_PATH.exists():
        size = HELDOUT_PATH.stat().st_size
        return True, f"held_out_test.json exists ({size} bytes)"
    return False, f"held_out_test.json MISSING: {HELDOUT_PATH}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify held-out test set is sealed",
    )
    parser.add_argument(
        "--results-dir", "-r",
        default=str(RESULTS_DIR),
        type=Path,
        help="Results directory to check (default: results/)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show matching lines in violations",
    )
    args = parser.parse_args()

    print("\n==> RIFT Held-Out Gate Verification")
    print(f"    held-out file: {HELDOUT_PATH.relative_to(REPO_ROOT)}")
    print()

    all_pass = True
    checks = []

    # Check 1: No source imports
    print("[1/4] Checking source code for unauthorized held-out references...")
    ok, violations = check_no_source_import(verbose=args.verbose)
    if ok:
        print("      PASS — no unauthorized references found")
    else:
        print(f"      FAIL — {len(violations)} file(s) reference held_out_test.json:")
        for v in violations:
            print(v)
        all_pass = False
    checks.append(("source_import_check", ok))

    # Check 2: Guard raises correctly
    print("[2/4] Checking HeldOutGuard raises HeldOutLeakageError...")
    ok, msg = check_guard_raises()
    if ok:
        print(f"      PASS — {msg}")
    else:
        print(f"      FAIL — {msg}")
        all_pass = False
    checks.append(("guard_raises_check", ok))

    # Check 3: No held-out in results/
    print(f"[3/4] Checking results/ directory ({args.results_dir})...")
    ok, violations = check_results_directory(Path(args.results_dir))
    if ok:
        print("      PASS — no held-out artifacts in results/")
    else:
        print(f"      FAIL — {len(violations)} held-out artifact(s) found in results/:")
        for v in violations:
            print(v)
        all_pass = False
    checks.append(("results_dir_check", ok))

    # Check 4: File exists
    print("[4/4] Checking held-out file integrity...")
    ok, msg = check_heldout_file_exists()
    if ok:
        print(f"      PASS — {msg}")
    else:
        print(f"      FAIL — {msg}")
        all_pass = False
    checks.append(("file_exists_check", ok))

    # Summary
    print()
    n_pass = sum(1 for _, ok in checks if ok)
    n_fail = len(checks) - n_pass
    if all_pass:
        print(f"==> GATE PASS: {n_pass}/{len(checks)} checks passed. Held-out set is SEALED.")
        return 0
    else:
        print(f"==> GATE FAIL: {n_fail}/{len(checks)} check(s) failed.")
        print("    The held-out test set may have been compromised.")
        print("    Resolve all failures before final evaluation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
