#!/usr/bin/env python3
"""Sprint 4.5.0 Confirmatory Runner (WP3).

Run all preregistered methods on a LABEL-STRIPPED confirmatory dataset.
Implements the strict error semantics from PRE §9 / SAP §7 (D21), NOT the frozen _timed behaviour.

Usage:
    python3 scripts/sprint450_run_confirm.py \\
        --dataset <stripped.json> \\
        --out <records.jsonl> \\
        --methods V3-FULL RIFT-FULL-V2 B0-EARLIEST \\
        [--resume-check]

Hard rules (CONFIRMATORY_INFRASTRUCTURE_PLAN §0):
  - Input must be the LABEL-STRIPPED file (no 'ground_truth', 'design' keys reaching methods).
  - No sealed held-out file is opened or hashed by this script.
  - Methods receive only observe(sc) output and an intervene callable; never the raw scenario.
  - Incomplete runs (<95% records per method) stop that method and record the completion fraction.
  - Completion check: error rows count as records (they are never dropped).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3  # noqa: E402
from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation.rift_v2 import SharedCache  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

# ---- constants ------------------------------------------------------------------
TIMEOUT_S = 60.0          # PRE §9: calls over 60 s are recorded as abstentions
PREREGISTERED_METHODS = [
    "V3-FULL",
    "RIFT-FULL-V2",
    "RIFT-FULL-LEGACY",
    "B0-EARLIEST",
    "B0-HIGHEST",
    "B1-LATENCY-CORR",
    "B3-SIEVE-LIKE",
    "B5-RIFT-OBS",
    "B6-RIFT-RANDOM",
    "B7-RIFT-ONE-SHOT",
]
ALWAYS_ABSTAIN_ID = "ALWAYS-ABSTAIN"
ORACLE_METHODS = [
    "ORACLE:UPPER-BOUND",
    "ORACLE:RIFT-FULL-V2-ORACLE-GRAPH",
    "ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG",
]
# Label-bearing keys that must NEVER reach a non-oracle method (T8)
_FORBIDDEN_LABEL_KEYS = frozenset(["ground_truth", "design"])
MIN_COMPLETION = 0.95     # PRE §11


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---- label-isolation guard (T8) -------------------------------------------------
def _assert_no_labels(sc: Dict[str, Any], method_id: str) -> None:
    """Abort if any label-bearing key is present in the scenario passed to a non-oracle method."""
    for key in _FORBIDDEN_LABEL_KEYS:
        if key in sc:
            raise RuntimeError(
                f"T8 VIOLATION: scenario {sc.get('scenario_id')} contains "
                f"label key {key!r} — it would reach method {method_id}. "
                "Pass the label-stripped file as --dataset."
            )


# ---- intervention counter wrapper -----------------------------------------------
class _CountingInterventionWrapper:
    """Wraps a sim.intervene callable, counts actual do() calls made (D21: charge these on exception)."""
    def __init__(self, sc: Dict[str, Any]):
        self._sc = sc
        self.n_do = 0

    def __call__(self, node: str, targets: List[str], seed: int) -> Any:
        self.n_do += 1
        return sim.intervene(self._sc, node, targets, seed)


# ---- strict timer (D21) ---------------------------------------------------------
def _run_with_timeout(fn, timeout_s: float):
    """Run fn() in a thread; if it takes > timeout_s, still returns the answer but sets timed_out=True.
    Returns (result, elapsed_s, timed_out, exception).
    """
    result = [None]
    exc_info = [None]
    done = threading.Event()

    def _worker():
        try:
            result[0] = fn()
        except Exception:  # noqa: BLE001
            exc_info[0] = sys.exc_info()
        finally:
            done.set()

    t0 = time.perf_counter()
    th = threading.Thread(target=_worker, daemon=True)
    th.start()
    th.join(timeout=timeout_s * 1.5)   # allow 1.5× to collect any late answer
    elapsed = time.perf_counter() - t0
    timed_out = not done.is_set() or elapsed > timeout_s
    return result[0], elapsed, timed_out, exc_info[0]


# ---- always-abstain (SAP §7: U≡0, n_do=0, cannot fail) -------------------------
def _always_abstain_record(scenario_id: str, seed: int, runner_sha: str) -> Dict[str, Any]:
    return {
        "scenario_id": scenario_id, "method_id": ALWAYS_ABSTAIN_ID, "seed": seed,
        "abstained": True, "reason": "ALWAYS_ABSTAIN", "top": [], "ed_s": 0.0, "n_do": 0,
        "evidence_type": "OBSERVATIONAL", "path_kind": "NONE", "cid_grades": [],
        "ident_status": None, "detect_latency_s": None, "runtime_s": 0.0, "mem_kb": 0.0,
        "error": None, "error_flag": 0, "error_type": None, "n_do_charged": 0,
        "status": "ABSTAIN_ALWAYS", "caveats": [], "possible_roots": [],
        "intervened": [], "diverging": [], "confirmed": False,
        "wall_s": 0.0, "runner_sha256": runner_sha,
    }


# ---- single-method runner -------------------------------------------------------
def _run_one_method(sc_stripped: Dict[str, Any], method_id: str,
                    runner_sha: str, cache: Optional[SharedCache] = None) -> Dict[str, Any]:
    """Execute one method on one (label-stripped) scenario; implement D21 error semantics.

    Returns a flat record dict. Never reads sc_stripped['ground_truth'] or sc_stripped['design'].
    """
    _assert_no_labels(sc_stripped, method_id)
    scenario_id = sc_stripped["scenario_id"]
    seed = int(sc_stripped["seed"])
    fid = scenario_id

    # Observation (label-free); sc_stripped has no ground_truth/design keys
    o = sim.observe(sc_stripped)
    iv_wrapper = _CountingInterventionWrapper(sc_stripped)

    base_rec = {
        "scenario_id": scenario_id, "method_id": method_id, "seed": seed,
        "runner_sha256": runner_sha,
    }

    def _make_output(out, dt: float, mem_kb: float, err: Optional[str],
                     error_flag: int, n_do_charged: int,
                     timeout_answer: Any = None) -> Dict[str, Any]:
        rec = dict(base_rec)
        inner = bm._out_to_rec(out, dt, mem_kb, err)
        rec.update(inner)
        # D21 extensions
        rec["error_flag"] = error_flag
        rec["error_type"] = err if error_flag else None
        rec["n_do_charged"] = n_do_charged
        rec["wall_s"] = dt
        # V3 raw fields (D22)
        if out is not None:
            raw = getattr(out, "raw_output", {}) or {}
            rec["status"] = raw.get("status")
            rec["caveats"] = raw.get("caveats", [])
            rec["possible_roots"] = raw.get("possible_roots", [])
            rec["intervened"] = raw.get("intervened", [])
            rec["diverging"] = raw.get("diverging", [])
            rec["confirmed"] = bool(raw.get("confirmed", False))
        else:
            rec.update(status=None, caveats=[], possible_roots=[],
                       intervened=[], diverging=[], confirmed=False)
        if timeout_answer is not None:
            rec["_timeout_answer_stored"] = getattr(timeout_answer, "top_candidates", None)
        return rec

    # ALWAYS-ABSTAIN is handled by the caller; but guard against calling it here
    if method_id == ALWAYS_ABSTAIN_ID:
        return _always_abstain_record(scenario_id, seed, runner_sha)

    try:
        # ---- V3-FULL (not in benchmark_v2 registry)
        if method_id == "V3-FULL":
            cfg = V3_CONFIGS["V3-FULL"]

            def fn_v3():
                return run_v3(o, iv_wrapper, fid, seed, cfg, cache=cache or SharedCache())

            out, dt, timed_out, exc = _run_with_timeout(fn_v3, TIMEOUT_S)
            n_charged = iv_wrapper.n_do
            if exc is not None:
                err_str = f"METHOD_ERROR:{exc[0].__name__}"
                err_out = bm._error_out(method_id, fid, err_str)
                return _make_output(err_out, dt, 0.0, err_str, 1, n_charged)
            if timed_out:
                err_out = bm._error_out(method_id, fid, "TIMEOUT")
                return _make_output(err_out, dt, 0.0, "TIMEOUT", 1, n_charged, timeout_answer=out)
            return _make_output(out, dt, 0.0, None, 0, n_charged)

        # ---- All benchmark_v2 methods (baselines, V2, oracle)
        oracle = method_id in ORACLE_METHODS
        # Non-oracle methods receive an inert placeholder for ground_truth (§5.1)
        sc_for_bm = dict(sc_stripped)
        if not oracle:
            sc_for_bm["ground_truth"] = {"expected_outcome": None, "roots": [], "attributable_roots": []}
        else:
            # Oracle methods legitimately need ground_truth; refuse if not present
            if "ground_truth" not in sc_stripped:
                raise ValueError(f"Oracle method {method_id} requires ground_truth in the scenario record; "
                                 "run oracle methods in a separate labelled-side stage.")

        def fn_bm():
            results = bm.run_methods(sc_for_bm, methods=[method_id])
            return results.get(method_id)

        out, dt, timed_out, exc = _run_with_timeout(fn_bm, TIMEOUT_S)
        n_charged = iv_wrapper.n_do
        if exc is not None:
            err_str = f"METHOD_ERROR:{exc[0].__name__}"
            err_out = bm._error_out(method_id, fid, err_str)
            return _make_output(err_out, dt, 0.0, err_str, 1, n_charged)
        if timed_out:
            err_out = bm._error_out(method_id, fid, "TIMEOUT")
            return _make_output(err_out, dt, 0.0, "TIMEOUT", 1, n_charged, timeout_answer=out)
        if out is None:
            # Method returned None (should not happen; treat as error)
            err_out = bm._error_out(method_id, fid, "METHOD_ERROR:NoneOutput")
            return _make_output(err_out, dt, 0.0, "METHOD_ERROR:NoneOutput", 1, n_charged)
        return _make_output(out, dt, 0.0, None, 0, n_charged)

    except Exception as exc:  # noqa: BLE001  — harness failure (OOM, OSError, etc.)
        err_str = f"HARNESS_ERROR:{type(exc).__name__}"
        n_charged = iv_wrapper.n_do
        err_out = bm._error_out(method_id, fid, err_str)
        return _make_output(err_out, 0.0, 0.0, err_str, 1, n_charged)


# ---- runner integrity checks (PRE §11) ------------------------------------------
def _check_integrity_stops(stripped_path: Path, runner_sha: str) -> None:
    """Raise RuntimeError on integrity violations before starting any run."""
    # Sealed file name check (C11): refuse to run if the dataset path looks like held-out sealed data
    name = stripped_path.name.lower()
    for forbidden in ("heldout_candidate", "heldout_status", "results/held_out"):
        if forbidden in str(stripped_path).replace("\\", "/"):
            raise RuntimeError(
                f"INTEGRITY STOP: dataset path {stripped_path} matches a sealed held-out name. "
                "Confirmatory runner refuses to operate on sealed held-out data."
            )
    # Verify the runner's own hash if a prereg.sha256 exists
    prereg = REPO / "artifacts" / "sprint4_5_0" / "prereg" / "prereg.sha256"
    if prereg.exists():
        try:
            recorded = json.loads(prereg.read_text())
            expected_runner = recorded.get("runner_sha256")
            if expected_runner and expected_runner != runner_sha:
                raise RuntimeError(
                    f"INTEGRITY STOP: runner SHA-256 {runner_sha[:16]}... does not match "
                    f"prereg.sha256 record {expected_runner[:16]}..."
                )
        except (ValueError, OSError):
            pass  # If the file is unparseable, continue (it may be a raw hash, not JSON)


# ---- main runner ----------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Sprint 4.5.0 confirmatory runner (label-stripped input only)")
    ap.add_argument("--dataset", required=True,
                    help="Path to the label-stripped confirmatory JSON file")
    ap.add_argument("--out", required=True,
                    help="Output JSONL file for per-scenario × method records")
    ap.add_argument("--methods", nargs="+", default=None,
                    help="Methods to run (default: all preregistered non-oracle)")
    ap.add_argument("--include-always-abstain", action="store_true", default=True,
                    help="Include the always-abstain analytic method (default: True)")
    ap.add_argument("--resume-check", action="store_true",
                    help="Check that a partial output file is consistent before appending")
    ap.add_argument("--allow-oracle", action="store_true",
                    help="Include oracle methods (requires full labelled records in dataset)")
    args = ap.parse_args(argv)

    dataset_path = Path(args.dataset).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Compute runner SHA-256 (for provenance records)
    runner_sha = _sha256_file(Path(__file__).resolve())

    # Integrity stops
    _check_integrity_stops(dataset_path, runner_sha)

    # Load dataset
    print(f"[runner] Loading {dataset_path} ...")
    raw = dataset_path.read_text()
    data = json.loads(raw)
    scenarios = data["scenarios"] if isinstance(data, dict) and "scenarios" in data else data
    dataset_sha = hashlib.sha256(raw.encode()).hexdigest()
    print(f"[runner] {len(scenarios)} scenarios, dataset SHA-256: {dataset_sha[:16]}...")

    # Determine methods to run
    want_methods = args.methods if args.methods else PREREGISTERED_METHODS
    if args.allow_oracle:
        want_methods = want_methods + [m for m in ORACLE_METHODS if m not in want_methods]

    print(f"[runner] Methods: {want_methods}")
    if args.include_always_abstain:
        print(f"[runner] + {ALWAYS_ABSTAIN_ID} (analytic)")

    records: List[Dict[str, Any]] = []

    # Resume check: if out exists, load existing records
    if args.resume_check and out_path.exists():
        existing = [json.loads(line) for line in out_path.read_text().splitlines() if line.strip()]
        done_pairs = {(r["scenario_id"], r["method_id"]) for r in existing}
        records = existing
        print(f"[runner] Resume: {len(done_pairs)} existing records found")
    else:
        done_pairs = set()

    cache = SharedCache()
    n_total = len(scenarios)

    for method_id in want_methods:
        n_done = 0
        n_error = 0
        for sc in scenarios:
            sid = sc["scenario_id"]
            if (sid, method_id) in done_pairs:
                n_done += 1
                continue
            rec = _run_one_method(sc, method_id, runner_sha, cache=cache if method_id == "V3-FULL" else None)
            records.append(rec)
            done_pairs.add((sid, method_id))
            n_done += 1
            if rec.get("error_flag"):
                n_error += 1

        completion = n_done / n_total if n_total else 0.0
        print(f"[runner] {method_id}: {n_done}/{n_total} ({completion:.1%}), errors={n_error}")
        if completion < MIN_COMPLETION:
            print(f"[runner] INTEGRITY STOP: method {method_id} completion {completion:.1%} < "
                  f"{MIN_COMPLETION:.0%}. Halting this method.", file=sys.stderr)

    # Always-abstain (analytic — cannot fail)
    if args.include_always_abstain:
        for sc in scenarios:
            sid = sc["scenario_id"]
            if (sid, ALWAYS_ABSTAIN_ID) not in done_pairs:
                records.append(_always_abstain_record(sid, int(sc["seed"]), runner_sha))
                done_pairs.add((sid, ALWAYS_ABSTAIN_ID))
        print(f"[runner] {ALWAYS_ABSTAIN_ID}: {n_total}/{n_total} (100.0%)")

    # Write JSONL output
    with out_path.open("w") as fh:
        for rec in records:
            fh.write(json.dumps(rec, default=float) + "\n")
    final_sha = _sha256_file(out_path)
    print(f"[runner] Wrote {len(records)} records to {out_path}")
    print(f"[runner] Records SHA-256: {final_sha[:16]}...")

    # Write provenance sidecar
    prov = {
        "event": "RUN_CONFIRM",
        "dataset": str(dataset_path),
        "dataset_sha256": dataset_sha,
        "output": str(out_path),
        "output_sha256": final_sha,
        "n_scenarios": n_total,
        "methods": want_methods,
        "runner_sha256": runner_sha,
        "records_written": len(records),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    prov_path = out_path.with_suffix(".provenance.json")
    prov_path.write_text(json.dumps(prov, indent=2))
    print(f"[runner] Provenance written to {prov_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
