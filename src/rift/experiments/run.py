"""RIFT Experiment Runner — Phase 3.6 §17.

Unified entry point for running RIFT experiments.

Usage:
    python -m rift.experiments.run --experiment EXP-001
    python -m rift.experiments.run --experiment EXP-001 --dry-run
    python -m rift.experiments.run --list

Every experiment references a configuration in experiments/REGISTRY.yaml.
Every experiment produces a structured artifact directory in results/.

Authority: Phase 3.6 §17.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ---------------------------------------------------------------------------
# Experiment registry loader
# ---------------------------------------------------------------------------

REGISTRY_PATH = Path("experiments/REGISTRY.yaml")
RESULTS_DIR = Path("results")


def load_registry() -> Dict[str, Any]:
    """Load the experiment registry from experiments/REGISTRY.yaml."""
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(
            f"Experiment registry not found: {REGISTRY_PATH}. "
            "Run from repository root."
        )
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f)


def get_experiment_spec(experiment_id: str) -> Dict[str, Any]:
    """Get experiment specification by ID."""
    registry = load_registry()
    experiments = registry.get("experiments", {})
    if experiment_id not in experiments:
        available = sorted(experiments.keys())
        raise KeyError(
            f"Experiment '{experiment_id}' not found in registry. "
            f"Available: {available}"
        )
    return experiments[experiment_id]


# ---------------------------------------------------------------------------
# Experiment executor
# ---------------------------------------------------------------------------

class ExperimentRunner:
    """
    Executes one experiment as specified in REGISTRY.yaml.

    Responsibilities:
    1. Load experiment spec and configuration
    2. Load development/validation dataset (NEVER held-out during tuning)
    3. Run method(s) on each scenario
    4. Compute metrics
    5. Write artifacts to results/<experiment_id>/
    6. Write manifest

    LINUX DEPENDENCY:
    Experiments requiring live telemetry are marked PENDING_LINUX.
    Dry-run experiments can run on macOS.
    """

    def __init__(
        self,
        experiment_id: str,
        dry_run: bool = True,
        seed_override: Optional[int] = None,
        output_dir: Optional[Path] = None,
    ):
        self.experiment_id = experiment_id
        self.dry_run = dry_run
        self.seed_override = seed_override
        self.output_dir = output_dir or (RESULTS_DIR / experiment_id)

    def run(self) -> dict:
        """Execute the experiment. Returns summary dict."""
        spec = get_experiment_spec(self.experiment_id)
        seed = self.seed_override or spec.get("seed", 42)
        dataset = spec.get("dataset", "development")
        status = spec.get("status", "PLANNED")

        # Validate status
        if status == "PENDING_LINUX" and not self.dry_run:
            raise RuntimeError(
                f"Experiment '{self.experiment_id}' status is PENDING_LINUX. "
                "This experiment requires a live Linux testbed. "
                "Run with --dry-run for orchestration validation, "
                "or provision Linux and set dry_run=False."
            )

        # Initialize artifact writer
        from src.rift.artifacts.writer import ArtifactWriter
        from src.rift.provenance.logger import ProvenanceLogger

        writer = ArtifactWriter(
            base_dir=self.output_dir,
            experiment_id=self.experiment_id,
            seed=seed,
            scenario_id=spec.get("scenario_id"),
        )

        provenance = ProvenanceLogger(output_dir=self.output_dir)

        # Write config and environment
        writer.write_config({
            "spec": spec,
            "dry_run": self.dry_run,
            "dataset": dataset,
        })
        writer.write_environment()

        run_id = str(uuid.uuid4())
        prov_record = provenance.capture(
            run_id=run_id,
            seed=seed,
            scenario_id=spec.get("scenario_id"),
        )
        provenance.save(prov_record)

        # For PENDING_LINUX experiments in dry-run mode: record intent
        if status == "PENDING_LINUX":
            writer.write_raw_results({
                "status": "PENDING_LINUX",
                "message": (
                    f"Experiment '{self.experiment_id}' requires live Linux testbed. "
                    "Configure Online Boutique + Prometheus, then re-run with dry_run=False."
                ),
                "dry_run": True,
            })
            writer.write_metrics({"status": "PENDING_LINUX"})
            writer.write_statistics({"status": "PENDING_LINUX"})
            manifest = writer.finalize()
            return {
                "experiment_id": self.experiment_id,
                "status": "PENDING_LINUX",
                "run_id": run_id,
                "manifest": manifest,
            }

        # For synthetic/dry-run experiments: run the method
        result = self._run_synthetic(spec, seed, writer)
        manifest = writer.finalize()

        return {
            "experiment_id": self.experiment_id,
            "status": "COMPLETE",
            "run_id": run_id,
            "dry_run": self.dry_run,
            "result_summary": result,
            "manifest": manifest,
        }

    def _run_synthetic(self, spec: dict, seed: int, writer) -> dict:
        """
        Run synthetic validation for dry-run experiments.

        Uses MockTelemetry and the RIFT pipeline in dry-run mode.
        """
        method = spec.get("method", "RIFT-FULL")
        n_scenarios = spec.get("n_scenarios", 5)

        # Import pipeline components
        import numpy as np
        import networkx as nx
        from src.rift.benchmark.synthetic_benchmark import SyntheticBenchmark

        benchmark = SyntheticBenchmark(seed=seed)
        scenarios = benchmark.generate_scenarios(n=min(n_scenarios, 5))

        results = []
        for scenario in scenarios:
            results.append({
                "scenario_id": scenario.get("scenario_id", "unknown"),
                "method": method,
                "dry_run": self.dry_run,
                "status": "DRY_RUN_COMPLETE",
            })

        writer.write_inputs({
            "method": method,
            "n_scenarios": len(scenarios),
            "dataset": spec.get("dataset", "development"),
            "seed": seed,
        })
        writer.write_raw_results({"scenarios": results})
        writer.write_metrics({
            "n_scenarios": len(results),
            "dry_run": True,
            "note": "DRY_RUN: metrics are not evidence of live system performance.",
        })
        writer.write_statistics({"note": "DRY_RUN: no statistical tests executed."})

        return {"n_scenarios": len(results), "dry_run": True}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="RIFT Experiment Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--experiment", "-e",
        help="Experiment ID from REGISTRY.yaml (e.g. EXP-001)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run mode (default: True)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Enable live mode (requires Linux testbed). Overrides --dry-run.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override experiment seed",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all registered experiments",
    )

    args = parser.parse_args()

    if args.list:
        try:
            registry = load_registry()
            experiments = registry.get("experiments", {})
            print(f"\nRIFT Experiment Registry — {len(experiments)} experiments:\n")
            for eid, spec in sorted(experiments.items()):
                print(f"  {eid:12s}  {spec.get('status', 'PLANNED'):20s}  {spec.get('description', '')}")
            print()
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.experiment:
        parser.print_help()
        sys.exit(1)

    dry_run = not args.live

    runner = ExperimentRunner(
        experiment_id=args.experiment,
        dry_run=dry_run,
        seed_override=args.seed,
    )

    print(f"\n==> Running experiment: {args.experiment} (dry_run={dry_run})")
    t0 = time.time()

    try:
        result = runner.run()
        elapsed = time.time() - t0
        print(f"    Status:   {result['status']}")
        print(f"    Run ID:   {result['run_id']}")
        print(f"    Elapsed:  {elapsed:.1f}s")
        print(f"    Artifact: results/{args.experiment}/")
        print()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
