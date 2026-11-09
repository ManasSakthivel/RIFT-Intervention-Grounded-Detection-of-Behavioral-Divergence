#!/usr/bin/env python3
"""One-command reproducible pipeline for Sprint 4.3.0 (Protocol v2).

    python3 scripts/sprint430_run_pipeline.py            # verify everything and reproduce dev + val
    python3 scripts/sprint430_run_pipeline.py --heldout  # additionally re-run held-out as NOT_VALID_FOR_FINAL_CLAIMS

Stages: datasets regenerate byte-identically -> independence re-verified (read-only) -> freeze verified ->
dev eval (+ablations) -> val eval (+ablations) -> analysis -> run metadata.
The held-out was opened exactly once (artifacts/sprint4_3_0/heldout_opened.json); a re-run is stamped
NOT_VALID_FOR_FINAL_CLAIMS and written to a separate directory so the original result is never overwritten.
Nothing here contacts a live system or touches src/rift/intervention, src/rift/safety or Stage 4 artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ART = REPO / "artifacts" / "sprint4_3_0"
PY = sys.executable


def run(label: str, *args: str) -> int:
    t = time.time()
    print(f"\n=== {label}: {' '.join(args)}", flush=True)
    r = subprocess.run([PY, *args], cwd=REPO, capture_output=True, text=True)
    tail = [ln for ln in r.stdout.splitlines() if ln.strip() and "Warning" not in ln and "-->" not in ln][-14:]
    print("\n".join(tail))
    print(f"--- exit {r.returncode} in {time.time() - t:.1f}s", flush=True)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heldout", action="store_true", help="re-run held-out (stamped NOT_VALID_FOR_FINAL_CLAIMS)")
    ap.add_argument("--skip-ablations", action="store_true")
    a = ap.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    abl = [] if a.skip_ablations else ["--ablations"]
    stages = [
        ("datasets_regenerate_identical", ["scripts/sprint430_generate_datasets.py", "--check"]),
        ("independence_verified_readonly", ["scripts/sprint430_verify_independence.py", "--check"]),
        ("held_out_still_sealed_gate", ["scripts/verify_heldout_sealed.py"]),
        ("eval_dev", ["scripts/sprint430_run_evaluation.py", "--split", "dev", *abl]),
        ("eval_val", ["scripts/sprint430_run_evaluation.py", "--split", "val", *abl]),
        ("analyze_dev", ["scripts/sprint430_analyze.py", "--split", "dev"]),
        ("analyze_val", ["scripts/sprint430_analyze.py", "--split", "val"]),
    ]
    if a.heldout:
        stages += [("eval_heldout_rerun_NOT_VALID", ["scripts/sprint430_run_evaluation.py", "--split", "held_out",
                                                    "--final", "--allow-reopen", *abl,
                                                    "--out", str(ART / "results" / "held_out_rerun")])]
    status = {}
    for name, args in stages:
        status[name] = run(name, *args)
        if status[name] != 0:
            break
    ok = all(v == 0 for v in status.values()) and len(status) == len(stages)
    meta = {"pipeline": "sprint430_run_pipeline", "started_utc": started,
            "finished_utc": datetime.now(timezone.utc).isoformat(), "stage_exit_codes": status, "ok": ok,
            "python": sys.version.split()[0], "heldout_rerun_requested": a.heldout,
            "protocol_sha256": hashlib.sha256((REPO / "docs/EVALUATION_PROTOCOL_V2.md").read_bytes()).hexdigest(),
            "freeze_sha256": hashlib.sha256((ART / "freeze.json").read_bytes()).hexdigest()
            if (ART / "freeze.json").is_file() else None}
    (ART / "run_metadata.json").write_text(json.dumps(meta, indent=1))
    print("\nPIPELINE", "OK" if ok else "FAILED", json.dumps(status))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
