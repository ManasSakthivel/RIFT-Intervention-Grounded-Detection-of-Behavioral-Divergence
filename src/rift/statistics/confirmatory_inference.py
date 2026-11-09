"""Cluster-aware inference for the RIFT confirmatory design (SAP sections 3-5, 7).

Design: S fixed structure strata (16) x F fixed fault families (16); each (structure, family) cell is one generator
template (the "group"); scenarios are nested in templates.  Paired differences d_i are analysed with

  * stratified ratio estimator   theta = sum_s W_s * mean_s,  W_s = n_s / N (fixed, never resampled)
  * template-stratified bootstrap-t  (PRIMARY per SAP 3):  groups resampled with replacement WITHIN each structure
  * family-block bootstrap-t         (MANDATORY SENSITIVITY per SAP 3.1, D19):  the F family columns are resampled
    as clusters (each carries its templates in every structure), weights fixed

This module is pure computation on arrays.  It performs no file I/O and never reads any dataset: confirmatory-mode
code can import it without being able to reach development or validation data (checked by a unit test).

One-sided p for H0: mu <= 0 is  p = (1 + #{b: t*_b >= theta/se}) / (B_valid + 1).
95% studentised CI = [theta - q_.975(t*) * se,  theta - q_.025(t*) * se].
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

ALPHA = 0.025          # one-sided (SAP 5)
DELTA = 0.10           # minimum useful effect (PRE 10)
DEFAULT_B = 20000      # SAP 3
SEED_TEMPLATE = 4505   # SAP 3
SEED_FAMILY = 4506     # SAP 3


@dataclass
class InferenceResult:
    method: str
    theta: float
    se: float
    p: float                      # one-sided, H0: mu <= 0
    lo: float                     # studentised 95% CI
    hi: float
    pct_lo: float                 # percentile bootstrap 95% CI (sensitivity)
    pct_hi: float
    n: int
    n_clusters: int
    B: int
    B_valid: int
    extra: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        return dict(self.__dict__)


def _codes(x) -> np.ndarray:
    return np.unique(np.asarray(x), return_inverse=True)[1]


class FixedStrataDesign:
    """Index structure of one analysis table.  `group` ids need only be unique within a stratum."""

    def __init__(self, stratum, group, family=None):
        stratum = np.asarray(stratum)
        group = np.asarray(group)
        if len(stratum) != len(group):
            raise ValueError("stratum and group must have equal length")
        self.n = len(stratum)
        si = _codes(stratum)
        gj = _codes(group)
        key = si.astype(np.int64) * (gj.max() + 1) + gj
        _, gi = np.unique(key, return_inverse=True)
        self.S = int(si.max() + 1)
        self.si = si
        self.gi = gi
        self.G = int(gi.max() + 1)
        self.sg = np.zeros(self.G, dtype=int)
        self.sg[gi] = si
        self.ng = np.bincount(gi).astype(float)
        self.members = [np.where(self.sg == s)[0] for s in range(self.S)]
        if any(len(m) < 2 for m in self.members):
            raise ValueError("every stratum needs >= 2 groups for a CR1 variance")
        self.Ns = np.bincount(si, minlength=self.S).astype(float)
        self.W = self.Ns / self.Ns.sum()
        if family is not None:
            family = np.asarray(family)
            if len(family) != self.n:
                raise ValueError("family must align with stratum")
            self.fi = _codes(family)
            self.F = int(self.fi.max() + 1)
            if self.F < 2:
                raise ValueError("family-block inference needs >= 2 families")
            self.cell = si.astype(np.int64) * self.F + self.fi
        else:
            self.fi = None
            self.F = 0
            self.cell = None

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _finish(method, theta, se, tstar, thstar, n, K, B, extra=None) -> InferenceResult:
        ok = np.isfinite(tstar)
        t = tstar[ok]
        if se <= 0 or len(t) == 0:
            return InferenceResult(method, float(theta), float(se), 1.0, float(theta), float(theta), float(theta),
                                   float(theta), n, K, B, int(len(t)), extra or {})
        p = (1 + np.sum(t >= theta / se)) / (len(t) + 1)
        q_lo, q_hi = np.quantile(t, [0.025, 0.975])
        pl, ph = np.quantile(thstar[ok], [0.025, 0.975])
        return InferenceResult(method, float(theta), float(se), float(p), float(theta - q_hi * se),
                               float(theta - q_lo * se), float(pl), float(ph), n, K, B, int(len(t)), extra or {})

    # ---------------------------------------------------------------- primary: template-stratified
    def template_bootstrap_t(self, d, B: int = DEFAULT_B, rng: Optional[np.random.Generator] = None,
                             seed: int = SEED_TEMPLATE) -> InferenceResult:
        d = np.asarray(d, dtype=float)
        if len(d) != self.n:
            raise ValueError("d length mismatch")
        rng = rng if rng is not None else np.random.default_rng(seed)
        Sg = np.bincount(self.gi, weights=d, minlength=self.G)
        ng = self.ng
        th_s = np.array([Sg[m].sum() / ng[m].sum() for m in self.members])
        theta = float(np.sum(self.W * th_s))
        var = 0.0
        for s, m in enumerate(self.members):
            K = len(m)
            r = Sg[m] - th_s[s] * ng[m]
            var += self.W[s] ** 2 * (K / (K - 1)) * np.sum(r ** 2) / ng[m].sum() ** 2
        se = float(np.sqrt(var))
        thb = np.zeros(B)
        varb = np.zeros(B)
        for s, m in enumerate(self.members):
            K = len(m)
            pick = m[rng.integers(0, K, size=(B, K))]
            Sb, nb = Sg[pick], ng[pick]
            ths = Sb.sum(1) / nb.sum(1)
            thb += self.W[s] * ths
            rb = Sb - ths[:, None] * nb
            varb += self.W[s] ** 2 * (K / (K - 1)) * np.sum(rb ** 2, axis=1) / nb.sum(1) ** 2
        seb = np.sqrt(varb)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(seb > 0, (thb - theta) / seb, np.nan)
        return self._finish("template_stratified_bootstrap_t", theta, se, t, thb, self.n, self.G, B)

    # ---------------------------------------------------------------- mandatory sensitivity: family-block
    def family_block_bootstrap_t(self, d, B: int = DEFAULT_B, rng: Optional[np.random.Generator] = None,
                                 seed: int = SEED_FAMILY) -> InferenceResult:
        if self.cell is None:
            raise ValueError("design was built without a family vector")
        d = np.asarray(d, dtype=float)
        if len(d) != self.n:
            raise ValueError("d length mismatch")
        rng = rng if rng is not None else np.random.default_rng(seed)
        S, F = self.S, self.F
        Ssf = np.bincount(self.cell, weights=d, minlength=S * F).reshape(S, F)
        nsf = np.bincount(self.cell, minlength=S * F).reshape(S, F).astype(float)
        Ns = nsf.sum(1)
        th_s = Ssf.sum(1) / Ns
        theta = float(np.sum(self.W * th_s))
        r_f = np.sum(self.W[:, None] * (Ssf - th_s[:, None] * nsf) / Ns[:, None], axis=0)
        se = float(np.sqrt(F / (F - 1) * np.sum(r_f ** 2)))
        pick = rng.integers(0, F, size=(B, F))
        Sb = Ssf[:, pick]                    # (S, B, F)
        nb = nsf[:, pick]
        Nb = nb.sum(2)                       # (S, B) replicate stratum totals
        valid = (Nb > 0).all(axis=0)
        Nsafe = np.where(Nb > 0, Nb, 1.0)
        ths = Sb.sum(2) / Nsafe
        thb = np.sum(self.W[:, None] * ths, axis=0)
        rb = np.sum(self.W[:, None, None] * (Sb - ths[:, :, None] * nb) / Nsafe[:, :, None], axis=0)   # (B, F)
        seb = np.sqrt(F / (F - 1) * np.sum(rb ** 2, axis=1))
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(valid & (seb > 0), (thb - theta) / seb, np.nan)
        return self._finish("family_block_bootstrap_t", theta, se, t, thb, self.n, F, B)


# ------------------------------------------------------------------------------------------------ convenience wrappers
def stratified_template_bootstrap_t(d, stratum, group, B=DEFAULT_B, seed=SEED_TEMPLATE, rng=None) -> InferenceResult:
    return FixedStrataDesign(stratum, group).template_bootstrap_t(d, B=B, rng=rng, seed=seed)


def family_block_bootstrap_t(d, stratum, group, family, B=DEFAULT_B, seed=SEED_FAMILY, rng=None) -> InferenceResult:
    return FixedStrataDesign(stratum, group, family).family_block_bootstrap_t(d, B=B, rng=rng, seed=seed)


# ------------------------------------------------------------------------------------------------ decision machinery
def interpret(lo: float, hi: float, theta: float, op_lo: float, delta: float = DELTA) -> str:
    """PRE section 10 as a pure function.  Rows are exhaustive and mutually exclusive."""
    if hi < 0:
        return "NEGATIVE-WORSE"
    if lo > 0:
        return "POSITIVE-USEFUL" if (theta >= delta and op_lo > 0) else "POSITIVE-SUBSTANDARD"
    if hi < delta:
        return "NEGATIVE-NO-USEFUL-EFFECT"
    return "INCONCLUSIVE"


def interpret_two_key(primary: InferenceResult, family: InferenceResult, op_primary: InferenceResult,
                      op_family: InferenceResult, delta: float = DELTA) -> Dict[str, object]:
    """Proposed D19 option C ("hull rule", requires owner approval): the label is computed on the HULL of the two
    studentised intervals, lo = min(lo_T, lo_F), hi = max(hi_T, hi_F).  A positive label needs BOTH intervals above 0,
    a NEGATIVE-WORSE label needs BOTH below 0.  Size is bounded by the family-block test's size."""
    lo = min(primary.lo, family.lo)
    hi = max(primary.hi, family.hi)
    op_lo = min(op_primary.lo, op_family.lo)
    theta = primary.theta
    return {"lo": lo, "hi": hi, "theta": theta, "op_lo": op_lo, "label": interpret(lo, hi, theta, op_lo, delta),
            "label_template_only": interpret(primary.lo, primary.hi, primary.theta, op_primary.lo, delta),
            "label_family_only": interpret(family.lo, family.hi, family.theta, op_family.lo, delta),
            "robust_to_family_dependence": bool((primary.lo > 0) == (family.lo > 0))}


def holm_adjust(pvals: Dict[str, float]) -> Dict[str, float]:
    """Holm step-down adjusted p-values (monotone, capped at 1)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out: Dict[str, float] = {}
    run = 0.0
    for j, (k, p) in enumerate(items):
        run = max(run, (m - j) * p)
        out[k] = min(1.0, run)
    return out


def gatekeep(p1: float, secondary: Dict[str, float], alpha: float = ALPHA) -> Dict[str, object]:
    """Fixed-sequence gate (SAP 5): H1 at full alpha; only if rejected, Holm over the secondary family at total alpha."""
    h1 = p1 < alpha
    adj = holm_adjust(secondary) if secondary else {}
    return {"H1_rejected": bool(h1), "holm_adjusted": adj,
            "secondary_rejected": sorted(k for k, v in adj.items() if v < alpha) if h1 else [],
            "secondary_status": "confirmatory" if h1 else "descriptive, not confirmatory"}


def mcnemar_exact(n10: int, n01: int) -> Dict[str, float]:
    """Exact two-sided McNemar on discordant pairs plus mid-p.  Ignores clustering: supporting evidence only (SAP 4)."""
    from scipy.stats import binom, binomtest
    nd = n10 + n01
    if nd == 0:
        return {"n_discordant": 0, "p_two_sided": 1.0, "p_mid": 1.0}
    k = min(n10, n01)
    p2 = float(binomtest(k, nd, 0.5, alternative="two-sided").pvalue)
    pmf = float(binom.pmf(k, nd, 0.5))
    return {"n_discordant": nd, "p_two_sided": min(1.0, p2), "p_mid": float(max(0.0, min(1.0, p2 - pmf)))}


def normal_power(N: float, mu: float, sd: float, deff: float, alpha: float = ALPHA) -> float:
    """Closed-form optimistic power (SAP 6.2); an upper bound for the bootstrap-t."""
    from scipy.stats import norm
    return float(1.0 - norm.cdf(norm.ppf(1 - alpha) - mu / (sd * np.sqrt(deff / N))))


def utility(correct, unsafe, n_do, lam: float = 2.0, gamma: float = 1.0, max_do: int = 20) -> np.ndarray:
    """U_i = C_i - lambda S_i - gamma n_do_i / max_do   (PRE 3.1).  Always-abstain scores identically 0."""
    c = np.asarray(correct, dtype=float)
    s = np.asarray(unsafe, dtype=float)
    n = np.asarray(n_do, dtype=float)
    return c - lam * s - gamma * n / max_do


def check_utility_invariants(u_by_method: Dict[str, np.ndarray], lam: float = 2.0, gamma: float = 1.0) -> List[str]:
    """Pre-analysis abort conditions (PRE 3.1): U_AA == 0 and U in [-(lam+gamma), 1].  Returns violations."""
    bad = []
    aa = u_by_method.get("ALWAYS-ABSTAIN")
    if aa is not None and np.any(np.asarray(aa) != 0):
        bad.append("ALWAYS-ABSTAIN utility is not identically 0")
    for k, u in u_by_method.items():
        u = np.asarray(u)
        if np.any(u < -(lam + gamma) - 1e-12) or np.any(u > 1 + 1e-12):
            bad.append(f"{k}: utility outside [-(lambda+gamma), 1]")
    return bad
