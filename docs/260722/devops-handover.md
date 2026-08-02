# DevOps handover — SEC-01…SEC-10

Actions the application changes cannot cover, because they need access to Vault,
PostgreSQL, Okta, the ingress or the repository settings.

**Companion document:** [security-remediation-plan.md](security-remediation-plan.md) —
the full audit, one section per task, with the reasoning behind each change.

**Pull request:** `security/sonar-remediation` → `dev_diceus` in
`BankalEtihad/data_governance`.

---

## Order of work

Items are grouped by **when** they happen relative to the pull request, not by
topic. Item IDs (`A1`, `B2`, …) are stable and are referenced from the plan and
from the PR description.

| Phase | When | Items | Gate |
|---|---|---|---|
| **0** | Before merging the PR | D1, E1, C1, C2 | Merge is blocked until these are answered |
| **1** | After merge, before deploying | A1–A4, B1–B4, D2 | Deploy is blocked until these are done |
| **2** | Deploying, and right after | C3, F1–F5 | Release sign-off |
| **3** | After the release | A5, E2, E3, F6, F7 | Blocks nothing |

**Why this order.** Phase 0 exists because its answers decide what goes into
Vault in phase 1: whether the ingress forwards `X-Forwarded-Proto` (C1) sets
`SECURE_SSL_REDIRECT`, and how the probes address the pod (C2) sets
`ALLOWED_HOSTS`. Running phase 1 first means guessing both. All of phase 1 is one
Vault edit plus one image rebuild, so it costs a single restart instead of
several.

Merging the PR deploys nothing by itself — nothing between phases 0 and 2 is
visible to users.

---

# Phase 0 — before merging the PR

Four questions. Two are answers only; two may require changes outside this
repository.

### [ ] D1. Does the image build copy `.env`?

**The most likely way these changes break something.**

`.env` is no longer tracked in git (`git rm --cached .env`).
`Dockerfile.dockerfile` lives outside this repository, so it could not be
inspected here.

If it contains `COPY .env` or similar, **the build fails after merge** — the file
is not in the checkout. Configuration has to come from the Vault-injected
environment, which `helm-values/dev.yaml` already supplies for every variable the
application reads.

Fix the Dockerfile before merging, or the first build on the target branch breaks.

### [ ] E1. Review and approve the new workflow

`.github/workflows/security_checks.yml` — two jobs, `secret-scan` and
`deploy-check`, on pull requests and on pushes to `master` and `dev`.

`.github/**` carries `merge=ours` and `CODEOWNERS` assigns the whole repository
to `@kgetihad`, so this cannot merge without a DevOps review.

Worth deciding at the same time: the existing `dev_ci.yml` triggers on branch
`dev`, while work happens on `dev_diceus`. If these checks should also run on
feature branches, the trigger list needs widening.

### [ ] C1. Does the ingress forward `X-Forwarded-Proto`?

The application now sets:

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

TLS terminates at the ingress, so Django only knows a request arrived over HTTPS
from that header. If the header is missing and `SECURE_SSL_REDIRECT` is on,
Django answers **301 to every request**, health probes included, and the pods
never reach `Ready`.

The answer decides B3 and B4. If it cannot be confirmed, treat it as "no".

### [ ] C2. How do liveness and readiness probes address the pod?

`ALLOWED_HOSTS = ["*"]` is gone. If kubelet probes by pod IP rather than by
hostname, they now get **400 Bad Request**.

The answer decides B2.

---

# Phase 1 — after merge, before deploying

One Vault edit and one image rebuild. Nothing here is visible to users until the
deploy in phase 2.

## Credential rotation

Everything in A1–A4 leaked through git history and **stays valid until rotated**.
The code changes removed the values from the source; they cannot revoke them.

### [ ] A1. Database password

Change the password of the PostgreSQL user, then update Vault:

```
secret/data/data-governance#DB_PASSWORD
```

The old value was in the committed `.env` and, as the literal `postgres`, in
`settings.py` and `storage/views.py`.

### [ ] A2. Django secret key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

```
secret/data/data-governance#DJANGO_SECRET_KEY
```

The previous key shipped in the source as a `django-insecure-…` fallback, so it
is public. Rotating invalidates existing sessions and outstanding password-reset
links — expect users to be logged out once, at the phase 2 restart.

### [ ] A3. Superuser password

```
secret/data/data-governance#DJANGO_SUPERUSER_PASSWORD
```

The current value is **5 characters**. Change it in Vault *and* on the existing
account: `scripts/init.sh` runs `createsuperuser` only when the account does not
exist, so Vault alone will not update an account that is already there.

### [ ] A4. Okta client secrets — two of them

**Independent of the deploy. Do not let it wait for the release.**

Revoke and reissue in the Okta admin console:

| Tenant | Where it leaked |
|---|---|
| `eu-bankaletihad.okta.com` | `dgFramework/settings.py`, commented-out OIDC block |
| `dev-24630760.okta.com` | same block |

SonarQube never flagged these — they sat inside comments. They remain valid, and
present in git history, until revoked in Okta.

## Environment variables

`DEBUG` and `ALLOWED_HOSTS` are **not** currently in `helm-values/dev.yaml`.
`HOST` already is and needs no change.

### [ ] B1. `DEBUG` — no action, but know what changed

Production has been running with `DEBUG = True` hardcoded, returning a full
traceback — including settings and database credentials — on any 500.

It now reads from the environment and **defaults to `False`**. Leaving it unset
is the correct configuration. Do not add it to Vault.

### [ ] B2. `ALLOWED_HOSTS` — set it explicitly

Driven by the answer to **C2**. The hostname is derived from `HOST`, which is
already in Vault; that covers normal traffic but not requests arriving by pod IP
or cluster DNS name.

```
secret/data/data-governance#ALLOWED_HOSTS = reports-govern.baelab.net,<pod-cidr-or-cluster-dns>
```

### [ ] B3. `SECURE_SSL_REDIRECT` — `False` for the first deploy

Driven by the answer to **C1**.

```
secret/data/data-governance#SECURE_SSL_REDIRECT = False
```

Defaults to `True` when `DEBUG=False`. Ship it off, then turn it on as a separate
change once C1 is confirmed and the pods are known good.

### [ ] B4. `SECURE_HSTS_SECONDS` — `0` for the first deploy

```
secret/data/data-governance#SECURE_HSTS_SECONDS = 0
```

Defaults to `31536000` (one year) when `DEBUG=False`. HSTS is hard to walk back:
browsers cache it for the full duration and refuse plain HTTP to the domain and
its subdomains. Enable deliberately, after C1, and only if the ingress does not
already send the header.

## Image

### [ ] D2. Rebuild the image — new dependency

`requirements.txt` gained `python-dotenv==1.2.2`. Nothing loaded `.env` before
this change, which is exactly why the code carried a
`platform.system() == "Windows"` branch with hardcoded credentials.

The application calls `load_dotenv()` at startup. In Kubernetes there is no
`.env` file and the call is a no-op — real environment variables always take
precedence, so Vault values win regardless.

---

# Phase 2 — deploying, and right after

Nothing below was executed by me: Django is not installed in the environment
where these changes were made, so the code was verified by `py_compile`, YAML
parsing and manual review only. **No page was rendered and no request was sent.**

### [ ] C3. Confirm cookies still work

`SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are now `True` whenever
`DEBUG=False`, so cookies stop being sent over plain HTTP. Fine behind an HTTPS
ingress — but if anything reaches the service over HTTP internally, logins and
form posts there stop working.

### [ ] F1. Pods reach `Ready`

No 301 loop and no 400 in the probe logs. This is where a wrong answer to C1 or
C2 surfaces.

### [ ] F2. Okta login works end to end

The browser POSTs to `/storage/oidc-login/`, which now requires a CSRF token.

### [ ] F3. All six posting forms

Excel import, CSV import, DB JSON upload, SQL parsing, JSON upload, save roles,
save reports. A missing token shows up as **403 Forbidden**.

### [ ] F4. Excel import against a real workbook

Empty cells used to be stored as the literal text `'nan'`, because they were
interpolated into the SQL. Parameter binding cannot do that, so they are now
`NULL`. Confirm that matches what the data is meant to express.

### [ ] F5. Diagram pages render

`/dm/diagram/...` and `/dm/field_diagram/...`, including sources whose names
contain quotes or angle brackets.

---

# Phase 3 — after the release

Nothing here blocks anything.

### [ ] A5. Decide on rewriting git history

Rotation makes the leaked values useless, which is usually enough for a private
repository. A full purge is the stronger option:

```bash
git filter-repo --path .env --invert-paths
```

Requires a force push and a fresh clone from everyone. Coordinate before running.
Until this is done, the secret-scan job runs with `--no-git` — see E2.

### [ ] E2. Triage the first secret-scan run

The scan runs `gitleaks detect --no-git`, covering the working tree rather than
history: a full scan would fail on every run until A5 is done.

gitleaks was not run locally. The first run may flag values that are not secrets:

- Okta `CLIENT_ID` in `settings.py` — a public identifier, not a credential
- ECR account id in `helm-values/dev.yaml`

If they are accepted as safe, add them to a `.gitleaks.toml` allowlist rather
than weakening the rule set.

### [ ] E3. Ask developers to enable the pre-commit hook

```bash
pip install pre-commit
pre-commit install
```

`.pre-commit-config.yaml` is in the repository, but without `pre-commit install`
the hook never runs. This is the control that would have stopped `.env` from
being committed in the first place.

### [ ] F6. Check HTML stored in descriptions

Any HTML deliberately stored in `query_description` or `source_description` now
renders as text, not markup. Check whether that was being relied on.

### [ ] F7. Re-run the SonarQube scan

Confirm the 5 vulnerabilities and 27 hotspots are closed.

---

## Rollback

Every change is a separate commit, `SEC-01` through `SEC-10`, so any single one
can be reverted on its own.

Prefer the environment variable over the revert — it is faster and keeps the
security fix in place.

| Symptom | Appears in | Set this first | Revert if that fails |
|---|---|---|---|
| Build fails on missing `.env` | Phase 1 | — (fix the Dockerfile, D1) | — |
| 301 loop, probes failing | Phase 2 | `SECURE_SSL_REDIRECT=False` | `SEC-10` |
| 400 on probes | Phase 2 | `ALLOWED_HOSTS=…` | `SEC-02` |
| 403 on forms | Phase 2 | — | `SEC-06` |
| Browsers pinned to HTTPS | Phase 3 | `SECURE_HSTS_SECONDS=0` — clients keep the cached policy until it expires | `SEC-10` |

---

## Item index

| ID | Item | Phase |
|---|---|---|
| A1 | Database password | 1 |
| A2 | Django secret key | 1 |
| A3 | Superuser password | 1 |
| A4 | Okta client secrets | 1 |
| A5 | Git history rewrite | 3 |
| B1 | `DEBUG` | 1 |
| B2 | `ALLOWED_HOSTS` | 1 |
| B3 | `SECURE_SSL_REDIRECT` | 1 |
| B4 | `SECURE_HSTS_SECONDS` | 1 |
| C1 | `X-Forwarded-Proto` | 0 |
| C2 | Probe addressing | 0 |
| C3 | Cookies over HTTP | 2 |
| D1 | Dockerfile `COPY .env` | 0 |
| D2 | Image rebuild | 1 |
| E1 | Approve workflow | 0 |
| E2 | Triage secret scan | 3 |
| E3 | Enable pre-commit | 3 |
| F1 | Pods `Ready` | 2 |
| F2 | Okta login | 2 |
| F3 | Posting forms | 2 |
| F4 | Excel import | 2 |
| F5 | Diagram pages | 2 |
| F6 | HTML in descriptions | 3 |
| F7 | SonarQube rescan | 3 |
