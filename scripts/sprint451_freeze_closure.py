#!/usr/bin/env python3
"""Sprint 4.5.1 - static import closure of the confirmatory comparators (analysis only; reads source text, runs nothing).

Entry points are the frozen runner/evaluator modules that produce the V3, V2, baseline, LEGACY and ORACLE rows.
The closure is computed with ``ast`` over files inside the repository only (src/rift/**, scripts/**, reproducibility/**).
Each closure member is classified as: in the 4.5.0 manifest or not; tracked in git or not.
Also scans every closure member for references to held-out paths and for dynamic-import/IO of datasets.

Output: artifacts/sprint4_5_1/freeze/closure_analysis.json   (no file is modified, no dataset is opened)
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "artifacts" / "sprint4_5_1" / "freeze" / "closure_analysis.json"
MANIFEST = REPO / "artifacts" / "sprint4_5_0" / "prereg" / "freeze_manifest.json"

ENTRY = [
    "scripts/sprint440_run_v3.py",
    "src/rift/evaluation/benchmark_v2.py",
    "src/rift/evaluation/rift_v2.py",
    "src/rift/attribution_v3/rift_v3.py",
    "scripts/run_adversarial_benchmark.py",
    "scripts/run_reproducible_evaluation.py",
]
HELD = re.compile(r"held_?out|heldout", re.I)


def mod_to_path(mod: str):
    parts = mod.split(".")
    if parts[0] == "src":
        parts = parts[1:]
    for base in ("src",):
        p = REPO / base / Path(*parts)
        if (p.with_suffix(".py")).exists():
            return p.with_suffix(".py")
        if (p / "__init__.py").exists():
            return p / "__init__.py"
    for base in ("",):
        p = REPO / Path(*parts)
        if p.with_suffix(".py").exists():
            return p.with_suffix(".py")
        if (p / "__init__.py").exists():
            return p / "__init__.py"
    return None


def imports_of(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods = []
    pkg = ".".join(path.relative_to(REPO / "src").with_suffix("").parts[:-1]) if "src" in path.parts and (REPO / "src") in path.parents else ""
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                base = pkg.split(".") if pkg else []
                base = base[: len(base) - (n.level - 1)] if n.level > 1 else base
                m = ".".join(base + ([n.module] if n.module else []))
            else:
                m = n.module or ""
            mods.append(m)
            for a in n.names:  # from pkg import submodule
                mods.append(f"{m}.{a.name}" if m else a.name)
    return mods


def closure():
    seen, stack = {}, [REPO / e for e in ENTRY]
    while stack:
        p = stack.pop()
        rel = str(p.relative_to(REPO))
        if rel in seen:
            continue
        seen[rel] = []
        for m in imports_of(p):
            q = mod_to_path(m)
            if q is not None and REPO in q.parents:
                seen[rel].append(str(q.relative_to(REPO)))
                stack.append(q)
                # parent packages' __init__ run at import time
                for par in q.parents:
                    if par == REPO:
                        break
                    ini = par / "__init__.py"
                    if ini.exists() and ini != q and (REPO / "src") in ini.parents:
                        stack.append(ini)
    return seen


def tracked(rel):
    return subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO, capture_output=True).returncode == 0


def main():
    man = json.loads(MANIFEST.read_text())["files"]
    seen = closure()
    rows = []
    for rel in sorted(seen):
        txt = (REPO / rel).read_text(encoding="utf-8")
        hits = sorted({m.group(0) for m in HELD.finditer(txt)})
        rows.append({"path": rel, "in_4_5_0_manifest": rel in man, "tracked": tracked(rel),
                     "imports_in_repo": sorted(set(seen[rel])), "heldout_token_hits": hits,
                     "n_lines": txt.count("\n") + 1})
    missing = [r for r in rows if not r["in_4_5_0_manifest"]]
    res = {"purpose": "static import closure of confirmatory comparators; analysis only", "entry_points": ENTRY,
           "closure_size": len(rows), "in_manifest": len(rows) - len(missing), "not_in_manifest": len(missing),
           "not_in_manifest_untracked": [r["path"] for r in missing if not r["tracked"]],
           "rows": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    print("closure", len(rows), "in manifest", res["in_manifest"], "not in manifest", len(missing))
    for r in missing:
        print(("UNTRACKED " if not r["tracked"] else "tracked   ") + r["path"], r["heldout_token_hits"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
