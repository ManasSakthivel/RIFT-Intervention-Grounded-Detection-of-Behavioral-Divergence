# Contributing to RIFT

Thank you for your interest. RIFT is an active research prototype.

## Scientific integrity

Before contributing code or data changes, read:

- [`docs/CLAIMS_REGISTRY.yaml`](docs/CLAIMS_REGISTRY.yaml) — every paper claim must remain traceable to evidence
- [`artifacts/FINAL_PRE_LINUX_FREEZE.json`](artifacts/FINAL_PRE_LINUX_FREEZE.json) — the frozen pre-Linux state

**Do not modify the held-out test set, scenario definitions, or statistical pipeline
after seeing results.** Any change to scientific code must be accompanied by an
explanation in the pull request and updated artifact hashes.

## Development workflow

```bash
# Install
python3.11 -m pip install -r requirements.txt

# Run tests before any commit
python3.11 -m pytest tests/ -q
# Must pass: 624 tests, 0 failures

# Lint (causal-claim phrase check + flake8)
make lint
```

## Pull request checklist

- [ ] All 624 tests pass
- [ ] No forbidden causal-claim phrases (`make lint`)
- [ ] No secrets, credentials, or absolute local paths committed
- [ ] Research artifacts that establish provenance are not deleted
- [ ] `env.txt` and `.env` are not staged

## Reporting issues

Open a GitHub issue. For scientific/methodology questions, reference the specific
document (hypothesis, experiment ID, claim ID) being questioned.
