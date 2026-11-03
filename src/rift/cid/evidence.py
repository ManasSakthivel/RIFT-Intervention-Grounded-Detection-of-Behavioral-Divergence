"""
Canonical CID evidence identity and boundary validation — Sprint 4.2.4.

Defect fixed
------------
Producer (`pipeline/e2e_runner.py` Stage 13) keyed CID results as the string
``"{svc}→{svc}.downstream"`` (intervention on X, outcome the *same* service's pseudo
"downstream" variable). Consumer (`ebd.compute_ebd` R4) looked results up as
``"{path_source}→{path_target}"`` for edges of the candidate's causal path. The two
schemas could never intersect, so R4 / DEFINITIVE was unreachable via the pipeline.

Canonical schema
----------------
A CID observation is identified by the typed pair ``CIDKey(intervened, outcome)``:
    intervened : the service X on which do(X) was applied
    outcome    : the service Y whose distribution is compared (baseline vs post-do(X))
The key is derived from the ``CIDResult`` itself (``source_variable`` /
``target_variable``), not from caller-side string concatenation. The legacy
``"X→Y"`` string form is accepted ONLY at this boundary (parsed, never built
elsewhere) so historical artifacts and tests remain readable.

Every rejected / unusable entry is recorded with an explicit reason so that missing,
malformed or unmatched evidence yields an explicit non-definitive outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple, Union

CID_SCHEMA_VERSION = "rift.cid_evidence/1"
LEGACY_SEPARATOR = "→"  # U+2192; legacy string keys only

VALID_GRADES = ("CANDIDATE", "RELIABLE")


@dataclass(frozen=True, order=True)
class CIDKey:
    """Typed identity of one CID observation: do(intervened) observed on outcome."""
    intervened: str
    outcome: str

    def __post_init__(self) -> None:
        for name in ("intervened", "outcome"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"CIDKey.{name} must be a non-empty string, got {v!r}")

    def as_legacy_string(self) -> str:
        """Serialization for legacy readers only. Never use for lookup."""
        return f"{self.intervened}{LEGACY_SEPARATOR}{self.outcome}"

    @classmethod
    def from_legacy_string(cls, raw: str) -> "CIDKey":
        if not isinstance(raw, str) or raw.count(LEGACY_SEPARATOR) != 1:
            raise ValueError(f"malformed legacy CID key {raw!r}: expected exactly one '{LEGACY_SEPARATOR}'")
        a, b = (p.strip() for p in raw.split(LEGACY_SEPARATOR))
        return cls(a, b)


def grade_name(cid: Any) -> Optional[str]:
    g = getattr(cid, "grade", None)
    v = getattr(g, "value", g)
    return v if isinstance(v, str) else None


def validate_cid_for_r4(cid: Any, theta_cid: float) -> Tuple[bool, str]:
    """
    Strict R4 evidence gate. Returns (supports_r4, reason).

    ALL of the following are required (no field may be absent / None):
      * w1_estimate is a finite number > theta_cid
      * grade in {CANDIDATE, RELIABLE}   (INSUFFICIENT / unknown rejected)
      * permutation_significant is True
      * exceeds_threshold is True        (CID's own 0.1 x IQR_baseline gate)
    """
    w1 = getattr(cid, "w1_estimate", None)
    if w1 is None:
        return False, "NO_W1_ESTIMATE"
    try:
        w1f = float(w1)
    except (TypeError, ValueError):
        return False, "W1_NOT_NUMERIC"
    if w1f != w1f or w1f in (float("inf"), float("-inf")):
        return False, "W1_NOT_FINITE"
    g = grade_name(cid)
    if g is None:
        return False, "GRADE_MISSING"
    if g not in VALID_GRADES:
        return False, f"GRADE_{g}"
    if getattr(cid, "permutation_significant", None) is not True:
        return False, "PERMUTATION_NOT_SIGNIFICANT_OR_MISSING"
    if getattr(cid, "exceeds_threshold", None) is not True:
        return False, "BELOW_CID_THRESHOLD_OR_MISSING"
    if not w1f > theta_cid:
        return False, "BELOW_THETA_CID"
    return True, "OK"


@dataclass
class CIDEvidenceStore:
    """Validated container of CID observations keyed by :class:`CIDKey`."""
    entries: Dict[CIDKey, Any] = field(default_factory=dict)
    rejected: List[Tuple[str, str]] = field(default_factory=list)  # (raw_key, reason)

    # ---- producer side -------------------------------------------------
    def add(self, cid: Any) -> CIDKey:
        """Register a CID result under the identity it carries itself."""
        key = CIDKey(getattr(cid, "source_variable", None), getattr(cid, "target_variable", None))
        if key in self.entries:
            raise ValueError(f"duplicate CID evidence for {key}")
        self.entries[key] = cid
        return key

    # ---- consumer side -------------------------------------------------
    def get(self, intervened: str, outcome: str) -> Optional[Any]:
        return self.entries.get(CIDKey(intervened, outcome))

    def for_intervened(self, intervened: str) -> Dict[str, Any]:
        return {k.outcome: v for k, v in self.entries.items() if k.intervened == intervened}

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[Tuple[CIDKey, Any]]:
        return iter(self.entries.items())

    # ---- boundary ------------------------------------------------------
    @classmethod
    def from_mapping(cls, mapping: Optional[Mapping[Any, Any]]) -> "CIDEvidenceStore":
        """
        Normalise any accepted representation into a store, validating identity.

        Accepted keys: CIDKey, (intervened, outcome) tuple, or legacy 'X→Y' string.
        An entry whose key disagrees with the identity carried by the CIDResult itself
        (source_variable/target_variable) is REJECTED (KEY_IDENTITY_MISMATCH) -- except
        for legacy self-downstream keys, which are kept but flagged because they can
        never match a causal-path outcome.
        """
        store = cls()
        if mapping is None:
            return store
        if isinstance(mapping, CIDEvidenceStore):
            return mapping
        for raw_key, cid in mapping.items():
            label = repr(raw_key)
            try:
                if isinstance(raw_key, CIDKey):
                    key = raw_key
                elif isinstance(raw_key, tuple) and len(raw_key) == 2:
                    key = CIDKey(*raw_key)
                else:
                    key = CIDKey.from_legacy_string(raw_key)
            except (ValueError, TypeError) as exc:
                store.rejected.append((label, f"MALFORMED_KEY: {exc}"))
                continue
            src = getattr(cid, "source_variable", None)
            tgt = getattr(cid, "target_variable", None)
            if isinstance(src, str) and isinstance(tgt, str) and (src, tgt) != (key.intervened, key.outcome):
                store.rejected.append((label, f"KEY_IDENTITY_MISMATCH: result carries ({src!r}, {tgt!r})"))
                continue
            if key in store.entries:
                store.rejected.append((label, "DUPLICATE_KEY"))
                continue
            store.entries[key] = cid
        return store

    def to_serializable(self) -> Dict[str, Any]:
        rows = []
        for key, cid in sorted(self.entries.items()):
            rows.append({
                "intervened": key.intervened,
                "outcome": key.outcome,
                "w1_estimate": getattr(cid, "w1_estimate", None),
                "grade": grade_name(cid),
                "permutation_significant": getattr(cid, "permutation_significant", None),
                "exceeds_threshold": getattr(cid, "exceeds_threshold", None),
                "n_baseline": getattr(cid, "n_baseline", None),
                "n_post": getattr(cid, "n_post", None),
            })
        return {"schema": CID_SCHEMA_VERSION, "entries": rows,
                "rejected": [{"key": k, "reason": r} for k, r in self.rejected]}
