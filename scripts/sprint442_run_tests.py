#!/usr/bin/env python3
"""Sprint 4.4.2: run the test suite with transparent protected-material classification.

    python3 scripts/sprint442_run_tests.py [pytest args...]          # default: whole suite
    python3 scripts/sprint442_run_tests.py --require-protected ...   # exit 3 if any protected check was unavailable
    python3 scripts/sprint442_run_tests.py --json out.json ...       # also write the classification as JSON

Exit codes: 0 = no failures (unavailable protected checks, if any, are listed and COUNTED SEPARATELY);
            1 = genuine failures; 3 = --require-protected and some protected check was unavailable.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from reproducibility.protected_materials import ProtectedMaterialPlugin  # noqa: E402


def main(argv) -> int:
    args = list(argv[1:])
    require = "--require-protected" in args
    if require:
        args.remove("--require-protected")
    out_json = None
    if "--json" in args:
        i = args.index("--json")
        out_json = args[i + 1]
        del args[i:i + 2]
    base = ["-q", "-p", "no:cacheprovider", "-W", "ignore"]
    plugin = ProtectedMaterialPlugin()
    rc = pytest.main(base + (args or ["tests"]), plugins=[plugin])
    s = plugin.summary()
    print("\n" + "=" * 78)
    print("RIFT test classification (Sprint 4.4.2)")
    print("=" * 78)
    print(f"  REPRODUCIBLE tests passed (committed materials only) : {len(s['REPRODUCIBLE_PASS'])}")
    print(f"  PROTECTED-material tests passed (materials present)  : {len(s['PROTECTED_PASS'])}")
    print(f"  PROTECTED-material checks UNAVAILABLE (NOT passed)   : {len(s['PROTECTED_UNAVAILABLE'])}")
    for nid in s["PROTECTED_UNAVAILABLE"]:
        print(f"      - {nid}\n          {plugin.records[nid]['detail']}")
    print(f"  Other skips                                          : {len(s['SKIPPED_OTHER'])}")
    print(f"  GENUINE FAILURES                                     : {len(s['FAILED'])}")
    for nid in s["FAILED"]:
        print(f"      - {nid}")
    if s["PROTECTED_UNAVAILABLE"]:
        print("  NOTE: unavailable protected-material integrity checks were NOT verified in this environment.")
    if out_json:
        Path(out_json).write_text(json.dumps({k: sorted(v) for k, v in s.items()}, indent=1))
    if s["FAILED"] or int(rc) not in (0, 5):
        return 1
    if require and s["PROTECTED_UNAVAILABLE"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
