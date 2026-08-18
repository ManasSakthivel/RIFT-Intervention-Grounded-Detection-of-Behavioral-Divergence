# RIFT Phase 3.5O — Reproduction Guide

**Document:** `docs/phase3_5/reproduction.md`  
**Phase:** 3.5O (Reproducibility Documentation Gate)  
**Status:** DOCUMENTATION_COMPLETE  
**Generated:** 2026-08-17  

---

> ⚠️ **Platform constraint — read first:**  
> **Network intervention (`tc`/`netem`) requires Linux. macOS cannot execute live interventions.**  
> All `tc`/`netem` calls on macOS are dry-run only and are marked `PARTIAL` in artifacts.  
> Do not claim cross-platform support for live network intervention.

---

## Table of Contents

1. [Environment Requirements](#1-environment-requirements)  
   - [Tier 1 — Python-only validation (macOS or Linux)](#tier-1--python-only-validation-macos-or-linux)  
   - [Tier 2 — Full live testbed (Linux only)](#tier-2--full-live-testbed-linux-only)  
2. [Pinned Dependency Versions](#2-pinned-dependency-versions)  
3. [Step-by-Step Reproduction](#3-step-by-step-reproduction)  
4. [Expected Outputs](#4-expected-outputs)  
5. [Known Issues and Troubleshooting](#5-known-issues-and-troubleshooting)  
6. [Explicit macOS Statement](#6-explicit-macos-statement)  
7. [Verification Checklist](#7-verification-checklist)  

---

## 1. Environment Requirements

### Tier 1 — Python-only validation (macOS or Linux)

Reproduces the 453-test suite (all algorithmic and data-model components). Does **not** exercise live network interventions.

| Requirement | Minimum | Recommended |
|---|---|---|
| Python | 3.10 | **3.11.x** (CPython) |
| pip | any recent | latest |
| OS | macOS or Linux | Ubuntu 22.04 LTS |
| Docker | not required | — |
| Linux kernel | not required | — |
| tc / iproute2 | not required | — |
| RAM | 4 GB | 8 GB |
| Disk | 2 GB | 5 GB |

> **Python version note:** `pyproject.toml` declares `requires-python = ">=3.10"` and the Makefile sets `PYTHON ?= python3.11`. The Phase 3 reference run recorded in `PHASE_3_MANIFEST.json` executed on Python 3.9.6 (pre-constraint), but the project's pinned `pydantic==2.7.1` and `model_validator(mode="after")` usage formally require Python 3.11 for guaranteed semantics. **Use Python 3.11.** See [`docs/ENVIRONMENT.md §3`](../ENVIRONMENT.md) for installation instructions.

### Tier 2 — Full live testbed (Linux only)

Adds live `tc`/`netem` network interventions, the Online Boutique microservice mesh, Prometheus, and Jaeger. Required for full Phase 3G/3H validation.

| Requirement | Minimum | Notes |
|---|---|---|
| OS | Linux | x86_64; Ubuntu 22.04 LTS recommended |
| Kernel | **4.9** (netem ABI stable) | 5.4+ recommended; reference run: 6.5.0-35-generic |
| Docker | **24.0+** | |
| Docker Compose | **v2.24+** (plugin) | `docker compose` — NOT standalone `docker-compose` |
| `CAP_NET_ADMIN` | required | for `tc` inside container |
| iproute2 / tc | required on host OR inside container | `apt-get install iproute2` |
| netem kernel module | `sch_netem` loaded | verify: `modinfo sch_netem` |
| Git | any | for recording HEAD SHA in build labels |
| RAM | **8 GB** minimum | Online Boutique requires ~6 GB at full load |
| Disk | **10 GB** minimum | image pulls: ~3 GB boutique + ~1 GB observability stack |
| CPU | 4 cores | 8 cores recommended |

> **Compose v2 syntax is mandatory.** The compose file uses `docker compose` (space, not hyphen). Using `docker-compose` v1 will fail.

---

## 2. Pinned Dependency Versions

All dependencies are locked in [`requirements.txt`](../../requirements.txt). The table below is derived directly from that file and from [`docs/ENVIRONMENT.md §4`](../ENVIRONMENT.md).

| Package | Pinned version | Role |
|---|---|---|
| `pydantic` | 2.7.1 | Data models, Phase 3A gate |
| `numpy` | 1.26.4 | Numerical computation, permutation tests |
| `scipy` | 1.13.1 | Statistical tests (permutation, CDF) |
| `scikit-learn` | 1.5.0 | ML utilities, cross-validation |
| `networkx` | 3.3 | Causal graph representation (PAG, DAG) |
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

> **Do not upgrade any pinned dependency** without re-running the full suite. `scipy`, `causal-learn`, and `pydantic` version changes can alter statistical results or model-validation behaviour.

---

## 3. Step-by-Step Reproduction

### Step 1 — Clone and install

```bash
git clone <repo-url>
cd rift

# Create and activate a virtual environment (strongly recommended)
python3.11 -m venv .venv
source .venv/bin/activate

# Install all pinned dependencies
python3.11 -m pip install --upgrade pip
python3.11 -m pip install -r requirements.txt

# Or use the Makefile target (checks python3.11 is on PATH first)
make setup
```

---

### Step 2 — Verify Python tests *(macOS or Linux — Tier 1)*

```bash
# Set required environment variables for determinism
export PYTHONHASHSEED=0
export PYTHONPATH=$(pwd)
export RIFT_SANDBOX_NAMESPACE=rift-eval-default

# Run the full test suite with coverage
make test
# Alias: python3.11 -m pytest tests/ --cov=src/rift --cov-report=term-missing -v

# Expected output:
#   453 passed, 0 failed, 0 errors
#   Coverage HTML: artifacts/coverage/index.html
#   Log:           artifacts/logs/test_full.log
```

To run component subsets:

```bash
make test-gate3a          # Phase 3A data-model gate: 119 tests
make test-unit            # Unit tests: tests/unit/
make test-causal          # Causal model tests: tests/causal/
make test-intervention    # Intervention integration tests (Linux: live; macOS: dry-run)
make test-safety          # Safety module tests: tests/integration/safety/
```

Full reproduction from a clean state (runs `clean` → `setup` → `test-gate3a` → `test`):

```bash
make reproduce-phase3
```

---

### Step 3 — Verify the host environment *(Linux only — Tier 2 prerequisite)*

```bash
# Kernel version (must be >= 4.9 for netem ABI stability)
uname -r
# Expected: 5.4+ (reference: 6.5.0-35-generic)

# tc version (from iproute2)
tc -Version
# Expected: tc utility, iproute2-X.X.X

# netem kernel module
modinfo sch_netem
# Expected: module metadata (filename, description, etc.)
# If not found: sudo modprobe sch_netem

# Docker version
docker --version
# Expected: Docker version 24.x or higher

# Docker Compose version (must be v2 plugin, not standalone)
docker compose version
# Expected: Docker Compose version v2.24.x or higher

# Available disk space
df -h .
# Need >= 10 GB free
```

---

### Step 4 — Deploy the testbed *(Linux only — Tier 2)*

```bash
# Set build-time traceability variables (recorded as OCI image labels)
export BUILD_DATE=$(date -Iseconds)
export GIT_SHA=$(git rev-parse HEAD)
export HOST_KERNEL=$(uname -r)
export HOST_OS=$(uname -s)

# Build the RIFT evaluation image
docker compose -f docker/docker-compose.yml build \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg GIT_SHA="$GIT_SHA" \
  --build-arg HOST_KERNEL="$HOST_KERNEL" \
  --build-arg HOST_OS="$HOST_OS"

# Pull Online Boutique microservice images (~3 GB)
docker compose -f docker/docker-compose.yml pull

# Start the full testbed (RIFT eval + 11 boutique services + Prometheus + Jaeger)
docker compose -f docker/docker-compose.yml up -d

# Allow services to stabilise (boutique-loadgen starts last)
sleep 60

# Health checks
curl -sf http://localhost:8080/ -o /dev/null && echo "boutique-frontend: OK"
curl -sf http://localhost:9090/ -o /dev/null && echo "prometheus: OK"
curl -sf http://localhost:16686/ -o /dev/null && echo "jaeger: OK"
```

Services started by the compose file:

| Service | Image | Port(s) |
|---|---|---|
| `rift-eval` | built from `docker/Dockerfile` | — |
| `boutique-frontend` | `gcr.io/…/frontend:v0.9.0` | 8080 |
| `boutique-cart` | `gcr.io/…/cartservice:v0.9.0` | — |
| `boutique-product` | `gcr.io/…/productcatalogservice:v0.9.0` | — |
| `boutique-checkout` | `gcr.io/…/checkoutservice:v0.9.0` | — |
| `boutique-recommend` | `gcr.io/…/recommendationservice:v0.9.0` | — |
| `boutique-payment` | `gcr.io/…/paymentservice:v0.9.0` | — |
| `boutique-email` | `gcr.io/…/emailservice:v0.9.0` | — |
| `boutique-shipping` | `gcr.io/…/shippingservice:v0.9.0` | — |
| `boutique-currency` | `gcr.io/…/currencyservice:v0.9.0` | — |
| `boutique-ad` | `gcr.io/…/adservice:v0.9.0` | — |
| `boutique-redis` | `redis:7.2-alpine` | — |
| `boutique-loadgen` | `gcr.io/…/loadgenerator:v0.9.0` | — |
| `prometheus` | `prom/prometheus:v2.52.0` | 9090 |
| `jaeger` | `jaegertracing/all-in-one:1.57` | 16686, 14268 |

---

### Step 5 — Verify telemetry

```bash
# Check all Prometheus scrape targets are UP
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool | grep '"health"'
# Expected: "health": "up" for each target

# Check Jaeger services are registered
curl -s http://localhost:16686/api/services | python3 -m json.tool
# Expected: JSON list including boutique service names
```

---

### Step 6 — Run network intervention tests *(Linux + CAP_NET_ADMIN — Tier 2)*

The `rift-eval` service in `docker-compose.yml` already declares `cap_add: [NET_ADMIN]`. To run intervention tests explicitly:

```bash
docker compose -f docker/docker-compose.yml run --cap-add NET_ADMIN rift-eval \
  python3.11 -m pytest tests/integration/intervention/ -v

# Log saved to: artifacts/logs/test_intervention.log (via volume mount)
```

---

### Step 7 — Run an end-to-end RIFT pipeline scenario

```bash
docker compose -f docker/docker-compose.yml run rift-eval \
  python3.11 -m src.rift.pipeline.e2e_runner --scenario NL_01

# Expected output: RIFTRunRecord JSON artifact written to artifacts/phase3/
```

---

### Step 8 — Tear down the testbed

```bash
docker compose -f docker/docker-compose.yml down -v
# -v removes named volumes (prometheus-data, jaeger-data, rift-artifacts)
```

---

## 4. Expected Outputs

| Validation | Expected result | Tier |
|---|---|---|
| `make test` / `make reproduce-phase3` | **453 PASS, 0 FAIL** | 1 (any OS) |
| `make test-gate3a` | **119 PASS** | 1 (any OS) |
| Boutique frontend health | HTTP 200 at `localhost:8080` | 2 (Linux) |
| Prometheus health | HTTP 200 at `localhost:9090` | 2 (Linux) |
| Jaeger health | HTTP 200 at `localhost:16686` | 2 (Linux) |
| Network intervention tests | PASS | 2 (Linux + CAP_NET_ADMIN) |
| E2E pipeline run | `RIFTRunRecord` JSON artifact | 2 (Linux) |

### Phase 3 component test breakdown (from `PHASE_3_MANIFEST.json`)

| Component | Tests | Status |
|---|---|---|
| 3A — Data models | 119/119 | VALIDATED |
| 3B — SCM | 39/39 | VALIDATED |
| 3E — FCI/PAG | 44/44 | VALIDATED |
| 3F — Identifiability | 37/37 | VALIDATED |
| 3I/3J — CID + Wasserstein | 46/46 | VALIDATED |
| 3K — EBD | 28/28 | VALIDATED |
| 3L — Cost optimizer | 24/24 | VALIDATED |
| 3M — Closed-loop | 49/49 | VALIDATED |
| 3N — Safety | 37/37 | VALIDATED |
| 3T — Statistics | 46/46 | VALIDATED |
| 3G/3H — Network intervention | — | **PARTIAL** (macOS dry-run; Linux required) |
| 3W — Independent validation | V1=50%, V2=100% | **PARTIAL** (oracle PAG; live testbed = Phase 10) |

---

## 5. Known Issues and Troubleshooting

### 1. macOS: `tc` commands are dry-run only

**Symptom:** `tc` calls in intervention tests silently succeed but produce no real network effect.  
**Root cause:** macOS does not expose Linux network namespaces or `sch_netem`.  
**Mitigation:** Run intervention tests inside the Docker container on a Linux host, or accept `PARTIAL` status and mark results as dry-run.

### 2. Python version discrepancy in Phase 3 manifest

**Symptom:** `PHASE_3_MANIFEST.json` records `"python_version": "3.9.6"`, but `pyproject.toml` requires `>=3.10` and `ENVIRONMENT.md` requires 3.11.  
**Root cause:** The manifest was generated on the development machine's system Python (3.9.6) before the `requires-python` constraint was enforced.  
**Mitigation:** **Use Python 3.11** as specified in the Makefile and `ENVIRONMENT.md`. The 3.9.6 run is a known discrepancy; reproducers should target 3.11.

### 3. Prometheus scrapes gRPC ports

**Symptom:** Some boutique services expose only gRPC; Prometheus HTTP scrapes may return no metrics or a connection error.  
**Mitigation:** An OpenTelemetry Collector sidecar may be needed to translate gRPC telemetry to Prometheus-scrapeable HTTP. This is deferred to Phase 10 (full evaluation). Current Prometheus config in `docker/prometheus.yml` covers the ports defined in the compose file.

### 4. `boutique-loadgen` start-up timing

**Symptom:** `boutique-loadgen` fails to reach the frontend immediately after `docker compose up -d`.  
**Mitigation:** Add a 30-second startup delay before expecting load generation to succeed. The compose file uses `restart: "no"`, so a failed start is not retried automatically. If needed, restart with `docker compose restart boutique-loadgen`.

### 5. Docker Compose v1 vs v2 syntax

**Symptom:** `docker-compose up` (v1 standalone) fails or behaves differently.  
**Fix:** Use `docker compose` (v2 plugin syntax). Verify: `docker compose version` should return `v2.24+`.

### 6. `CAP_NET_ADMIN` required for `tc` tests

**Symptom:** Intervention tests fail with `RTNETLINK answers: Operation not permitted`.  
**Fix:** The `rift-eval` service in `docker-compose.yml` already includes `cap_add: [NET_ADMIN]`. For `docker run` invocations outside compose, always pass `--cap-add NET_ADMIN`.

### 7. Disk space exhaustion during image pull

**Symptom:** `docker compose pull` fails mid-way with `no space left on device`.  
**Fix:** Ensure ≥10 GB free disk. Run `docker system prune -f` to reclaim space from unused images before pulling.

### 8. `PYTHONHASHSEED` not set

**Symptom:** Dict/set ordering differs across runs; some property-based tests produce non-deterministic failures.  
**Fix:** Always export `PYTHONHASHSEED=0` before running the test suite outside Docker. Inside Docker, the compose file sets this automatically.

---

## 6. Explicit macOS Statement

> **This project cannot perform live network interventions on macOS.**
>
> The `tc`/`netem` mechanism requires the Linux kernel (`>=4.9`) with `CAP_NET_ADMIN` and the `sch_netem` kernel module. These are not available on macOS (Darwin), regardless of Docker Desktop's presence, because Docker Desktop on macOS runs containers inside a lightweight Linux VM that does **not** grant `NET_ADMIN` to guest containers by default.
>
> All intervention results obtained on macOS are **dry-run only** and are explicitly marked `"status": "PARTIAL"` in `PHASE_3_MANIFEST.json` (component `3G_3H_intervention`).
>
> **Do not claim cross-platform support for live network intervention.** A Linux host with `CAP_NET_ADMIN` is the blocking requirement for full Tier 2 reproduction.

---

## 7. Verification Checklist

### Tier 1 (any OS)

- [ ] Python 3.11 is installed and on `PATH` (`python3.11 --version`)
- [ ] Virtual environment created and activated
- [ ] `pip install -r requirements.txt` completed without errors
- [ ] `PYTHONHASHSEED=0` and `PYTHONPATH=$(pwd)` exported
- [ ] **453 tests pass** (`make test` or `make reproduce-phase3`)
- [ ] Gate 3A passes: 119/119 (`make test-gate3a`)
- [ ] Coverage HTML generated at `artifacts/coverage/index.html`
- [ ] No forbidden causal-claim phrases (`make lint`)

### Tier 2 (Linux only)

- [ ] Linux kernel `>=4.9` (`uname -r`)
- [ ] `sch_netem` module present (`modinfo sch_netem`)
- [ ] `tc` available and reporting version (`tc -Version`)
- [ ] Docker `>=24.0` installed (`docker --version`)
- [ ] Docker Compose v2 plugin installed (`docker compose version`)
- [ ] `CAP_NET_ADMIN` available to the `rift-eval` container
- [ ] `≥8 GB` RAM and `≥10 GB` free disk verified
- [ ] Build args (`BUILD_DATE`, `GIT_SHA`, `HOST_KERNEL`, `HOST_OS`) exported
- [ ] `docker compose -f docker/docker-compose.yml build` succeeds
- [ ] All Online Boutique images pulled successfully
- [ ] `boutique-frontend` accessible at `http://localhost:8080`
- [ ] Prometheus accessible at `http://localhost:9090`
- [ ] Jaeger accessible at `http://localhost:16686`
- [ ] Network intervention tests pass (`make test-intervention` inside container)
- [ ] E2E pipeline run produces `RIFTRunRecord` JSON artifact

---

## Reference

| File | Purpose |
|---|---|
| [`docs/ENVIRONMENT.md`](../ENVIRONMENT.md) | Full environment spec (authoritative for Python, Docker, system packages) |
| [`Makefile`](../../Makefile) | All build, test, and reproduction targets |
| [`docker/Dockerfile`](../../docker/Dockerfile) | Reproducible evaluation image (python:3.11-slim + iproute2 + iptables) |
| [`docker/docker-compose.yml`](../../docker/docker-compose.yml) | Full testbed (Online Boutique + Prometheus + Jaeger + rift-eval) |
| [`requirements.txt`](../../requirements.txt) | Pinned Python dependencies |
| [`pyproject.toml`](../../pyproject.toml) | Package metadata (`rift 0.1.0-phase3`, `requires-python = ">=3.10"`) |
| [`artifacts/phase3/PHASE_3_MANIFEST.json`](../../artifacts/phase3/PHASE_3_MANIFEST.json) | Phase 3 gate results: 453 tests, component statuses |
