# RIFT Gate 3.5B — Online Boutique Testbed Validation

**Status:** `PENDING_DEPLOYMENT`  
**Source of truth:** [`docker/docker-compose.yml`](../../docker/docker-compose.yml)  
**Scrape config:** [`docker/prometheus.yml`](../../docker/prometheus.yml)  

---

## 1. Online Boutique Version

| Field | Value |
|---|---|
| Application | Google microservices-demo (Online Boutique) |
| Version | **v0.9.0** |
| Image registry | `gcr.io/google-samples/microservices-demo` |
| Compose file version | `3.9` |

---

## 2. Container Image Versions

All Online Boutique service images use the exact tag `v0.9.0`. Observability and infrastructure images are pinned to specific versions.

| Container Name | Image | Version |
|---|---|---|
| `boutique-frontend` | `gcr.io/google-samples/microservices-demo/frontend` | `v0.9.0` |
| `boutique-cart` | `gcr.io/google-samples/microservices-demo/cartservice` | `v0.9.0` |
| `boutique-product` | `gcr.io/google-samples/microservices-demo/productcatalogservice` | `v0.9.0` |
| `boutique-checkout` | `gcr.io/google-samples/microservices-demo/checkoutservice` | `v0.9.0` |
| `boutique-recommend` | `gcr.io/google-samples/microservices-demo/recommendationservice` | `v0.9.0` |
| `boutique-payment` | `gcr.io/google-samples/microservices-demo/paymentservice` | `v0.9.0` |
| `boutique-email` | `gcr.io/google-samples/microservices-demo/emailservice` | `v0.9.0` |
| `boutique-shipping` | `gcr.io/google-samples/microservices-demo/shippingservice` | `v0.9.0` |
| `boutique-currency` | `gcr.io/google-samples/microservices-demo/currencyservice` | `v0.9.0` |
| `boutique-ad` | `gcr.io/google-samples/microservices-demo/adservice` | `v0.9.0` |
| `boutique-loadgen` | `gcr.io/google-samples/microservices-demo/loadgenerator` | `v0.9.0` |
| `boutique-redis` | `redis` | `7.2-alpine` |
| `prometheus` | `prom/prometheus` | `v2.52.0` |
| `jaeger` | `jaegertracing/all-in-one` | `1.57` |
| `rift-eval` | `rift-eval` | `latest` (local build) |

> **Note on `x-boutique-defaults` template:** The YAML anchor `x-boutique-defaults` in
> `docker-compose.yml` declares `image: gcr.io/google-samples/microservices-demo/` — with no
> service suffix and no tag. This is an incomplete placeholder used only for shared environment
> variable defaults (`DISABLE_TRACING`, `DISABLE_PROFILER`, etc.). Every boutique service
> **overrides** this with a fully-qualified tagged image. The placeholder is never used as a
> deployable image reference.

---

## 3. Deployment Configuration

### Network

```
Network name : rift-eval-network
Driver       : bridge
Subnet       : 172.30.0.0/16
Isolation    : No egress to production; no real user traffic; no persistent data
```

### Named Volumes

| Volume | Purpose |
|---|---|
| `rift-artifacts` | RIFT evaluation output artifacts |
| `prometheus-data` | Prometheus TSDB (retention: 1 hour) |
| `jaeger-data` | Jaeger trace staging (`/tmp`, in-memory) |

### Service Ports (Host Exposure)

Only three services expose ports to the host:

| Service | Host Port → Container Port | Purpose |
|---|---|---|
| `boutique-frontend` | `8080` → `8080` | HTTP user interface |
| `prometheus` | `9090` → `9090` | Prometheus UI and API |
| `jaeger` | `16686` → `16686` | Jaeger UI |
| `jaeger` | `14268` → `14268` | Jaeger HTTP Thrift collector (trace ingestion) |

All other services communicate only on the internal `rift-eval-network`.

---

## 4. Network Topology Diagram

```
  HOST MACHINE
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │  :8080       :9090       :16686/:14268                                           │
  │   │             │              │                                                 │
  │   ▼             ▼              ▼                                                 │
  │  rift-eval-network  (172.30.0.0/16, bridge, isolated)                           │
  │  ┌──────────────────────────────────────────────────────────────────────────┐   │
  │  │                                                                          │   │
  │  │  [boutique-loadgen]──────────────────────────────────────────────►       │   │
  │  │   USERS=10, Locust                          HTTP :8080                   │   │
  │  │                                                ▼                         │   │
  │  │                                    [boutique-frontend :8080]             │   │
  │  │                                   /   |    |    |    |   \               │   │
  │  │                        gRPC:3550 /    |    |    |    |    \ gRPC:9555   │   │
  │  │                                ▼     |    |    |    |     ▼             │   │
  │  │                      [product]  |    |    |    |    |   [ad]            │   │
  │  │                                 |    |    |    |                        │   │
  │  │                      gRPC:7000  ▼    |    |    ▼  gRPC:50051           │   │
  │  │                      [currency] |    |    | [shipping]                  │   │
  │  │                                 |    |    |                             │   │
  │  │                      gRPC:7070  ▼    |    ▼  gRPC:5050                 │   │
  │  │                      [cart]◄────┘    |  [checkout]                     │   │
  │  │                        │             |   /  |  \  \                     │   │
  │  │                        │             |  /   |   \  \──────gRPC:7000     │   │
  │  │                   Redis:6379         ▼ /    |    ▼         ▼            │   │
  │  │                        │          [recommend→product] [payment:50051]  │   │
  │  │                        ▼          [8080]    |  [email:8080]             │   │
  │  │                    [redis:6379]             |                           │   │
  │  │                                             ▼                           │   │
  │  │                                   [checkout also calls:]                │   │
  │  │                                     product, shipping, payment,         │   │
  │  │                                     email, currency, cart               │   │
  │  │                                                                          │   │
  │  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
  │  │  │  OBSERVABILITY                                                   │   │   │
  │  │  │                                                                  │   │   │
  │  │  │  [prometheus :9090] ──scrape──► all services (see §7 caveats)   │   │   │
  │  │  │                                                                  │   │   │
  │  │  │  [jaeger :16686/:14268] ◄──traces── all boutique services        │   │   │
  │  │  │                          JAEGER_SERVICE_ADDR=jaeger:14268        │   │   │
  │  │  └─────────────────────────────────────────────────────────────────┘   │   │
  │  └──────────────────────────────────────────────────────────────────────────┘   │
  └──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Service Dependency Graph

### Call graph (runtime)

```
boutique-loadgen
  └─► boutique-frontend
        ├─► boutique-product      (gRPC :3550)
        ├─► boutique-currency     (gRPC :7000)
        ├─► boutique-cart         (gRPC :7070)
        │     └─► boutique-redis  (Redis :6379)
        ├─► boutique-recommend    (gRPC :8080)
        │     └─► boutique-product
        ├─► boutique-shipping     (gRPC :50051)
        ├─► boutique-checkout     (gRPC :5050)
        │     ├─► boutique-product
        │     ├─► boutique-shipping
        │     ├─► boutique-payment (gRPC :50051)
        │     ├─► boutique-email   (gRPC :8080)
        │     ├─► boutique-currency
        │     └─► boutique-cart
        └─► boutique-ad           (gRPC :9555)
```

### Observability graph

```
prometheus  ──scrape──►  boutique-frontend :8080
            ──scrape──►  boutique-cart     :7070   [WILL FAIL — KI-003]
            ──scrape──►  boutique-product  :3550   [WILL FAIL — KI-003]
            ──scrape──►  boutique-checkout :5050   [WILL FAIL — KI-003]
            ──scrape──►  boutique-recommend:8080   [WILL FAIL — KI-003]
            ──scrape──►  boutique-payment  :50051  [WILL FAIL — KI-003]
            ──scrape──►  boutique-shipping :50051  [WILL FAIL — KI-003]
            ──scrape──►  boutique-currency :7000   [WILL FAIL — KI-003]
            ──scrape──►  boutique-ad       :9555   [WILL FAIL — KI-003]
            ──scrape──►  localhost:9090             [WILL SUCCEED — self]

all boutique services  ──traces──►  jaeger:14268
```

---

## 6. Service Internal Ports

| Service | Internal Port | Protocol | Notes |
|---|---|---|---|
| `boutique-frontend` | 8080 | HTTP | Also host-exposed |
| `boutique-cart` | 7070 | gRPC | |
| `boutique-product` | 3550 | gRPC | |
| `boutique-checkout` | 5050 | gRPC | |
| `boutique-recommend` | 8080 | gRPC | Same port as frontend, different container |
| `boutique-payment` | 50051 | gRPC | |
| `boutique-email` | 8080 | gRPC | |
| `boutique-shipping` | 50051 | gRPC | Same port as payment, different container |
| `boutique-currency` | 7000 | gRPC | |
| `boutique-ad` | 9555 | gRPC | |
| `boutique-redis` | 6379 | Redis | |

---

## 7. Telemetry Sources

### 7.1 Prometheus (`prom/prometheus:v2.52.0`)

- **Scrape interval:** 15 seconds  
- **Evaluation interval:** 15 seconds  
- **Retention:** 1 hour  
- **Config file:** `docker/prometheus.yml` (mounted read-only)  
- **TSDB path:** `/prometheus` (named volume `prometheus-data`)

**⚠️ Known Issue KI-003 — Prometheus scrape targets for boutique services will fail.**  
Online Boutique v0.9.0 services expose gRPC ports, not HTTP Prometheus `/metrics` endpoints.
Prometheus is configured to scrape these ports (as documented in `prometheus.yml`), but all
boutique service targets will show `DOWN` because gRPC traffic on those ports does not serve
Prometheus text format. The only target expected to be `UP` is the Prometheus self-scrape
(`localhost:9090`).

**Implication for RIFT experiments:** RIFT telemetry analysis for Gate 3 experiments must be
sourced from Jaeger distributed traces and HTTP-level response data, not from Prometheus pull
metrics of individual boutique services.

### 7.2 Jaeger (`jaegertracing/all-in-one:1.57`)

- **Storage:** In-memory (`SPAN_STORAGE_TYPE=memory`)  
- **Max traces:** 50,000  
- **Trace collection port:** `14268` (HTTP Thrift)  
- **UI port:** `16686`  
- All boutique services are configured with `JAEGER_SERVICE_ADDR=jaeger:14268` via the
  `x-boutique-defaults` anchor. With `DISABLE_TRACING=0`, services will emit spans on each
  request.

**Jaeger is the primary telemetry source for RIFT behavioral analysis.**

---

## 8. Workload Configuration

| Parameter | Value |
|---|---|
| Load generator | Locust (inside `loadgenerator:v0.9.0`) |
| Target | `boutique-frontend:8080` (`FRONTEND_ADDR`) |
| Simulated users | **10** (`USERS=10`) |
| Traffic type | Synthetic (no real user data) |

**⚠️ Known Issue KI-002 — Loadgen startup timing.**  
`boutique-loadgen` declares `depends_on: boutique-frontend` but uses no health condition.
Docker Compose starts `boutique-loadgen` as soon as `boutique-frontend`'s container is
created, not when it is ready to accept connections. This causes Locust connection errors in
approximately the first 30 seconds. These transient errors do not constitute a gate failure,
but experiment baselines should be collected after the 30-second startup window has elapsed.

---

## 9. Health Check Procedure

The full health check procedure is documented in
[`artifacts/phase3_5/testbed_health/health_check_procedure.json`](../../artifacts/phase3_5/testbed_health/health_check_procedure.json).

### Summary (8 phases)

| Phase | Name | What it checks |
|---|---|---|
| 1 | Pull images | All images pull without error |
| 2 | Build rift-eval | Local image builds successfully |
| 3 | Start containers | All 14 containers reach `Up` state |
| 4 | Port connectivity | `localhost:8080`, `localhost:9090`, `localhost:16686` respond |
| 5 | Prometheus targets | Prometheus API is reachable; self-scrape is `UP` |
| 6 | Jaeger ingestion | At least one service appears in `/api/services` after 60s |
| 7 | Loadgen activity | `docker logs boutique-loadgen` shows Locust request lines |
| 8 | Error rate | No sustained errors in frontend logs after 30s startup window |

### Estimated total time: ~10 minutes (fast network, warm cache)

---

## 10. What "PASS" Means for Gate 3.5B

Gate 3.5B PASSES when **all** of the following are true on a Linux host:

1. ✅ All 14 containers are in `Up` state (`docker compose ps` shows no `Exit` or `Restarting`)
2. ✅ `curl http://localhost:8080/` returns HTTP 200
3. ✅ `curl http://localhost:9090/-/healthy` returns Prometheus OK
4. ✅ `curl http://localhost:16686/api/services` returns a non-empty service list (after 60s)
5. ✅ `docker logs boutique-loadgen` shows active Locust HTTP request lines
6. ✅ No sustained errors in `boutique-frontend` logs after the 30s startup window
7. ✅ RIFT harness (`rift-eval`) can reach Prometheus and Jaeger by their internal hostnames

The following are **acceptable** and do not block PASS:

- Prometheus showing boutique service scrape targets as `DOWN` (KI-003 — expected)
- Transient Locust connection errors in the first 30s (KI-002 — expected)

---

## 11. Current Status: PENDING_DEPLOYMENT

**This testbed has not been deployed.** The configuration has been documented from source files
(`docker/docker-compose.yml`, `docker/prometheus.yml`) but no containers have been started.

**Blocking reason:** The current development host is macOS. While Docker Desktop for macOS
can run Linux containers, the RIFT evaluation harness requires `NET_ADMIN` capability and
`tc netem` for network intervention experiments. These are unreliable or unavailable in
macOS Docker Desktop's Linux VM. Full deployment requires a native Linux host.

Health check results are documented in
[`artifacts/phase3_5/testbed_health/health_check_results.json`](../../artifacts/phase3_5/testbed_health/health_check_results.json)
with `status: "PENDING_DEPLOYMENT"` and all phases marked `NOT_RUN`.

---

## 12. How to Achieve PASS on Linux

Run the following from the repository root on a Linux host with Docker Engine installed:

```bash
# Step 1: Pull all images (~5–10 min first time)
docker compose -f docker/docker-compose.yml pull --ignore-buildable

# Step 2: Build RIFT evaluation harness
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
GIT_SHA=$(git rev-parse --short HEAD) \
HOST_OS=$(uname -s) \
HOST_KERNEL=$(uname -r) \
docker compose -f docker/docker-compose.yml build rift-eval

# Step 3: Start the full stack
docker compose -f docker/docker-compose.yml up -d

# Step 4: Wait for startup (~30s), then verify container states
sleep 30 && docker compose -f docker/docker-compose.yml ps

# Step 5: Verify frontend
curl -sf http://localhost:8080/ -o /dev/null && echo "frontend:OK"

# Step 6: Verify Prometheus
curl -sf http://localhost:9090/-/healthy && echo "prometheus:OK"

# Step 7: Wait for loadgen traffic, then verify Jaeger traces
sleep 60 && curl -sf 'http://localhost:16686/api/services'

# Step 8: Check loadgen is active
docker logs boutique-loadgen --tail 20

# Step 9: Check for sustained errors (should be 0)
docker logs boutique-frontend --since 1m 2>&1 | grep -i 'error\|panic\|fatal' | wc -l
```

Once all checks pass, update
[`artifacts/phase3_5/testbed_health/health_check_results.json`](../../artifacts/phase3_5/testbed_health/health_check_results.json)
with `status: "PASS"` and record actual outputs for each phase.

---

## 13. Known Issues Summary

| ID | Component | Severity | Description |
|---|---|---|---|
| KI-001 | `x-boutique-defaults` | Informational | Image placeholder has no tag/suffix — intentional template anchor, never deployed directly |
| KI-002 | `boutique-loadgen` | Timing | `depends_on` uses no health condition; causes ~30s of transient startup errors |
| KI-003 | Prometheus scrapes | Observability gap | Boutique gRPC ports do not expose `/metrics`; all service targets will show `DOWN` |

---

*Document generated for RIFT research project, Gate 3.5B. Status: PENDING_DEPLOYMENT.*
