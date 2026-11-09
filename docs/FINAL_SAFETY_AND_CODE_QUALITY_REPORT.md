# FINAL SAFETY AND CODE QUALITY REPORT (Agent 6)

- Branch: `remediation-and-manuscript-closure` (from `ebad911`)
- Scope: `src/rift/safety/safety.py`, `src/rift/intervention/backends/linux_tc_netem.py`,
  `src/rift/intervention/watchdog.py`, `src/rift/intervention/network_intervention.py`,
  `src/rift/intervention/intervention_lifecycle.py`, `src/rift/pipeline/e2e_runner.py`,
  `src/rift/fault_injection/fault_injector.py`, `configs/live.yaml`
- Platform: macOS Darwin, Python 3.9.6. No live `tc`/`nsenter`/`ip netns` was executed. Every
  subprocess probe below used `unittest.mock.patch`, or the platform guard (`sys.platform`) blocked it.
- This review made **no source, test, dataset, artifact or sealed-data modification**. The only
  file written is this report. `git status --short` showed the same 196 entries before and
  after every command I ran.

## 1. Verdict

**CONDITIONAL PASS for the simulated and dry-run research pipeline. FAIL for any live
host-attached intervention until findings S-1 to S-3 are fixed.**

- The hardened pieces (`SafetyController`, `LinuxTcNetemBackend`, `DetachedRollbackWatchdog`) behave as designed on every probe except the edge cases in section 5.
- None of the hardened pieces is wired into the code path that would actually run a live intervention. The live-capable engine `NetworkInterventionEngine` has none of the new guards (S-1).
- None of the 11 modified files can change any historical Sprint 4.3/4.4/4.5.1 number (section 6).

## 2. Tests executed

| Command | Result |
|---|---|
| `pytest tests/unit/test_safety_namespace_remediation.py tests/unit/test_watchdog_remediation.py tests/unit/test_network_intervention.py tests/unit/test_closed_loop.py tests/unit/test_cid.py tests/unit/test_phase36_new_modules.py` | 178 passed |
| `pytest tests/integration tests/unit/test_prometheus_client.py tests/unit/test_telemetry_remediation_419.py tests/unit/test_sprint423_ebd_attribution.py tests/unit/test_sprint424_stage4_attribution.py` | 150 passed |
| `pytest tests` (full suite, `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`) | **1016 passed, 0 failed, 0 skipped**, 15 third-party warnings (urllib3 LibreSSL, matplotlib pyparsing) |

Caveat: this is the local Python 3.9.6 environment. It is not the Python 3.11 CI environment (see
`docs/FINAL_REPRODUCIBILITY_REPORT.md`).

## 3. Isolation proofs (fail-closed behaviour that holds)

Static and runtime probes against the modified code:

| Check | Evidence | Result |
|---|---|---|
| `SafetyController` rejects empty, whitespace, `None`, `host`, `root`, `default`, `/proc/1/ns/net`, `Host`, non-`rift-eval-*`, `RIFT-EVAL-DEFAULT`, and `rift-eval-default\n` | Probe output; `safety.py:87-97`; `tests/unit/test_safety_namespace_remediation.py` | Hard stop |
| An unconfigured `SafetyController()` blocks even `rift-eval-default` (approved list empty) | Probe | Fail-closed |
| `LinuxTcNetemBackend()` with no target: `_wrap_ns` raises, and no command is built | `linux_tc_netem.py:123-135`; probe | Fail-closed |
| `container_pid` 0 or 1, `sandbox_namespace` `host`/`root`/`default` (case-insensitive), and `netns_path` `/proc/1/ns/net` or `/proc/self/ns/net` are rejected at construction | `linux_tc_netem.py:108-121`; 3 unit tests | Fail-closed |
| `InterventionLifecycle.authorize()` with namespace `host` → ABORTED, `apply()` unreachable; `rollback()` after abort returns True | Probe | Fail-closed |
| `InterventionLifecycle.prepare()` rejects a NaN `target_value` | Probe | Fail-closed |
| `LinuxTcNetemBackend` on non-Linux: `rollback()` raises `RuntimeError` (it does not silently do nothing) | Probe, `sys.platform == darwin` | Fail-closed |
| `WatchdogSpec` rejects `target_pid <= 1` and `timeout_s` above 30 s | `watchdog.py:45-53`; unit test | Fail-closed |
| Watchdog script re-checks that `/proc/<pid>/ns` exists and that the target netns inode differs from `/proc/1/ns/net` before deleting qdiscs | `watchdog.py:92-103`; unit test `test_watchdog_command_includes_host_netns_avoidance` | Holds |
| Watchdog is spawned with `start_new_session=True`, so it survives the parent dying | `watchdog.py:120-125`; unit test | Holds |
| E2E runner defaults to `dry_run=True` and `MockTelemetry` (marked `synthetic_substitution=True`, `is_valid_for_gate=False`) | Probe: 4-service dry run completed, outcome ABSTAIN-class (`attribution=None`, confidence `NONE`) | Holds |

## 4. Rollback review

`LinuxTcNetemBackend.rollback()` (`linux_tc_netem.py:214-238`) now issues three commands in
order: `tc filter del`, `tc qdisc del ... parent 1:<h>`, and the newly added
`tc qdisc del ... root handle 1:`. Each is wrapped by `_wrap_ns`.

Positive: the new root-qdisc deletion closes the leaked-`prio`-root defect. Every command is
namespace-wrapped. `rollback()` is idempotent (non-zero returns are ignored, since the rule may
already be gone).

Weaknesses found by probe (all by mocked `_run_tc`):

- **S-2 Rollback reports success unconditionally.**
  With every `tc del` returning 1, `rollback()` returned `ROLLED_BACK` (attempts=1).
  `SafetyController.assess_post_rollback(rollback_succeeded=...)` has nothing truthful to consume.
  Fed `status == ROLLED_BACK`, it returned `APPROVED_AUTONOMOUS`, so the `ROLLBACK_FAILURE`
  hard stop and the kill-switch can never trigger from this backend. The same applies to
  `NetworkInterventionEngine.rollback()`, which computes `all_ok` and then discards it.
- **S-4 Partial `apply` failure is not tracked.** If command 1 (root qdisc add) succeeds and
  command 2 or 3 fails, `apply()` returns `FAILED`, adds nothing to `_active`, and issues no
  cleanup. `rollback_all()` then returns 0 records and the root `prio` qdisc stays. The
  independent watchdog is the only remaining safeguard.
- **S-5 Shared root deletion.** `rollback()` of any one record deletes the root qdisc, which
  destroys sibling bands (1:2, 1:3) for any other concurrent records. The e2e runner assigns
  bands 1-3 for up to three simultaneous interventions. Rolling back one of them kills the
  others without their records knowing.
- The backend's `verify()` returns `precision_check_pass=True` if the handle number appears
  anywhere in `tc qdisc show` output (`"1" in text`), so it is a weak check. It does not affect
  safety fail-closed behaviour but it weakens the "verified" claim.

## 5. Findings (ranked)

### S-1 (HIGH, blocks live use): The live path bypasses the hardened guards

- `RIFTEndToEndRunner.__init__` (`e2e_runner.py:495`) builds `NetworkInterventionEngine(dry_run=dry_run)` with no namespace, and `FaultInjector` does the same (`fault_injector.py:358`).
- `NetworkInterventionEngine._run_cmd` (`network_intervention.py:184-203`) prepends `ip netns exec` only if `sandbox_namespace` is set. Otherwise it runs bare `tc` on the host.
- **Probe** (mocked `subprocess.run`): `NetworkInterventionEngine(dry_run=False)` with no namespace issued **5 un-namespaced `tc` commands** (first: `tc qdisc add dev eth0 root ...`). That is a host-interface modification.
- The hardened `LinuxTcNetemBackend` is **not referenced anywhere under `src/`** except its own file. `DetachedRollbackWatchdog` is likewise unreferenced outside tests. `SafetyController.assess_pre_intervention` is only reached through `InterventionLifecycle`, which the e2e runner does not use.
- `RIFTEndToEndRunner._safety_checker = SafetyController()` is constructed but **never called inside `run()`**.
- Consequence: the Sprint 4.5.1 safety "hardening" is real and tested, but it protects only code that the pipeline does not call. `configs/live.yaml` comments describe container-NetNS isolation that nothing in the live code path enforces.

### S-3 (MEDIUM): `sandbox_namespace` is not validated against `rift-eval-*` in the backend

- Probe: `LinuxTcNetemBackend(sandbox_namespace="prod-payments")` and `" host"` (leading space) are accepted and produce `ip netns exec prod-payments tc ...`. The docstring says the safety controller validates the pattern, but the backend does not require it to have been called.
- `container_pid=2` (kernel thread / non-container) and `netns_path` variants `/proc/1/ns/net/` and `/proc/../proc/1/ns/net` are accepted. Only exact string matches on two paths are rejected, so path normalisation can bypass the host-netns check. A negative `container_pid` is silently ignored and falls through to `sandbox_namespace`.
- `FaultInjector._inject_network` sets `self._network_engine.sandbox_namespace = namespace` (line 631) with no pattern check, and `inject()` documents but does not enforce the `rift-eval-*` rule.

### S-6 (LOW): Watchdog input hygiene

- `WatchdogSpec.interface` is interpolated unsanitised into a `sh -c` script. Probe: `interface="eth0; touch /tmp/PWNED #"` appears verbatim in the generated script (I only generated the string, never ran it).
- `timeout_s=float("nan")` passes validation because both comparisons are False. `sleep nan` then behaves as `sleep` with an invalid argument and the watchdog does not delay as intended.
- Impact is low: the interface value is internal, not user input. Still, `shlex` is imported and unused in `watchdog.py`.

### S-7 (LOW): E2E runner accepts invalid configuration silently

Probes with `MockTelemetry`:

| Input | Behaviour |
|---|---|
| `services=[]`, empty graph | `run()` returns a record with `attribution=None`; no exception |
| Graph that lacks the declared services | Returns a record with `attribution=None`; no exception |
| `post_window_s=-1`, `observe_window_s=0` | Accepted; no exception |
| `dry_run=False` with no namespace | Constructs successfully (see S-1) |

Failing to an abstention is the safe direction. The negative-window acceptance is a validation gap, not a safety defect.

### S-8 (INFO): `InterventionLifecycle.apply()` uses `tc_handle="10:"`

`NetworkInterventionRecord.__post_init__` rejects it, so `apply()` raises `ValueError` for every candidate. Probe: `prepare()` and `authorize()` succeed, then `apply()` raises "tc_handle '10:' maps to band 10 ...". That is fail-closed, but the lifecycle is unusable. It also hard-codes `dest_ip="0.0.0.0"`. This is pre-existing and not among the 11 modified files.

## 6. Review of the 11 modified files

| File | Change | Methodology or result impact |
|---|---|---|
| `src/rift/safety/safety.py` | Added `HOST_NAMESPACE_INTERVENTION`, `MISSING_NAMESPACE`, `INVALID_NAMESPACE` enum members. The members are not used anywhere (host/empty namespace maps to `PRODUCTION_NAMESPACE`). Blank and host-name checks added. | None. Strictly tightens the gate. |
| `src/rift/intervention/backends/linux_tc_netem.py` | `container_pid`, `netns_path`, constructor validation, fail-closed `_wrap_ns`, root-qdisc rollback. | None. Backend is unused by the pipeline (S-1). |
| `src/rift/pipeline/e2e_runner.py` | OTel spanmetrics queries with gRPC fallback; configurable windows; CID stored via `CIDEvidenceStore` under (intervened, outcome) identity; abstain on `NOT_IDENTIFIABLE` with no R4; extra EBD fields. | Changes live-pipeline behaviour only. Not imported by the Sprint 4.3/4.4/4.5.1 evaluation scripts (grep: only `pipeline/__init__.py`, `cid/evidence.py`, `scripts/generate_pre_linux_status.py`). Does not affect stored V2/V3 numbers, but any future live or e2e claim must be regenerated under the new code. |
| `src/rift/fault_injection/fault_injector.py` | `MANIFEST_SPLIT_DEVELOPMENT` 36 → 50. | Constant must match the v2 manifest. This is a data-metadata alignment, not a result change. Its internal consistency with `datasets/rift_faults/manifest.json` is covered by `tests/unit/test_sprint424_dataset_manifest.py` (passing). |
| `configs/live.yaml` | Comments only. | None. |
| `validation/run_cid_validation.py` | `sys.path` and output path `parents[2]` → `parents[1]`. | None to the algorithm. The old output path pointed outside the repo; the new one writes `artifacts/phase3/cid_validation.json`. |
| `artifacts/phase3/cid_validation.json` | Last-digit float differences. | Re-generated output, not hand-edited. Treat as a changed historical artifact (floating-point noise). Commit it separately or revert it to preserve the original bytes. |
| `artifacts/phase3/independent_validation_report.json` | V1 precision@1 0.5 → 0.8333 (PASS), V5 FAR 0.3333 → 0.0. | **Changed historical result.** I did not establish what produced it. It must not be cited as an independent validation until the generating run and its inputs are documented. This is the one item in the set that could change a prior claim. |
| `analysis/tables/table4_scenarios.py` | Removed the held-out filename mapping. | Safety improvement. Table 4 can no longer open the sealed file. Regenerate Table 4 only if it previously included held-out rows. |
| `scripts/verify_heldout_sealed.py` | Fail-closed manifest SHA-256 verification. | Safety improvement; tests pass. |
| `datasets/rift_faults/manifest.json`, `requirements.txt`, `.github/workflows/test.yml` | Dataset manifest v2; dependency/CI changes. | Outside this safety scope; see the dataset and reproducibility reports. |

Nothing in the diff touches `datasets/rift_v2/dev.json`, `val.json`, preregistration docs or
sealed held-out content.

## 7. Recommended fixes (not applied; none required for the manuscript)

1. **S-1:** Route `RIFTEndToEndRunner` and `FaultInjector` through `LinuxTcNetemBackend` for any `dry_run=False` run. Have `NetworkInterventionEngine._run_cmd` raise when `dry_run=False` and no isolation target is set. Call `SafetyController.assess_pre_intervention` and arm `DetachedRollbackWatchdog` before `apply`. Add a regression test asserting that no un-namespaced command is ever built.
2. **S-2:** Make `rollback()` return `FAILED`/`ROLLBACK_FAILED` when the filter/qdisc deletions fail with something other than "not found", and feed that result to `assess_post_rollback`.
3. **S-3:** In the backend, require `rift-eval-*` for `sandbox_namespace`, require `container_pid > 1` and not negative, resolve `netns_path` with `os.path.realpath` before the host comparison, and `.strip()` before the host-name check.
4. **S-4/S-5:** Track partially applied records and clean up on failed `apply`. Delete the root qdisc only when no other band is active.
5. **S-6:** Validate `interface` with a regex (`^[A-Za-z0-9_.-]{1,15}$`), use `shlex.quote`, and reject non-finite `timeout_s`.
6. Provenance for `artifacts/phase3/independent_validation_report.json` before any citation.

## 8. Limits of this review

- No Linux host, container, `CAP_NET_ADMIN` or real `tc` was available, so kernel-level behaviour of the commands is unverified. Command strings were inspected, not executed.
- The watchdog's runtime behaviour (shell script, signals, inode check) was reviewed by reading and by its unit tests only.
- Safety conclusions apply to the repository's local working tree on branch `remediation-and-manuscript-closure`; nothing was pushed, staged or committed.

## 9. Impact on the manuscript

For the empirical-study framing, the safety layer should be described as **implemented and
unit-tested, simulator/dry-run only, not validated on a live testbed**. It should not be
described as protecting a live deployment. Every reported result comes from the simulator-based
evaluation; none depends on the live intervention code.
