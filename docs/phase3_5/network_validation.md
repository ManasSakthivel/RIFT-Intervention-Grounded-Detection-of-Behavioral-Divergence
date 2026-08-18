# Phase 3.5 — Network Intervention Validation
**Gate 3.5A | Status: PARTIAL**

---

## Platform Statement

> **macOS cannot execute live tc/netem network interventions.**
> All tc-based intervention tests require Linux kernel ≥ 4.9 with `CAP_NET_ADMIN`.
> On this host (macOS darwin arm64), all tc commands run in dry-run mode only.
> Do not claim cross-platform support for live network intervention.

---

## 1. Required Linux Environment

| Requirement | Value |
|---|---|
| Linux kernel | ≥ 4.9 |
| iproute2 / tc | Any version shipping `sch_netem` |
| Kernel module | `sch_netem` (verify: `modinfo sch_netem`) |
| Capability | `CAP_NET_ADMIN` |
| Docker image | `python:3.11-slim` + `iproute2` + `iptables` (see `docker/Dockerfile`) |
| docker-compose | `cap_add: NET_ADMIN` on `rift-eval` service |

To run with full capabilities on Linux:
```bash
docker compose -f docker/docker-compose.yml run --cap-add NET_ADMIN rift-eval \
  python3 -m pytest tests/integration/intervention/ -v
```

---

## 2. Approved Intervention Mechanism

Frozen in [`docs/PHASE_3_SPEC_FREEZE.md §11`](../PHASE_3_SPEC_FREEZE.md):

```
tc u32 classifier + per-destination netem
```

**NOT global eth0 netem** — only traffic to the target destination IP is affected.

### Apply sequence:
```bash
# Step 1: Root prio qdisc (idempotent)
tc qdisc add dev eth0 root handle 1: prio priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0

# Step 2: netem child for this intervention
tc qdisc add dev eth0 parent 1:10 handle 10: netem \
  delay 100.0ms 5.0ms distribution normal loss 0.00%

# Step 3: u32 filter targeting destination IP only (per-destination)
tc filter add dev eth0 parent 1: protocol ip u32 \
  match ip dst 172.30.0.X/32 flowid 1:10
```

### Rollback sequence:
```bash
tc filter del dev eth0 parent 1: protocol ip u32 \
  match ip dst 172.30.0.X/32 flowid 1:10
tc qdisc del dev eth0 parent 1:10 handle 10:
```

Implementation: [`src/rift/intervention/network_intervention.py`](../../src/rift/intervention/network_intervention.py)

---

## 3. Critical Distinction: Command Success vs do(X) Execution

> **"tc command returned 0" is NOT equivalent to "do(X) was successfully executed."**

A `tc` command returning exit code 0 means the Linux kernel accepted the rule. It does **not** mean:
- The destination IP correctly resolves to the target service
- The netem delay was actually applied to packets
- The requested latency matches the measured effect
- Non-target services were unaffected

The **five intervention-validity checks** must all pass before an intervention is considered a valid `do(X)`:

| Check | What it verifies | Measurement |
|---|---|---|
| 1. Target received intervention | RTT to dest_ip increased by ~requested_latency | `ping -c 10 {dest_ip}` |
| 2. Non-targets unaffected | RTT to non-target IPs unchanged (< 2σ) | `ping -c 10 {non_target_ip}` |
| 3. Metric changed in expected direction | Service latency p99 increased in Prometheus | `PromQL query` |
| 4. Rollback restored state | Post-rollback RTT returns to baseline AND tc shows no remaining rule | `ping` + `tc qdisc show` |
| 5. No unexpected blast radius | `verify_side_effect_isolation()` returns `(True, [])` | RIFT safety check |

---

## 4. The 7 Required Intervention Tests

| Test | Description | Status |
|---|---|---|
| NET-1: Latency | Apply 100ms to frontend→checkout; verify RTT delta | PENDING_LINUX_EXECUTION |
| NET-2: Packet loss | Apply 10% loss to cart→redis_cart | PENDING_LINUX_EXECUTION |
| NET-3: Rollback | Apply then rollback; verify tc rules removed | PENDING_LINUX_EXECUTION |
| NET-4: Wrong target | Install rule for non-existent IP; verify no service affected | PENDING_LINUX_EXECUTION |
| NET-5: Destination isolation | Latency to checkout only; product IP unaffected | PENDING_LINUX_EXECUTION |
| NET-6: Repeated intervention | Apply, rollback, apply again; verify no rule accumulation | PENDING_LINUX_EXECUTION |
| NET-7: Intervention failure | Run without CAP_NET_ADMIN; verify FAILED status, no partial state | PENDING_LINUX_EXECUTION |

All 7 tests pass in dry_run mode. Dry-run validation artifact: [`artifacts/phase3_5/network/intervention_test_results.json`](../../artifacts/phase3_5/network/intervention_test_results.json)

---

## 5. Docker Bridge Network Concern

**P1 Risk (from hostile review):** Online Boutique uses gRPC over HTTP/2 persistent connections. tc u32 operates at the IP packet level and applies to new AND existing TCP connections. However, on Docker bridge networks with NAT, the destination IP seen at the container level is the internal bridge IP, not the host IP. The tc rule must be installed *inside the rift-eval container's network namespace* targeting the *container-internal IP* of the target service.

This must be verified on live Linux deployment:
```bash
# Inside rift-eval container: get boutique-checkout IP
docker inspect boutique-checkout | grep IPAddress
# Then install tc rule targeting that IP
```

---

## 6. Gate Decision

**PARTIAL** — Dry-run validation complete. Linux live execution required for PASS.

Conditions for PASS:
- [ ] All 7 intervention tests pass on Linux host with CAP_NET_ADMIN
- [ ] All 5 validity checks pass with independent measurements
- [ ] Rollback verified via independent RTT measurement (not just tc exit code)
- [ ] Destination isolation confirmed for at least 3 scenarios

Artifacts: [`artifacts/phase3_5/network/`](../../artifacts/phase3_5/network/)
