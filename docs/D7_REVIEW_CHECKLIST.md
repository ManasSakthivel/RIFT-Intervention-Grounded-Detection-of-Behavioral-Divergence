# D7 — Independent Reviewer Evaluation Checklist

This checklist is to be completed by the designated independent scientific reviewer to evaluate the scientific validity of the RIFT pre-registration package, the experimental design, and the proposed confirmatory pipeline.

## Reviewer Information
* **Name:** `[To be completed by reviewer]`
* **Institution:** `[To be completed by reviewer]`
* **Date of Evaluation:** `[To be completed by reviewer]`
* **Package SHA-256 Sums Checked:** `[Yes / No]`

---

## Evaluation Questions

Please provide a brief written assessment and a grade (**Met**, **Partially Met**, **Not Met**) for each of the following twelve items:

### 1. Research Question Meaningfulness
*Is the research question ("Does RIFT provide useful and safe root-cause attribution beyond always-abstain, using intervention evidence robust to unrelated temporal changes?") scientifically meaningful and operationally valuable?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 2. Causal Framework Coherence
*Is the proposed causal attribution framework (integrating EBD, MSIS, Fast Causal Inference, and Causal Intervention Divergence) technically coherent, mathematically grounded, and aligned with standard causal graph theory (PAGs/SCMs)?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 3. Ground-Truth L-struct Independence
*Is the newly introduced `L-struct` (threshold-free structural label) and its continuous detectability covariates (SNR, expected intervention effect, and timing) sufficiently independent of RIFT's own internal detection logic (θ_detect=3.0, snr>=4.0)?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 4. Dataset Independence and Partitioning
*Are the dataset splits (development, validation, and the proposed confirmatory generator) independent and appropriately partitioned? Does the retired legacy held-out split (with 15 content twins) and the newly mapped adversarial topological sharing represent an acceptable, fully-disclosed limitation?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 5. Statistical Units and Clustering
*Are the statistical units and cluster-aware inference procedures justified? Does the family-block bootstrap-t (clustering on fault families) correctly control Type I error compared to template-level resampling, given the crossed structure × fault-family design?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 6. Baseline Fairness and Always-Abstain
*Are the baselines fair, especially the always-abstain reference policy? Does the linear utility model ($U = C - \lambda \cdot S - \gamma \cdot (n_{do} / 20)$) fairly penalize incorrect, unsafe, or high-cost interventions?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 7. Endpoint Definition
*Are the primary endpoints (strict expected utility at default weights $\lambda=2$, $\kappa=0.05$) and secondary endpoints (outcome accuracy, wrong root, and conditional accuracy) appropriately defined and locked in advance?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 8. Confirmatory Power & Sample Size
*Is the confirmatory sample size ($N=2000$) and power design ($0.34–0.67$ under family-level dependence, $0.80–0.99$ under independence) defensible? Is the owner's "conditional go" decision scientifically robust?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 9. Reproducibility & Environment Hardening
*Are the reproducibility environment checks (requirements.txt pinning, final_repro_check.py, and deterministic seed-based generator) sufficient to guarantee numerical replication across Python 3.9 and 3.11?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 10. Manuscript Claim Traceability
*Are the manuscript's conclusions and negative results supported by the existing empirical evidence? Does the evidence map (FINAL_MANUSCRIPT_EVIDENCE_MAP.md) establish a 100% faithful, overclaim-free traceability matrix?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 11. Additional Controls & Limitations
*Are the documented threats to validity (definitional circularity, synthetic-only evaluation, unobserved-root limits, lack of live system validation) sufficiently comprehensive? What additional experiments, controls, or clarifications are required?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

### 12. Pre-registration Approval
*Would you approve the pre-registration package (Protocol v2, Dataset Protocol, Statistical Plan, and Confirmatory Infrastructure) to execute the confirmatory run, knowing that the experiment can only be run once and its results are legally binding?*
* **Grade:** `[Met / Partially Met / Not Met]`
* **Comments:**

---

## Overall Evaluation Verdict
Please select exactly one overall verdict:

* **[ ] APPROVE**  
  *The pre-registration is accepted without changes. The owner is authorized to generate the confirmatory dataset and run the pipeline.*
* **[ ] APPROVE WITH MINOR CHANGES**  
  *The pre-registration is accepted, subject to completing the specific minor adjustments detailed below. No further review round is needed.*
* **[ ] MAJOR REVISION REQUIRED**  
  *The pre-registration has significant issues that must be addressed. A full revision and a second round of independent human review are required before any data generation.*
* **[ ] REJECT THE CURRENT PROTOCOL**  
  *The experimental protocol is fundamentally flawed, and the confirmatory run cannot proceed. The manuscript must be restricted to exploratory results only.*

---

## Required Modifications / Reviewer Comments
`[Reviewer to insert any requested adjustments or notes here]`

---

## Sign-off
* **Signature:** `________________________________________`
* **Date:** `____________________`
