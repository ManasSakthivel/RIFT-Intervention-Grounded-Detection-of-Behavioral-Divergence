# Sage+Chaos Baseline Documentation
# Phase 3.6 §11
# Status: DEFERRED_TO_PHASE_8

## Status

**DEFERRED_TO_PHASE_8**

The Sage+Chaos comparison requires pre-labeled fault injection data with
ground-truth root-cause annotations at the trace level. This data is not
yet available for the RIFT evaluation testbed.

This baseline is NOT marked as MISSING. It is correctly deferred with an
explicit reason and documented interface contract.

## Definition

Sage+Chaos combines:
- **Sage**: ML-based anomaly scoring on distributed traces
- **Chaos**: Chaos engineering fault injection for ground-truth labeling

The comparison would evaluate whether RIFT's interventional approach
outperforms Sage's purely observational trace anomaly scoring.

## Interface Requirements (for Phase 8)

When Sage+Chaos data becomes available, the following interface must be satisfied:

### Input (what Sage+Chaos receives)
- Same IncidentContext as all baselines (no extra information)
- Pre-labeled trace data with fault type and root-cause service
- Same time window as RIFT evaluation

### Output (what Sage+Chaos returns)
- BaselineOutput with top_candidates ranked by Sage score
- abstained=True if Sage score is below threshold
- detection_latency_s measured from same incident_window[0]

### Data requirements
- Minimum: 36 development scenarios with pre-labeled traces
- Ground-truth: root-cause service + fault type per scenario
- Format: OpenTelemetry spans with fault annotations

## Interface Stub

`src/rift/baselines/sage_chaos.py` — `SageChaosStub`

The stub returns abstained=True with notes indicating DEFERRED status.
It must be replaced with a real implementation in Phase 8.

## Reason for Deferral

Pre-labeled fault data with Sage-compatible trace annotations requires:
1. Deployed Online Boutique on Linux (PENDING_LINUX)
2. Sage evaluation harness (not yet available in this repository)
3. Pre-labeled trace collection run (requires live execution)

Do NOT fabricate Sage+Chaos results. Do NOT mark this baseline as
SUPPORTED in the claims registry until Phase 8 data is collected.

## Claims Registry Impact

Any paper claim comparing RIFT against Sage+Chaos must remain:
  status: PLANNED
until Phase 8 live data collection is complete.
