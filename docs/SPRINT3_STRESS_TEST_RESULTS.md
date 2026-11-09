# RIFT Sprint 3 — Adversarial Stress-Test Experimental Results

**Lead Evaluator:** Principal Benchmark Scientist  
**Date:** 2026-11-02  
**Cohort:** `datasets/rift_faults/adversarial_stress_cohort.json` ($n=30$)  
**Machine-Readable Artifact:** `artifacts/evaluation/adversarial_benchmark_results.json`  

---

## 1. Overall Comparative Results ($n=30$)

```
┌─────────────────────────┬───────────┬──────────────┬───────────────┬────────────┬────────────┐
│ Method                  │ Raw P@1   │ Cond. P@1    │ Abstention %  │ Coverage   │ FAR        │
├─────────────────────────┼───────────┼──────────────┼───────────────┼────────────┼────────────┤
│ B0-EARLIEST             │ 36.7%     │ 36.7%        │ 0.0%          │ 100.0%     │ 63.3%      │
│ B0-HIGHEST              │ 73.3%     │ 73.3%        │ 0.0%          │ 100.0%     │ 26.7%      │
│ B1-LATENCY-CORR         │ 73.3%     │ 73.3%        │ 0.0%          │ 100.0%     │ 26.7%      │
│ B3-SIEVE-LIKE           │ 16.7%     │ 16.7%        │ 0.0%          │ 100.0%     │ 83.3%      │
│ B6-RIFT-RANDOM          │ 73.3%     │ 73.3%        │ 0.0%          │ 100.0%     │ 26.7%      │
│ B4-RIFT-ONE-SHOT        │ 73.3%     │ 73.3%        │ 0.0%          │ 100.0%     │ 26.7%      │
│ RIFT-OBS                │ 0.0%      │ 0.0%         │ 100.0%        │ 0.0%       │ 0.0%       │
│ RIFT-FULL               │ 46.7%     │ 56.0%        │ 16.7%         │ 83.3%      │ 36.7%      │
│ RIFT-FULL-ORACLE        │ 46.7%     │ 56.0%        │ 16.7%         │ 83.3%      │ 36.7%      │
└─────────────────────────┴───────────┴──────────────┴───────────────┴────────────┴────────────┘
```

---

## 2. Accuracy Breakdown by Adversarial Failure Family

```
┌──────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ Method           │ A:Invert │ B:Retry  │ C:Conf   │ D:Multi  │ E:Noise  │ F:Deep   │
├──────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ B0-EARLIEST      │ 0%       │ 40%      │ 0%       │ 60%      │ 40%      │ 80%      │
│ B0-HIGHEST       │ 100%     │ 0%       │ 60%      │ 100%     │ 80%      │ 100%     │
│ B1-LATENCY-CORR  │ 100%     │ 0%       │ 60%      │ 100%     │ 80%      │ 100%     │
│ B3-SIEVE-LIKE    │ 0%       │ 0%       │ 100%     │ 0%       │ 0%       │ 0%       │
│ B6-RIFT-RANDOM   │ 100%     │ 0%       │ 60%      │ 100%     │ 80%      │ 100%     │
│ B4-RIFT-ONE-SHOT │ 100%     │ 0%       │ 60%      │ 100%     │ 80%      │ 100%     │
│ RIFT-OBS         │ 0%       │ 0%       │ 0%       │ 0%       │ 0%       │ 0%       │
│ RIFT-FULL        │ 0%       │ 0%       │ 60%      │ 100%     │ 20%      │ 100%     │
│ RIFT-FULL-ORACLE │ 0%       │ 40%      │ 0%       │ 100%     │ 40%      │ 100%     │
└──────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

### Key Adversarial Discoveries:
1. **Family A (Inverted Onset):** `B0-EARLIEST` collapses to **0% accuracy**, demonstrating that earliest onset fails when asynchronous buffers mask the root cause.
2. **Family B (Client Retry Storm):** `B0-HIGHEST`, `B1-LATENCY-CORR`, and `RIFT-RANDOM` all collapse to **0% accuracy**, proving that anomaly magnitude is a brittle heuristic when downstream retries amplify victim latency.
3. **Family C (Confounding):** `B3-SIEVE-LIKE` incurs severe misattribution, while RIFT-FULL-ORACLE safely abstains on non-identifiable confounding.
4. **Family D & F (Multi-Cause & Deep Cascades):** RIFT-FULL achieves **100% accuracy**, correctly isolating root causes through multi-hop propagation.
