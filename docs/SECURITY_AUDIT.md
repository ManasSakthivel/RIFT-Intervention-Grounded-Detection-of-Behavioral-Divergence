# RIFT Security Audit
# Phase 3.6 §31
# Date: Phase 3.6
# Auditor: Automated scan + manual review

## Summary

| Check | Result |
|---|---|
| API keys in source | PASS (none found) |
| Tokens in source | PASS (none found) |
| Passwords in source | PASS (none found) |
| Private endpoints | PASS (only localhost references) |
| Environment secrets | PASS (.env in .gitignore) |
| Credential files | PASS (none present) |
| .gitignore coverage | PASS (see below) |

**Overall: PASS**

---

## Scan Methodology

Scanned all `.py`, `.yaml`, `.json`, `.md`, `.sh` files for:
- `api_key`, `apikey`, `API_KEY`
- `password`, `passwd`, `pwd`
- `token`, `TOKEN`
- `secret`, `SECRET`
- `credential`, `private_key`
- `Bearer`, `Authorization: `

All matches reviewed manually. False positives documented below.

---

## Findings

### P001 — No findings
No API keys, tokens, passwords, or credentials found in the repository.

All Prometheus/Jaeger URLs reference localhost or Docker service names
(e.g., `http://prometheus:9090`). These are configuration references,
not production endpoints.

The `RIFT_PROMETHEUS_URL` and `RIFT_JAEGER_URL` environment variables
are referenced in `docker/docker-compose.yml` as environment variable
references (`${RIFT_PROMETHEUS_URL}`) — not hardcoded values.

---

## .gitignore Coverage

The following patterns are confirmed present in `.gitignore`:

| Pattern | Purpose |
|---|---|
| `.env` | Environment secrets |
| `*.env` | All env files |
| `credentials/` | Credential directories |
| `artifacts/logs/` | Runtime logs |
| `*.log` | Log files |
| `__pycache__/` | Python cache |
| `.pytest_cache/` | Test cache |
| `results/` | Experiment results (large) |
| `*.pyc` | Compiled Python |
| `.coverage` | Coverage data |
| `artifacts/coverage/` | HTML coverage reports |

---

## Excluded from Version Control

The following categories MUST NOT be committed:

1. `.env` files with any values
2. Kubernetes service account tokens
3. Docker registry credentials
4. Any file containing real IP addresses of production systems
5. SSH private keys
6. `local_*` experiment results

---

## Legitimate Public Configuration

The following items appear to be credentials but are NOT — they are
legitimate public test configuration:

- `rift-eval-*` namespace names: Not secrets; public test namespace convention
- `localhost:9090`: Prometheus default port; public
- `172.30.0.0/16`: Docker bridge subnet; public

---

## Recurring Security Requirements

1. ProvenanceLogger._check_no_secrets() validates all provenance records
2. ArtifactWriter does not log environment variables
3. configs/held_out.yaml oracle_token field is always `null` in VCS
4. No test fixture hardcodes real credentials

---

## Next Steps

1. Provision Linux testbed: ensure no production credentials are mounted
2. Before public repository release: re-run automated scan
3. Add pre-commit hook: `grep -rn 'api_key\|password\|token' src/`
