"""
RIFT SCM — Time-Sliced Structural Causal Model
Phase 3B implementation.

Causal claims are INTERVENTION-CONSISTENT, not "causally accurate".
All results validated on synthetic ground-truth scenarios only.
"""

from .scm import (
    TimeSlicedVariable,
    StructuralEquation,
    SCM,
    make_chain_scm,
    make_fork_scm,
    make_collider_scm,
    make_mediated_scm,
    make_confounder_scm,
    make_feedback_scm,
    make_queueing_scm,
)

__all__ = [
    "TimeSlicedVariable",
    "StructuralEquation",
    "SCM",
    "make_chain_scm",
    "make_fork_scm",
    "make_collider_scm",
    "make_mediated_scm",
    "make_confounder_scm",
    "make_feedback_scm",
    "make_queueing_scm",
]
