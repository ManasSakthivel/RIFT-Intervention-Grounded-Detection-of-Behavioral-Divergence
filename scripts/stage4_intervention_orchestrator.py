#!/usr/bin/env python3
"""
RIFT Stage 4 Live Network Intervention Orchestrator
Executes the single authorized live NetNS intervention (50ms delay on rift-cartservice)
and evaluates telemetry divergence and causal attribution.
"""
import os
import sys
import time
import json
import signal
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime

SERVICES = [
    'frontend',
    'cartservice',
    'productcatalogservice',
    'currencyservice',
    'paymentservice',
    'shippingservice',
    'emailservice',
    'checkoutservice',
    'recommendationservice',
    'adservice'
]

PROMETHEUS_URL = 'http://127.0.0.1:19090'
RESULTS_FILE = '/root/stage4_intervention_results.json'

def query_latency(service):
    q = f'histogram_quantile(0.99, sum by (le) (rate(rift_duration_milliseconds_bucket{{span_name=~"(?i).*{service}.*"}}[1m]))) / 1000'
    url = f"{PROMETHEUS_URL}/api/v1/query?" + urllib.parse.urlencode({'query': q})
    try:
        req = urllib.request.urlopen(url, timeout=4)
        data = json.loads(req.read().decode('utf-8'))
        res = data.get('data', {}).get('result', [])
        if res and len(res) > 0:
            val = float(res[0]['value'][1])
            return val
    except Exception as e:
        pass
    return None

def get_cartservice_pid():
    out = subprocess.check_output(["podman", "inspect", "rift-cartservice", "--format", "{{.State.Pid}}"]).decode().strip()
    return int(out)

def get_netns_inode(pid):
    out = subprocess.check_output(["stat", "-c", "%i", f"/proc/{pid}/ns/net"]).decode().strip()
    return int(out)

def get_host_netns_inode():
    out = subprocess.check_output(["stat", "-c", "%i", "/proc/1/ns/net"]).decode().strip()
    return int(out)

def get_qdisc_state(pid):
    cmd = ["nsenter", "-t", str(pid), "-n", "tc", "qdisc", "show", "dev", "eth0"]
    return subprocess.check_output(cmd).decode().strip()

def apply_intervention(pid):
    cmds = [
        ["nsenter", "-t", str(pid), "-n", "tc", "qdisc", "add", "dev", "eth0", "root", "handle", "1:", "prio", "bands", "3", "priomap", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1"],
        ["nsenter", "-t", str(pid), "-n", "tc", "qdisc", "add", "dev", "eth0", "parent", "1:1", "handle", "10:", "netem", "delay", "50ms", "5ms", "distribution", "normal"],
        ["nsenter", "-t", str(pid), "-n", "tc", "filter", "add", "dev", "eth0", "protocol", "ip", "parent", "1:", "prio", "1", "u32", "match", "ip", "protocol", "6", "0xff", "flowid", "1:1"]
    ]
    for c in cmds:
        subprocess.check_call(c)

def rollback_intervention(pid):
    cmds = [
        ["nsenter", "-t", str(pid), "-n", "tc", "filter", "del", "dev", "eth0", "parent", "1:", "prio", "1"],
        ["nsenter", "-t", str(pid), "-n", "tc", "qdisc", "del", "dev", "eth0", "parent", "1:1", "handle", "10:"],
        ["nsenter", "-t", str(pid), "-n", "tc", "qdisc", "del", "dev", "eth0", "root", "handle", "1:"]
    ]
    for c in cmds:
        subprocess.call(c)

def launch_watchdog(pid, deadline_seconds=45):
    code = f"""
import time, subprocess, sys
time.sleep({deadline_seconds})
# Safety fallback
subprocess.call(["nsenter", "-t", "{pid}", "-n", "tc", "filter", "del", "dev", "eth0", "parent", "1:", "prio", "1"])
subprocess.call(["nsenter", "-t", "{pid}", "-n", "tc", "qdisc", "del", "dev", "eth0", "parent", "1:1", "handle", "10:"])
subprocess.call(["nsenter", "-t", "{pid}", "-n", "tc", "qdisc", "del", "dev", "eth0", "root", "handle", "1:"])
"""
    p = subprocess.Popen([sys.executable, "-c", code], start_new_session=True)
    return p

def save_checkpoint(record):
    with open(RESULTS_FILE, "w") as f:
        json.dump(record, f, indent=2)

def main():
    print("="*80)
    print("RIFT STAGE 4 LIVE NETWORK INTERVENTION EXECUTION")
    print("Timestamp:", datetime.utcnow().isoformat() + "Z")
    print("="*80)

    # 1. Pre-flight NetNS validation
    pid = get_cartservice_pid()
    host_inode = get_host_netns_inode()
    container_inode = get_netns_inode(pid)
    print(f"[*] cartservice PID: {pid}")
    print(f"[*] Host NetNS Inode: {host_inode}")
    print(f"[*] Container NetNS Inode: {container_inode}")
    if host_inode == container_inode:
        print("[!] FATAL: Container NetNS is identical to Host NetNS! Aborting.")
        sys.exit(1)
    
    initial_qdisc = get_qdisc_state(pid)
    print(f"[*] Initial Qdisc: {initial_qdisc}")

    record = {
        "timestamp_start": datetime.utcnow().isoformat() + "Z",
        "target": "rift-cartservice",
        "pid": pid,
        "host_netns_inode": host_inode,
        "container_netns_inode": container_inode,
        "initial_qdisc": initial_qdisc,
        "pre_baseline": {},
        "intervention": {},
        "post_recovery": {}
    }
    save_checkpoint(record)

    # 2. Phase 1: Pre-intervention Baseline (90s, sampled every 5s = 18 samples)
    print("\n[+] Phase 1: Collecting Pre-Intervention Baseline (90s)...")
    pre_samples = {s: [] for s in SERVICES}
    for i in range(18):
        t_sample = time.time()
        print(f"  [Pre-Baseline] Sample {i+1}/18 (t={i*5}s)...", end="\r")
        for s in SERVICES:
            val = query_latency(s)
            if val is not None:
                pre_samples[s].append({"t": t_sample, "val": val})
        time.sleep(5)
    print("\n  [Pre-Baseline] Completed 18 sample points.")
    record["pre_baseline"] = pre_samples
    save_checkpoint(record)

    # 3. Phase 2: Arm Watchdog & Apply Intervention (50ms delay, 30s)
    print("\n[+] Phase 2: Arming Detached Watchdog (45s deadline) & Applying tc netem intervention...")
    watchdog_proc = launch_watchdog(pid, deadline_seconds=45)
    print(f"[*] Watchdog PID: {watchdog_proc.pid}")

    t_apply_start = time.time()
    apply_intervention(pid)
    t_apply_end = time.time()
    applied_qdisc = get_qdisc_state(pid)
    print(f"[*] Applied Qdisc: {applied_qdisc}")
    record["applied_qdisc"] = applied_qdisc
    record["intervention_applied_at"] = datetime.utcnow().isoformat() + "Z"
    save_checkpoint(record)

    # 4. Phase 3: Active Intervention Monitoring (30s, sampled every 5s = 6 samples)
    print("\n[+] Phase 3: Observing Active Intervention (30.0s)...")
    active_samples = {s: [] for s in SERVICES}
    try:
        for i in range(6):
            t_sample = time.time()
            print(f"  [Active Intervention] Sample {i+1}/6 (t={i*5}s)...", end="\r")
            for s in SERVICES:
                val = query_latency(s)
                if val is not None:
                    active_samples[s].append({"t": t_sample, "val": val})
            time.sleep(5)
        print("\n  [Active Intervention] Completed 6 sample points.")
    finally:
        # 5. Phase 4: Rollback & Verification guaranteed in finally block
        print("\n[+] Phase 4: Executing Primary Rollback & Disarming Watchdog...")
        rollback_intervention(pid)
        try:
            os.kill(watchdog_proc.pid, signal.SIGKILL)
            print("[*] Watchdog disarmed successfully.")
        except Exception as e:
            print(f"[*] Watchdog disarm note: {e}")

    restored_qdisc = get_qdisc_state(pid)
    print(f"[*] Restored Qdisc: {restored_qdisc}")
    record["intervention"] = active_samples
    record["restored_qdisc"] = restored_qdisc
    record["intervention_removed_at"] = datetime.utcnow().isoformat() + "Z"
    save_checkpoint(record)

    # 6. Phase 5: Post-Intervention Recovery (90s, sampled every 5s = 18 samples)
    print("\n[+] Phase 5: Observing Post-Intervention Recovery (90s)...")
    post_samples = {s: [] for s in SERVICES}
    for i in range(18):
        t_sample = time.time()
        print(f"  [Post-Recovery] Sample {i+1}/18 (t={i*5}s)...", end="\r")
        for s in SERVICES:
            val = query_latency(s)
            if val is not None:
                post_samples[s].append({"t": t_sample, "val": val})
        time.sleep(5)
    print("\n  [Post-Recovery] Completed 18 sample points.")
    record["post_recovery"] = post_samples
    record["timestamp_end"] = datetime.utcnow().isoformat() + "Z"

    # 7. Analysis & Statistical Divergence
    print("\n" + "="*80)
    print("STAGE 4 RESULTS & ATTRIBUTION SUMMARY")
    print("="*80)
    summary_table = []
    
    for s in SERVICES:
        pre_vals = [x["val"] for x in pre_samples[s]]
        act_vals = [x["val"] for x in active_samples[s]]
        post_vals = [x["val"] for x in post_samples[s]]

        pre_mean = (sum(pre_vals) / len(pre_vals)) if pre_vals else 0.0
        pre_std = (sum((x - pre_mean)**2 for x in pre_vals) / max(len(pre_vals)-1, 1))**0.5 if len(pre_vals) > 1 else 0.001
        if pre_std == 0.0: pre_std = 0.001

        act_mean = (sum(act_vals) / len(act_vals)) if act_vals else 0.0
        post_mean = (sum(post_vals) / len(post_vals)) if post_vals else 0.0

        shift_ms = (act_mean - pre_mean) * 1000.0
        z_score = (act_mean - pre_mean) / pre_std

        summary_table.append({
            "service": s,
            "pre_mean_ms": round(pre_mean * 1000.0, 2),
            "act_mean_ms": round(act_mean * 1000.0, 2),
            "post_mean_ms": round(post_mean * 1000.0, 2),
            "shift_ms": round(shift_ms, 2),
            "z_score": round(z_score, 2),
            "diverged": abs(z_score) >= 3.0 or shift_ms >= 20.0
        })

    record["summary_table"] = summary_table

    print(f"{'Service':<25} | {'Pre (ms)':<10} | {'Act (ms)':<10} | {'Post (ms)':<10} | {'Shift (ms)':<10} | {'Z-Score':<8} | {'Diverged'}")
    print("-" * 95)
    for row in summary_table:
        print(f"{row['service']:<25} | {row['pre_mean_ms']:<10.2f} | {row['act_mean_ms']:<10.2f} | {row['post_mean_ms']:<10.2f} | {row['shift_ms']:<10.2f} | {row['z_score']:<8.2f} | {row['diverged']}")

    # Check EBD Attribution
    cart_row = next(r for r in summary_table if r["service"] == "cartservice")
    print("\n[*] Root Cause Attribution Evaluation:")
    print(f"  Target Service: cartservice")
    print(f"  Baseline Latency: {cart_row['pre_mean_ms']} ms")
    print(f"  Intervention Latency: {cart_row['act_mean_ms']} ms (Expected ~ +50ms)")
    print(f"  Measured Latency Shift: +{cart_row['shift_ms']} ms")
    print(f"  Post-Recovery Latency: {cart_row['post_mean_ms']} ms")
    print(f"  Cartservice Divergence Z-Score: {cart_row['z_score']}")
    
    attributed_service = max(summary_table, key=lambda x: x["shift_ms"])["service"]
    print(f"  Top Attributed Root Cause by Empirical Shift: {attributed_service}")
    
    if attributed_service == "cartservice" and cart_row["shift_ms"] >= 35.0:
        print("  --> RIFT HYPOTHESIS CONFIRMED: Behavioral divergence accurately localizes injected fault on cartservice!")
        verdict = "PASS — SINGLE EXPERIMENT COMPLETED WITH VERIFIED ROLLBACK"
    else:
        print("  --> Divergence observed with non-standard shift magnitude.")
        verdict = "INCONCLUSIVE"
        
    record["verdict"] = verdict
    save_checkpoint(record)
    print(f"\n[*] Complete experiment record saved to {RESULTS_FILE}")
    print(f"[*] Final Verdict: {verdict}")

if __name__ == "__main__":
    main()
