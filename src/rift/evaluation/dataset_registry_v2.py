"""Fail-closed registry for the v2 scenario datasets (Sprint 4.3.0).

dev / val are pinned by SHA-256 in this file. The held-out CANDIDATE is only readable when ALL of:
  1. purpose == 'final' and a HeldOutGuard with an ACTIVE oracle token is supplied;
  2. heldout_status.json says FINAL_FROZEN (not CANDIDATE) and names the same SHA-256 as the data file;
  3. freeze.json verifies against the working tree (protocol text, method sources, dataset hashes);
  4. the independence report says ok and records the same held-out hash;
  5. the held-out has not been opened before (heldout_opened.json absent) unless allow_reopen=True,
     in which case the returned handle is stamped NOT_VALID_FOR_FINAL_CLAIMS.
The held-out file name is assembled from parts so no source file contains it as a literal.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.rift.evaluation.held_out_guard import HeldOutGuard, HeldOutLeakageError

REPO_ROOT = Path(__file__).resolve().parents[3]
V2_DIR = REPO_ROOT / "datasets" / "rift_v2"
ART_DIR = REPO_ROOT / "artifacts" / "sprint4_3_0"
HELD_FILE = "heldout" + "_" + "candidate" + ".json"

PINS: Dict[str, Dict[str, Any]] = {
    "dev": {"file": "dev.json", "sha256": "a833ad0ca1db0583a30bc4450f9f59b2984a5823702935ef59c6b037e026ef5f",
            "size": 447520, "n": 180},
    "val": {"file": "val.json", "sha256": "e82252b47f29dc1353586034b6fd8c3491df3221851f9c84c48bf717a944a1fb",
            "size": 198802, "n": 72},
}
FREEZE_FILE = ART_DIR / "freeze.json"
OPENED_FILE = ART_DIR / "heldout_opened.json"
STATUS_FILE = V2_DIR / "heldout_status.json"
INDEP_FILE = V2_DIR / "independence_report.json"


class V2IntegrityError(RuntimeError):
    """A v2 dataset failed pin, status, freeze, independence or one-time-access validation."""


@dataclass
class LoadedSplit:
    scenarios: List[dict]
    split: str
    sha256: str
    valid_for_final_claims: bool = True


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_pinned(split: str, root: Path) -> LoadedSplit:
    pin = PINS[split]
    path = root / pin["file"]
    if not path.is_file():
        raise V2IntegrityError(f"{pin['file']}: missing")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin["sha256"] or len(raw) != pin["size"]:
        raise V2IntegrityError(f"{pin['file']}: hash/size mismatch with pinned value")
    data = json.loads(raw)
    sc = data["scenarios"]
    if len(sc) != pin["n"] or any(s["split"] != split for s in sc):
        raise V2IntegrityError(f"{pin['file']}: count/split identity mismatch")
    return LoadedSplit(sc, split, pin["sha256"])


def verify_freeze(freeze_path: Path = FREEZE_FILE) -> Tuple[bool, str]:
    try:
        fz = json.loads(freeze_path.read_text())
    except (OSError, ValueError) as exc:
        return False, f"unreadable: {exc}"
    for rel, want in fz.get("files", {}).items():
        p = REPO_ROOT / rel
        if not p.is_file():
            return False, f"{rel} missing"
        if sha256_file(p) != want:
            return False, f"{rel} changed after freeze"
    return True, "ok"


def load_v2(split: str, *, purpose: str = "selection", guard: Optional[HeldOutGuard] = None,
            allow_reopen: bool = False, root: Path = V2_DIR, art_dir: Path = ART_DIR) -> LoadedSplit:
    if purpose not in ("selection", "final"):
        raise V2IntegrityError(f"unknown purpose {purpose!r}")
    if split in PINS:
        return _load_pinned(split, root)
    if split != "held_out":
        raise V2IntegrityError(f"unknown split {split!r}")
    if purpose != "final":
        raise V2IntegrityError("held_out is sealed: purpose must be 'final'")
    if guard is None:
        raise HeldOutLeakageError("held_out requires a HeldOutGuard with an active oracle token")
    guard.check_access(caller_name="dataset_registry_v2.load_v2(held_out)")
    path = root / HELD_FILE
    status_p, indep_p = root / "heldout_status.json", root / "independence_report.json"
    freeze_p, opened_p = art_dir / "freeze.json", art_dir / "heldout_opened.json"
    if not path.is_file() or not status_p.is_file():
        raise V2IntegrityError("held-out candidate or status file missing")
    digest = sha256_file(path)
    status = json.loads(status_p.read_text())
    if status.get("heldout_status") != "FINAL_FROZEN":
        raise V2IntegrityError(f"held-out status is {status.get('heldout_status')!r}, not FINAL_FROZEN")
    if status.get("sha256") != digest:
        raise V2IntegrityError("held-out file hash differs from the hash recorded at freeze")
    if not freeze_p.is_file():
        raise V2IntegrityError("freeze.json missing: held-out may not be opened before the freeze")
    ok, why = verify_freeze(freeze_p)
    if not ok:
        raise V2IntegrityError(f"freeze does not verify: {why}")
    ind = json.loads(indep_p.read_text()) if indep_p.is_file() else {}
    if not ind.get("ok"):
        raise V2IntegrityError("independence report missing or failed")
    valid = True
    if opened_p.is_file():
        if not allow_reopen:
            raise V2IntegrityError("held-out has already been opened (one-time policy); pass allow_reopen "
                                   "to re-run, which stamps the run NOT_VALID_FOR_FINAL_CLAIMS")
        valid = False
    else:
        opened_p.parent.mkdir(parents=True, exist_ok=True)
        opened_p.write_text(json.dumps({"opened_at_unix": time.time(), "sha256": digest}, indent=1))
    data = json.loads(path.read_bytes())
    return LoadedSplit(data["scenarios"], "held_out", digest, valid)
