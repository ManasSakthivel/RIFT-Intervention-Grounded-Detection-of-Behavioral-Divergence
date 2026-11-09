# D7 — Reviewer Evidence Package

This index defines the clean, reviewer-facing evidence package. It binds every major pre-publication manuscript, technical report, and pre-registration design document to its exact cryptographic SHA-256 checksum.

---

## 1. Evidence Package Directory

The reviewer is supplied with the following 10 core documents, which are located in the `docs/` folder of the RIFT workspace:

### 1.1 Core Research & Manuscript
* **Document:** `docs/IEEE_ACCESS_MANUSCRIPT_DRAFT.md`  
* **Role:** The complete 12-section research paper drafted for IEEE Access.
* **SHA-256 Hash:** `c40cf71ba73a6b0325ad06144902efd5c343edf0900ed3285d2d9b5ba3cb2646`

* **Document:** `docs/FINAL_MANUSCRIPT_EVIDENCE_MAP.md`  
* **Role:** Granular claims-to-evidence bidirectional traceability matrix.
* **SHA-256 Hash:** `9970500d6af212f22233a73017c093a1fd3d9e48198c983b670a5123b69976aa`

### 1.2 Scientific Validity & Remediation Reports
* **Document:** `docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md`  
* **Role:** Core scientific audit addressing circularity, statistical units, and temporal confounding.
* **SHA-256 Hash:** `c2ea37f91002a5f2f7dfdafe441d4742f244538809d83d1cbe1a5839d622741c`

* **Document:** `docs/FINAL_GROUND_TRUTH_INDEPENDENCE_REPORT.md`  
* **Role:** Structural ground-truth design report (`L-struct` implementation).
* **SHA-256 Hash:** `d37ecd2a28bc2ba969290801484dd2cd99bb668cec96b60cca6fb58fc182b2fc`

* **Document:** `docs/FINAL_DATASET_INDEPENDENCE_REPORT.md`  
* **Role:** Cross-split leakage checks and legacy contamination analysis.
* **SHA-256 Hash:** `7577e5ac46603ca5d861b42b7b62f2bb9702e13aa946e71837358cbfc4b5518e`

### 1.3 Pre-registration Plans & Protocols
* **Document:** `docs/FINAL_CONFIRMATORY_STATISTICAL_PLAN.md`  
* **Role:** The frozen cluster-aware inference plan and Monte Carlo simulations.
* **SHA-256 Hash:** `08e0a8efb581be868e37a4cca2bd43e3a3cb54eaea801cb56cb37fb29b512780`

* **Document:** `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md`  
* **Role:** Technical Work Packages (WP1–WP5) and testing rules (T1–T10).
* **SHA-256 Hash:** `976708c78f91245aabb142c9f340897061082f3d6d918d9f33219da37d09769a`

* **Document:** `docs/FINAL_CONFIRMATORY_PIPELINE_REPORT.md`  
* **Role:** The complete, safety-locked confirmatory generator, runner, and analyzer report.
* **SHA-256 Hash:** `94c2e24c518204e6f5cd5765147cd7b2ab062b5e94d6e67e6bbd09a9ee7902b2`

### 1.4 Reproducibility & Evaluation Checklists
* **Document:** `docs/FINAL_REPRODUCIBILITY_REPORT.md`  
* **Role:** Exact Python 3.9/3.11 environment locks and reproduction checks.
* **SHA-256 Hash:** `f607a7ba09c67db8712c5fae1625fa012ed8e6934d5de9ee80372473368118a6`

* **Document:** `docs/D7_REVIEW_CHECKLIST.md`  
* **Role:** The 12-item checklist to be completed by the reviewer.
* **SHA-256 Hash:** `038364e115945f32a51aac098a06174a1b75bdaf535554bd54c68e2b1a3d47d9`

---

## 2. Integrity Verification
The reviewer can independently verify the integrity of the supplied files by executing the following command from the package directory:
```bash
shasum -c docs/D7_REVIEW_SHA256SUMS.txt
```
All listed files must return `OK`.

---

## 3. Data Protection Policy
* **Sealed Data Isolation:** To prevent pre-trial leakage and post-hoc tuning, **no raw held-out split files (e.g. `held_out_test.json` or `heldout_candidate.json`) are included in this package.**
* **Security & Credentials:** This package contains zero credentials, absolute local path mappings, or private telemetry credentials.
