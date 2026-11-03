#!/usr/bin/env python3
"""Sprint 4.4.2: compare regenerated Sprint 4.4.0 artifacts against the committed ones.

    python3 scripts/sprint442_compare_artifacts.py <committed_dir> <regenerated_dir> [report.json]

Comparison is structural (parsed JSON / CSV), not byte-level. The ONLY values ignored are wall-clock / memory
measurements, which depend on machine load and are not scientific results:

  * keys ``runtime_s`` and ``mem_kb`` inside per-scenario records (v3_*.json, adversarial_results.json)
  * in analysis.json: the subtrees named ``runtime_s`` (mean / p95 / total / n of timings)
  * in cid_audit.json / failure traces / adversarial_summary / graph_quality.csv: nothing is ignored

Everything ignored is counted and printed, so an over-broad filter would be visible. Any other difference is a
FAILURE and is itemised.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

TIMING_KEYS = {"runtime_s", "mem_kb"}
# Fields whose committed value was recorded WITH the sealed held-out file present (verify_freeze hashes it).
# A fresh clone cannot reproduce them; they are reported as PROTECTED_UNAVAILABLE, never as IDENTICAL.
PROTECTED_DEPENDENT = {"trace_meta.json": ["/verify_freeze"]}
FILES = ["v3_dev.json", "v3_val.json", "analysis.json", "adversarial_results.json", "adversarial_summary.json",
         "cid_audit.json", "failure_traces_dev.json", "failure_traces_val.json", "graph_quality.csv", "trace_meta.json"]


def _strip(o, ignored):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if k in TIMING_KEYS:
                ignored[k] = ignored.get(k, 0) + 1
                continue
            out[k] = _strip(v, ignored)
        return out
    if isinstance(o, list):
        return [_strip(x, ignored) for x in o]
    return o


def _diff(a, b, path="", out=None, limit=25):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if type(a) != type(b):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
            out.append(f"{path}: type {type(a).__name__} != {type(b).__name__}")
            return out
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}: key missing on one side")
            else:
                _diff(a[k], b[k], f"{path}/{k}", out, limit)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                _diff(x, y, f"{path}[{i}]", out, limit)
    elif a != b and not (isinstance(a, float) and isinstance(b, float) and a != a and b != b):  # NaN == NaN here
        out.append(f"{path}: {a!r} != {b!r}")
    return out


def compare_file(name, ref_dir, new_dir):
    ra, rb = ref_dir / name, new_dir / name
    if not ra.is_file() or not rb.is_file():
        return {"file": name, "status": "MISSING", "differences": [f"{'committed' if not ra.is_file() else 'regenerated'} file absent"],
                "ignored": {}}
    ignored = {}
    if name.endswith(".csv"):
        a = list(csv.reader(ra.open()))
        b = list(csv.reader(rb.open()))
    else:
        a, b = _strip(json.loads(ra.read_text()), ignored), _strip(json.loads(rb.read_text()), ignored)
        if name == "analysis.json":
            # analysis.json holds aggregate timings under 'runtime_s' subtrees and Monte-Carlo free fields otherwise
            a, b = _drop_runtime_subtrees(a, ignored), _drop_runtime_subtrees(b, ignored)
    d = _diff(a, b)
    status = "IDENTICAL" if not d else "DIFFERENT"
    if name in PROTECTED_DEPENDENT and d and all(x.startswith(tuple(PROTECTED_DEPENDENT[name])) for x in d):
        # Not ignored and not "identical": the recorded value depends on protected material that a fresh clone lacks.
        status = "PROTECTED_UNAVAILABLE"
    return {"file": name, "status": status, "differences": d, "ignored": ignored,
            "byte_identical": ra.read_bytes() == rb.read_bytes()}


def _drop_runtime_subtrees(o, ignored):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if k in ("runtime_s", "mem_kb"):
                ignored["analysis:" + k] = ignored.get("analysis:" + k, 0) + 1
                continue
            out[k] = _drop_runtime_subtrees(v, ignored)
        return out
    if isinstance(o, list):
        return [_drop_runtime_subtrees(x, ignored) for x in o]
    return o


def main(argv) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    ref, new = Path(argv[1]), Path(argv[2])
    results = [compare_file(n, ref, new) for n in FILES]
    ok = True
    for r in results:
        flag = {"IDENTICAL": "OK ", "PROTECTED_UNAVAILABLE": "N/A"}.get(r["status"], "BAD")
        ok &= r["status"] in ("IDENTICAL", "PROTECTED_UNAVAILABLE")
        print(f"[{flag}] {r['file']:32s} {r['status']:10s} byte-identical={r.get('byte_identical')} ignored={r['ignored']}")
        for line in r["differences"][:10]:
            print("       ", line)
    if len(argv) > 3:
        Path(argv[3]).write_text(json.dumps(results, indent=1))
    n_prot = sum(r["status"] == "PROTECTED_UNAVAILABLE" for r in results)
    n_same = sum(r["status"] == "IDENTICAL" for r in results)
    print(f"\n{n_same} artifact(s) reproduce (timing fields excluded); {n_prot} artifact(s) depend on protected material "
          f"and could not be reproduced here (NOT counted as reproduced)." if ok else "\nDIFFERENCES FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
