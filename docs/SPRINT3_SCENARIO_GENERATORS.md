# RIFT Sprint 3 — Scenario Generators & Mathematics

**Lead Author:** Benchmark Architecture Lead  
**Date:** 2026-11-02  
**Implementation Source:** `src/rift/benchmark/adversarial_generator.py`  

---

## 1. Mathematical Data-Generating Equations

### Family A: Inverted Onset
$$\text{Value}_{\text{victim}}(t) = 45.0 + \mathcal{N}(0, 5) \quad \text{for } t \ge t_{\text{inject}}$$
$$\text{Value}_{\text{root}}(t) = \begin{cases}
\mathcal{N}(0, 10) & \text{for } t_{\text{inject}} \le t < t_{\text{inject}} + T_{\text{buffer}} \\
55.0 + \mathcal{N}(0, 5) & \text{for } t \ge t_{\text{inject}} + T_{\text{buffer}}
\end{cases}$$

### Family B: Client Retry Amplification
$$\text{Value}_{\text{root}}(t) = 35.0 + \mathcal{N}(0, 4) \quad (z \approx 3.5)$$
$$\text{Value}_{\text{child}}(t) = 80.0 + \mathcal{N}(0, 8) \quad (z \approx 8.0)$$

### Family C: Shared Infrastructure Confounding
$$\text{Value}_{\text{svc}}(t) = 50.0 + \mathcal{N}(0, 6) \quad \forall \text{ svc } \in \{s_{\text{root}}, s_{\text{affected}}\} \text{ for } t \ge t_{\text{inject}}$$

### Family E: Noisy Telemetry with Random Dropouts
$$\text{Value}_{\text{all}}(t) \sim \mathcal{N}(\mu, 15.0), \quad \text{Pr}(\text{drop}) = 0.15$$
