# D7 — External Review Invitation Template

This template is immediately ready to be customized and sent by the project owner to a selected independent researcher from the candidate shortlist.

---

**Subject:** Research Peer Review Invitation: RIFT Microservice Causal Attribution Protocol (Pre-registration Review)

**Dear [Candidate Name],**

I hope this email finds you well. 

I am writing to invite you to conduct an independent pre-registration scientific review of our latest project, **RIFT (Root-cause Intervention-based Fault-attribution with-abstention Tracker)**. We are preparing a manuscript titled *"Where Intervention-Grounded Root-Cause Attribution Fails: A Synthetic Study with a Conservative Abstaining Framework"* for submission to **IEEE Access**.

### Research Context & Motivation
Root-cause analysis (RCA) in modern microservices is severely confounded by load propagation and telemetry noise, making purely observational correlation tools highly unreliable. RIFT is a diagnostic framework designed to combine **interventional evidence (chaos injection)** with **causal structure discovery (Fast Causal Inference on traces)** to attribute root causes. Crucially, the method is designed to conservatively **abstain** when learned graphical patterns are unidentifiable (e.g. adjacent to hidden confounders) or when interventional signals are weak.

### Why We Are Requesting Your Expertise
Given your established contributions in the domain of **[Reviewer's Field, e.g., Causal Discovery / Microservice Observability]**, we would be honored to receive your critical evaluation of our experimental methodology, statistical plans, and pre-registered confirmatory trial design. 

### Key Findings & Empirical Realism (Commitment to Rigor)
In keeping with strict research integrity, we have pre-registered our hypotheses and locked our evaluation protocol prior to executing our main trials. Our initial validation runs on a $252$-scenario synthetic corpus and a $108$-scenario spent held-out split have yielded crucial **negative and mixed results**:
1. **Always-Abstain Dominance:** Under standard operational weights, RIFT V3 achieves negative expected utility ($U = -0.338$) and does *not* statistically outperform a trivial always-abstain reference policy on outcome accuracy.
2. **Definitional Label Circularity:** We discovered that our ground-truth simulator labels definitionally mirrored our detection constants. We have proposed a threshold-free structural label scheme (**L-struct**) and continuous detectability covariates reported strictly as sensitivity analyses to remediate this.
3. **Crossed Statistical Dependence:** We documented that template-level bootstrap-t tests over-reject nominal nulls (Type I error up to $20\%$), and we have formulated a conservative cluster-aware **family-block bootstrap-t** and a fail-safe **Hull Rule** to control size.

### Your Role and Review Effort
We are seeking an honest, unvarnished scientific critique—**not a rubber stamp**. You are fully authorized to reject our protocol, recommend major structural changes, or challenge our statistical assumptions.

The review package contains only concise, high-level methodological specifications and reports (~35 pages total). We estimate the review will require approximately **2 to 4 hours** of your time. 

If you accept, we will provide you with a clean, hashed reviewer package containing:
* The full IEEE Access manuscript draft.
* The pre-registration dataset and statistical plans.
* The safety, reproducibility, and L-struct remediation reports.
* A structured 12-item evaluation checklist with four overall verdict options (Approve, Approve with Minor Changes, Major Revision, Reject).

We do not provide or request access to any sealed held-out raw data to prevent leakage. All document versions are secured with SHA-256 cryptographic checksums.

We would be deeply grateful if you could let us know of your availability by **[Date, e.g., November 12, 2026]**. 

Thank you very much for your time, consideration, and dedication to scientific integrity.

Sincerely,

**[Project Owner Name]**  
[Project Owner Title/Institution]  
[Project Owner Contact Details]  
