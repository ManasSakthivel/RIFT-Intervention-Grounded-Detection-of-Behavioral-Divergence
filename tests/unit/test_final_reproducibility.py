"""Final execution (Agent 5): environment-reconciliation guards. Committed materials only; never opens the held-out split.

* requirements.txt must pin exactly the canonical lock (modulo PEP 508 markers), so CI cannot silently drift back to the
  causal-learn 0.1.3.8 stack that changes `ident_status` on V2D-0117 (Sprint 4.4.2).
* The installed causal-learn must be the canonical 0.1.4.8.
* Functional check: the FCI-dependent V3 pipeline on V2D-0117 (the scenario whose label is causal-learn-version-sensitive)
  must reproduce the committed record fields. This is a real execution test, not an import check.
"""
import importlib.metadata as md
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

LOCK = ROOT / "reproducibility" / "requirements-canonical-py39.lock.txt"
REQ = ROOT / "requirements.txt"


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse(path: Path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        spec = line.split(";")[0].strip()
        name, ver = spec.split("==")
        out[_norm(name)] = ver.strip()
    return out


def test_requirements_txt_pins_equal_canonical_lock():
    assert _parse(REQ) == _parse(LOCK)


def test_requirements_txt_uses_markers_only_for_legacy_interpreter_backports():
    marked = {_norm(l.split("==")[0]) for l in REQ.read_text().splitlines()
              if l.strip() and not l.lstrip().startswith("#") and ";" in l.split("#")[0]}
    assert marked == {"backports-asyncio-runner", "exceptiongroup", "tomli", "importlib-resources"}


def test_installed_causal_learn_is_canonical():
    assert md.version("causal-learn") == _parse(LOCK)["causal-learn"] == "0.1.4.8"


def test_ci_workflow_installs_requirements_txt_and_has_no_causal_learn_override():
    lines = [l for l in (ROOT / ".github" / "workflows" / "test.yml").read_text().splitlines()
             if not l.lstrip().startswith("#")]
    wf = "\n".join(lines)
    assert "pip install -r requirements.txt" in wf
    assert "causal-learn" not in wf


def test_v2d0117_ident_status_matches_committed_v3_record():
    """Regression for the single causal-learn-version-dependent label (6 V3 records on dev)."""
    import warnings
    warnings.filterwarnings("ignore")
    import sprint440_run_v3 as r
    from src.rift.attribution_v3.rift_v3 import V3_CONFIGS
    from src.rift.evaluation.dataset_registry_v2 import load_v2

    committed = {x["scenario_id"]: x for x in json.loads(
        (ROOT / "artifacts" / "sprint4_4_0" / "v3_dev.json").read_text())}
    sc = next(s for s in load_v2("dev").scenarios if s["scenario_id"] == "V2D-0117")
    res = r.run_scenario(sc, list(V3_CONFIGS))
    for k, v in res.items():
        c = committed["V2D-0117"]["methods"][k]
        assert v["record"]["ident_status"] == c["record"]["ident_status"] == "IDENTIFIABLE", k
        assert v["record"]["abstained"] == c["record"]["abstained"], k
        assert v["score"] == c["score"], k


@pytest.mark.parametrize("pkg", ["numpy", "scipy", "scikit-learn", "networkx", "pandas", "causal-learn"])
def test_numeric_stack_matches_canonical_lock(pkg):
    assert md.version(pkg) == _parse(LOCK)[_norm(pkg)]


def test_final_repro_check_refuses_to_write_into_artifacts():
    import final_repro_check as f
    with pytest.raises(SystemExit):
        f.main(["x", str(ROOT / "artifacts" / "sprint4_4_0")])
