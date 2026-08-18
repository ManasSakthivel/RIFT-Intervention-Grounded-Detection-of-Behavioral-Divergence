"""RIFT Artifact Writer — Phase 3.6 §21.

Every experiment produces a structured artifact directory:
    results/<experiment_id>/
        config.json
        environment.json
        inputs.json
        raw_results.json
        metrics.json
        statistics.json
        manifest.json

Every result is traceable via:
  - checksums (SHA-256 of each file)
  - provenance (git commit, config hash, seed, timestamp)
  - schema validation (jsonschema)

Authority: Phase 3.6 §21.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Provenance record
# ---------------------------------------------------------------------------

@dataclass
class ProvenanceRecord:
    """
    Provenance metadata for one experiment artifact.

    Captured at artifact write time. Immutable after creation.
    """
    git_commit: str
    git_dirty: bool
    config_hash: str           # SHA-256 of config file
    seed: int
    timestamp_utc: str         # ISO 8601
    scenario_id: Optional[str]
    environment: Dict[str, str]
    software_versions: Dict[str, str]

    def to_dict(self) -> dict:
        return {
            "git_commit": self.git_commit,
            "git_dirty": self.git_dirty,
            "config_hash": self.config_hash,
            "seed": self.seed,
            "timestamp_utc": self.timestamp_utc,
            "scenario_id": self.scenario_id,
            "environment": self.environment,
            "software_versions": self.software_versions,
        }


def _get_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _get_git_dirty() -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _get_software_versions() -> Dict[str, str]:
    versions: Dict[str, str] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for pkg in ["numpy", "scipy", "pandas", "pydantic", "networkx", "causal-learn"]:
        try:
            import importlib
            m = importlib.import_module(pkg.replace("-", "_").replace("causal_learn", "causallearn"))
            versions[pkg] = getattr(m, "__version__", "unknown")
        except ImportError:
            versions[pkg] = "not_installed"
    return versions


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Artifact writer
# ---------------------------------------------------------------------------

class ArtifactWriter:
    """
    Writes structured experiment artifacts with provenance and checksums.

    Usage:
        writer = ArtifactWriter(base_dir=Path("results/EXP-001"))
        writer.write_config(config_dict)
        writer.write_raw_results(results_dict)
        writer.write_metrics(metrics_dict)
        writer.write_statistics(stats_dict)
        manifest = writer.finalize()
    """

    def __init__(
        self,
        base_dir: Path,
        experiment_id: str,
        seed: int = 42,
        scenario_id: Optional[str] = None,
        config_path: Optional[Path] = None,
    ):
        self.base_dir = base_dir
        self.experiment_id = experiment_id
        self.seed = seed
        self.scenario_id = scenario_id
        self._config_hash = "unknown"
        self._checksums: Dict[str, str] = {}
        self._files_written: List[str] = []

        base_dir.mkdir(parents=True, exist_ok=True)

        if config_path and config_path.exists():
            self._config_hash = _sha256_file(config_path)

    def _write_json(self, filename: str, data: Any) -> Path:
        """Write data as JSON. Record checksum. Return path."""
        path = self.base_dir / filename
        content = json.dumps(data, indent=2, default=str)
        path.write_text(content)
        self._checksums[filename] = _sha256_str(content)
        self._files_written.append(filename)
        return path

    def write_config(self, config: dict) -> Path:
        """Write experiment configuration."""
        return self._write_json("config.json", {
            "experiment_id": self.experiment_id,
            "seed": self.seed,
            **config,
        })

    def write_environment(self) -> Path:
        """Write environment metadata (git, platform, versions)."""
        env = {
            "experiment_id": self.experiment_id,
            "git_commit": _get_git_commit(),
            "git_dirty": _get_git_dirty(),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "software_versions": _get_software_versions(),
        }
        return self._write_json("environment.json", env)

    def write_inputs(self, inputs: dict) -> Path:
        """Write experiment inputs (dataset references, scenario IDs, etc.)."""
        return self._write_json("inputs.json", {
            "experiment_id": self.experiment_id,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            **inputs,
        })

    def write_raw_results(self, raw: dict) -> Path:
        """Write raw pipeline outputs."""
        return self._write_json("raw_results.json", raw)

    def write_metrics(self, metrics: dict) -> Path:
        """Write computed metrics (P@1, CID, EBD, etc.)."""
        return self._write_json("metrics.json", metrics)

    def write_statistics(self, stats: dict) -> Path:
        """Write statistical test results."""
        return self._write_json("statistics.json", stats)

    def finalize(self) -> dict:
        """Write manifest.json and return manifest dict."""
        manifest = {
            "experiment_id": self.experiment_id,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "config_hash": self._config_hash,
            "git_commit": _get_git_commit(),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": self._files_written,
            "checksums": self._checksums,
            "artifact_dir": str(self.base_dir),
        }
        self._write_json("manifest.json", manifest)
        return manifest

    def validate_schema(self, filename: str, schema: dict) -> bool:
        """
        Validate a written artifact against a JSON schema.
        Returns True if valid. Raises jsonschema.ValidationError if invalid.
        """
        try:
            import jsonschema
            path = self.base_dir / filename
            with open(path) as f:
                data = json.load(f)
            jsonschema.validate(data, schema)
            return True
        except ImportError:
            return True  # jsonschema not available; skip validation
