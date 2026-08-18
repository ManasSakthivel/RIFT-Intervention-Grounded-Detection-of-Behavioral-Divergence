"""RIFT Provenance Logger — Phase 3.6 §24.

Every run records:
  - git commit
  - configuration hash
  - environment
  - seed
  - scenario
  - timestamp
  - software version
  - model version if applicable
  - dataset version

SECURITY: Never logs secrets. Never stores API keys.
All paths logged are relative to repo root.

Authority: Phase 3.6 §24.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Run provenance record
# ---------------------------------------------------------------------------

@dataclass
class RunProvenanceRecord:
    """
    Complete provenance record for one RIFT run.

    Serializable to JSON. Must be attached to every RIFTRunRecord.
    """
    run_id: str
    git_commit: str
    git_dirty: bool
    config_hash: str
    config_path: str
    environment_hash: str
    seed: int
    scenario_id: Optional[str]
    timestamp_utc: str
    python_version: str
    platform_info: str
    dataset_version: str       # manifest seed + split counts hash
    rift_version: str          # from src/rift/__init__.py if available
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "git_commit": self.git_commit,
            "git_dirty": self.git_dirty,
            "config_hash": self.config_hash,
            "config_path": self.config_path,
            "environment_hash": self.environment_hash,
            "seed": self.seed,
            "scenario_id": self.scenario_id,
            "timestamp_utc": self.timestamp_utc,
            "python_version": self.python_version,
            "platform_info": self.platform_info,
            "dataset_version": self.dataset_version,
            "rift_version": self.rift_version,
            "notes": self.notes,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

class ProvenanceLogger:
    """
    Captures and stores provenance metadata for RIFT runs.

    Usage:
        logger = ProvenanceLogger(output_dir=Path("artifacts/logs"))
        record = logger.capture(run_id="abc", seed=42, scenario_id="fault_001")
        logger.save(record)
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("artifacts/logs")
        self._log = logging.getLogger("rift.provenance")

    def _get_git_commit(self) -> str:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    def _get_git_dirty(self) -> bool:
        try:
            r = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=5
            )
            return bool(r.stdout.strip())
        except Exception:
            return False

    def _hash_config(self, config_path: Optional[Path]) -> str:
        if not config_path or not config_path.exists():
            return "no_config"
        h = hashlib.sha256()
        with open(config_path, "rb") as f:
            h.update(f.read())
        return h.hexdigest()[:16]

    def _env_hash(self) -> str:
        env_str = platform.python_version() + platform.platform()
        return hashlib.sha256(env_str.encode()).hexdigest()[:16]

    def _dataset_version(self) -> str:
        """Hash the manifest.json to detect dataset drift."""
        manifest = Path("datasets/rift_faults/manifest.json")
        if not manifest.exists():
            return "no_manifest"
        h = hashlib.sha256()
        with open(manifest, "rb") as f:
            h.update(f.read())
        return h.hexdigest()[:16]

    def _rift_version(self) -> str:
        try:
            import rift
            return getattr(rift, "__version__", "0.1.0-dev")
        except ImportError:
            return "unknown"

    def capture(
        self,
        run_id: str,
        seed: int = 42,
        scenario_id: Optional[str] = None,
        config_path: Optional[Path] = None,
        notes: str = "",
    ) -> RunProvenanceRecord:
        """Capture complete provenance metadata for a run."""
        record = RunProvenanceRecord(
            run_id=run_id,
            git_commit=self._get_git_commit(),
            git_dirty=self._get_git_dirty(),
            config_hash=self._hash_config(config_path),
            config_path=str(config_path) if config_path else "none",
            environment_hash=self._env_hash(),
            seed=seed,
            scenario_id=scenario_id,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            python_version=platform.python_version(),
            platform_info=platform.platform(),
            dataset_version=self._dataset_version(),
            rift_version=self._rift_version(),
            notes=notes,
        )

        # Validate no secrets in record
        self._check_no_secrets(record)
        return record

    def _check_no_secrets(self, record: RunProvenanceRecord) -> None:
        """Ensure no API keys or credentials appear in the provenance record."""
        secret_patterns = ["api_key", "password", "token", "secret", "credential"]
        record_json = record.to_json().lower()
        for pattern in secret_patterns:
            if pattern in record_json:
                raise ValueError(
                    f"Potential secret detected in provenance record: '{pattern}'. "
                    "RIFT provenance must never contain credentials or API keys."
                )

    def save(self, record: RunProvenanceRecord, filename: Optional[str] = None) -> Path:
        """Save provenance record to output_dir."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or f"provenance_{record.run_id}.json"
        path = self.output_dir / fname
        path.write_text(record.to_json())
        return path
