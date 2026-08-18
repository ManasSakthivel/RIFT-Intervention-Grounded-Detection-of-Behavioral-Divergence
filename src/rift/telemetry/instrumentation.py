"""RIFT Performance Instrumentation — Phase 3.6 §28.

Instruments every pipeline stage with wall time, CPU time, and structural
metadata (n_variables, n_edges, n_interventions).

Every stage is recorded as a StageInstrumentRecord. At run completion,
an InstrumentationReport summarizes the full pipeline.

Authority: Phase 3.6 specification §28.
"""
from __future__ import annotations

import resource
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Generator, List, Optional

# ---------------------------------------------------------------------------
# Per-stage record
# ---------------------------------------------------------------------------

@dataclass
class StageInstrumentRecord:
    """
    Instrumentation record for one pipeline stage.

    wall_time_s  : elapsed real time (time.perf_counter)
    cpu_time_s   : user+system CPU time (resource.getrusage, UNIX only)
    memory_mb    : resident set size at stage end (ru_maxrss, approximate)
    n_variables  : number of causal variables processed (if applicable)
    n_edges      : number of graph edges (if applicable)
    n_interventions : number of interventions executed (if applicable)
    """
    stage_name: str
    wall_time_s: float = 0.0
    cpu_time_s: float = 0.0
    memory_mb: float = 0.0
    n_variables: int = 0
    n_edges: int = 0
    n_interventions: int = 0
    notes: str = ""


@dataclass
class InstrumentationReport:
    """
    Full pipeline instrumentation report for one RIFT run.
    """
    run_id: str
    stages: List[StageInstrumentRecord] = field(default_factory=list)

    def total_wall_time_s(self) -> float:
        return sum(s.wall_time_s for s in self.stages)

    def total_cpu_time_s(self) -> float:
        return sum(s.cpu_time_s for s in self.stages)

    def bottleneck_stage(self) -> Optional[str]:
        """Return the stage name with the highest wall time."""
        if not self.stages:
            return None
        return max(self.stages, key=lambda s: s.wall_time_s).stage_name

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "total_wall_time_s": self.total_wall_time_s(),
            "total_cpu_time_s": self.total_cpu_time_s(),
            "bottleneck_stage": self.bottleneck_stage(),
            "stages": [
                {
                    "stage_name": s.stage_name,
                    "wall_time_s": s.wall_time_s,
                    "cpu_time_s": s.cpu_time_s,
                    "memory_mb": s.memory_mb,
                    "n_variables": s.n_variables,
                    "n_edges": s.n_edges,
                    "n_interventions": s.n_interventions,
                    "notes": s.notes,
                }
                for s in self.stages
            ],
        }


# ---------------------------------------------------------------------------
# Context manager for stage instrumentation
# ---------------------------------------------------------------------------

def _get_cpu_time_s() -> float:
    """Return current process CPU time (user+system) in seconds."""
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_utime + usage.ru_stime
    except Exception:
        return 0.0


def _get_memory_mb() -> float:
    """Return current process peak RSS in MB (platform-dependent)."""
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # Linux: ru_maxrss in kB; macOS: in bytes
        import platform
        if platform.system() == "Darwin":
            return usage.ru_maxrss / (1024 * 1024)
        return usage.ru_maxrss / 1024
    except Exception:
        return 0.0


@contextmanager
def instrument_stage(
    report: InstrumentationReport,
    stage_name: str,
    n_variables: int = 0,
    n_edges: int = 0,
    n_interventions: int = 0,
    notes: str = "",
) -> Generator[StageInstrumentRecord, None, None]:
    """
    Context manager that instruments a pipeline stage.

    Usage:
        with instrument_stage(report, "FCI", n_variables=5) as rec:
            result = run_fci(...)
            rec.n_edges = len(result.edges)

    The StageInstrumentRecord is appended to report.stages on exit.
    """
    rec = StageInstrumentRecord(
        stage_name=stage_name,
        n_variables=n_variables,
        n_edges=n_edges,
        n_interventions=n_interventions,
        notes=notes,
    )
    t_wall_start = time.perf_counter()
    t_cpu_start = _get_cpu_time_s()

    try:
        yield rec
    finally:
        rec.wall_time_s = time.perf_counter() - t_wall_start
        rec.cpu_time_s = _get_cpu_time_s() - t_cpu_start
        rec.memory_mb = _get_memory_mb()
        report.stages.append(rec)
