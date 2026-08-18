"""
RIFT Identifiability — Test Suite (Phase 3F)
Authority: docs/PHASE_3_SPEC_FREEZE.md Section 4

Ground-truth test cases:
  TC-1  Simple chain X→Y (no confounders)            → IDENTIFIABLE / BACKDOOR / Z=[]
  TC-2  Backdoor path X←Z→Y, Z observed              → IDENTIFIABLE / BACKDOOR / Z=[Z]
  TC-3  Hidden confounder X↔Y only                   → NOT_IDENTIFIABLE / ABSTAIN
  TC-4  Mediated X→M→Y with hidden X↔Y               → IDENTIFIABLE / FRONT_DOOR / M=[M]
  TC-5  PAG ambiguity o→ edge on causal path          → CONDITIONALLY_IDENTIFIABLE
  TC-6  Full non-identifiable (bidirected + no mediator) → NOT_IDENTIFIABLE / ABSTAIN

ABSTAIN invariant verified for every NOT_IDENTIFIABLE result:
  result.abstains == True
  result.adjustment_set is None
  result.method == IdentificationMethod.ABSTAIN
"""

import pytest

from rift.identifiability import (
    IdentificationMethod,
    IdentifiabilityResult,
    IdentifiabilityStatus,
    PAGEdge,
    PAGEdgeType,
    PAGResult,
    check_backdoor,
    check_frontdoor,
    identify_query,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pag(variables, edges, observed=None):
    """Convenience constructor."""
    if observed is None:
        observed = list(variables)
    return PAGResult(variables=list(variables), edges=list(edges), observed_variables=list(observed))


def directed(src, tgt):
    return PAGEdge(src, tgt, PAGEdgeType.DIRECTED)


def bidirected(src, tgt):
    return PAGEdge(src, tgt, PAGEdgeType.BIDIRECTED)


def partial(src, tgt):
    """o→ edge."""
    return PAGEdge(src, tgt, PAGEdgeType.PARTIALLY_DIRECTED)


def undirected(src, tgt):
    """o-o edge."""
    return PAGEdge(src, tgt, PAGEdgeType.UNDIRECTED)


def assert_abstain(result: IdentifiabilityResult) -> None:
    """Assert the full ABSTAIN contract for NOT_IDENTIFIABLE results."""
    assert result.abstains is True, "abstains property must be True"
    assert result.status == IdentifiabilityStatus.NOT_IDENTIFIABLE
    assert result.method == IdentificationMethod.ABSTAIN
    assert result.adjustment_set is None, "no adjustment set should be returned when abstaining"
    assert result.blocking_reason is not None and len(result.blocking_reason) > 0, (
        "blocking_reason must explain why RIFT abstains"
    )


# ===========================================================================
# TC-1: Simple chain X → Y — no confounders
# ===========================================================================
# Ground truth: IDENTIFIABLE via backdoor with empty adjustment set.
# There are no backdoor paths into X, so Z = [] satisfies the criterion.
# ===========================================================================


class TestTC1SimpleChain:
    """TC-1: X → Y with no confounders."""

    VARS = ["X", "Y"]
    EDGES = [directed("X", "Y")]
    OBSERVED = ["X", "Y"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_check_backdoor_returns_empty_set(self):
        adj = check_backdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert adj == [], f"Expected empty adjustment set, got {adj!r}"

    def test_identify_query_identifiable(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.status == IdentifiabilityStatus.IDENTIFIABLE
        assert result.method == IdentificationMethod.BACKDOOR
        assert result.adjustment_set == []
        assert not result.abstains

    def test_identify_query_no_blocking_reason(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.blocking_reason is None

    def test_identify_query_fields(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.query_source == "X"
        assert result.query_target == "Y"


# ===========================================================================
# TC-2: Fork / backdoor path  X ← Z → Y,  Z observed
# ===========================================================================
# Ground truth: IDENTIFIABLE via backdoor with adjustment set {Z}.
# The fork Z creates a backdoor path X ← Z → Y; conditioning on Z blocks it.
# ===========================================================================


class TestTC2BackdoorFork:
    """TC-2: X ← Z → Y, Z observed (classic backdoor)."""

    VARS = ["X", "Z", "Y"]
    EDGES = [
        directed("Z", "X"),  # backdoor path
        directed("Z", "Y"),
        directed("X", "Y"),  # causal path
    ]
    OBSERVED = ["X", "Z", "Y"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_check_backdoor_returns_z(self):
        adj = check_backdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert adj is not None
        assert "Z" in adj

    def test_identify_query_identifiable(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.status == IdentifiabilityStatus.IDENTIFIABLE
        assert result.method == IdentificationMethod.BACKDOOR
        assert "Z" in (result.adjustment_set or [])
        assert not result.abstains

    def test_z_is_not_descendant_of_x(self):
        # Z is a cause of X, never a descendant — adjustment is valid
        result = identify_query(self.pag, "X", "Y")
        assert "X" not in (result.adjustment_set or [])


# ===========================================================================
# TC-3: Hidden confounder  X ↔ Y  (bidirected edge only)
# ===========================================================================
# Ground truth: NOT_IDENTIFIABLE — the bidirected edge signals a latent
# common cause that cannot be blocked by any observed variable.
# RIFT must ABSTAIN.
# ===========================================================================


class TestTC3HiddenConfounder:
    """TC-3: X ↔ Y (hidden common cause, no mediators, no other paths)."""

    VARS = ["X", "Y"]
    EDGES = [bidirected("X", "Y")]
    OBSERVED = ["X", "Y"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_check_backdoor_returns_none(self):
        adj = check_backdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert adj is None, "Bidirected-only graph has no valid backdoor set"

    def test_check_frontdoor_returns_none(self):
        m = check_frontdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert m is None, "No directed causal path → front-door inapplicable"

    def test_identify_query_not_identifiable(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.status == IdentifiabilityStatus.NOT_IDENTIFIABLE

    def test_abstain_contract(self):
        result = identify_query(self.pag, "X", "Y")
        assert_abstain(result)

    def test_blocking_reason_mentions_bidirected(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.blocking_reason is not None
        reason_lower = result.blocking_reason.lower()
        assert "bidir" in reason_lower or "hidden" in reason_lower or "confounder" in reason_lower


# ===========================================================================
# TC-4: Mediated  X → M → Y  with hidden confounder  X ↔ Y
# ===========================================================================
# Ground truth: IDENTIFIABLE via front-door with mediator set {M}.
# The hidden confounder blocks backdoor; front-door applies because:
#   (a) X → M → Y is the only directed path,
#   (b) no confounding between X and M,
#   (c) {X} blocks all backdoor paths M → Y.
# ===========================================================================


class TestTC4FrontDoorMediation:
    """TC-4: X → M → Y with X ↔ Y; front-door via {M}."""

    VARS = ["X", "M", "Y"]
    EDGES = [
        directed("X", "M"),
        directed("M", "Y"),
        bidirected("X", "Y"),  # hidden confounder
    ]
    OBSERVED = ["X", "M", "Y"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_check_backdoor_fails(self):
        adj = check_backdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert adj is None, "Bidirected X↔Y should block backdoor identification"

    def test_check_frontdoor_returns_m(self):
        m = check_frontdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert m is not None, "Front-door criterion should apply via mediator M"
        assert "M" in m

    def test_identify_query_identifiable_via_frontdoor(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.status == IdentifiabilityStatus.IDENTIFIABLE
        assert result.method == IdentificationMethod.FRONT_DOOR
        assert result.adjustment_set is not None
        assert "M" in result.adjustment_set

    def test_not_abstaining(self):
        result = identify_query(self.pag, "X", "Y")
        assert not result.abstains

    def test_no_blocking_reason(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.blocking_reason is None


# ===========================================================================
# TC-5: PAG ambiguity — o→ edge on causal path
# ===========================================================================
# Ground truth: CONDITIONALLY_IDENTIFIABLE — identification depends on which
# MAG within the PAG equivalence class is the true one.
# ===========================================================================


class TestTC5PAGAmbiguity:
    """TC-5: X o→ Y (PARTIALLY_DIRECTED edge — PAG ambiguity)."""

    VARS = ["X", "Y"]
    EDGES = [partial("X", "Y")]  # o→
    OBSERVED = ["X", "Y"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_identify_query_conditionally_identifiable(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.status == IdentifiabilityStatus.CONDITIONALLY_IDENTIFIABLE

    def test_disambiguating_intervention_present(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.disambiguating_intervention is not None

    def test_not_abstaining(self):
        result = identify_query(self.pag, "X", "Y")
        assert not result.abstains

    def test_notes_mention_pag_ambiguity(self):
        result = identify_query(self.pag, "X", "Y")
        assert "PAG" in result.notes or "ambiguity" in result.notes.lower() or "o→" in result.notes


class TestTC5bUndirectedAmbiguity:
    """TC-5b: X o-o Y (UNDIRECTED — maximal PAG ambiguity)."""

    VARS = ["X", "Y"]
    EDGES = [undirected("X", "Y")]
    OBSERVED = ["X", "Y"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_conditionally_identifiable(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.status == IdentifiabilityStatus.CONDITIONALLY_IDENTIFIABLE


# ===========================================================================
# TC-6: Full non-identifiable structure — bidirected with no mediators
# ===========================================================================
# Ground truth: NOT_IDENTIFIABLE → ABSTAIN.
# Structure: W → X ↔ Y ← V (multiple hidden confounders, no mediators,
# no observed adjustment set that blocks all backdoor paths).
# ===========================================================================


class TestTC6FullNonIdentifiable:
    """TC-6: X ↔ Y ↔ W (bidirected chain), no mediators, no IV candidates.

    All paths between X and Y are confounded.  W is also confounded with X via
    the hidden cause shared with Y (W↔X bidirected), so W is not a valid IV.
    No backdoor, front-door, or IV identification is possible → NOT_IDENTIFIABLE.
    """

    VARS = ["X", "Y", "W"]
    EDGES = [
        bidirected("X", "Y"),   # hidden confounder X–Y
        bidirected("W", "X"),   # W is also confounded with X — not a valid IV
    ]
    OBSERVED = ["X", "Y", "W"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_backdoor_fails(self):
        adj = check_backdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert adj is None

    def test_frontdoor_fails(self):
        m = check_frontdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert m is None

    def test_not_identifiable(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.status == IdentifiabilityStatus.NOT_IDENTIFIABLE

    def test_abstain_contract(self):
        result = identify_query(self.pag, "X", "Y")
        assert_abstain(result)

    def test_notes_mention_abstain(self):
        result = identify_query(self.pag, "X", "Y")
        assert "ABSTAIN" in result.notes.upper() or "abstain" in result.notes.lower()


# ===========================================================================
# TC-7: Variable not in PAG  → NOT_IDENTIFIABLE / ABSTAIN
# ===========================================================================


class TestTC7VariableNotInPAG:
    """TC-7: Query variable absent from PAG."""

    VARS = ["X", "Y"]
    EDGES = [directed("X", "Y")]
    OBSERVED = ["X", "Y"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_missing_source_abstains(self):
        result = identify_query(self.pag, "Z_missing", "Y")
        assert_abstain(result)

    def test_missing_target_abstains(self):
        result = identify_query(self.pag, "X", "Z_missing")
        assert_abstain(result)


# ===========================================================================
# TC-8: Longer chain X → A → B → Y — no confounders
# ===========================================================================
# Ground truth: IDENTIFIABLE via backdoor (empty set) — longer chains with
# no confounders still satisfy backdoor with Z = [].
# ===========================================================================


class TestTC8LongerChain:
    """TC-8: X → A → B → Y (multi-hop chain, no confounders)."""

    VARS = ["X", "A", "B", "Y"]
    EDGES = [
        directed("X", "A"),
        directed("A", "B"),
        directed("B", "Y"),
    ]
    OBSERVED = ["X", "A", "B", "Y"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_backdoor_empty(self):
        adj = check_backdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert adj == []

    def test_identifiable(self):
        result = identify_query(self.pag, "X", "Y")
        assert result.status == IdentifiabilityStatus.IDENTIFIABLE
        assert result.method == IdentificationMethod.BACKDOOR
        assert result.adjustment_set == []


# ===========================================================================
# TC-9: IV fallback — X ← U → Y with Z → X (Z is an IV)
# ===========================================================================
# Ground truth: REQUIRES_INTERVENTION (IV candidate found but not usable
# in Phase 3 observation mode).
# ===========================================================================


class TestTC9IVFallback:
    """TC-9: Z → X ↔ Y — IV candidate available."""

    VARS = ["Z", "X", "Y"]
    EDGES = [
        directed("Z", "X"),
        bidirected("X", "Y"),   # hidden confounder blocks backdoor/front-door
    ]
    OBSERVED = ["Z", "X", "Y"]

    def setup_method(self):
        self.pag = pag(self.VARS, self.EDGES, self.OBSERVED)

    def test_backdoor_fails(self):
        adj = check_backdoor(self.EDGES, "X", "Y", self.OBSERVED)
        assert adj is None

    def test_requires_intervention_or_not_identifiable(self):
        result = identify_query(self.pag, "X", "Y")
        # IV check may find Z; result is REQUIRES_INTERVENTION or NOT_IDENTIFIABLE
        assert result.status in (
            IdentifiabilityStatus.REQUIRES_INTERVENTION,
            IdentifiabilityStatus.NOT_IDENTIFIABLE,
        )

    def test_if_requires_intervention_has_disambiguating(self):
        result = identify_query(self.pag, "X", "Y")
        if result.status == IdentifiabilityStatus.REQUIRES_INTERVENTION:
            assert result.disambiguating_intervention is not None
            assert result.method == IdentificationMethod.INSTRUMENTAL_VARIABLE


# ===========================================================================
# Parametric ABSTAIN sweep — any NOT_IDENTIFIABLE must satisfy ABSTAIN contract
# ===========================================================================


NOT_IDENTIFIABLE_CASES = [
    # (name, variables, edges, observed, source, target)
    (
        "bidirected_only",
        ["X", "Y"],
        [bidirected("X", "Y")],
        ["X", "Y"],
        "X", "Y",
    ),
    (
        "no_path_to_target",
        ["X", "Y", "Z"],
        [directed("X", "Z")],   # no path X→Y
        ["X", "Y", "Z"],
        "X", "Y",
    ),
    (
        "x_bidir_y_w_bidir_x",
        ["X", "Y", "W"],
        [bidirected("X", "Y"), bidirected("W", "X")],
        ["X", "Y", "W"],
        "X", "Y",
    ),
]


@pytest.mark.parametrize("name,variables,edges,observed,source,target", NOT_IDENTIFIABLE_CASES)
def test_not_identifiable_abstain_contract(name, variables, edges, observed, source, target):
    """All NOT_IDENTIFIABLE results must fully satisfy the ABSTAIN contract."""
    p = pag(variables, edges, observed)
    result = identify_query(p, source, target)
    if result.status == IdentifiabilityStatus.NOT_IDENTIFIABLE:
        assert_abstain(result), f"ABSTAIN contract violated for case '{name}'"
