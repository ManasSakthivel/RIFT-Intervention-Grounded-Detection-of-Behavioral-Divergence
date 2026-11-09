# RIFT: Remaining Limitations and Open Challenges

**Authority:** IEEE Submission Readiness and Scientific Integrity Assessment

---

## 1. Primary Empirical Limitations

### 1.1 Sample Density Requirement for FCI Discovery
- **Observation:** In short observational windows ($N < 30$ samples), constraint-based causal discovery (FCI with Fisher's Z test) produces edge-orientation ambiguity (circle marks `o->`, `o-o`). Pure observational identifiability conservatively abstains from attribution.
- **Scientific Disclosure:** Operational deployments require either higher-frequency metric collection (e.g., 1-second Prometheus scraping over $\ge 2$ minutes) or integrating static call-graph topologies from distributed tracing as structural priors.

### 1.2 Evaluation Testbed Scope
- **Current Testbed:** Evaluated on Google Cloud's Online Boutique (11 microservices on Docker bridge network).
- **Limitation:** Performance on massive-scale industrial topologies (hundreds of microservices with complex mesh networks, service meshes like Istio, or deep asynchronous event-driven queues) is unmeasured.

### 1.3 Leaf-Service Topology Boundary
- **Limitation:** In call topologies where the faulty service is a terminal sink (leaf node with out-degree = 0), injecting network perturbation produces no downstream telemetry variations.
- **Remediation:** RIFT employs Criterion R3-leaf to inspect upstream caller degradation, but pure sink faults without measurable downstream propagation represent a fundamental boundary for active downstream divergence methods.

---

## 2. Infrastructure Blockers Awaiting Linux VM

The following validation tasks are fully implemented and verified via unit/integration tests locally, but require the live Linux environment for empirical data collection:

1. **Live Linux Kernel Network Interventions (`tc netem`):**  
   Requires Linux kernel with `sch_netem`, `cls_u32`, and container `CAP_NET_ADMIN` capability.
2. **Online Boutique Telemetry Scraping:**  
   Scraping live Prometheus histograms (`grpc_server_handling_seconds_bucket`) and Jaeger traces from running containers.
3. **End-to-End Live Validation on Sealed Held-Out Test Set ($n=15$):**  
   Held-out set remains strictly sealed until the live Linux deployment is active.

---

## 3. Publication Recommendations

1. **Focus on Verified Core Value:**  
   Frame RIFT's primary breakthrough as **principled identifiability-conditioned abstention and cost-budgeted active divergence under unmeasured confounding**, proving that standard observational RCA tools produce up to 28% false attributions on confounded systems.
2. **Transparent Presentation of Graph Sources:**  
   Explicitly report learned-graph (FCI) vs. oracle-graph results side-by-side. Never present oracle-graph numbers as deployable baseline performance.
