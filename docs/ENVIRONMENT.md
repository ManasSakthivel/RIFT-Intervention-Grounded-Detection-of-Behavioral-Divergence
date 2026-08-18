# RIFT — Environment Requirements

**Document:** `docs/ENVIRONMENT.md`  
**Applies to:** All contributors, reviewers, and reproduction auditors  
**Phase:** 3 (Evaluation and Reproducibility)

---

## 1. Purpose

This document specifies every dependency, configuration, and assumption required to run the RIFT evaluation testbed and reproduce Phase 3 results. A reader who follows this document from scratch on a clean machine should arrive at an identical test environment.

---

## 2. Host Machine Requirements

| Property | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Free disk | 10 GB | 20 GB |
| OS | Linux (x86_64) | Ubuntu 22.04 LTS or Debian 12 |
| Kernel | 5.4+ | 6.1+ |

> **macOS / Windows note:** The `tc netem` network intervention mechanism requires Linux kernel capabilities (`NET_ADMIN`). On macOS or Windows, intervention tests must run inside the Docker container (see §5). Unit tests and causal model tests run on any platform.

---

## 3. Python Environment

### 3.1 Required version

```
Python 3.11.x  (CPython reference implementation)
```

Python 3.9 and 3.10 are **not supported** due to use of `from __future__ import annotations` semantics with pydantic v2's `model_validator(mode="after")`.  
Python 3.12+ is untested; results may differ due to hash-randomisation changes.

### 3.2 Install Python 3.11

**Ubuntu / Debian:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3.11-dev
```

**macOS (Homebrew):**
```bash
brew install python@3.11
```

**From source (fallback):**
```bash
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar xf Python-3.11.9.tgz && cd Python-3.11.9
./configure --enable-optimizations && make -j$(nproc) && sudo make altinstall
```

### 3.3 Virtual environment

All dependencies must be installed into a dedicated virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
make setup
```

Never install into the system Python. The `Makefile` assumes `python3.11` is on `PATH`; override with `make setup PYTHON=/path/to/python3.11`.

---

## 4. Python Dependencies

All dependencies are pinned in [`requirements.txt`](../requirements.txt). The exact versions below have been validated for Phase 3 reproducibility.

| Package | Pinned version | Purpose |
|---|---|---|
| `pydantic` | 2.7.1 | Data models, validation (Phase 3A gate) |
| `numpy` | 1.26.4 | Numerical computation, array ops |
| `scipy` | 1.13.1 | Statistical tests (permutation, CDF) |
| `scikit-learn` | 1.5.0 | ML utilities, cross-validation |
| `networkx` | 3.3 | Causal graph representation and traversal |
| `pandas` | 2.2.2 | Time-series alignment, metric windows |
| `causal-learn` | 0.1.3.8 | FCI algorithm implementation |
| `pyarrow` | 16.1.0 | Dataset I/O for RIFT fault traces |
| `statsmodels` | 0.14.2 | Statistical diagnostics |
| `hypothesis` | 6.103.1 | Property-based testing |
| `pytest` | 8.2.1 | Test runner |
| `pytest-cov` | 5.0.0 | Coverage reporting |
| `matplotlib` | 3.9.0 | Result visualisation |
| `seaborn` | 0.13.2 | Statistical plots |
| `tqdm` | 4.66.4 | Progress display |
| `jsonschema` | 4.22.0 | Schema validation utilities |

> **Do not upgrade any pinned dependency without re-running the full Phase 3 test suite.** Version changes in `scipy`, `causal-learn`, or `pydantic` can alter statistical results or model validation behaviour.

---

## 5. Docker Environment

For fully hermetic reproduction (recommended for reviewers), use the provided Docker image.

### 5.1 Requirements

| Tool | Minimum version |
|---|---|
| Docker | 24.0+ |
| Docker Compose | v2.24+ (plugin, not standalone) |

### 5.2 Build and run

```bash
# Build the reproducible image
docker build \
  --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --build-arg GIT_SHA="$(git rev-parse HEAD)" \
  --build-arg HOST_KERNEL="$(uname -r)" \
  --build-arg HOST_OS="$(uname -s)" \
  -t rift-eval:latest \
  -f docker/Dockerfile .

# Run the Gate 3A test suite
docker run --rm rift-eval:latest \
  python3.11 -m pytest tests/unit/test_data_models.py -v

# Run the full test suite
docker run --rm rift-eval:latest \
  python3.11 -m pytest tests/ --tb=short -v

# Run the full testbed (RIFT + Online Boutique + observability)
cd docker
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
GIT_SHA="$(git -C .. rev-parse HEAD)" \
HOST_KERNEL="$(uname -r)" \
HOST_OS="$(uname -s)" \
docker compose up -d

# Run Phase 3 reproduction inside the testbed
docker compose run rift-eval make reproduce-phase3
```

### 5.3 What the Docker image contains

- Python 3.11-slim (Debian Bookworm base)
- All pinned pip dependencies from `requirements.txt`
- `iproute2` (provides `tc`, `ip`) for netem-based interventions
- `iptables` for network partition interventions
- Non-root user `rift` (uid 1001) executes all tests
- Build-time labels record OS, kernel version, git SHA, and build date

### 5.4 Reproducibility guarantee

The image is fully deterministic: given the same `requirements.txt` and the same base image digest, two builds from the same source tree will produce identical test results. The base image is pinned by tag (`python:3.11-slim`); for absolute reproducibility, pin by digest:

```bash
# Get the current digest
docker inspect python:3.11-slim --format '{{index .RepoDigests 0}}'
# Then pin in Dockerfile: FROM python@sha256:<digest>
```

---

## 6. System Packages (host, for non-Docker execution)

Network intervention tests require `tc` from `iproute2`. Install on the host if running tests outside Docker:

```bash
# Ubuntu / Debian
sudo apt-get install iproute2 iptables

# Fedora / RHEL
sudo dnf install iproute iptables
```

Verify:
```bash
tc -Version    # expected: tc utility, iproute2-X.X.X
ip -Version    # expected: ip utility, iproute2-X.X.X
```

Network intervention tests also require `CAP_NET_ADMIN`. Either run as root (not recommended) or grant the capability to the test process:

```bash
sudo setcap cap_net_admin+ep $(which python3.11)
```

---

## 7. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `RIFT_SANDBOX_NAMESPACE` | `rift-eval-default` | Namespace prefix for sandbox enforcement. Intervention targets must match `rift-eval-*`. |
| `RIFT_PROMETHEUS_URL` | `http://localhost:9090` | Prometheus scrape endpoint |
| `RIFT_JAEGER_URL` | `http://localhost:16686` | Jaeger query endpoint |
| `PYTHONHASHSEED` | `0` | Set to `0` for deterministic dict/set ordering in reproducibility runs |
| `PYTHONPATH` | *(project root)* | Must include the project root so `src.rift.*` imports resolve |

Set for local runs:
```bash
export PYTHONHASHSEED=0
export PYTHONPATH=$(pwd)
export RIFT_SANDBOX_NAMESPACE=rift-eval-default
```

---

## 8. Makefile Targets

| Target | Description |
|---|---|
| `make setup` | Install deps, create directories |
| `make test` | Run all tests with HTML coverage report |
| `make test-unit` | Unit tests only (`tests/unit/`) |
| `make test-causal` | Causal model tests (`tests/causal/`) |
| `make test-intervention` | Intervention integration tests |
| `make test-safety` | Safety module tests |
| `make test-gate3a` | Phase 3A gate: data model round-trips + validators |
| `make reproduce-phase3` | Full reproduction from clean state |
| `make lint` | Forbidden-phrase check + flake8 |
| `make clean` | Remove generated artefacts |

Override Python interpreter:
```bash
make setup PYTHON=/usr/local/bin/python3.11
make test PYTHON=/usr/local/bin/python3.11
```

---

## 9. Recorded Environment (Phase 3 Reference Run)

The following environment was used to produce the Phase 3 reference results. Deviations from this environment should be noted when reporting results.

| Property | Value |
|---|---|
| OS | Ubuntu 22.04.4 LTS |
| Kernel | 6.5.0-35-generic (x86_64) |
| Python | CPython 3.11.9 |
| pydantic | 2.7.1 |
| numpy | 1.26.4 |
| scipy | 1.13.1 |
| causal-learn | 0.1.3.8 |
| Docker | 26.1.3 |
| Docker Compose | v2.27.0 |
| CPU | AMD EPYC 7763 (8 vCPU) |
| RAM | 16 GB |

---

## 10. Known Platform Differences

| Platform | Impact | Mitigation |
|---|---|---|
| macOS (arm64) | `tc netem` not available; intervention tests will skip | Run in Docker |
| Windows (WSL2) | Network namespace isolation may differ | Run in Docker |
| Python 3.12+ | `__future__` annotation semantics may differ | Pin to 3.11 |
| numpy > 1.26.x | Random seed behaviour may differ for permutation tests | Do not upgrade |
| causal-learn > 0.1.3.8 | FCI output format changes are untested | Do not upgrade |

---

## 11. Verifying the Environment

Run the following to confirm the environment is correctly configured:

```bash
# Python version
python3.11 --version
# Expected: Python 3.11.x

# Key package versions
python3.11 -c "import pydantic; print('pydantic', pydantic.VERSION)"
python3.11 -c "import numpy; print('numpy', numpy.__version__)"
python3.11 -c "import scipy; print('scipy', scipy.__version__)"

# Gate 3A (must pass before any other Phase 3 work)
make test-gate3a
# Expected: 119 passed, 0 failed

# tc (for intervention tests on Linux hosts)
tc -Version
# Expected: tc utility, iproute2-X.X.X
```
