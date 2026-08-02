# DevOps handover — SEC-01…SEC-10

Actions the application changes cannot cover, because they need access to Vault,
PostgreSQL, Okta, the ingress or the repository settings.

**Companion document:** [security-remediation-plan.md](security-remediation-plan.md) —
the full audit, one section per task, with the reasoning behind each change.

**Branch:** `dev_diceus`, commits `70089bc..c84a1aa` (11 commits, not pushed yet).

| Block | Items | Blocking a deploy? |
|---|---|---|
| A. Credential rotation | 5 | No — but the old values stay valid until done |
| B. Environment variables | 4 | **Yes** |
| C. Ingress and probes | 3 | **Yes** |
| D. Image build | 2 | **Yes** |
| E. Repository and CI | 3 | No |
| F. Post-deploy verification | 6 | — |

> **Read block D first.** If the image build copies a committed `.env`, the build
> breaks on the very first run after these commits.

---

## A. Credential rotation

Everything here leaked through git history and stays valid until rotated.
The application changes remove the values from the source; they cannot revoke them.

### [ ] A1. Database password

Change the password of the PostgreSQL user, then update Vault:

```
secret/data/data-governance#DB_PASSWORD
```

Old value was in the committed `.env` and, as the literal `postgres`, in
`settings.py` and `storage/views.py`.

### [ ] A2. Django secret key

Generate and store a new key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

```
secret/data/data-governance#DJANGO_SECRET_KEY
```

The previous key shipped in the source as a `django-insecure-…` fallback, so it
is public. Rotating it invalidates existing sessions and any outstanding
password-reset links — expect users to be logged out once.

### [ ] A3. Superuser password

```
secret/data/data-governance#DJANGO_SUPERUSER_PASSWORD
```

The current value is **5 characters**. Change it in Vault *and* on the existing
account — `scripts/init.sh` runs `createsuperuser` only when the account does not
exist yet, so Vault alone will not update an account that is already there.

### [ ] A4. Okta client secrets — two of them

Revoke and reissue in the Okta admin console:

| Tenant | Where it leaked |
|---|---|
| `eu-bankaletihad.okta.com` | `dgFramework/settings.py`, commented-out OIDC block |
| `dev-24630760.okta.com` | same block |

SonarQube never flagged these — they sat inside comments. They remain valid and
present in git history until revoked in Okta. **Highest-value item in this block.**

### [ ] A5. Decide on rewriting git history

Rotation makes the leaked values useless, which is usually enough for a private
repository. A full purge is the stronger option:

```bash
git filter-repo --path .env --invert-paths
```

Requires a force push and a fresh clone from everyone. Coordinate before running.
Until this is done, the secret-scan job in CI runs with `--no-git` (working tree
only) — see E2.

---

## B. Environment variables

`DEBUG` and `ALLOWED_HOSTS` are **not** currently in `helm-values/dev.yaml`.
`HOST` already is and needs no change.

### [ ] B1. `DEBUG` — no action needed, but know what changed

Production has been running with `DEBUG = True` hardcoded, which returns a full
traceback — including settings and database credentials — on any 500.

It now reads from the environment and **defaults to `False`**. Leaving it unset
is the correct configuration. Do not add it to Vault.

### [ ] B2. `ALLOWED_HOSTS` — set it explicitly

`ALLOWED_HOSTS = ["*"]` accepted every Host header. It now derives the hostname
from `HOST`, which is already in Vault. That covers normal traffic but **not**
requests that arrive by pod IP or cluster DNS name — see C2.

Recommended, as a comma-separated list:

```
secret/data/data-governance#ALLOWED_HOSTS = reports-govern.baelab.net,<pod-cidr-or-cluster-dns>
```

### [ ] B3. `SECURE_SSL_REDIRECT` — set to `False` for the first deploy

```
secret/data/data-governance#SECURE_SSL_REDIRECT = False
```

Defaults to `True` when `DEBUG=False`. Ship it off, confirm C1, then turn it on
in a separate change. Rationale in C1.

### [ ] B4. `SECURE_HSTS_SECONDS` — set to `0` for the first deploy

```
secret/data/data-governance#SECURE_HSTS_SECONDS = 0
```

Defaults to `31536000` (one year) when `DEBUG=False`. HSTS is hard to walk back:
browsers cache it for the full duration and will refuse plain HTTP to the domain
and its subdomains. Enable deliberately, after C1, and only if the ingress does
not already send the header.

---

## C. Ingress and probes

### [ ] C1. Confirm the ingress forwards `X-Forwarded-Proto`

The app now sets:

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

TLS terminates at the ingress, so Django only knows a request was HTTPS from
that header. If it is missing and `SECURE_SSL_REDIRECT=True`, Django answers
**301 to every request**, including health probes, and the pods never become
ready. This is the single most likely way these changes break a deploy — hence
B3.

### [ ] C2. Check how liveness and readiness probes reach the pod

If kubelet probes by pod IP rather than by hostname, they now hit
`ALLOWED_HOSTS` and get **400 Bad Request**, because `["*"]` is gone.

Either add the pod CIDR / cluster DNS name to `ALLOWED_HOSTS` (B2), or point the
probes at a hostname that is already allowed.

### [ ] C3. Confirm cookies survive

`SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are now `True` whenever
`DEBUG=False`. Cookies stop being sent over plain HTTP. Fine behind an
HTTPS ingress; if anything reaches the service over HTTP internally, logins and
form posts there will stop working.

---

## D. Image build

### [ ] D1. Check whether the build copies `.env` — **do this before deploying**

`.env` is no longer tracked in git (`git rm --cached .env`). `Dockerfile.dockerfile`
lives outside this repository, so I could not inspect it.

If it contains `COPY .env` or similar, **the build now fails** — the file is not
in the checkout. Configuration has to come from the Vault-injected environment,
which `helm-values/dev.yaml` already provides for every variable the app reads.

### [ ] D2. Rebuild the image — new dependency

`requirements.txt` gained `python-dotenv==1.2.2`. Nothing loaded `.env` before
this change, which is exactly why the code carried a
`platform.system() == "Windows"` branch with hardcoded credentials.

The app calls `load_dotenv()` at startup. In Kubernetes there is no `.env` file
and the call is a no-op — real environment variables always take precedence, so
Vault values win regardless.

---

## E. Repository and CI

### [ ] E1. Review and approve the new workflow

`.github/workflows/security_checks.yml` — two jobs, `secret-scan` and
`deploy-check`, on pull requests and on pushes to `master` and `dev`.

`.github/**` carries `merge=ours` and `CODEOWNERS` assigns the whole repository
to `@kgetihad`, so this needs a DevOps review. Note the existing `dev_ci.yml`
triggers on branch `dev`, while work happens on `dev_diceus` — worth aligning if
these checks should run on feature branches too.

### [ ] E2. Triage the first secret-scan run

The scan runs `gitleaks detect --no-git`, so it covers the working tree, not
history — a full scan would fail on every run until A5 is done.

I could not run gitleaks locally. The first run may flag values that are not
secrets:

- Okta `CLIENT_ID` in `settings.py` — a public identifier, not a credential
- ECR account id in `helm-values/dev.yaml`

If they are accepted as safe, add them to a `.gitleaks.toml` allowlist rather
than weakening the rule set.

### [ ] E3. Ask developers to enable the pre-commit hook

```bash
pip install pre-commit
pre-commit install
```

`.pre-commit-config.yaml` is in the repository. Without `pre-commit install` the
hook does not run — this is the local half of E2, and the control that would
have stopped `.env` from being committed in the first place.

---

## F. Post-deploy verification

Nothing below was executed by me: Django is not installed in the environment
where these changes were made, so the code was verified by `py_compile`, YAML
parsing and manual review only. **No page was rendered and no request was sent.**

- [ ] **F1.** Pods reach `Ready`; no 301 loop and no 400 in the probe logs (C1, C2)
- [ ] **F2.** Login through Okta works end to end — the browser POSTs to
      `/storage/oidc-login/`, which now requires a CSRF token
- [ ] **F3.** All six forms that post: Excel import, CSV import, DB JSON upload,
      SQL parsing, JSON upload, save roles, save reports. A missing token shows
      up as **403 Forbidden**
- [ ] **F4.** Excel import against a real workbook. Empty cells used to be stored
      as the literal text `'nan'`; parameter binding cannot do that, so they are
      now `NULL`. Confirm that matches what the data is supposed to mean
- [ ] **F5.** Diagram pages (`/dm/diagram/...`, `/dm/field_diagram/...`) still
      render, including sources whose names contain quotes or angle brackets
- [ ] **F6.** Any HTML deliberately stored in `query_description` or
      `source_description` now renders as text, not markup — check whether that
      was being used
- [ ] **F7.** Re-run the SonarQube scan and confirm 5 vulnerabilities and 27
      hotspots are closed

---

## Rollback

Every change is a separate commit, `SEC-01` through `SEC-10`, so any single one
can be reverted on its own.

The likely candidates, in order of probability:

| Symptom | Revert | Or set |
|---|---|---|
| 301 loop, probes failing | `c84a1aa` (SEC-10) | `SECURE_SSL_REDIRECT=False` |
| 400 on probes | `9d9a407` (SEC-02) | `ALLOWED_HOSTS=...` |
| 403 on forms | `791f27e` (SEC-06) | — |
| Build fails on missing `.env` | — | fix the Dockerfile (D1) |

Prefer the environment variable over the revert: it is faster, and it keeps the
security fix in place.
