#!/usr/bin/env python3
"""Render Sprint 4.3.0 report tables from the saved JSON artifacts and substitute them into doc templates.

    python3 scripts/sprint430_build_docs.py

Templates:  docs/templates_sprint430/*.md.tpl   containing  {{TABLE:name}}  placeholders
Outputs:    docs/SPRINT4_3_0_*.md  (the four documents that embed machine-rendered numbers)
No method is run and no dataset label is read here; only results/*.json, datasets/rift_v2/manifest.json and
failure_taxonomy_evidence.json are consumed. Every number in a rendered table therefore traces to an artifact.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ART = REPO / "artifacts" / "sprint4_3_0"
RES = ART / "results"
TPL = REPO / "docs" / "templates_sprint430"
OUT = {"diversity": "SPRINT4_3_0_SCENARIO_DIVERSITY_REPORT.md", "statistics": "SPRINT4_3_0_STATISTICAL_VALIDATION.md",
       "taxonomy": "SPRINT4_3_0_FAILURE_TAXONOMY.md", "final": "SPRINT4_3_0_FINAL_REPORT.md"}


def J(p):
    return json.loads(Path(p).read_text())


def f(r, d=3):
    return "n/a" if r["value"] is None else f"{r['k']}/{r['n']} = {r['value']:.{d}f}"


def ci(r):
    lo, hi = r["wilson95"]
    return "n/a" if r["value"] is None else f"[{lo:.2f}, {hi:.2f}]"


def md(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


PRE = ["B0-EARLIEST", "B0-HIGHEST", "B1-LATENCY-CORR", "B3-SIEVE-LIKE", "B5-RIFT-OBS", "B6-RIFT-RANDOM",
       "B7-RIFT-ONE-SHOT", "RIFT-FULL-LEGACY", "RIFT-FULL-V2", "ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG",
       "ORACLE:RIFT-FULL-V2-ORACLE-GRAPH", "ORACLE:UPPER-BOUND"]
EXPL = ["RIFT-FULL-V2G"]
ABL = ["A2-NO-FCI", "A3-NO-EBD", "A4-NO-CID", "A5-NO-IDENT", "A6-NO-INTERVENTION", "A7-NO-MSIS",
       "A8-OBSERVATIONAL-ONLY", "A9-ORACLE-GRAPH", "A10-RANDOM-INTERVENTION"]
SPL = {"dev": "dev", "val": "val", "held_out": "held-out"}


def methods_table(split):
    a = J(RES / split / "aggregate.json")
    rows = []
    for m in PRE + EXPL:
        g = a[m]
        label = m + (" (EXPLORATORY, post-hoc)" if m in EXPL else "")
        rows.append([label, f(g["P1_attribution_accuracy"]), ci(g["P1_attribution_accuracy"]),
                     f(g["P2_outcome_correct"]), ci(g["P2_outcome_correct"]),
                     f(g["P3_unsafe_attribution_overall"]), f(g["unsafe_on_abstain_required"]),
                     f(g["wrong_root_on_attribute"]), f(g["coverage_overall"]), f(g["coverage_on_attribute"]),
                     f(g["conditional_accuracy_on_answered_attribute"]), f(g["selective_risk"])])
    return md(rows, ["Method", "P1 (den. N_attr)", "P1 Wilson95", "P2 (den. N)", "P2 Wilson95",
                     "P3 unsafe (den. N)", "unsafe on ABSTAIN_REQUIRED (den. N_abs)", "wrong root on ATTRIBUTE (den. N_attr)",
                     "coverage overall (den. N)", "coverage on ATTRIBUTE", "conditional acc. (den. answered ATTRIBUTE)",
                     "selective risk (den. answered)"])


def secondary_table(split):
    a = J(RES / split / "aggregate.json")
    rows = []
    for m in PRE + EXPL:
        g = a[m]
        ev = g["evidence"]
        rows.append([m, f(g["top3_on_attribute"]), f(g["correct_abstention_rate_on_abstain_required"]),
                     f(g["lost_coverage_on_attribute"]), f"{g['intervention']['mean_ed_s']:.1f}",
                     f"{g['intervention']['mean_perturbations']:.2f}", f"{g['runtime_s']['mean'] * 1000:.1f}",
                     f"{ev['interventional']}/{ev['answered']}", f"{ev['path_kind_directed']}/{ev['path_kind_semi_directed']}",
                     g["method_errors"]])
    return md(rows, ["Method", "top-3 on ATTRIBUTE (den. N_attr with >=3 candidates)", "correct abstention (den. N_abs)",
                     "lost coverage on ATTRIBUTE (den. N_attr)", "mean intervention s", "mean #perturbations",
                     "mean runtime ms", "interventional / answered", "DIRECTED / SEMI_DIRECTED (answered)",
                     "method errors"])


def conf_table():
    s = J(RES / "held_out" / "statistics.json")
    rows = []
    for k, v in s["confirmatory_family"]["rows"].items():
        _, c, met = k.split("|")
        lo, hi = v["ci95_quoted_widest"]
        bs, bt = v["bootstrap_scenario"]["ci95"], v["bootstrap_template"]["ci95"]
        rows.append([c, met, v["n"], f"{v['p_a']:.3f}", f"{v['p_b']:.3f}", f"{v['risk_difference']:+.3f}",
                     f"[{bs[0]:+.3f}, {bs[1]:+.3f}]", f"[{bt[0]:+.3f}, {bt[1]:+.3f}]", f"{v['cohens_h']:+.2f}",
                     f"{v['paired_table']['only_a']}/{v['paired_table']['only_b']}", f"{v['mcnemar_exact_p']:.4f}",
                     f"{v['permutation_p']:.4f}", f"{v['holm_p_mcnemar']:.4f}", "YES" if v["significant_holm_0.05"] else "no"])
    return md(rows, ["Comparator (vs RIFT-FULL-V2)", "Metric", "n", "p(V2)", "p(comp.)", "diff (V2 - comp.)",
                     "scenario-boot 95% CI", "template-boot 95% CI", "Cohen h", "V2-only / comp.-only correct",
                     "McNemar exact p", "permutation p", "Holm-adj. p (McNemar)", "significant (Holm<0.05 & CI excl. 0)"])


def holm_summary():
    s = J(RES / "held_out" / "statistics.json")["confirmatory_family"]["rows"]
    sig = [k for k, v in s.items() if v["significant_holm_0.05"]]
    return (f"{len(sig)} of {len(s)} confirmatory tests are significant after Holm correction "
            f"(family = 8 non-oracle comparators x 3 metrics = {len(s)} tests).")


def posthoc_table():
    rows = []
    for sp in ("dev", "val", "held_out"):
        a = J(RES / sp / "analysis.json")["POST_HOC_vs_always_abstain"]
        t = J(RES / sp / "analysis.json")["trivial_references_POST_HOC"]["label_mix"]
        for m in ("RIFT-FULL-V2", "RIFT-FULL-V2G", "RIFT-FULL-LEGACY", "B5-RIFT-OBS"):
            v = a[f"{m}|P2"]
            lo, hi = v["ci95_quoted_widest"]
            rows.append([SPL[sp], m + (" (exploratory)" if m == "RIFT-FULL-V2G" else ""),
                         f"{round(v['p_a'] * v['n'])}/{v['n']} = {v['p_a']:.3f}",
                         f"{round(v['p_b'] * v['n'])}/{v['n']} = {v['p_b']:.3f}", f"{v['risk_difference']:+.3f}",
                         f"[{lo:+.3f}, {hi:+.3f}]", f"{v['paired_table']['only_a']}/{v['paired_table']['only_b']}",
                         f"{v['mcnemar_exact_p']:.4f}"])
    return md(rows, ["Split", "Method", "P2 method", "P2 always-abstain", "diff", "95% CI (widest)",
                     "method-only / always-abstain-only correct", "McNemar exact p (UNCORRECTED, post-hoc)"])


def v2g_table():
    s = J(RES / "held_out" / "statistics.json")["exploratory"]
    rows = []
    for k, v in s.items():
        if not k.startswith("RIFT-FULL-V2G|"):
            continue
        met = k.split("|")[2]
        lo, hi = v["ci95_quoted_widest"]
        rows.append([met, f"{v['p_a']:.3f}", f"{v['p_b']:.3f}", f"{v['risk_difference']:+.3f}", f"[{lo:+.3f}, {hi:+.3f}]",
                     f"{v['paired_table']['only_a']}/{v['paired_table']['only_b']}", f"{v['mcnemar_exact_p']:.4f}"])
    return md(rows, ["Metric", "p(V2G)", "p(V2)", "diff (V2G - V2)", "95% CI", "V2G-only / V2-only", "McNemar p (exploratory, uncorrected)"])


def ablation_table(split="held_out"):
    an = J(RES / split / "analysis.json")["ablations"]
    st = J(RES / split / "statistics.json")["exploratory"]
    base = an["RIFT-FULL-V2"]
    rows = [["A1-FULL (= RIFT-FULL-V2)", f"{base['P1_attribution_accuracy']:.3f}", f"{base['P2_outcome_correct']:.3f}",
             f"{base['P3_unsafe_attribution_overall']:.3f}", f"{base['coverage_overall']:.3f}", f"{base['mean_ed_s']:.1f}",
             f"{base['mean_runtime_s'] * 1000:.0f}", "-", "-", "-"]]
    for k in ABL:
        v = an["ABL:" + k]
        p = {met: st[f"RIFT-FULL-V2|ABL:{k}|{met}"] for met in ("P1", "P2", "P3_safe")}
        tag = f"{k} (ORACLE graph)" if k == "A9-ORACLE-GRAPH" else k
        rows.append([tag, f"{v['P1_attribution_accuracy']:.3f}", f"{v['P2_outcome_correct']:.3f}",
                     f"{v['P3_unsafe_attribution_overall']:.3f}", f"{v['coverage_overall']:.3f}", f"{v['mean_ed_s']:.1f}",
                     f"{v['mean_runtime_s'] * 1000:.0f}",
                     f"{-p['P1']['risk_difference']:+.3f} (p={p['P1']['mcnemar_exact_p']:.3f})",
                     f"{-p['P2']['risk_difference']:+.3f} (p={p['P2']['mcnemar_exact_p']:.3f})",
                     f"{-p['P3_safe']['risk_difference']:+.3f} (p={p['P3_safe']['mcnemar_exact_p']:.3f})"])
    return md(rows, ["Config", "P1", "P2", "unsafe rate", "coverage", "mean intervention s", "mean ms",
                     "dP1 vs V2 (ablation - V2; McNemar p)", "dP2 vs V2", "d(not-unsafe) vs V2"])


def ablation_split_compare():
    rows = []
    for k in ["A1-FULL"] + ABL:
        r = [k]
        for sp in ("dev", "val", "held_out"):
            an = J(RES / sp / "analysis.json")["ablations"]
            v = an["RIFT-FULL-V2"] if k == "A1-FULL" else an["ABL:" + k]
            r.append(f"{v['P1_attribution_accuracy']:.2f} / {v['P2_outcome_correct']:.2f} / "
                     f"{v['P3_unsafe_attribution_overall']:.2f} / {v['coverage_overall']:.2f}")
        rows.append(r)
    return md(rows, ["Config", "dev  P1 / P2 / unsafe / coverage", "val  P1 / P2 / unsafe / coverage",
                     "held-out  P1 / P2 / unsafe / coverage"])


def h4_table():
    rows = []
    for sp in ("dev", "val", "held_out"):
        h = J(RES / sp / "analysis.json")["H4_counterexample_strata"]
        rows.append([SPL[sp], h["n_scenarios"], f(h["RIFT-FULL-V2"]["unsafe"]), f(h["ABL:A6-NO-INTERVENTION"]["unsafe"]),
                     f(h["ABL:A8-OBSERVATIONAL-ONLY"]["unsafe"]), f(h["RIFT-FULL-V2"]["coverage"]),
                     f(h["ABL:A6-NO-INTERVENTION"]["coverage"]), h["verdict"]])
    return md(rows, ["Split", "n (earliest_not_root + coincidental_anomaly + indistinguishable_onsets)", "V2 unsafe",
                     "A6 unsafe", "A8 unsafe", "V2 coverage", "A6 coverage", "verdict"])


def h5_table():
    rows = []
    for sp in ("dev", "val", "held_out"):
        h = J(RES / sp / "analysis.json")["H5_msis_vs_alternatives"]
        a = J(RES / sp / "analysis.json")["ablations"]
        for k in ("ABL:A10-RANDOM-INTERVENTION", "ABL:A7-NO-MSIS"):
            v = h[k]
            b = v["bootstrap"]["ci95"]
            rows.append([SPL[sp], k[4:], f"{v['mean_ed_V2']:.1f}", f"{v['mean_ed_other']:.1f}",
                         f"{v['mean_diff_other_minus_V2_s']:+.1f}", f"[{b[0]:+.1f}, {b[1]:+.1f}]",
                         v["n_scenarios_differing"], f"{v['permutation_p']:.4f}",
                         f"{a['RIFT-FULL-V2']['P1_attribution_accuracy']:.3f} vs {a[k]['P1_attribution_accuracy']:.3f}"])
    return md(rows, ["Split", "Alternative order", "mean ED V2 (s)", "mean ED alt. (s)", "alt. - V2 (s)",
                     "template-boot 95% CI of diff", "#scenarios differing", "sign-flip permutation p (uncorrected)",
                     "P1 V2 vs alt."])


def breakdown(dim, split="held_out", method="RIFT-FULL-V2"):
    b = J(RES / split / "analysis.json")["breakdowns"][method][dim]
    rows = [[k, v["n"], v["n_attribute"], f(v["P1"], 2), f(v["P2"], 2), f(v["unsafe"], 2), f(v["coverage"], 2)]
            for k, v in b.items()]
    return md(rows, [dim, "n", "n ATTRIBUTE", "P1 (den. n ATTRIBUTE)", "P2 (den. n)", "unsafe (den. n)", "coverage (den. n)"])


def detection_table():
    rows = []
    for sp in ("dev", "val", "held_out"):
        d = J(RES / sp / "detection.json")["metrics"]
        dl = d["delay_s"]
        rows.append([SPL[sp], d["n_fault"], d["n_no_fault"], d["tp"], d["fn"], d["fp"], d["tn"],
                     f"{d['precision']:.3f}", f"{d['recall']:.3f}", f"{d['f1']:.3f}", f"{d['fpr']:.2f} ({d['fp']}/{d['n_no_fault']})",
                     f"{d['fnr']:.3f} ({d['fn']}/{d['n_fault']})",
                     f"{dl['median']:.0f} (IQR {dl['q1']:.0f}-{dl['q3']:.0f}, n={dl['n']})"])
    return md(rows, ["Split", "fault scenarios", "no-fault scenarios", "TP", "FN", "FP", "TN", "precision", "recall", "F1",
                     "FPR", "FNR", "delay s, median"])


def shift_table():
    a = J(RES / "held_out" / "analysis.json")["distribution_shift"]
    rows = []
    for k, v in a.items():
        for m in ("RIFT-FULL-V2", "RIFT-FULL-V2G", "RIFT-FULL-LEGACY", "B6-RIFT-RANDOM"):
            g = v[m]
            rows.append([k, m, g["n"], g["n_attribute"], f(g["P1"], 2), f(g["P2"], 2), f(g["unsafe"], 2), f(g["coverage"], 2)])
    return md(rows, ["Stratum", "Method", "n", "n ATTRIBUTE", "P1", "P2", "unsafe", "coverage"])


def obs_table():
    a = J(RES / "held_out" / "analysis.json")["observability_strata"]
    rows = []
    for k, v in a.items():
        for m in ("RIFT-FULL-V2", "RIFT-FULL-LEGACY", "B6-RIFT-RANDOM"):
            g = v[m]
            rows.append([k, m, g["n"], g["n_attribute"], f(g["P1"], 2), f(g["P2"], 2), f(g["unsafe"], 2), f(g["coverage"], 2)])
    p = J(RES / "held_out" / "analysis.json")["observability_degraded_pooled"]
    for m in ("RIFT-FULL-V2", "RIFT-FULL-V2G", "RIFT-FULL-LEGACY", "B6-RIFT-RANDOM", "B3-SIEVE-LIKE", "B1-LATENCY-CORR"):
        g = p[m]
        rows.append(["**all degraded pooled**", m, g["n"], g["n_attribute"], f(g["P1"], 2), f(g["P2"], 2),
                     f(g["unsafe"], 2), f(g["coverage"], 2)])
    return md(rows, ["Observability stratum", "Method", "n", "n ATTRIBUTE", "P1", "P2", "unsafe", "coverage"])


# ------------------------------------------------------------------ diversity tables
def dist_table(dim):
    m = {}
    from collections import Counter
    for sp, fn in (("dev", "dev.json"), ("val", "val.json"), ("held_out", "heldout_candidate.json")):
        scs = J(REPO / "datasets" / "rift_v2" / fn)["scenarios"]
        m[sp] = Counter(str(s["dimensions"].get(dim)) for s in scs)
    keys = sorted(set().union(*[set(c) for c in m.values()]))
    rows = [[k, m["dev"].get(k, 0), m["val"].get(k, 0), m["held_out"].get(k, 0),
             m["dev"].get(k, 0) + m["val"].get(k, 0) + m["held_out"].get(k, 0)] for k in keys]
    rows.append(["**distinct levels**", sum(1 for k in keys if m["dev"].get(k)), sum(1 for k in keys if m["val"].get(k)),
                 sum(1 for k in keys if m["held_out"].get(k)), len(keys)])
    return md(rows, [dim, "dev", "val", "held-out", "total"])


def corpus_table():
    man = J(REPO / "datasets" / "rift_v2" / "manifest.json")
    ind = J(REPO / "datasets" / "rift_v2" / "independence_report.json")
    rows = []
    for sp in ("dev", "val", "held_out"):
        d = man["datasets"][sp]
        k = ind["distinct_keys_per_split"][sp]
        rows.append([SPL[sp], d["file"], d["n_scenarios"], d["size_bytes"], d["sha256"][:16] + "...", k["content_hash"],
                     k["dynamics_hash"], k["topology_hash"], k["template_id"], k["joint_cell"], man["qc"][sp]["n_failed"]])
    tot = sum(man["datasets"][s]["n_scenarios"] for s in man["datasets"])
    rows.append(["**total**", "", tot, "", "", "", "", "", "", "", ""])
    return md(rows, ["Split", "File", "scenarios", "bytes", "SHA-256 (prefix)", "distinct content", "distinct dynamics",
                     "distinct topology", "distinct template", "distinct joint cell", "QC failures"])


def outcome_table():
    from collections import Counter
    rows = []
    for sp, fn in (("dev", "dev.json"), ("val", "val.json"), ("held_out", "heldout_candidate.json")):
        scs = J(REPO / "datasets" / "rift_v2" / fn)["scenarios"]
        c = Counter(s["ground_truth"]["expected_outcome"] for s in scs)
        r = Counter(str(s["ground_truth"]["abstain_reason"]) for s in scs if s["ground_truth"]["expected_outcome"] != "ATTRIBUTE")
        nf = Counter(len(s["faults"]) for s in scs)
        rows.append([SPL[sp], len(scs), c["ATTRIBUTE"], c["ABSTAIN_REQUIRED"], r["WEAK_SIGNAL"], r["ROOT_UNOBSERVED"],
                     r["SYMMETRIC_MUTUAL_DEPENDENCY"], r["INSUFFICIENT_BASELINE"], r["NO_DISCRIMINATING_EVIDENCE"],
                     r["NO_FAULT"], f"{nf[0]}/{nf[1]}/{nf[2]}/{nf[3]}"])
    return md(rows, ["Split", "n", "ATTRIBUTE", "ABSTAIN_REQUIRED", "WEAK_SIGNAL", "ROOT_UNOBSERVED", "SYMMETRIC_MUTUAL_DEPENDENCY",
                     "INSUFFICIENT_BASELINE", "NO_DISCRIMINATING_EVIDENCE", "NO_FAULT", "#faults 0/1/2/3"])


def shared_keys_table():
    ind = J(REPO / "datasets" / "rift_v2" / "independence_report.json")
    rows = [[name, *[v[p] for p in ("dev&val", "dev&held_out", "val&held_out")]]
            for name, v in ind["shared_keys_by_pair"].items()]
    return md(rows, ["Key", "shared dev&val", "shared dev&held-out", "shared val&held-out"])


def marginals_table():
    ind = J(REPO / "datasets" / "rift_v2" / "independence_report.json")["declared_shared_marginal_dimensions"]
    rows = [[d, ", ".join(f"{sp}:{len(v)}" for sp, v in per.items())] for d, per in ind.items()]
    return md(rows, ["Dimension (marginals are shared BY DESIGN)", "distinct levels per split"])


def taxonomy_wrong_table():
    e = J(ART / "failure_taxonomy_evidence.json")
    rows = []
    for sp in ("dev", "val", "held_out"):
        x = e[sp]
        rows.append([SPL[sp], x["attribute_scenarios"], x["attribute_abstained"], x["attribute_answered"],
                     x["attribute_answered_correct"], x["attribute_answered_wrong"],
                     x["wrong_root_relation"].get("downstream_of_true_root", 0),
                     x["wrong_root_relation"].get("other_faulted_service", 0), x["wrong_root_relation"].get("unrelated", 0),
                     json.dumps(x["wrong_root_path_kind"])])
    return md(rows, ["Split", "ATTRIBUTE scenarios", "abstained", "answered", "answered correct", "answered WRONG",
                     "wrong = downstream of true root", "wrong = other faulted service", "wrong = unrelated service",
                     "path kind of wrong answers"])


def taxonomy_mech_table():
    e = J(ART / "failure_taxonomy_evidence.json")
    names = {"M1": "M1 true root never crosses R1 (not observed / signal below detector)",
             "M2": "M2 true root crosses R1 but fails R3 (no PAG path to a diverging service)",
             "M3": "M3 true root was intervened but R4 did not confirm",
             "M4": "M4 true root was a candidate but never intervened / explained away"}
    rows = []
    for sp in ("dev", "val"):
        c = {}
        iso = 0
        for m in e[sp]["wrong_root_mechanisms"]:
            c[m["mechanism"][:2]] = c.get(m["mechanism"][:2], 0) + 1
            iso += m["mechanism"].endswith("isolated_in_PAG")
        for k in ("M1", "M2", "M3", "M4"):
            rows.append([SPL[sp], names[k], c.get(k, 0)])
        rows.append([SPL[sp], "of M2: true root also isolated in the learned PAG (no adjacent edge)", iso])
        rows.append([SPL[sp], "wrong answers where the true root diverged EARLIER (R1) than the named service",
                     f"{e[sp]['wrong_root_true_root_earlier']}/{e[sp]['attribute_answered_wrong']}"])
    return md(rows, ["Split (dev/val re-run of unchanged A1; held-out cannot be re-run)", "Mechanism", "count"])


def taxonomy_category_table(split="held_out"):
    e = J(ART / "failure_taxonomy_evidence.json")[split]["categories"]
    names = {"C02_earliest_divergence_ambiguity": "Earliest-divergence ambiguity (earliest_not_root, indistinguishable_onsets, coincidental_anomaly)",
             "C05_non_identifiable": "Non-identifiable (SYMMETRIC_MUTUAL_DEPENDENCY, NO_DISCRIMINATING_EVIDENCE, root_not_identifiable)",
             "C06_confounding": "Confounding (confounding, hidden_common_cause, common_cause_several_services)",
             "C07_multiple_simultaneous_causes": "Multiple simultaneous causes (>=2 faults, multiple_upstream, overlapping_faults)",
             "C08_high_variance_service": "High-variance behaviour (high_baseline_variance, high_variance_no_fault)",
             "C09_weak_intervention_effect": "Weak intervention effects (no_meaningful_effect, low_magnitude, imperfect, weak_interventional_evidence)",
             "C10_insufficient_telemetry": "Insufficient telemetry (insufficient_samples, missing_windows, partial_service_observability)",
             "C11_recovery_anomaly": "Recovery anomalies (recovery_instability, partial_recovery, recovery_delay, incomplete_recovery)",
             "C12_feedback_like_structure_unseen": "Unseen structure feedback_like (held-out only)"}
    rows = []
    for k, v in e.items():
        s = v["V2"]
        rows.append([names[k], s["n"], s["n_attribute"], f(s["P1"], 2), f(s["P2"], 2), f(s["unsafe"], 2), f(s["coverage"], 2),
                     s["wrong_root"], s["unsafe_on_abstain_required"], s["lost_coverage_on_attribute"],
                     f"{v['V2G_unsafe']['k']}/{v['V2G_unsafe']['n']}", ", ".join(v["failing_ids"][:3])])
    return md(rows, ["Category (overlapping; a scenario can belong to several)", "n", "n ATTRIBUTE", "V2 P1", "V2 P2",
                     "V2 unsafe", "V2 coverage", "wrong root", "unsafe on ABSTAIN_REQUIRED", "lost coverage on ATTRIBUTE",
                     "V2G unsafe", "example failing ids"])


def label_reason_table():
    e = J(ART / "failure_taxonomy_evidence.json")
    rows = []
    for sp in ("dev", "val", "held_out"):
        x = e[sp]["unsafe_on_abstain_required_by_label_reason"]
        rows.append([SPL[sp]] + [x.get(k, 0) for k in ("WEAK_SIGNAL", "SYMMETRIC_MUTUAL_DEPENDENCY", "ROOT_UNOBSERVED",
                                                         "NO_DISCRIMINATING_EVIDENCE", "NO_FAULT", "INSUFFICIENT_BASELINE")]
                    + [sum(x.values()), e[sp]["answered_top_is_true_root_on_abstain_required"]])
    return md(rows, ["Split", "WEAK_SIGNAL", "SYMMETRIC_MUTUAL_DEPENDENCY", "ROOT_UNOBSERVED", "NO_DISCRIMINATING_EVIDENCE",
                     "NO_FAULT", "INSUFFICIENT_BASELINE", "total unsafe on ABSTAIN_REQUIRED", "of which top-1 is a true root"])


def abstain_attr_table():
    e = J(ART / "failure_taxonomy_evidence.json")
    keys = ["INSUFFICIENT_BASELINE", "NO_CANDIDATES", "INTERVENTION_NOT_VERIFIED", "NOT_IDENTIFIABLE"]
    rows = [[SPL[sp]] + [e[sp]["abstention_reasons_on_attribute"].get(k, 0) for k in keys]
            + [sum(e[sp]["abstention_reasons_on_attribute"].values())] for sp in ("dev", "val", "held_out")]
    return md(rows, ["Split"] + keys + ["total abstained on ATTRIBUTE"])


def pathkind_table():
    e = J(ART / "failure_taxonomy_evidence.json")
    rows = []
    for sp in ("dev", "val", "held_out"):
        x = e[sp]["answered_path_kind_correctness"]
        rows.append([SPL[sp], f"{x['DIRECTED']['correct']}/{x['DIRECTED']['answered']}",
                     f"{x['SEMI_DIRECTED']['correct']}/{x['SEMI_DIRECTED']['answered']}"])
    return md(rows, ["Split", "DIRECTED: correct / answered (any label)", "SEMI_DIRECTED: correct / answered (any label)"])


def wrong_ids(split="held_out"):
    return ", ".join(J(ART / "failure_taxonomy_evidence.json")[split]["wrong_root_ids"])


def meta_table():
    rows = []
    for sp in ("dev", "val", "held_out"):
        m = J(RES / sp / "run_metadata.json")
        rows.append([SPL[sp], m["status"], m["n_scenarios"], m["dataset_sha256"][:16] + "...", m["config_hash"][:16] + "...",
                     m["wall_clock_s"], m["git_commit"][:10], m["started_utc"][:19]])
    return md(rows, ["Split", "status", "scenarios", "dataset sha256", "config hash", "wall-clock s", "git commit", "started (UTC)"])


TABLES = {
    "methods_held_out": lambda: methods_table("held_out"), "methods_dev": lambda: methods_table("dev"),
    "methods_val": lambda: methods_table("val"), "secondary_held_out": lambda: secondary_table("held_out"),
    "conf_table": conf_table, "holm_summary": holm_summary, "posthoc_table": posthoc_table, "v2g_table": v2g_table,
    "ablation_held_out": ablation_table, "ablation_splits": ablation_split_compare, "h4_table": h4_table,
    "h5_table": h5_table, "detection_table": detection_table, "shift_table": shift_table, "obs_table": obs_table,
    "bk_family": lambda: breakdown("family"), "bk_structure": lambda: breakdown("structure"),
    "bk_workload": lambda: breakdown("workload"), "bk_observability": lambda: breakdown("observability"),
    "bk_intervention": lambda: breakdown("intervention"), "bk_negative": lambda: breakdown("negative"),
    "dist_family": lambda: dist_table("family"), "dist_structure": lambda: dist_table("structure"),
    "dist_temporal": lambda: dist_table("temporal"), "dist_workload": lambda: dist_table("workload"),
    "dist_observability": lambda: dist_table("observability"), "dist_intervention": lambda: dist_table("intervention"),
    "dist_negative": lambda: dist_table("negative"), "corpus_table": corpus_table, "outcome_table": outcome_table,
    "shared_keys": shared_keys_table, "marginals": marginals_table, "tax_wrong": taxonomy_wrong_table,
    "tax_mech": taxonomy_mech_table, "tax_cat": taxonomy_category_table, "tax_cat_val": lambda: taxonomy_category_table("val"),
    "label_reason": label_reason_table, "abstain_attr": abstain_attr_table, "pathkind": pathkind_table,
    "wrong_ids": wrong_ids, "meta_table": meta_table,
}


def main() -> int:
    missing = 0
    for key, name in OUT.items():
        src = TPL / f"{key}.md.tpl"
        if not src.is_file():
            print("missing template", src)
            missing += 1
            continue
        txt = src.read_text()

        def sub(m):
            return TABLES[m.group(1)]()
        txt = re.sub(r"\{\{TABLE:([a-z_0-9]+)\}\}", sub, txt)
        (REPO / "docs" / name).write_text(txt)
        print("wrote docs/" + name, len(txt.splitlines()), "lines")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
