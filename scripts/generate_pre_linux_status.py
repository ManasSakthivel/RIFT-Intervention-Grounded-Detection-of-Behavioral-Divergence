#!/usr/bin/env python3.11
"""Generate PRE_LINUX_STATUS.json — Phase 3.6 §32.

Run after all macOS tests pass to generate the pre-Linux readiness artifact.
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path


def get_git_commit() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def check_file_exists(path: str) -> dict:
    p = Path(path)
    return {"path": path, "exists": p.exists(), "status": "PASS" if p.exists() else "FAIL"}


def main():
    output_dir = Path("artifacts/pre_linux")
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Component checks ─────────────────────────────────────────────────────
    components = {
        "RIFT-FULL pipeline": "src/rift/pipeline/e2e_runner.py",
        "CID evaluator": "src/rift/cid/cid.py",
        "EBD evaluator": "src/rift/ebd/ebd.py",
        "Safety controller": "src/rift/safety/safety.py",
        "Closed-loop machine": "src/rift/loop/closed_loop.py",
        "FCI runner": "src/rift/fci/fci_runner.py",
        "Identifiability": "src/rift/identifiability/identifiability.py",
        "Cost model/MSIS": "src/rift/optimizer/cost_model.py",
        "Network intervention": "src/rift/intervention/network_intervention.py",
        "Intervention lifecycle": "src/rift/intervention/intervention_lifecycle.py",
        "DryRun backend": "src/rift/intervention/backends/dry_run.py",
        "LinuxTcNetem backend": "src/rift/intervention/backends/linux_tc_netem.py",
        "Fault injector": "src/rift/fault_injection/fault_injector.py",
        "RIFT-OBS baseline": "src/rift/baselines/rift_obs.py",
        "RIFT-RANDOM baseline": "src/rift/baselines/rift_random.py",
        "Sieve-like baseline": "src/rift/baselines/sieve_like.py",
        "Sage+Chaos stub": "src/rift/baselines/sage_chaos.py",
        "Oracle upper bound": "src/rift/baselines/oracle.py",
        "Attribution metrics": "src/rift/evaluation/attribution_metrics.py",
        "Divergence metrics": "src/rift/evaluation/divergence_metrics.py",
        "EBD metrics": "src/rift/evaluation/ebd_metrics.py",
        "Statistical framework": "src/rift/statistics/stats.py",
        "Power analysis": "src/rift/evaluation/power.py",
        "Held-out guard": "src/rift/evaluation/held_out_guard.py",
        "Artifact writer": "src/rift/artifacts/writer.py",
        "Provenance logger": "src/rift/provenance/logger.py",
        "Experiment runner": "src/rift/experiments/run.py",
        "Failure taxonomy": "src/rift/models/failure_codes.py",
        "Telemetry normalizer": "src/rift/telemetry/normalizer.py",
        "Instrumentation": "src/rift/telemetry/instrumentation.py",
        "Data models": "src/rift/models/data_models.py",
        "SCM": "src/rift/scm/scm.py",
        "Time-sliced G_T": "src/rift/graph/time_slice.py",
        "Anomaly subgraph": "src/rift/graph/anomaly_subgraph.py",
    }

    docs = {
        "SYSTEM_COMPLETENESS_MATRIX": "docs/SYSTEM_COMPLETENESS_MATRIX.md",
        "CLAIMS_REGISTRY": "docs/CLAIMS_REGISTRY.yaml",
        "PAPER_EVIDENCE_MATRIX": "docs/PAPER_EVIDENCE_MATRIX.md",
        "SECURITY_AUDIT": "docs/SECURITY_AUDIT.md",
        "TELEMETRY_ARCHITECTURE": "docs/telemetry/ARCHITECTURE.md",
        "RIFT_OBS_DOC": "docs/baselines/RIFT_OBS.md",
        "RIFT_RANDOM_DOC": "docs/baselines/RIFT_RANDOM.md",
        "SIEVE_LIKE_DOC": "docs/baselines/SIEVE_LIKE.md",
        "SAGE_CHAOS_DOC": "docs/baselines/SAGE_CHAOS.md",
        "ORACLE_DOC": "docs/baselines/ORACLE.md",
    }

    configs_required = {
        "development": "configs/development.yaml",
        "validation": "configs/validation.yaml",
        "held_out": "configs/held_out.yaml",
        "live": "configs/live.yaml",
        "dry_run": "configs/dry_run.yaml",
    }

    deployment = {
        "docker-compose": "docker/docker-compose.yml",
        "prometheus": "docker/prometheus.yml",
        "otel-collector": "docker/otel-collector-config.yaml",
        "start_testbed": "scripts/start_testbed.sh",
        "stop_testbed": "scripts/stop_testbed.sh",
        "health_check": "scripts/health_check_testbed.sh",
        "cleanup": "scripts/cleanup_testbed.sh",
    }

    registry = {
        "REGISTRY.yaml": "experiments/REGISTRY.yaml",
    }

    def check_group(group: dict) -> dict:
        results = {}
        all_pass = True
        for name, path in group.items():
            exists = Path(path).exists()
            results[name] = {"path": path, "exists": exists, "status": "PASS" if exists else "FAIL"}
            if not exists:
                all_pass = False
        return results, all_pass

    component_results, comp_pass = check_group(components)
    doc_results, doc_pass = check_group(docs)
    config_results, config_pass = check_group(configs_required)
    deploy_results, deploy_pass = check_group(deployment)
    registry_results, registry_pass = check_group(registry)

    # ── Linux dependency declaration ─────────────────────────────────────────
    linux_pending = [
        "Live Prometheus/OTEL telemetry collection",
        "Online Boutique deployment on Linux",
        "tc netem per-destination interventions (CAP_NET_ADMIN)",
        "kubectl-based fault injection",
        "Live E2E RIFTRunRecord with live_telemetry_used=True",
        "Final hypothesis tests H1-H5 (require live data)",
        "Final Precision@1 measurement on held-out test set",
    ]

    # ── Build status ──────────────────────────────────────────────────────────
    all_implemented = all([comp_pass, doc_pass, config_pass, deploy_pass, registry_pass])
    platform_name = platform.system()

    status = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": get_git_commit(),
        "platform": platform_name,
        "python_version": platform.python_version(),
        "phase": "3.6",
        "pre_linux_ready": all_implemented,
        "components": component_results,
        "documentation": doc_results,
        "configurations": config_results,
        "deployment": deploy_results,
        "experiment_registry": registry_results,
        "linux_pending": linux_pending,
        "linux_validation_status": "PENDING_LINUX",
        "frozen_historical_results": {
            "raw_precision_at_1": 0.50,
            "conditional_precision_at_1": 0.60,
            "source": "artifacts/phase3_5/v1_decomposition.json",
            "note": "Synthetic only. NOT final publication results.",
        },
        "phase_4_authorized": False,
        "phase_4_note": "Phase 4 NOT authorized until live Linux E2E validation is complete.",
    }

    output_path = output_dir / "PRE_LINUX_STATUS.json"
    output_path.write_text(json.dumps(status, indent=2))
    print(f"==> PRE_LINUX_STATUS.json written: {output_path}")

    # Summary
    print()
    print("=" * 60)
    print(f" PRE-LINUX STATUS: {'READY' if all_implemented else 'PARTIAL'}")
    print(f" Components:     {'ALL PRESENT' if comp_pass else 'MISSING ITEMS'}")
    print(f" Documentation:  {'ALL PRESENT' if doc_pass else 'MISSING ITEMS'}")
    print(f" Configurations: {'ALL PRESENT' if config_pass else 'MISSING ITEMS'}")
    print(f" Deployment:     {'ALL PRESENT' if deploy_pass else 'MISSING ITEMS'}")
    print(f" Registry:       {'ALL PRESENT' if registry_pass else 'MISSING ITEMS'}")
    print(f" Platform:       {platform_name}")
    print(f" Linux tests:    PENDING_LINUX")
    print("=" * 60)


if __name__ == "__main__":
    main()
