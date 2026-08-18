"""
RIFT CID — Causal Intervention Divergence
Authority: docs/PHASE_3_SPEC_FREEZE.md Sections 6, 7, 8
"""

from .cid import CIDGrade, CIDResult, compute_cid

__all__ = ["CIDGrade", "CIDResult", "compute_cid"]
