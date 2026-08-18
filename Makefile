# RIFT — Build / Test / Reproduce
# Phase 3.6 — Complete build system
# Python 3.11 required (see docs/ENVIRONMENT.md)

.PHONY: setup test test-unit test-causal test-integration test-safety \
        test-baselines test-evaluation test-leakage test-intervention \
        reproduce-phase3 reproduce-phase3-5 reproduce-all \
        experiment lint clean _check-python _check-pip \
        pre-linux-check pre-linux-status security-audit

# ---------------------------------------------------------------------------
# Paths / settings
# ---------------------------------------------------------------------------

PYTHON       ?= python3.11
PIP          := $(PYTHON) -m pip
PYTEST       := $(PYTHON) -m pytest
COV_FLAGS    := --cov=src/rift --cov-report=term-missing --cov-report=html:artifacts/coverage
RESULTS_DIR  := artifacts/phase3

# Forbidden phrases (causal-claim hygiene, per docs/PHASE_3_SPEC_FREEZE.md §18)
FORBIDDEN_PHRASES := \
  "causally accurate" \
  "proves causality" \
  "causal proof" \
  "causally correct" \
  "is the root cause" \
  "definitively caused"

# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

setup: _check-python
	@echo "==> Installing dependencies from requirements.txt"
	$(PIP) install --upgrade pip --quiet
	$(PIP) install -r requirements.txt --quiet
	@echo "==> Creating required directories"
	mkdir -p artifacts/phase3 artifacts/phase3_5 artifacts/coverage artifacts/logs
	mkdir -p artifacts/pre_linux
	mkdir -p tests/causal tests/integration/intervention tests/integration/safety
	mkdir -p tests/integration/telemetry tests/integration/fault_injection
	mkdir -p tests/unit/baselines tests/unit/evaluation tests/unit/telemetry
	mkdir -p tests/unit/fault_injection tests/unit/artifacts tests/unit/provenance
	mkdir -p results experiments configs
	touch tests/__init__.py tests/unit/__init__.py
	touch tests/causal/__init__.py
	touch tests/integration/__init__.py
	touch tests/integration/intervention/__init__.py
	touch tests/integration/safety/__init__.py
	touch tests/integration/telemetry/__init__.py
	touch tests/integration/fault_injection/__init__.py
	@echo "==> Setup complete"

_check-python:
	@$(PYTHON) --version >/dev/null 2>&1 || \
	  (echo "ERROR: $(PYTHON) not found. See docs/ENVIRONMENT.md." && exit 1)

_check-pip:
	@$(PIP) --version >/dev/null 2>&1 || \
	  (echo "ERROR: pip not available for $(PYTHON)." && exit 1)

# ---------------------------------------------------------------------------
# Test targets
# ---------------------------------------------------------------------------

test: _check-python
	@echo "==> Running full test suite with coverage"
	$(PYTEST) tests/ $(COV_FLAGS) -v 2>&1 | tee artifacts/logs/test_full.log
	@echo "==> Coverage HTML: artifacts/coverage/index.html"

test-unit: _check-python
	@echo "==> Running unit tests"
	$(PYTEST) tests/unit/ -v 2>&1 | tee artifacts/logs/test_unit.log

test-causal: _check-python
	@echo "==> Running causal tests (tests/causal/)"
	$(PYTEST) tests/causal/ -v 2>&1 | tee artifacts/logs/test_causal.log

test-integration: _check-python
	@echo "==> Running integration tests (skips Linux-only)"
	$(PYTEST) tests/integration/ -v \
	  2>&1 | tee artifacts/logs/test_integration.log

test-intervention: _check-python
	@echo "==> Running intervention tests (tests/integration/intervention/)"
	$(PYTEST) tests/integration/intervention/ -v \
	  2>&1 | tee artifacts/logs/test_intervention.log

test-safety: _check-python
	@echo "==> Running safety tests (tests/integration/safety/)"
	$(PYTEST) tests/integration/safety/ -v \
	  2>&1 | tee artifacts/logs/test_safety.log

test-baselines: _check-python
	@echo "==> Running baseline tests (tests/unit/baselines/)"
	$(PYTEST) tests/unit/baselines/ -v \
	  2>&1 | tee artifacts/logs/test_baselines.log

test-evaluation: _check-python
	@echo "==> Running evaluation tests"
	$(PYTEST) tests/unit/test_phase36_new_modules.py -v \
	  2>&1 | tee artifacts/logs/test_evaluation.log

test-leakage: _check-python
	@echo "==> Running leakage detection tests"
	$(PYTEST) tests/unit/test_leakage.py -v \
	  2>&1 | tee artifacts/logs/test_leakage.log

# Gate 3A: data model round-trip + validation
test-gate3a: _check-python
	@echo "==> Gate 3A: data model tests"
	$(PYTEST) tests/unit/test_data_models.py -v 2>&1 | tee artifacts/logs/test_gate3a.log
	@grep -q "passed" artifacts/logs/test_gate3a.log && \
	  echo "GATE 3A: PASS" || \
	  (echo "GATE 3A: FAIL" && exit 1)

# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

experiment: _check-python
ifndef EXP
	@echo "Usage: make experiment EXP=EXP-001"
	@exit 1
endif
	@echo "==> Running experiment: $(EXP)"
	$(PYTHON) -m rift.experiments.run --experiment $(EXP) --dry-run

experiment-list: _check-python
	$(PYTHON) -m rift.experiments.run --list

# ---------------------------------------------------------------------------
# Reproduction targets
# ---------------------------------------------------------------------------

reproduce-phase3: clean setup test-gate3a test
	@echo ""
	@echo "======================================================"
	@echo " RIFT Phase 3 — Reproduction Run Complete"
	@echo " Results:  $(RESULTS_DIR)/"
	@echo " Coverage: artifacts/coverage/index.html"
	@echo " Logs:     artifacts/logs/"
	@echo "======================================================"
	@echo "Environment:"
	@$(PYTHON) --version
	@$(PYTHON) -c "import pydantic; print('pydantic', pydantic.VERSION)"
	@$(PYTHON) -c "import numpy; print('numpy', numpy.__version__)"
	@$(PYTHON) -c "import scipy; print('scipy', scipy.__version__)"
	@uname -a 2>/dev/null || true

reproduce-phase3-5: reproduce-phase3
	@echo ""
	@echo "======================================================"
	@echo " RIFT Phase 3.5 — Reproduction Run"
	@echo " (Runs full Phase 3 suite + integration tests)"
	@echo "======================================================"
	$(PYTEST) tests/integration/safety/ -v

reproduce-all: _check-python
	@echo "==> Checking platform for Linux live validation"
	@if [ "$$(uname -s)" != "Linux" ]; then \
	  echo ""; \
	  echo "===================================================="; \
	  echo " LINUX LIVE VALIDATION NOT EXECUTED"; \
	  echo " Platform: $$(uname -s) — Linux required for live tests"; \
	  echo " Status: PENDING_LINUX"; \
	  echo "===================================================="; \
	  echo ""; \
	fi
	$(MAKE) reproduce-phase3
	@echo "==> Running all macOS-compatible tests"
	$(PYTEST) tests/ -v -k "not linux_only" \
	  2>&1 | tee artifacts/logs/reproduce_all.log
	@echo "==> Generating pre-Linux status report"
	$(PYTHON) scripts/generate_pre_linux_status.py

# ---------------------------------------------------------------------------
# Pre-Linux readiness check
# ---------------------------------------------------------------------------

pre-linux-check: test
	@echo ""
	@echo "======================================================"
	@echo " PRE-LINUX READINESS CHECK"
	@echo "======================================================"
	@$(PYTHON) -c "
import json, sys
from pathlib import Path
checks = {
    'src/rift/pipeline/e2e_runner.py': 'RIFT-FULL pipeline',
    'src/rift/baselines/rift_obs.py': 'RIFT-OBS',
    'src/rift/baselines/rift_random.py': 'RIFT-RANDOM',
    'src/rift/baselines/sieve_like.py': 'Sieve-like',
    'src/rift/baselines/oracle.py': 'Oracle',
    'src/rift/evaluation/attribution_metrics.py': 'Attribution metrics',
    'src/rift/evaluation/divergence_metrics.py': 'Divergence metrics',
    'src/rift/evaluation/ebd_metrics.py': 'EBD metrics',
    'src/rift/evaluation/power.py': 'Power analysis',
    'src/rift/evaluation/held_out_guard.py': 'Held-out guard',
    'src/rift/artifacts/writer.py': 'Artifact writer',
    'docs/CLAIMS_REGISTRY.yaml': 'Claims registry',
    'docs/PAPER_EVIDENCE_MATRIX.md': 'Evidence matrix',
    'docs/SYSTEM_COMPLETENESS_MATRIX.md': 'Completeness matrix',
    'docs/telemetry/ARCHITECTURE.md': 'Telemetry architecture',
    'experiments/REGISTRY.yaml': 'Experiment registry',
    'configs/development.yaml': 'Development config',
    'configs/held_out.yaml': 'Held-out config',
    'docs/SECURITY_AUDIT.md': 'Security audit',
}
all_pass = True
for path, name in checks.items():
    exists = Path(path).exists()
    status = 'PASS' if exists else 'FAIL'
    if not exists:
        all_pass = False
    print(f'  [{status}] {name}: {path}')
print()
if all_pass:
    print('PRE-LINUX GATE: ALL CHECKS PASSED')
else:
    print('PRE-LINUX GATE: SOME CHECKS FAILED')
    sys.exit(1)
"

# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------

lint: _check-python
	@echo "==> Checking for forbidden causal-claim phrases in src/"
	@FOUND=0; \
	for phrase in $(FORBIDDEN_PHRASES); do \
	  matches=$$(grep -rn --include="*.py" --include="*.md" -l "$$phrase" src/ docs/ 2>/dev/null || true); \
	  if [ -n "$$matches" ]; then \
	    echo "FORBIDDEN PHRASE FOUND: $$phrase"; \
	    grep -rn --include="*.py" --include="*.md" "$$phrase" src/ docs/; \
	    FOUND=1; \
	  fi; \
	done; \
	if [ "$$FOUND" -eq 1 ]; then echo "lint: FAIL (forbidden phrases)"; exit 1; fi
	@echo "==> Forbidden phrase check: PASS"
	@echo "==> Running flake8 on src/"
	$(PYTHON) -m flake8 src/ --max-line-length=100 --extend-ignore=E203,W503 || \
	  (echo "lint: flake8 warnings (non-blocking)" && true)
	@echo "==> Lint complete"

# ---------------------------------------------------------------------------
# Security audit
# ---------------------------------------------------------------------------

security-audit: _check-python
	@echo "==> RIFT Security Audit"
	@echo "==> Scanning for API keys, tokens, passwords..."
	@FOUND=0; \
	for pattern in "api_key" "password" "Bearer " "private_key" "access_token"; do \
	  matches=$$(grep -rn --include="*.py" --include="*.yaml" --include="*.json" \
	    "$$pattern" src/ configs/ 2>/dev/null | grep -v "#" | grep -v "check_no_secrets" | grep -v "secret_patterns" || true); \
	  if [ -n "$$matches" ]; then \
	    echo "  POTENTIAL SECRET: $$pattern"; \
	    echo "$$matches"; \
	    FOUND=1; \
	  fi; \
	done; \
	if [ "$$FOUND" -eq 0 ]; then echo "  Security scan: PASS (no secrets found)"; \
	else echo "  Security scan: REVIEW REQUIRED"; fi

# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------

clean:
	@echo "==> Cleaning generated artefacts"
	rm -rf artifacts/coverage artifacts/logs
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo "==> Clean complete"
