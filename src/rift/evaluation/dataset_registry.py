"""
Dataset registry and integrity gate — Sprint 4.2.4 (Issues 3 and 4).

Single source of truth for which scenario files exist, what their SHA-256 and sizes must be, and
which *purpose* each may be loaded for. All loaders fail CLOSED: a missing file, a hash mismatch,
a wrong split identity, or an attempt to read held-out labels without an active HeldOutGuard
oracle token (or for threshold selection at all) raises :class:`DatasetIntegrityError`.

Design notes
------------
* Paths are resolved relative to the repository root derived from THIS file's location, never the
  current working directory.
* Expected hashes are pinned in source (not read from the manifest) so that tampering with a data
  file AND its manifest together is still detected; the manifest is cross-checked against the pins.
* The held-out filename is derived from the split name (no literal path string), so that
  ``scripts/verify_heldout_sealed.py`` keeps flagging any direct reference elsewhere.
* Data files are never modified by this module.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.rift.evaluation.held_out_guard import HeldOutGuard, HeldOutLeakageError

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_SUBDIR = ("datasets", "rift_faults")

SPLIT_DEVELOPMENT = "DEVELOPMENT"
SPLIT_VALIDATION = "VALIDATION"
SPLIT_HELD_OUT_TEST = "HELD_OUT_TEST"

PURPOSE_SELECTION = "selection"   # threshold / hyper-parameter selection, development work
PURPOSE_FINAL = "final"           # one-shot final evaluation


class DatasetIntegrityError(RuntimeError):
    """A dataset failed path, hash, identity or access-purpose validation."""


@dataclass(frozen=True)
class DatasetSpec:
    split: str                 # identity declared INSIDE the file
    stem: str                  # filename stem; file is <stem>.json
    sha256: str
    size_bytes: int
    n_scenarios: int
    id_field: str = "fault_id"
    sealed: bool = False       # True => needs oracle token and purpose=final
    declared_split_in_file: bool = True

    @property
    def filename(self) -> str:
        return self.stem + ".json"


# Pins. Changing a dataset file REQUIRES a deliberate edit of this table (visible in review).
REGISTRY: Dict[str, DatasetSpec] = {
    SPLIT_DEVELOPMENT: DatasetSpec(
        SPLIT_DEVELOPMENT, "development",
        "d8960776ee3556a8b98de4767c3e8bd14f430f828983fcf50b0114dce8a1aebd", 44761, 50),
    SPLIT_VALIDATION: DatasetSpec(
        SPLIT_VALIDATION, "validation",
        "2363f6bbea6f86eb883525be90151655ca9ddac01aa9ad5b6e8351dc4953d0f3", 15580, 18),
    SPLIT_HELD_OUT_TEST: DatasetSpec(
        SPLIT_HELD_OUT_TEST, "held_out_test",
        "4337675b723dff1b88246216078a51e5b9aa1ffe976541739516d716ba18dd91", 13823, 15,
        sealed=True),
    "ADVERSARIAL": DatasetSpec(
        "ADVERSARIAL", "adversarial_stress_cohort",
        "46e769c6e75895fa25bfc22616aabb38757a2dac3c3c190025a4e57eb1215577", 18333, 30,
        id_field="scenario_id", declared_split_in_file=False),
}

# Historical manifest preserved byte-for-byte (generator output, 69 scenarios).
HISTORICAL_MANIFEST_V1 = "manifest.v1_generator_69.json"
HISTORICAL_MANIFEST_V1_SHA256 = "8fe47d2730bf02f554e4b98c5b6fb7ed58213ee5799abf6108e1e4bed6c3fde1"


def data_dir(root: Optional[Path] = None) -> Path:
    return Path(root or REPO_ROOT).joinpath(*DATA_SUBDIR)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _spec(split: str) -> DatasetSpec:
    try:
        return REGISTRY[split]
    except KeyError:
        raise DatasetIntegrityError(f"unknown dataset split {split!r}; known: {sorted(REGISTRY)}")


def resolve_path(split: str, root: Optional[Path] = None) -> Path:
    return data_dir(root) / _spec(split).filename


def verify_bytes(split: str, raw: bytes, spec: Optional[DatasetSpec] = None) -> Dict[str, Any]:
    """Validate raw bytes against the pin and the file's own declared identity; return parsed JSON."""
    spec = spec or _spec(split)
    digest = sha256_bytes(raw)
    if digest != spec.sha256:
        raise DatasetIntegrityError(
            f"{spec.filename}: SHA-256 mismatch (expected {spec.sha256[:16]}..., got {digest[:16]}...)")
    if len(raw) != spec.size_bytes:
        raise DatasetIntegrityError(f"{spec.filename}: size {len(raw)} != pinned {spec.size_bytes}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DatasetIntegrityError(f"{spec.filename}: invalid JSON: {exc}")
    scenarios = data.get("scenarios") if isinstance(data, dict) else None
    if not isinstance(scenarios, list):
        raise DatasetIntegrityError(f"{spec.filename}: missing 'scenarios' list")
    if len(scenarios) != spec.n_scenarios:
        raise DatasetIntegrityError(
            f"{spec.filename}: {len(scenarios)} scenarios != pinned {spec.n_scenarios}")
    if spec.declared_split_in_file:
        if data.get("split") != spec.split:
            raise DatasetIntegrityError(
                f"{spec.filename}: declares split {data.get('split')!r}, registry expects {spec.split!r} "
                "(wrong dataset identity / substitution)")
        if data.get("n_scenarios") != spec.n_scenarios:
            raise DatasetIntegrityError(f"{spec.filename}: header n_scenarios mismatch")
        wrong = [s.get("fault_id") for s in scenarios if s.get("split") != spec.split]
        if wrong:
            raise DatasetIntegrityError(
                f"{spec.filename}: {len(wrong)} scenario(s) carry a different split label, e.g. {wrong[:3]}")
    ids = [s.get(spec.id_field) for s in scenarios]
    if None in ids or len(set(ids)) != len(ids):
        raise DatasetIntegrityError(f"{spec.filename}: scenario ids missing or duplicated within file")
    return data


def load_split(
    split: str,
    *,
    purpose: str = PURPOSE_SELECTION,
    guard: Optional[HeldOutGuard] = None,
    root: Optional[Path] = None,
) -> List[dict]:
    """
    Load and verify a split's scenarios.

    Sealed (held-out) data requires ALL of: purpose == 'final', a HeldOutGuard with an ACTIVE oracle
    token. Anything else raises. Non-sealed data never needs a guard.
    """
    if purpose not in (PURPOSE_SELECTION, PURPOSE_FINAL):
        raise DatasetIntegrityError(f"unknown purpose {purpose!r}")
    spec = _spec(split)
    if spec.sealed:
        if purpose != PURPOSE_FINAL:
            raise DatasetIntegrityError(
                f"{split} is sealed: it may not be read for purpose={purpose!r} "
                "(threshold selection / development must not touch held-out labels)")
        if guard is None:
            raise HeldOutLeakageError(f"{split} requires a HeldOutGuard with an active oracle token")
        guard.check_access(caller_name=f"dataset_registry.load_split({split})")  # raises if no token
    path = resolve_path(split, root)
    if not path.is_file():
        raise DatasetIntegrityError(f"{spec.filename}: file not found at {path}")
    data = verify_bytes(split, path.read_bytes(), spec)
    return data["scenarios"]


def verify_all_files(root: Optional[Path] = None) -> List[str]:
    """
    Integrity check that does NOT parse labels into the caller: hashes/size only.
    Returns a list of problems (empty == OK). Used by verify_heldout_sealed.py (check 4).
    """
    problems: List[str] = []
    for name, spec in REGISTRY.items():
        path = resolve_path(name, root)
        if not path.is_file():
            problems.append(f"{spec.filename}: MISSING at {path}")
            continue
        raw = path.read_bytes()
        if sha256_bytes(raw) != spec.sha256 or len(raw) != spec.size_bytes:
            problems.append(f"{spec.filename}: hash/size does not match pinned value")
    mpath = data_dir(root) / HISTORICAL_MANIFEST_V1
    if not mpath.is_file():
        problems.append(f"{HISTORICAL_MANIFEST_V1}: MISSING")
    elif sha256_bytes(mpath.read_bytes()) != HISTORICAL_MANIFEST_V1_SHA256:
        problems.append(f"{HISTORICAL_MANIFEST_V1}: historical manifest was modified")
    return problems
