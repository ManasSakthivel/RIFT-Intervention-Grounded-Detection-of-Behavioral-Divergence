"""RIFT Experiment Registry — Phase 3.6 §18.

All experiments are defined here in YAML format.
See experiments/REGISTRY.yaml for the canonical registry.
This module validates the registry on import.
"""
from __future__ import annotations

from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent.parent.parent / "experiments" / "REGISTRY.yaml"
