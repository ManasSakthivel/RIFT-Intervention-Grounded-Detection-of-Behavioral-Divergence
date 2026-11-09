# RIFT: Linux VM Requirements, Execution & Cleanup Specification

**Lead Investigator:** Agent L (Linux/VM Dependency and Deployment Readiness Owner)  
**Date:** 2026-11-02  
**Authority:** VM Deployment, Live Testbed Execution, and Safe Cleanup Mandate  

---

## 1. Remote Linux VM Credentials & Access Specification

- **Target Host:** `9.30.57.225` (Internal Intranet Host)
- **Port:** `22`
- **User:** `root`
- **Authentication Method:** Password (`@!DanielJulia20031998`)
- **Connection Command:**
  ```bash
  sshpass -p '@!DanielJulia20031998' ssh -o StrictHostKeyChecking=no root@9.30.57.225
  ```

---

## 2. Why macOS Darwin is Insufficient for Live Telemetry & Interventions

1. **Linux Traffic Control (`tc netem`):**  
   Linux network impairment modules (`sch_netem`, `cls_u32`, `sch_prio`) operate in the Linux kernel network stack. macOS uses `pfctl` / `dummynet` with different queuing semantics and no container namespace traffic filtering.
2. **Container `CAP_NET_ADMIN` Capability:**  
   Simulating per-destination container latency and packet loss requires Docker on Linux with direct access to container network namespaces (`veth` pairs).
3. **Prometheus Scraping of Online Boutique:**  
   Scraping live gRPC metrics (`grpc_server_handling_seconds_bucket`) requires running the 11 microservice containers on a Docker bridge network.

---

## 3. Automated VM Deployment and Execution Procedure

When the remote Linux host is reachable via VPN/Intranet routing:

### Step 1: Provisioning & Code Sync
```bash
# Clone or rsync repository to /root/rift-experiment
sshpass -p '@!DanielJulia20031998' ssh -o StrictHostKeyChecking=no root@9.30.57.225 << 'EOF'
  mkdir -p /root/rift-experiment
  cd /root/rift-experiment
  git clone https://github.com/ManasSakthivel/RIFT-Intervention-Grounded-Detection-of-Behavioral-Divergence.git .
  git checkout remediation/reproducible-evaluation
  pip3 install -r requirements.txt
EOF
```

### Step 2: Start Testbed and Run Live Experiments
```bash
sshpass -p '@!DanielJulia20031998' ssh -o StrictHostKeyChecking=no root@9.30.57.225 << 'EOF'
  cd /root/rift-experiment
  ./scripts/start_testbed.sh
  ./scripts/health_check_testbed.sh
  python3 -m rift.experiments.run --experiment EXP-001 --live
EOF
```

---

## 4. Idempotent VM Cleanup Procedure (Only What We Created)

To safely return the VM to its exact initial state without disturbing other system services:

```bash
sshpass -p '@!DanielJulia20031998' ssh -o StrictHostKeyChecking=no root@9.30.57.225 << 'EOF'
  echo "=== Cleaning up RIFT Testbed Containers and Network Queues ==="
  # 1. Stop and remove only Online Boutique and Prometheus containers created by start_testbed.sh
  docker stop frontend cartservice productcatalogservice currencyservice paymentservice \
              shippingservice emailservice checkoutservice recommendationservice \
              adservice redis-cart prometheus jaeger 2>/dev/null || true
  docker rm frontend cartservice productcatalogservice currencyservice paymentservice \
            shippingservice emailservice checkoutservice recommendationservice \
            adservice redis-cart prometheus jaeger 2>/dev/null || true

  # 2. Remove Online Boutique docker network if created
  docker network rm boutique-net 2>/dev/null || true

  # 3. Clean up any residual tc qdisc rules on interfaces
  tc qdisc del dev eth0 root 2>/dev/null || true
  tc qdisc del dev docker0 root 2>/dev/null || true

  # 4. Remove temporary workspace directory
  rm -rf /root/rift-experiment

  echo "=== Cleanup Complete: VM returned to clean state ==="
EOF
```
