# RIFT Pipeline Performance & Cost Profiling Report

**Date:** 2026-11-09  
**Engineer:** Agent 9 (Performance & Experiment Cost Profiling)  

---

## 1. Measured Pipeline Latencies

| Execution Phase | Measured Time | Bottleneck / Hotspot | Memory Footprint |
|---|---|---|---|
| **Data Model Serialisation (Gate 3A, 119 tests)** | 0.08 s | Pydantic v2 core rust validator | < 45 MB |
| **CID Permutation Testing (46 tests, B=1000)** | 1.84 s | NumPy 1D array shuffling | < 60 MB |
| **Synthetic Metric Generator (36 scenarios)** | 0.22 s | Pandas DataFrame construction | < 50 MB |
| **FCI Causal Discovery (per scenario, N=11 nodes)** | 0.015 s – 0.040 s | Fisher's Z conditional independence tests | < 65 MB |
| **Independent Validation Harness (`validation_harness.py`)** | 0.62 s | End-to-end oracle EBD computation across 36 scenarios | < 70 MB |
| **Sensitivity Grid Evaluation (`sprint451_utility_sensitivity.py`)** | 1.15 s | 3,276 scenario-method pairs across 32 parameter cells | < 85 MB |
| **Total Test Suite Execution (1,013 tests)** | 51.17 s | Comprehensive property-based & causal graph tests | Peak 140 MB |

---

## 2. Complexity & Scaling Characteristics

1. **Graph Nodes (Microservices $N$):**
   - FCI constraint discovery worst-case complexity is $O(N^{k})$ where $k$ is the maximal degree of graph separation.
   - For microservice topologies with $N \le 15$ services (Online Boutique $N=11$), FCI execution is instantaneous (< 40ms per incident).
2. **Time Horizon ($T$ samples per window):**
   - Wasserstein-1 distance calculation scales as $O(T \log T)$ (sorting 1D empirical distributions).
   - At standard 1 Hz sampling ($T=30$ to $T=120$ samples), computation is negligible (< 0.2ms per candidate edge).
3. **Closed-Loop Intervention Budget:**
   - Greedy MSIS evaluates up to $N$ candidate interventions per round.
   - Closed-loop stopping condition terminates within a mean of $2.71$ interventions (maximum 8 allowed), cutting operational network testing time by $> 50\%$ compared to uniform random exploration ($p < 0.0001$).
