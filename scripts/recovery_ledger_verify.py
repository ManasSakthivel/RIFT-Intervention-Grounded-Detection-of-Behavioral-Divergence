#!/usr/bin/env python3
"""Read-only verifier for docs/recovery/CLAIMS_EVIDENCE_LEDGER.md.

Recomputes every headline figure the ledger classifies from saved records and prints PASS / FAIL / SKIP per check.
It never re-runs a method on dev/val/held-out data, never writes an artifact, and never opens the spent
held-out *label* file (held-out numbers come from the `score` fields saved in Sprint 4.3.0's per_scenario.json).

    PYTHONPATH=src:. python3.11 scripts/recovery_ledger_verify.py

Exit code 1 if any check FAILs. SKIP (input file absent, e.g. untracked artifacts on a fresh clone) is not a failure.
"""
from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter
from contextlib import redirect_stdout
from math import comb
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(("PASS" if ok else "FAIL", name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def skip(name, why):
    RESULTS.append(("SKIP", name, why))
    print(f"[SKIP] {name}  -- {why}")


def jload(rel):
    p = REPO / rel
    return json.loads(p.read_text()) if p.exists() else None


def mcnemar_exact(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def score(g, rec):
    ans = not rec["abstained"]
    top = rec["top"][0][0] if ans and rec["top"] else None
    attr = g["expected_outcome"] == "ATTRIBUTE"
    correct = bool(ans and attr and top in g["roots"])
    unsafe = bool(ans and ((not attr) or top not in g["roots"]))
    return correct, unsafe, correct or (not ans and not attr), attr


# ------------------------------------------------------------------ A. V2 / V3 / always-abstain on dev+val (N=252)
def section_a():
    print("\n== A. V2 / V3 / always-abstain, pooled dev+val (datasets/rift_v2, artifacts/sprint4_3_0, artifacts/sprint4_4_0)")
    rows, by_reason = [], Counter()
    for sp in ("dev", "val"):
        lab = {s["scenario_id"]: s for s in jload(f"datasets/rift_v2/{sp}.json")["scenarios"]}
        v3 = {r["scenario_id"]: r["methods"]["V3-FULL"]["record"] for r in jload(f"artifacts/sprint4_4_0/v3_{sp}.json")}
        v2 = {r["scenario_id"]: r["methods"]["RIFT-FULL-V2"]["record"]
              for r in jload(f"artifacts/sprint4_3_0/results/{sp}/per_scenario.json")}
        for sid, s in lab.items():
            g = s["ground_truth"]
            rows.append((score(g, v3[sid]), score(g, v2[sid])))
            if g["expected_outcome"] == "ABSTAIN_REQUIRED":
                by_reason["n"] += 1
                by_reason["V3"] += v3[sid]["abstained"]
                by_reason["V2"] += v2[sid]["abstained"]
    n = len(rows)
    n_attr = sum(a[3] for a, _ in rows)
    p1 = [sum(r[i][0] for r in rows) for i in (0, 1)]
    unsafe = [sum(r[i][1] for r in rows) for i in (0, 1)]
    p2 = [sum(r[i][2] for r in rows) for i in (0, 1)]
    aa = n - n_attr
    check("pooled N / ATTRIBUTE / ABSTAIN_REQUIRED = 252 / 99 / 153", (n, n_attr, aa) == (252, 99, 153), f"{n}/{n_attr}/{aa}")
    check("V3 P1 = 45/99, V2 P1 = 36/99", (p1[0], p1[1]) == (45, 36), f"V3 {p1[0]}, V2 {p1[1]}")
    check("unsafe: V3 48/252, V2 79/252, AA 0", (unsafe[0], unsafe[1]) == (48, 79), f"V3 {unsafe[0]}, V2 {unsafe[1]}")
    check("P2: V3 160/252, V2 137/252, AA 153/252", (p2[0], p2[1], aa) == (160, 137, 153), f"V3 {p2[0]}, V2 {p2[1]}, AA {aa}")
    b = sum(1 for a, _ in rows if a[2] and a[3])
    c = sum(1 for a, _ in rows if (not a[3]) and not a[2])
    p = mcnemar_exact(b, c)
    check("V3 vs AA on P2 not significant (exact McNemar p ~ 0.51)", abs(p - 0.5104) < 5e-4,
          f"V3-only {b}, AA-only {c}, p={p:.4f}  (V3 is +7 scenarios ahead of AA on P2, not significantly)")
    check("V3 abstains on 115/153 ABSTAIN_REQUIRED, V2 on 101/153", (by_reason["V3"], by_reason["V2"]) == (115, 101),
          f"V3 {by_reason['V3']}, V2 {by_reason['V2']}")
    return rows


# ------------------------------------------------------------------ B. utility artifact
def section_b():
    print("\n== B. Utility (artifacts/sprint4_5_1/utility/utility_verification.json)")
    d = jload("artifacts/sprint4_5_1/utility/utility_verification.json")
    s = d["primary_lambda2_gamma1"]["strict"]
    o = d["primary_lambda2_gamma1"]["operational"]
    near = lambda x, y, t=1e-6: abs(x - y) < t  # noqa: E731
    check("strict V3-AA mean = -0.3377", near(s["V3_minus_AA"]["template"]["mean"], -0.3376984, 1e-6))
    check("strict V2-AA mean = -0.5619", near(s["V2_minus_AA"]["template"]["mean"], -0.5619048, 1e-6))
    check("strict V3-V2 mean = +0.2242, CI excludes 0", s["V3_minus_V2"]["template"]["pct95"][0] > 0
          and near(s["V3_minus_V2"]["template"]["mean"], 0.2242063, 1e-6),
          f"pct95 {s['V3_minus_V2']['template']['pct95']}")
    check("operational V3-AA = -0.1948, V2-AA = -0.3635", near(o["V3_minus_AA"]["template"]["mean"], -0.1948413, 1e-6)
          and near(o["V2_minus_AA"]["template"]["mean"], -0.3634921, 1e-6))
    check("V3 break-even lambda* (kappa=0) = 0.9375; CI-significance limit = 0.61",
          near(d["decomposition_pooled"]["V3-FULL"]["break_even_lambda_kappa0_point"], 0.9375)
          and d["lambda_significance_limit_V3_vs_AA"]["kappa=0.0"]["strict_template"] == 0.61)
    check("56/58 preregistered utility claims verified (2 are rounding-level)",
          (d["n_claims_verified"], d["n_claims"]) == (56, 58),
          "; ".join(x["claim"] for x in d["claims_not_verified"]))
    check("per-scenario U is NOT bounded in [0,1]", "FALSE" in d["per_scenario_bounds"]["claim_U_in_[0,1]"])


# ------------------------------------------------------------------ C. spent held-out (V2 only) from saved scores
def section_c():
    print("\n== C. Spent Sprint 4.3.0 held-out, V2 only (saved score fields; labels not opened)")
    per = jload("artifacts/sprint4_3_0/results/held_out/per_scenario.json")
    if per is None:
        return skip("held-out V2 counts", "artifacts/sprint4_3_0/results/held_out/per_scenario.json absent (untracked)")
    S = [r["methods"]["RIFT-FULL-V2"]["score"] for r in per]
    n = len(S)
    n_attr = sum(s["expected"] == "ATTRIBUTE" for s in S)
    p1 = sum(bool(s["correct"]) for s in S)
    p2 = sum(bool(s["p2"]) for s in S)
    un = sum(bool(s["unsafe"]) for s in S)
    b = sum(1 for s in S if s["p2"] and s["expected"] == "ATTRIBUTE")
    c = sum(1 for s in S if s["expected"] != "ATTRIBUTE" and not s["p2"])
    check("held-out V2: P1 20/45, P2 60/108, unsafe 37/108", (n, n_attr, p1, p2, un) == (108, 45, 20, 60, 37),
          f"n={n} attr={n_attr} P1={p1} P2={p2} unsafe={un}")
    check("held-out always-abstain P2 = 63/108; V2 vs AA exact McNemar p ~ 0.76",
          (n - n_attr) == 63 and abs(mcnemar_exact(b, c) - 0.761) < 2e-3, f"V2-only {b}, AA-only {c}")


# ------------------------------------------------------------------ D. legacy 36-scenario validation harness
def section_d():
    print("\n== D. Legacy validation harness (36 dev scenarios, ORACLE PAG)  [no file written]")
    sys.path.insert(0, str(REPO / "validation"))
    with redirect_stdout(io.StringIO()):
        from validation_harness import SPLIT_DEVELOPMENT, SyntheticBenchmark, validate_scenario  # type: ignore
    sc = [s for s in SyntheticBenchmark().generate_all_faults(seed=42) if s.split == SPLIT_DEVELOPMENT]
    res = [validate_scenario(s, SyntheticBenchmark.SERVICES) for s in sc]
    nc = [r for r in res if not r.confounded]
    cf = [r for r in res if r.confounded]
    found = sum(r.root_cause_found for r in nc)
    check("'P@1 83.33%' = 10/12 non-confounded (oracle PAG)", (found, len(nc)) == (10, 12), f"{found}/{len(nc)}")
    check("both misses are redis_cart with confidence NONE",
          sorted((r.scenario_id, r.root_cause, r.top_confidence) for r in nc if not r.root_cause_found)
          == [("RC_01", "redis_cart", "NONE"), ("RC_02", "redis_cart", "NONE")])
    check("metric is 'root found at any rank', but rank==1 for all 12", Counter(r.root_cause_rank for r in nc) == {1: 12})
    abst = sum(r.abstained for r in cf)
    warn = sum((not r.abstained) and r.has_assumption_warning for r in cf)
    named = sum(r.top_candidate == r.root_cause for r in cf)
    check("'24/24 confounded' counts WARNINGS, not abstentions: abstained 0/24, warning-only 24/24",
          (abst, warn, len(cf)) == (0, 24, 24), f"abstained={abst} warning-only={warn}")
    check("on all 24 confounded the top CANDIDATE is the true root (i.e. it still attributes)", named == 24
          and Counter(r.top_confidence for r in cf) == {"CANDIDATE": 24}, f"named true root {named}/24")


# ------------------------------------------------------------------ E. legacy 50/18/15 comparative artifacts
def section_e():
    print("\n== E. Legacy comparative artifacts (artifacts/evaluation/*, 50 dev / 18 val / 15 held-out)")
    dev = jload("artifacts/evaluation/comparative_results_development.json")
    if dev is None:
        return skip("legacy comparative checks", "artifacts/evaluation/ absent (untracked)")
    att = {m: e["attribution"] for m, e in dev["evaluations"].items()}
    sr = dev["scenario_results"]
    check("RIFT-FULL (learned FCI) dev: raw P@1 0.88, abstention 0.06, FAR 0.0638  (NOT 0%/100% as in FINAL_EVALUATION_REPORT)",
          abs(att["RIFT-FULL"]["raw_precision_at_1"] - 0.88) < 1e-9 and abs(att["RIFT-FULL"]["abstention_rate"] - 0.06) < 1e-9
          and abs(att["RIFT-FULL"]["false_attribution_rate"] - 0.0638) < 1e-4)
    conf = lambda m: [r for r in sr[m] if r["is_confounded"]]  # noqa: E731
    check("learned RIFT-FULL abstains on 0/24 confounded; ORACLE-PAG variant abstains on 24/24",
          (sum(r["abstained"] for r in conf("RIFT-FULL")), sum(r["abstained"] for r in conf("RIFT-FULL-ORACLE")),
           len(conf("RIFT-FULL"))) == (0, 24, 24))
    sv = sr["SIEVE-LIKE"]
    wrong_c = sum((not r["abstained"]) and not r["correct"] for r in sv if r["is_confounded"])
    wrong_n = sum((not r["abstained"]) and not r["correct"] for r in sv if not r["is_confounded"])
    check("SIEVE-LIKE 28% FAR is 14/50 overall: 3/24 confounded, 11/26 non-confounded (NOT '28% on confounded')",
          (wrong_c, wrong_n) == (3, 11), f"confounded wrong {wrong_c}/24, non-confounded wrong {wrong_n}/26")
    b1 = sr["B1-LATENCY-CORR"]
    check("trivial B1-LATENCY-CORR is 50/50 correct (benchmark has no discriminative power)", sum(r["correct"] for r in b1) == 50)
    tests = jload("artifacts/evaluation/statistical_test_results.json")
    check("current artifact: H1 significant, H2 NOT significant (report states the opposite)",
          tests["H1_Intervention_vs_Obs"]["significant"] is True and tests["H2_Identifiability_Abstention"]["significant"] is False,
          f"H1 p={tests['H1_Intervention_vs_Obs']['p_value_raw']:.2e}, H2 p={tests['H2_Identifiability_Abstention']['p_value_raw']}")
    src = (REPO / "scripts/run_reproducible_evaluation.py").read_text()
    check("H4 inputs are hard-coded constants (30.0 s vs 60.0 s), not measurements",
          bool(re.search(r"ed_rift = np\.full\(len\(rift_p1\), 30\.0\)", src))
          and bool(re.search(r"ed_rand = np\.full\(len\(rift_p1\), 60\.0\)", src))
          and "total_intervention_ed_s=30.0" in src)
    check("H2 test compares RIFT-FULL against an all-zeros vector (not against SIEVE-LIKE as its label says)",
          "wilcoxon_one_sided(rift_conf, np.zeros_like(rift_conf)" in src)


# ------------------------------------------------------------------ F. Stage 4 live intervention
def section_f():
    print("\n== F. Stage 4 live intervention (N=1)")
    d = jload("artifacts/stage4_intervention_results.json")
    if d is None:
        return skip("Stage 4 checks", "artifacts/stage4_intervention_results.json absent (untracked / protected)")
    import hashlib
    sha = hashlib.sha256((REPO / "artifacts/stage4_intervention_results.json").read_bytes()).hexdigest()
    check("historical Stage 4 artifact SHA-256 unchanged (e4cf1391...dcffe)",
          sha == "e4cf1391c83bcb33070e8bc4ae3f8b792df2e0d1970df14524fc6c8d5d1dcffe")
    check("rollback + netns isolation recorded true; qdisc restored to noqueue",
          d["rollback_verified"] is True and d["netns_isolation_verified"] is True and "noqueue" in d["restored_qdisc"])
    import statistics as st
    z = {}
    for svc in ("cartservice", "frontend", "shippingservice", "checkoutservice"):
        pre = [p["val"] for p in d["pre_baseline"][svc]]
        act = [p["val"] for p in d["intervention"][svc]]
        z[svc] = (st.mean(act) - st.mean(pre)) / st.stdev(pre)
    check("telemetry Z: cartservice 143.06, frontend 37.56, checkout 1.95, shipping -12.70",
          (round(z["cartservice"], 2), round(z["frontend"], 2), round(z["checkoutservice"], 2), round(z["shippingservice"], 2))
          == (143.06, 37.56, 1.95, -12.70), str({k: round(v, 2) for k, v in z.items()}))
    check("sample sizes per service: 15 pre / 12 active / 23 post", all(
        (len(d["pre_baseline"][s]), len(d["intervention"][s]), len(d["post_recovery"][s])) == (15, 12, 23)
        for s in d["pre_baseline"]))
    check("artifact still carries the LITERAL 'attribution_accuracy_top1 = 1.0' / verdict PASS (historical, not an inference)",
          d.get("attribution_accuracy_top1") == 1.0 and d.get("attributed_root_cause") == "cartservice")
    off = jload("artifacts/sprint4_2_4/stage4_attribution_result.json")
    if off is None:
        return skip("offline Stage 4 attribution", "artifacts/sprint4_2_4/stage4_attribution_result.json absent")
    p, e = off["prediction"], off["evaluation"]
    check("offline pipeline on the same telemetry: ABSTAINED / NOT_IDENTIFIABLE, top1_correct = null, n_trials = 1",
          p["abstained"] and p["abstention_reason"] == "NOT_IDENTIFIABLE" and e["top1_correct"] is None and e["n_trials"] == 1)
    check("EBD candidate = cartservice but tied with frontend, shippingservice, adservice; CID INSUFFICIENT (15/12 < 20)",
          p["ebd_candidate"] == "cartservice" and sorted(p["ebd_tied_at_t_star"]) == ["adservice", "frontend", "shippingservice"]
          and p["cid_grade"] == "INSUFFICIENT")


def main():
    for fn in (section_a, section_b, section_c, section_d, section_e, section_f):
        try:
            fn()
        except FileNotFoundError as exc:  # fresh clone without untracked artifacts
            skip(fn.__name__, f"missing input: {exc.filename}")
    c = Counter(r[0] for r in RESULTS)
    print(f"\nSUMMARY: {c['PASS']} PASS, {c['FAIL']} FAIL, {c['SKIP']} SKIP")
    sys.exit(1 if c["FAIL"] else 0)


if __name__ == "__main__":
    main()
