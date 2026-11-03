#!/usr/bin/env python3
"""Sprint 4.5.1 (Agent 6): cross-document consistency checker for the Sprint 4.5.0 preregistration set.

Read-only. Re-runnable at any time:

    python3 scripts/sprint451_doc_consistency_check.py            # writes artifacts/sprint4_5_1/consistency/
    python3 scripts/sprint451_doc_consistency_check.py --strict   # exit 1 on any WARN as well as FAIL

Checks
  A  every backticked repo path / markdown link in the six docs exists, or is in the PLANNED allow-list
  B  every 64-hex SHA-256 is known to freeze_manifest.json (files / lock / held-out string / manifest file /
     a few live-hashed historical artifacts); line-level path<->hash agreement; truncated 8-hex hashes
  C  key numeric claims (presence in the right docs, stale or contradictory variants outside SUPERSEDED context)
  D  forbidden phrases used affirmatively
  E  manifest hygiene: no self-referential hash; 51 files; frozen docs not edited; docs do not embed their own hash
  F  evidence checks: numbers quoted in docs recomputed from artifacts/sprint4_5_0/prereg_audit/*.json and from
     closed-form power formulas
  G  decision register consistency (D-ids / A-ids), label set, research-question wording, H5-not-confirmatory

It never opens, parses or hashes any held-out dataset: paths that name a sealed held-out file are not even stat'ed.
Python 3.9 compatible.
"""
import argparse
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT_DIR = os.path.join(REPO, "artifacts", "sprint4_5_1", "consistency")

DOCS = {
    "PRE": "docs/SPRINT4_5_0_PREREGISTRATION.md",
    "SAP": "docs/SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md",
    "CID": "docs/SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md",
    "DATA": "docs/SPRINT4_5_0_DATASET_PROTOCOL.md",
    "AUD": "docs/SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md",
    "PLAN": "docs/SPRINT4_5_0_EXECUTION_PLAN.md",
}
MANIFEST = "artifacts/sprint4_5_0/prereg/freeze_manifest.json"

# Paths that are protected: never stat, read or hash these (names only).
PROTECTED_RE = re.compile(r"(heldout_candidate|held_out_test|heldout_status|results/held_out|heldout_opened)")

# Planned-but-not-yet-existing paths (prefix match). Everything here is created later by the researcher / a later sprint.
PLANNED = [
    "src/rift/cid_reliability",
    "src/rift/scenarios/generator_confirm.py",
    "scripts/sprint450_analyze.py",
    "scripts/sprint450_generate_confirmatory.py",
    "scripts/sprint450_run_confirm.py",
    "artifacts/sprint4_5_0/confirm",
    "artifacts/sprint4_5_0/cid_reliability",
    "artifacts/sprint4_5_0/results",
    "artifacts/sprint4_5_0/prereg/prereg.sha256",
    "artifacts/sprint4_5_0/prereg/decisions.json",
    "artifacts/sprint4_5_0/prereg/freeze_verification.json",
    "artifacts/sprint4_5_0/prereg/PREREGISTRATION.md",
    "artifacts/sprint4_5_0/prereg/ledger",
    "prereg.sha256", "decisions.json", "freeze_verification.json", "prereg/freeze_verification.json",
    "docs/SPRINT4_5_0_CID_RELIABILITY_REPORT.md",
    "docs/SPRINT4_5_0_FINAL_REPORT.md",
    "SPRINT4_5_0_CID_RELIABILITY_REPORT.md", "SPRINT4_5_0_FINAL_REPORT.md",
    "docs/SPRINT4_5_1_FINAL_REPORT.md", "docs/SPRINT4_5_1_SCIENTIFIC_REVIEW.md", "docs/SPRINT4_5_1_REPRODUCIBILITY_REPORT.md",
    "run.py", "estimators.py", "dgp.py", "metrics.py", "windows.py", "acceptance.py", "controls.py", "cells.py", "analyse.py",
    "prereg/PREREGISTRATION.md",
    "tests/unit/test_sprint450",
]
# Bare names that are not repo paths at all.
IGNORE_TOKENS = {"x->y", "HEAD", "joblib", "confirm"}


# ----------------------------------------------------------------------------------------------------------------
def norm(s):
    return (s.replace("\u2212", "-").replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-"))


def read_doc(key):
    p = os.path.join(REPO, DOCS[key])
    with open(p, encoding="utf-8") as f:
        return f.read().split("\n")


def sha256_file(rel):
    if PROTECTED_RE.search(rel):
        raise RuntimeError("refusing to hash protected path: " + rel)
    h = hashlib.sha256()
    with open(os.path.join(REPO, rel), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    try:
        return subprocess.check_output(("git",) + args, cwd=REPO, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


class Report(object):
    def __init__(self):
        self.items = []  # (level, check, where, message)

    def add(self, level, check, where, msg):
        self.items.append({"level": level, "check": check, "where": where, "message": msg})

    def count(self, level):
        return sum(1 for i in self.items if i["level"] == level)


R = Report()


def line_contexts(lines):
    """Yield (lineno, text, superseded_flag, heading_path). SUPERSEDED context = a heading in the current stack carries
    the word SUPERSEDED, or the line is inside the top blockquote revision banner (lines starting with '>')."""
    stack = []
    for n, raw in enumerate(lines, 1):
        m = re.match(r"^(#{1,6})\s+(.*)$", raw)
        if m:
            lvl = len(m.group(1))
            stack = [s for s in stack if s[0] < lvl]
            stack.append((lvl, m.group(2)))
        sup = any("SUPERSEDED" in s[1] for s in stack) or raw.lstrip().startswith(">")
        yield n, raw, sup, " > ".join(s[1][:40] for s in stack)


# ----------------------------------------------------------------------------------------------------------------
# A. paths
def repo_index():
    files = set()
    out = git("ls-files")
    if out:
        files.update(out.split("\n"))
    out = git("ls-files", "-o", "--exclude-standard")
    if out:
        files.update(out.split("\n"))
    return files


def expand_braces(tok):
    m = re.search(r"\{([^{}]+)\}", tok)
    if not m:
        return [tok]
    res = []
    for alt in m.group(1).split(","):
        res.extend(expand_braces(tok[:m.start()] + alt + tok[m.end():]))
    return res


def is_planned(tok):
    t = tok.rstrip("/")
    for p in PLANNED:
        if t == p or t.startswith(p.rstrip("/") + "/") or t.endswith("/" + p) or os.path.basename(t) == p:
            return True
    return False


def check_paths(index):
    tok_re = re.compile(r"`([^`\n]+)`")
    link_re = re.compile(r"\]\(([^)\s]+)\)")
    ext_re = re.compile(r"\.(py|json|md|txt|lock|sha256|csv|yaml|yml|toml|sh)$")
    basenames = {}
    for f in index:
        basenames.setdefault(os.path.basename(f), []).append(f)
    summary = {}
    for key in DOCS:
        counts = {"exists": 0, "planned": 0, "missing": 0, "protected_not_stat": 0, "skipped": 0}
        seen = set()
        for n, raw, sup, _ in line_contexts(read_doc(key)):
            cands = [m.group(1) for m in tok_re.finditer(raw)] + [m.group(1) for m in link_re.finditer(raw)]
            for tok in cands:
                t = tok.strip().rstrip(".,;:")
                t = t.split("::")[0]
                if re.match(r"^rift-[a-z0-9-]+/\d", t):
                    continue  # generator version tags, not paths
                if (" " in t or any(c in t for c in "<>|$=(),;") or "…" in t or t in IGNORE_TOKENS
                        or t.startswith("--") or t.startswith("http") or t.startswith("#")):
                    continue
                if "/" not in t and not ext_re.search(t):
                    continue
                if not ("/" in t or ext_re.search(t)):
                    continue
                if t.startswith("("):
                    continue
                if (key, t) in seen:
                    continue
                seen.add((key, t))
                if PROTECTED_RE.search(t):
                    counts["protected_not_stat"] += 1
                    continue
                if is_planned(t):
                    counts["planned"] += 1
                    continue
                variants = expand_braces(t)
                ok = True
                for v in variants:
                    v2 = v.rstrip("/")
                    if v2.startswith("../"):
                        v2 = os.path.normpath(os.path.join("docs", v2)).replace(os.sep, "/")
                    cands2 = [v2]
                    if "/" not in v2 and not v2.startswith("docs"):
                        cands2.append("docs/" + v2)  # bare doc name relative to docs/
                    found = False
                    for c in cands2:
                        if "*" in c:
                            found = bool(glob.glob(os.path.join(REPO, c)))
                        else:
                            found = c in index or os.path.isdir(os.path.join(REPO, c)) or c.rstrip("/") + "/" in {
                                f[:len(c) + 1] for f in index if f.startswith(c.rstrip("/") + "/")}
                        if found:
                            break
                    if not found and "/" not in v2 and v2 in basenames:
                        found = True  # bare file name present somewhere in the repo
                    if not found and "/" in v2 and any(f.endswith("/" + v2) and f.startswith(("src/rift/", "scripts/", "tests/")) for f in index):
                        found = True  # path given relative to src/rift (e.g. cid/evidence.py)
                    if not found:
                        ok = False
                        R.add("FAIL" if not sup else "WARN", "A.path", "%s:%d" % (key, n),
                              "referenced path does not exist and is not in the PLANNED allow-list: `%s`%s"
                              % (v, " (inside SUPERSEDED context)" if sup else ""))
                counts["exists" if ok else "missing"] += 1
        summary[key] = counts
    return summary


# ----------------------------------------------------------------------------------------------------------------
# B. hashes
def load_manifest():
    with open(os.path.join(REPO, MANIFEST)) as f:
        return json.load(f)


def check_hashes(man):
    known = {}
    for rel, v in man["files"].items():
        known[v["sha256"]] = rel
    lock = man["dependency_lock"]["sha256"]
    known[lock] = "dependency lock"
    ho = man.get("heldout_sha256_string_copied_from_independence_report_NOT_RECOMPUTED")
    if ho:
        known[ho] = "held-out SHA-256 STRING (not recomputed)"
    mh = sha256_file(MANIFEST)
    known[mh] = "freeze_manifest.json (file)"
    for rel in ("artifacts/stage4_intervention_results.json",):
        if os.path.exists(os.path.join(REPO, rel)):
            known[sha256_file(rel)] = rel + " (historical, not a V3 input)"
    pathhash = {rel: v["sha256"] for rel, v in man["files"].items()}
    pathhash["reproducibility/requirements-canonical-py39.lock.txt"] = lock
    hex64 = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
    trunc = re.compile(r"(?<![0-9a-f])([0-9a-f]{8})(?:…|\.\.\.)([0-9a-f]{0,6})(?![0-9a-f])")
    tok_re = re.compile(r"`([^`\n]+)`")
    stats = {}
    for key in DOCS:
        s = {"full": 0, "known": 0, "unknown": 0, "line_pairs_checked": 0, "line_pair_mismatch": 0,
             "trunc": 0, "trunc_unmatched": 0}
        for n, raw, sup, _ in line_contexts(read_doc(key)):
            hs = hex64.findall(raw)
            for h in hs:
                s["full"] += 1
                if h in known:
                    s["known"] += 1
                else:
                    s["unknown"] += 1
                    R.add("FAIL", "B.hash", "%s:%d" % (key, n), "64-hex hash not in manifest/lock/held-out string: " + h[:16] + "…")
            paths = [t for t in tok_re.findall(raw) if t in pathhash]
            if len(paths) == 1 and len(hs) == 1:
                s["line_pairs_checked"] += 1
                if pathhash[paths[0]] != hs[0]:
                    if hs[0] in known:
                        s["line_pair_mismatch"] += 1
                        R.add("FAIL", "B.hash", "%s:%d" % (key, n),
                              "hash on this line belongs to %s, not to `%s`" % (known[hs[0]], paths[0]))
            for m in trunc.finditer(raw):
                s["trunc"] += 1
                pre, suf = m.group(1), m.group(2)
                if not any(k.startswith(pre) and k.endswith(suf) for k in known):
                    s["trunc_unmatched"] += 1
                    R.add("FAIL", "B.hash", "%s:%d" % (key, n), "truncated hash %s…%s matches no known hash" % (pre, suf))
        stats[key] = s
    # commit ids
    commit = man["git"]["commit"]
    for key in DOCS:
        for n, raw, sup, _ in line_contexts(read_doc(key)):
            for c in re.findall(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", raw):
                if c != commit and not c.startswith(tuple(known)):
                    if git("cat-file", "-t", c) != "commit":
                        R.add("FAIL", "B.commit", "%s:%d" % (key, n), "40-hex id is not a commit: " + c)
            for c in re.findall(r"`([0-9a-f]{7})`", raw):
                if git("cat-file", "-t", c) != "commit":
                    R.add("WARN", "B.commit", "%s:%d" % (key, n), "short id `%s` is not a commit in this repo" % c)
    return stats, known


# ----------------------------------------------------------------------------------------------------------------
# E. manifest hygiene
def check_manifest(man, known):
    out = {}
    txt = open(os.path.join(REPO, MANIFEST), encoding="utf-8").read()
    mh = sha256_file(MANIFEST)
    out["manifest_sha256"] = mh
    out["n_files"] = len(man["files"])
    if mh in txt:
        R.add("FAIL", "E.manifest", MANIFEST, "manifest contains its own SHA-256 (self-reference)")
    for k in man:
        if "manifest" in k.lower() and "sha" in k.lower():
            R.add("FAIL", "E.manifest", MANIFEST, "manifest has a key that looks like a self-hash claim: " + k)
    if man["files"] and len(man["files"]) != 51:
        R.add("FAIL", "E.manifest", MANIFEST, "expected 51 files, found %d" % len(man["files"]))
    for rel in man["files"]:
        if PROTECTED_RE.search(rel):
            R.add("FAIL", "E.manifest", MANIFEST, "manifest lists a protected path: " + rel)
    sprint_docs = [r for r in man["files"] if r.startswith("docs/SPRINT4_5_")]
    if sprint_docs:
        R.add("FAIL", "E.manifest", MANIFEST, "preregistration docs are listed in the frozen manifest: %s" % sprint_docs)
    docs_in_manifest = [r for r in man["files"] if r.startswith("docs/")]
    out["docs_in_manifest"] = docs_in_manifest
    if docs_in_manifest != ["docs/EVALUATION_PROTOCOL_V2.md"]:
        R.add("WARN", "E.manifest", MANIFEST, "docs in manifest: %s (expected only docs/EVALUATION_PROTOCOL_V2.md)" % docs_in_manifest)
    # all manifest files still match (working tree + HEAD)
    bad = []
    for rel, v in man["files"].items():
        try:
            if sha256_file(rel) != v["sha256"]:
                bad.append(rel)
            head = subprocess.check_output(["git", "show", "HEAD:" + rel], cwd=REPO, stderr=subprocess.DEVNULL)
            if hashlib.sha256(head).hexdigest() != v["sha256"]:
                bad.append(rel + " (HEAD)")
        except Exception as exc:
            bad.append("%s (%s)" % (rel, exc))
    out["frozen_mismatches"] = bad
    if bad:
        R.add("FAIL", "E.freeze", MANIFEST, "frozen files differ from manifest: %s" % bad)
    # docs referenced by the PRE as stating the manifest hash
    pre = "\n".join(read_doc("PRE"))
    m = re.search(r"manifest SHA-256[^`]*`([0-9a-f]{64})`", pre)
    if m:
        out["pre_states_manifest_sha256"] = m.group(1)
        if m.group(1) != mh:
            R.add("FAIL", "E.manifest", "PRE", "PRE states manifest hash %s… but the manifest file now hashes to %s…" % (m.group(1)[:12], mh[:12]))
    # docs must not embed their own hash, nor the hash of a sibling doc
    dh = {k: sha256_file(DOCS[k]) for k in DOCS}
    for k, h in dh.items():
        for k2 in DOCS:
            body = "\n".join(read_doc(k2))
            if h in body or h[:16] in body:
                R.add("FAIL", "E.selfhash", k2, "document %s embeds the SHA-256 of %s (%s)" % (k2, k, "itself" if k == k2 else "a sibling"))
        for k2 in DOCS:
            for n, raw, sup, _ in line_contexts(read_doc(k2)):
                if re.search(r"(this (document|file)['’]s? (own )?(SHA|hash))|hash of this document", raw, re.I):
                    R.add("WARN", "E.selfhash", "%s:%d" % (k2, n), "possible claim that the document contains its own hash")
    out["doc_sha256_current"] = dh
    # frozen doc untouched
    d = git("diff", "--stat", "HEAD", "--", "docs/EVALUATION_PROTOCOL_V2.md")
    if d:
        R.add("FAIL", "E.freeze", "docs/EVALUATION_PROTOCOL_V2.md", "frozen protocol document differs from HEAD")
    return out


# ----------------------------------------------------------------------------------------------------------------
# D. forbidden phrases
FORBID = [(re.compile(r"causally accurate", re.I), "causally accurate"),
          (re.compile(r"production[- ]ready", re.I), "production-ready"),
          (re.compile(r"\bguarantee(s|d)?\b", re.I), "guarantee(s)")]
RULE_CTX = re.compile(r"(not use|never|not used|are not|forbidden|prohibit|language rule|do not|rule|terms|words|"
                      r"no language|without|avoid|does not|must not|nor )", re.I)


def check_phrases():
    res = {}
    for key in DOCS:
        c = {"rule_statements": 0, "affirmative": 0}
        for n, raw, sup, _ in line_contexts(read_doc(key)):
            for rx, name in FORBID:
                if rx.search(raw):
                    if RULE_CTX.search(raw) or re.search(r"[\"“`]%s" % re.escape(name.split("(")[0]), raw, re.I):
                        c["rule_statements"] += 1
                    else:
                        c["affirmative"] += 1
                        R.add("FAIL", "D.language", "%s:%d" % (key, n), "forbidden phrase '%s' not in a rule statement: %s" % (name, raw.strip()[:120]))
        # CANDIDATE-grade must never be called definitive
        for n, raw, sup, _ in line_contexts(read_doc(key)):
            if re.search(r"CANDIDATE", raw) and re.search(r"\bdefinitive\b", raw, re.I) and not re.search(
                    r"(not|never|no)\b[^.]{0,60}\bdefinitive|not definitive|DEFINITIVE-labelled", raw, re.I):
                R.add("WARN", "D.language", "%s:%d" % (key, n), "CANDIDATE and 'definitive' on one line without negation: " + raw.strip()[:120])
        res[key] = c
    return res


# ----------------------------------------------------------------------------------------------------------------
# C. numeric claims
def occ(key, rx, flags=0):
    out = []
    r = re.compile(rx, flags)
    for n, raw, sup, hp in line_contexts(read_doc(key)):
        t = norm(raw)
        for m in r.finditer(t):
            out.append({"doc": key, "line": n, "sup": sup, "text": raw.strip()[:140], "full": norm(raw), "groups": m.groups()})
    return out


CLAIMS = [
    # id, description, must=[(doc, regex)], stale=(regex, allowed-context regex)
    ("N=2000", "confirmatory sample size 2000", [("PRE", r"2000 scenarios|N = 2000"), ("SAP", r"N = 2000"), ("AUD", r"N = 2000"),
                                                  ("DATA", r"N = 2000|\*\*2000\*\*")],
     (r"\bN\s*=\s*800\b|\bTarget N = 800|N=800\b", r"insufficient|not adequate|not used|underpowered|only just|gives|earlier|previous|N = 800 is|N = 800 gives|N = 800 \||54%|0\.54|\bpower\b")),
    ("250 groups", ">= 250 groups, max 25", [("PRE", r"250 groups"), ("SAP", r"250 groups"), ("DATA", r"K\s*(≥|>=)\s*250|250 groups"), ("AUD", r"250 groups")],
     (r"(≥|>=)\s*(1\d\d|2[0-4]\d)\s+groups", None)),
    ("40% / 800 / 1200", "ATTRIBUTE quota 40% = 800 of 2000; 1200 ABSTAIN_REQUIRED", [("PRE", r"800 ATTRIBUTE"), ("PRE", r"1200 ABSTAIN_REQUIRED"), ("PRE", r"40%"),
                                                                                   ("DATA", r"800 \(40\.0%\)"), ("AUD", r"40%")],
     None),
    ("lambda=2", "lambda = 2.0 primary", [("PRE", r"λ = 2\.0"), ("SAP", r"λ = 2\.0"), ("AUD", r"λ = 2"), ("PLAN", r"λ = 2")], None),
    ("gamma=1", "gamma = 1.0 with c = n_do/20", [("PRE", r"γ = 1\.0"), ("SAP", r"γ = 1\.0"), ("AUD", r"γ = 1"), ("PRE", r"n_do,i\s*/\s*20|n_do\s*/\s*20")], None),
    ("kappa=0.05", "kappa = 0.05 per do() == gamma 1", [("PRE", r"κ = 0\.05"), ("AUD", r"κ = 0\.05"), ("SAP", r"γ = 20κ|κ and γ are related")], None),
    ("delta=0.10", "minimum useful effect 0.10", [("PRE", r"δ = 0\.10"), ("AUD", r"δ = 0\.10"), ("SAP", r"δ")], None),
    ("218 cells", "218 = 214 + 4", [("CID", r"218"), ("CID", r"214"), ("AUD", r"218 cells"), ("PLAN", r"218 cells")],
     (r"\b(?!218\b|214\b|210\b)\d{3}\s+(?:simulation |factorial |mixture )?cells\b", None)),
    ("seven estimators", "seven core estimators E0-E6 (+ E7 diagnostic)", [("CID", r"seven core estimators"), ("AUD", r"seven|E0–E6|E0-E6"), ("PLAN", r"seven|E0–E6|E0-E6")],
     (r"\b(six|eight|nine)\s+(core\s+)?estimators", None)),
    ("power 0.90/0.76", "H1 power at N=2000, DEFF 2 / 3", [("PRE", r"0\.90"), ("PRE", r"0\.76"), ("SAP", r"0\.90"), ("SAP", r"0\.76"), ("AUD", r"0\.90"), ("AUD", r"0\.76")], None),
    ("-0.338 CI", "V3 mean U -0.338 CI [-0.465,-0.219]", [("PRE", r"-0\.338"), ("PRE", r"-0\.465,\s*-0\.219"), ("SAP", r"-0\.465,\s*-0\.219"), ("AUD", r"-0\.338"),
                                                        ("AUD", r"-0\.46,\s*-0\.22")],
     (r"-0\.33[0-79]\b", r"π_ref|post-strat|0\.4 →")),
    ("break-even 0.938", "break-even lambda at kappa=0", [("PRE", r"0\.938"), ("AUD", r"0\.938"), ("SAP", r"0\.938")], None),
    ("51 files", "51 frozen files", [("PRE", r"51 files"), ("AUD", r"51"), ("PLAN", r"51")], (r"\b(49|50|52) (files|hashes)\b", None)),
    ("tests", "663 reproducible (clean export); 886 + 2 = 888 (full tree, 4.4.2)", [("PRE", r"663"), ("PRE", r"886"), ("AUD", r"663"), ("AUD", r"886"), ("SAP", r"663"),
                                                                                  ("SAP", r"886"), ("PLAN", r"663"), ("PLAN", r"886")],
     (r"\b880\b", r"outdated|880 figure|earlier figure")),
    ("DEFF 1.37 / K=21", "empirical group DEFF", [("PRE", r"1\.37"), ("SAP", r"1\.37"), ("AUD", r"1\.37")], None),
    ("17 pairs", "17 pairs per split (V2 pair set)", [("PRE", r"17 "), ("AUD", r"17 "), ("DATA", r"17 ")], None),
]


def check_claims():
    res = {}
    for cid, desc, must, stale in CLAIMS:
        entry = {"description": desc, "present": [], "missing": [], "stale": []}
        for doc, rx in must:
            hits = occ(doc, rx)
            if hits:
                entry["present"].append({"doc": doc, "regex": rx, "n": len(hits), "first_line": hits[0]["line"]})
            else:
                entry["missing"].append({"doc": doc, "regex": rx})
                R.add("FAIL", "C.claim", doc, "claim '%s' expected (/%s/) but not found" % (cid, rx))
        if stale:
            rx, ctx = stale
            for doc in DOCS:
                for h in occ(doc, rx):
                    if h["sup"]:
                        continue
                    if ctx and re.search(ctx, h["full"], re.I):
                        continue
                    entry["stale"].append({"doc": doc, "line": h["line"], "text": h["text"]})
                    R.add("FAIL", "C.stale", "%s:%d" % (doc, h["line"]), "possible stale/contradictory variant of '%s': %s" % (cid, h["text"]))
        res[cid] = entry
    # alpha usage: '\u03b1 = 0.05' used for H1 / Holm / primary outside SUPERSEDED context
    for doc in DOCS:
        for h in occ(doc, r"α\s*=\s*0\.05\b"):
            if h["sup"]:
                continue
            if re.search(r"H1|Holm|primary|one-sided", h["text"]) and not re.search(r"per-pair|CID|two-sided|earlier|replace|inconsistent|previous|plan", h["text"], re.I):
                R.add("WARN", "C.alpha", "%s:%d" % (doc, h["line"]), "α = 0.05 in a primary/Holm context (primary is one-sided 0.025): " + h["text"])
    # kappa/gamma swapped
    for doc in DOCS:
        for pat in (r"γ\s*=\s*0\.05\b", r"κ\s*=\s*1(\.0)?\b(?!\d)"):
            for h in occ(doc, pat):
                if not h["sup"]:
                    R.add("FAIL", "C.kappa_gamma", "%s:%d" % (doc, h["line"]), "κ/γ swapped or mis-scaled: " + h["text"])
    # (lambda, kappa|gamma) pairs
    pairs = {}
    for doc in DOCS:
        for h in occ(doc, r"λ\s*=\s*([0-9.]+)\s*[,;]?\s*(?:and\s*)?(κ|γ)\s*=\s*([0-9.]+)"):
            lam, sym, val = h["groups"]
            ok = (float(lam.rstrip(".")) == 2.0 and ((sym == "κ" and float(val.rstrip(".")) == 0.05) or (sym == "γ" and float(val.rstrip(".")) == 1.0)))
            pairs.setdefault(doc, []).append({"line": h["line"], "pair": "λ=%s,%s=%s" % (lam, sym, val), "primary": ok})
    res["_lambda_kappa_pairs"] = pairs
    # usage census
    census = {}
    for doc in DOCS:
        t = norm("\n".join(read_doc(doc)))
        census[doc] = {"kappa": len(re.findall("κ", t)), "gamma": len(re.findall("γ", t))}
    res["_symbol_census"] = census
    return res


# ----------------------------------------------------------------------------------------------------------------
# G. register, labels, question
def check_register():
    out = {}
    d_re = re.compile(r"^\|\s*(D\d+)\s*\|")
    a_re = re.compile(r"^\|\s*([AX]\d+(?:[–-][AX]\d+)?)\s*\|")
    reg = {}

    def expand(tok):
        m = re.fullmatch(r"([AX])(\d+)[–-]\1?(\d+)", tok)
        if m:
            return ["%s%d" % (m.group(1), i) for i in range(int(m.group(2)), int(m.group(3)) + 1)]
        return [tok]

    for key in ("PRE", "AUD"):
        ids = []
        for n, raw, sup, hp in line_contexts(read_doc(key)):
            m = d_re.match(raw) or a_re.match(raw)
            if m and ("ecision" in hp or "register" in hp.lower() or "Decisions" in hp):
                ids.extend(expand(m.group(1)))
        reg[key] = ids
    out["register_ids"] = reg
    if reg["PRE"] and reg["AUD"] and [i for i in reg["PRE"] if i not in reg["AUD"]]:
        R.add("FAIL", "G.register", "PRE vs AUD", "ids in PRE §14 not in AUD register: %s" % [i for i in reg["PRE"] if i not in reg["AUD"]])
    if reg["PRE"] and reg["AUD"] and [i for i in reg["AUD"] if i not in reg["PRE"]]:
        R.add("FAIL", "G.register", "PRE vs AUD", "ids in AUD register not in PRE §14: %s" % [i for i in reg["AUD"] if i not in reg["PRE"]])
    all_ids = set(reg["PRE"]) | set(reg["AUD"])
    max_d = max([int(i[1:]) for i in all_ids if i.startswith("D")] or [0])
    # every D-id mentioned anywhere must exist in the register
    for key in DOCS:
        for n, raw, sup, _ in line_contexts(read_doc(key)):
            for m in re.finditer(r"\bD(\d{1,2})\b", raw):
                if int(m.group(1)) > max_d or int(m.group(1)) < 1:
                    R.add("WARN", "G.register", "%s:%d" % (key, n), "D%s referenced but not in register (max D%d)" % (m.group(1), max_d))
    # classification counts in AUD register vs PRE status block
    cls_re = re.compile(r"\b(BLOCKER|MUST FIX|REQUIRES RESEARCHER APPROVAL|ACCEPTED LIMITATION|INFORMATIONAL)\b")
    counts = {}
    for n, raw, sup, hp in line_contexts(read_doc("AUD")):
        m = d_re.match(raw) or a_re.match(raw)
        if m and "ecision register" in hp:
            c = cls_re.findall(raw)
            if len(c) != 1:
                R.add("FAIL", "G.register", "AUD:%d" % n, "register row %s must carry exactly one classification" % m.group(1))
            else:
                counts[c[0]] = counts.get(c[0], 0) + 1
    out["classification_counts_from_AUD_register"] = counts
    out["register_rows"] = sum(counts.values())
    m_rows = re.search(r"(\d+) rows", "\n".join(read_doc("PRE")))
    if not m_rows or int(m_rows.group(1)) != sum(counts.values()):
        R.add("FAIL", "G.register", "PRE status block", "row count: AUD register has %d, PRE says %s" % (sum(counts.values()), m_rows.group(1) if m_rows else "absent"))
    pre_txt = "\n".join(read_doc("PRE"))
    for cls, cnt in counts.items():
        m = re.search(r"%s\W{0,6}(\d+)" % re.escape(cls), pre_txt)
        if not m or int(m.group(1)) != cnt:
            R.add("FAIL", "G.register", "PRE status block", "classification count for %s: AUD register says %d, PRE says %s" % (cls, cnt, m.group(1) if m else "absent"))
    return out


def label_of(lo, hi, th, op_lo, delta=0.10):
    """The PRE section 10 rule, written as code so exhaustiveness can be enumerated."""
    hits = []
    if lo > 0 and th >= delta and op_lo > 0:
        hits.append("POSITIVE-USEFUL")
    if lo > 0 and (th < delta or op_lo <= 0):
        hits.append("POSITIVE-SUBSTANDARD")
    if hi < 0:
        hits.append("NEGATIVE-WORSE")
    if lo <= 0 <= hi and hi < delta:
        hits.append("NEGATIVE-NO-USEFUL-EFFECT")
    if lo <= 0 and hi >= delta:
        hits.append("INCONCLUSIVE")
    return hits


def check_label_logic():
    """Enumerate a grid of (lo, hi, theta, op_lo) with lo <= theta <= hi; every point must get exactly one label."""
    vals = [-0.5, -0.1, -0.0001, 0.0, 0.0001, 0.05, 0.0999, 0.10, 0.1001, 0.3, 0.8]
    n = bad = 0
    examples = []
    for lo in vals:
        for hi in vals:
            if hi < lo:
                continue
            for th in vals:
                if not (lo <= th <= hi):
                    continue
                for op in vals:
                    n += 1
                    h = label_of(lo, hi, th, op)
                    if len(h) != 1:
                        bad += 1
                        if len(examples) < 5:
                            examples.append({"lo": lo, "hi": hi, "theta": th, "op_lo": op, "labels": h})
    if bad:
        R.add("FAIL", "G.labels", "PRE section 10", "interpretation rows are not exhaustive/exclusive on %d of %d grid points, e.g. %s" % (bad, n, examples))
    return {"grid_points": n, "violations": bad, "examples": examples}


LABELS = ["POSITIVE-USEFUL", "POSITIVE-SUBSTANDARD", "NEGATIVE-WORSE", "NEGATIVE-NO-USEFUL-EFFECT", "INCONCLUSIVE"]


def check_labels_question():
    out = {"label_logic": check_label_logic()}
    for key in ("PRE", "SAP"):
        t = "\n".join(read_doc(key))
        for lab in LABELS:
            if lab not in t:
                R.add("FAIL", "G.labels", key, "label %s absent" % lab)
        extra = set(re.findall(r"\b(?:POSITIVE|NEGATIVE)-[A-Z-]+\b", t)) - set(LABELS)
        if extra:
            R.add("FAIL", "G.labels", key, "unknown label tokens: %s" % sorted(extra))
    # research question wording
    q = {}
    for key in DOCS:
        t = " ".join(norm("\n".join(read_doc(key))).split())
        m = re.search(r"(Does frozen RIFT-FULL-V3 [^?]*\?)", t)
        if m:
            q[key] = re.sub(r"\*+", "", m.group(1))
    out["question_by_doc"] = q
    ref = q.get("PRE")
    for key, text in q.items():
        if ref and text != ref:
            R.add("FAIL", "G.question", key, "research-question wording differs from PRE: " + text[:200])
    # H5 / exploratory never confirmatory
    for key in DOCS:
        for n, raw, sup, _ in line_contexts(read_doc(key)):
            if re.search(r"\bH5\b", raw) and re.search(r"confirmatory", raw) and not re.search(
                    r"not confirmatory|exploratory|descriptive|diagnostic|no inferential|no claim|non-confirmatory|never presented", raw, re.I):
                R.add("WARN", "G.exploratory", "%s:%d" % (key, n), "H5 on a line mentioning 'confirmatory' without an exploratory qualifier: " + raw.strip()[:120])
    return out


# ----------------------------------------------------------------------------------------------------------------
# F. evidence checks
def phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def zq(p):  # upper-tail quantile via bisection (no scipy dependency)
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if phi(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def power(mu, sd, n, deff, a):
    return phi(mu / (sd * math.sqrt(deff / float(n))) - zq(1 - a))


def n_req(sd, delta, deff, a, pw):
    return int(math.ceil(((zq(1 - a) + zq(pw)) * sd / delta) ** 2 * deff))


def parse_power_tables(key):
    """rows: | N | d1 | d2 | d3 |   (AUD)   or  | N | mu | d1 | d2 | d3 |   (SAP)"""
    rows = []
    for n, raw, sup, hp in line_contexts(read_doc(key)):
        cells = [c.strip().strip("*").replace(",", "") for c in raw.strip().strip("|").split("|")]
        if raw.strip().startswith("|") and cells and re.fullmatch(r"\d{3,4}", cells[0]):
            vals = []
            for c in cells[1:]:
                try:
                    vals.append(float(c))
                except ValueError:
                    vals.append(None)
            rows.append((n, int(cells[0]), vals, hp))
    return rows


def check_evidence():
    out = {}
    a1 = json.load(open(os.path.join(REPO, "artifacts/sprint4_5_0/prereg_audit/audit.json")))
    a2 = json.load(open(os.path.join(REPO, "artifacts/sprint4_5_0/prereg_audit/audit_part2.json")))
    sd = a1["power"]["sd_pooled_V3_lam2_kap0.05"]
    sd2 = a2["G_power"]["sd_V3_minus_V2_utility"]
    ev = {"sd_V3": sd, "sd_V3_minus_V2": sd2}
    # primary result
    p = a1["primary_candidate_parameters"]["lam=2.0,kap=0.05"]
    chk = []

    def cmp(name, doc_val, true_val, tol):
        ok = abs(doc_val - true_val) <= tol
        chk.append({"name": name, "doc": doc_val, "recomputed": true_val, "ok": ok})
        if not ok:
            R.add("FAIL", "F.evidence", name, "doc says %s, recomputed %s" % (doc_val, true_val))

    cmp("V3 mean U (λ=2,κ=0.05)", -0.338, p["mean"], 0.0006)
    cmp("V3 CI lo", -0.465, p["ci95_template_cluster"][0], 0.0006)
    cmp("V3 CI hi", -0.219, p["ci95_template_cluster"][1], 0.0006)
    cmp("V2 mean U", -0.562, p["V2_mean"], 0.0006)
    cmp("V3-V2", 0.224, p["V3_minus_V2"][0], 0.0006)
    cmp("V3-V2 CI lo", 0.085, p["V3_minus_V2"][1][0], 0.0006)
    cmp("V3-V2 CI hi", 0.365, p["V3_minus_V2"][1][1], 0.0006)
    be = a1["break_even_lambda"]["V3-FULL"]
    for k, (l, lo, hi) in {"kappa=0.0": (0.938, 0.61, 1.42), "kappa=0.025": (0.582, 0.31, 0.97), "kappa=0.05": (0.227, 0.00, 0.54)}.items():
        cmp("λ* %s" % k, l, be[k]["lambda_star"], 0.0006)
        cmp("λ* %s lo" % k, lo, be[k]["ci95_template_cluster"][0], 0.0051)
        cmp("λ* %s hi" % k, hi, be[k]["ci95_template_cluster"][1], 0.0051)
    cmp("DEFF union-find", 1.37, a2["C_union_find_group_clustering"]["deff_empirical"], 0.0051)
    cmp("DEFF topology", 1.07, a2["C_topology_hash_clustering"]["deff_empirical"], 0.0051)
    cmp("ICC template", 0.027, a1["clustering_at_V3_lam2_kap0.05"]["template"]["icc"], 0.0006)
    cmp("DEFF template", 1.06, a1["clustering_at_V3_lam2_kap0.05"]["template"]["deff_empirical_at_observed_cluster_sizes"], 0.0051)
    cmp("DEFF structure", 2.21, a1["clustering_at_V3_lam2_kap0.05"]["structure"]["deff_empirical_at_observed_cluster_sizes"], 0.0051)
    pp = a2["G_prior_predictive_from_dev_val_bootstrap"]
    cmp("P(U>0) λ=0.5", 0.043, pp["lam=0.5,kap=0.05"]["P(bootstrap_mean_U>0)"], 0.0006)
    cmp("P(U>0) λ=0.75", 0.002, pp["lam=0.75,kap=0.05"]["P(bootstrap_mean_U>0)"], 0.0006)
    A = a2["A_strata_and_post_stratification"]["V3-FULL|lam=2.0,kap=0.05"]
    cmp("break-even prevalence (2,0.05)", 0.885, A["break_even_prevalence"], 0.0006)
    cmp("break-even prevalence (1,0.05)", 0.666, a2["A_strata_and_post_stratification"]["V3-FULL|lam=1.0,kap=0.05"]["break_even_prevalence"], 0.0006)
    cmp("break-even prevalence (2,0)", 0.663, a2["A_strata_and_post_stratification"]["V3-FULL|lam=2.0,kap=0.0"]["break_even_prevalence"], 0.0006)
    cmp("operational V3 λ=1", -0.076, a2["B_operational_unsafe_definition"]["V3-FULL"]["U_operational"]["lam=1.0"], 0.0006)
    cmp("operational V3 λ=2", -0.195, a2["B_operational_unsafe_definition"]["V3-FULL"]["U_operational"]["lam=2.0"], 0.0006)
    cmp("operational V3 λ=4", -0.433, a2["B_operational_unsafe_definition"]["V3-FULL"]["U_operational"]["lam=4.0"], 0.0006)
    # closed-form power
    pw = {}
    cmp("power N=800 DEFF1", 0.83, power(0.10, sd, 800, 1.0, 0.025), 0.0051)
    cmp("power N=800 DEFF1.5", 0.66, power(0.10, sd, 800, 1.5, 0.025), 0.0051)
    cmp("power N=800 DEFF2", 0.54, power(0.10, sd, 800, 2.0, 0.025), 0.0051)
    cmp("power N=2000 DEFF2", 0.90, power(0.10, sd, 2000, 2.0, 0.025), 0.0051)
    cmp("power N=2000 DEFF3", 0.76, power(0.10, sd, 2000, 3.0, 0.025), 0.0051)
    cmp("power N=2000 DEFF1.5 (2 d.p.)", 0.96, power(0.10, sd, 2000, 1.5, 0.025), 0.0051)
    cmp("power SD1.17 N=800 DEFF2", 0.40, power(0.10, 1.17, 800, 2.0, 0.025), 0.0051)
    cmp("power SD1.17 N=2000 DEFF2", 0.77, power(0.10, 1.17, 2000, 2.0, 0.025), 0.0051)
    cmp("power Holm m4 N=2000 DEFF2", 0.78, power(0.10, sd, 2000, 2.0, 0.00625), 0.0051)
    cmp("MDE80 N=2000 DEFF2", 0.086, (zq(0.975) + zq(0.8)) * sd * math.sqrt(2.0 / 2000), 0.0006)
    cmp("MDE80 N=2000 DEFF3", 0.105, (zq(0.975) + zq(0.8)) * sd * math.sqrt(3.0 / 2000), 0.0006)
    cmp("MDE80 N=800 DEFF2", 0.136, (zq(0.975) + zq(0.8)) * sd * math.sqrt(2.0 / 800), 0.0006)
    for dl, df, pwr, want in [(0.10, 1.0, 0.8, 738), (0.10, 1.5, 0.8, 1106), (0.10, 2.0, 0.8, 1475), (0.10, 3.0, 0.8, 2212),
                              (0.10, 1.0, 0.9, 987), (0.10, 1.5, 0.9, 1481), (0.10, 2.0, 0.9, 1974)]:
        got = n_req(sd, dl, df, 0.025, pwr)
        cmp("N req δ=%s DEFF=%s power=%s" % (dl, df, pwr), want, got, 1)
    # negative-case sample sizes (SAP 6.5): hi<0 at 80% power, DEFF2
    mu = abs(p["mean"])
    cmp("N to exclude 0 (DEFF 2)", 130, ((zq(0.975) + zq(0.8)) * sd / mu) ** 2 * 2.0, 2)
    cmp("N to exclude δ (DEFF 2)", 77, ((zq(0.975) + zq(0.8)) * sd / (mu + 0.10)) ** 2 * 2.0, 2)
    # H2 power (Holm first step 0.025/3)
    a_h = 0.025 / 3.0
    cmp("H2 full DEFF2", 1.00, power(0.224, sd2, 2000, 2.0, a_h), 0.0051)
    cmp("H2 half DEFF2", 0.79, power(0.112, sd2, 2000, 2.0, a_h), 0.0051)
    cmp("H2 0.10 DEFF2", 0.67, power(0.10, sd2, 2000, 2.0, a_h), 0.0051)
    cmp("H2 0.05 DEFF2", 0.17, power(0.05, sd2, 2000, 2.0, a_h), 0.0051)
    cmp("H2 half DEFF3", 0.58, power(0.112, sd2, 2000, 3.0, a_h), 0.0051)
    cmp("H2 0.10 DEFF3", 0.47, power(0.10, sd2, 2000, 3.0, a_h), 0.0051)
    # H4 (McNemar normal approximation on effective discordant pairs = N_attr/DEFF)
    def mc(n_attr, disc, plus, deff, alpha_tail):
        nd = n_attr * disc / deff
        z = zq(1 - alpha_tail)
        return 1 - phi((z - (2 * plus - 1) * math.sqrt(nd)) / (2 * math.sqrt(plus * (1 - plus))))
    disc4 = 29.0 / 99.0
    plus_full = 19.0 / 29.0
    plus_half = 0.5 + (plus_full - 0.5) / 2.0
    cmp("H4 full (DEFF2 on n_attr)", 0.85, mc(800, disc4, plus_full, 2.0, a_h), 0.0051)
    # Sprint 4.5.1 (revision 3): documents now state 0.23 (recomputed 0.2348); 0.24 was a rounding error in the earlier drafts.
    cmp("H4 half (DEFF2 on n_attr)", 0.23, mc(800, disc4, plus_half, 2.0, a_h), 0.0051)
    out["checks"] = chk
    out["n_checks"] = len(chk)
    out["n_failed"] = sum(1 for c in chk if not c["ok"])
    # parse and compare the power tables in AUD §4.1 and SAP §6.3
    tab = []
    for key in ("AUD", "SAP"):
        for n, N, vals, hp in parse_power_tables(key):
            if key == "AUD":
                mu_, cols = 0.10, vals
            else:
                mu_, cols = (vals[0] if vals else 0.10), vals[1:]
            if "Sample" not in hp and "6." not in hp and "power" not in hp.lower() and "4." not in hp:
                continue
            for df, v in zip((1.5, 2.0, 3.0), cols):
                if v is None:
                    continue
                t = power(mu_, sd, N, df, 0.025)
                ok = abs(round(t, 3 if v * 1000 % 10 else 2) - v) <= 0.0051 + 0.0005
                tab.append({"doc": key, "line": n, "N": N, "mu": mu_, "deff": df, "doc_value": v, "recomputed": round(t, 4), "ok": ok})
                if not ok:
                    R.add("FAIL", "F.powertable", "%s:%d" % (key, n), "N=%d μ=%s DEFF=%s: doc %.3f vs recomputed %.4f" % (N, mu_, df, v, t))
    out["power_table_cells"] = tab
    out["power_table_cells_checked"] = len(tab)
    return out


# ----------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit non-zero on WARN as well")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    for k, p in DOCS.items():
        if not os.path.exists(os.path.join(REPO, p)):
            print("missing doc", p)
            return 2
    man = load_manifest()
    index = repo_index()
    result = {"docs": DOCS, "manifest": MANIFEST}
    result["A_paths"] = check_paths(index)
    hs, known = check_hashes(man)
    result["B_hashes"] = hs
    result["E_manifest"] = check_manifest(man, known)
    result["C_claims"] = check_claims()
    result["D_language"] = check_phrases()
    result["G_register"] = check_register()
    result["G_labels_question"] = check_labels_question()
    result["F_evidence"] = check_evidence()
    result["findings"] = R.items
    result["totals"] = {lvl: R.count(lvl) for lvl in ("FAIL", "WARN", "INFO")}
    result["git_head"] = git("rev-parse", "HEAD")
    with open(os.path.join(OUT_DIR, "consistency_report.json"), "w") as f:
        json.dump(result, f, indent=1, sort_keys=True, default=str)
    lines = ["# Sprint 4.5.1 document consistency report (generated)", "",
             "Re-run: `python3 scripts/sprint451_doc_consistency_check.py [--strict]`", "",
             "HEAD `%s`; FAIL %d, WARN %d" % (result["git_head"], result["totals"]["FAIL"], result["totals"]["WARN"]), "",
             "## Path check", ""]
    for k, c in result["A_paths"].items():
        lines.append("* %s: %s" % (k, c))
    lines += ["", "## Hash check", ""]
    for k, c in result["B_hashes"].items():
        lines.append("* %s: %s" % (k, c))
    lines += ["", "## Manifest", "", "* sha256 %s; files %d; frozen mismatches %s" % (
        result["E_manifest"]["manifest_sha256"], result["E_manifest"]["n_files"], result["E_manifest"]["frozen_mismatches"])]
    lines += ["", "## Evidence checks: %d recomputed, %d failed; power-table cells compared %d" % (
        result["F_evidence"]["n_checks"], result["F_evidence"]["n_failed"], result["F_evidence"]["power_table_cells_checked"])]
    lines += ["", "## Findings", ""]
    if not R.items:
        lines.append("none")
    for it in R.items:
        lines.append("* **%s** [%s] %s - %s" % (it["level"], it["check"], it["where"], it["message"]))
    with open(os.path.join(OUT_DIR, "consistency_report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if result["totals"]["FAIL"] or (args.strict and result["totals"]["WARN"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
