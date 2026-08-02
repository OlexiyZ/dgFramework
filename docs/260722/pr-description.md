<!--
Pull request description for `security/sonar-remediation` -> `dev_diceus`.
Kept in the repository so the summary survives the branch.

Links below are relative to the repository root, which is how GitHub resolves
them in a pull request body. Reading this file directly in the repo, they will
point one level up from docs/260722/.
-->

# Security: close SonarQube findings (SEC-01..SEC-10)

Closes the SonarQube findings for `BankalEtihad_data_governance`: **5 BLOCKER vulnerabilities** and **27 HIGH security hotspots**, plus four issues found during the work that Sonar did not report.

One commit per task, `SEC-01` through `SEC-10`. Full analysis in [`docs/260722/security-remediation-plan.md`](docs/260722/security-remediation-plan.md).

## What changed

| | Task | Effect |
|---|---|---|
| P0 | SEC-01 | `.env` removed from git tracking; two Okta client secrets and a bare password stripped from `settings.py` comments |
| P0 | SEC-02 | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_PASSWORD` read from the environment; `DEBUG` now defaults to `False` |
| P0 | SEC-03 | `load2db()` uses `django.db.connection` instead of its own psycopg2 connection with inlined credentials |
| P0 | SEC-04 | `storage/views_old.py` and `storage/views_dg.py` deleted — unreferenced dead code |
| P1 | SEC-05 | The import `INSERT` is parameterised; both quote-escaping helpers removed |
| P1 | SEC-06 | All 12 `@csrf_exempt` decorators removed; nine POST endpoints now send `X-CSRFToken` |
| P1 | SEC-07 | `diagram.html` ships data via `json_script`; database values escaped at 22 sites in `dm/views.py` |
| P2 | SEC-08 | Navbar and Bootstrap link moved out of Python strings into templates; no `\|safe` left |
| P2 | SEC-09 | gitleaks as a pre-commit hook and a CI job |
| P2 | SEC-10 | `manage.py check --deploy` in CI, with the security headers it requires |

## Found along the way, not in the Sonar report

- **SQL injection** in the Excel/CSV import — user-supplied cell values were interpolated into `INSERT` statements (SEC-05)
- **`DEBUG = True` hardcoded in production**, returning full tracebacks with database credentials on any 500 (SEC-02)
- **`ALLOWED_HOSTS = ["*"]`** (SEC-02)
- **Two live Okta client secrets** sitting in `settings.py` comments — invisible to Sonar, still valid until revoked in Okta (SEC-01)

## Three things that changed the shape of the work

**Nothing loaded `.env`.** Neither `python-dotenv` nor `django-environ` was a dependency, which is exactly why the `platform.system() == "Windows"` branch with hardcoded credentials existed — there were no environment variables locally. `python-dotenv` is now a dependency. Real environment variables still take precedence, so Vault-injected values in Kubernetes are unaffected.

**`import_excel` and `import_csv` sent the CSRF token inside the JSON body.** Django reads it from `request.POST` or the `X-CSRFToken` header, never from a JSON body, so the token was being ignored entirely. Simply dropping `@csrf_exempt` would have broken both imports with a 403.

**SEC-07 was twice the size it looked.** `json_script` fixes the script-context breakout, but markmap renders each node's `content` as HTML, and that content is built by concatenating SVG markup with field names and descriptions straight from the database. Escaping was needed at 22 call sites.

## DevOps actions required

Full checklist, phase by phase, in [`docs/260722/devops-handover.md`](docs/260722/devops-handover.md).
Merging this PR deploys nothing by itself, so the work splits into two gates.

**Phase 0 — blocks this merge.** Two of these are answers rather than changes, but they decide what goes into Vault next:

- [ ] **D1. Check `Dockerfile.dockerfile` for `COPY .env`** — the file is no longer in the repository, so a build that copies it fails after merge. The Dockerfile lives outside this repo and could not be inspected here.
- [ ] **E1. Approve `.github/workflows/security_checks.yml`** — `.github/**` is `merge=ours` with `CODEOWNERS @kgetihad`, so this cannot merge without a DevOps review.
- [ ] **C1. Does the ingress forward `X-Forwarded-Proto`?** If not, `SECURE_SSL_REDIRECT` makes Django answer 301 to every request, health probes included, and the pods never reach `Ready`.
- [ ] **C2. How do the probes address the pod?** `ALLOWED_HOSTS = ["*"]` is gone, so probes arriving by pod IP get 400.

**Phase 1 — blocks the deploy, not this merge.** One Vault edit and one image rebuild:

- [ ] **B2–B4.** Set `ALLOWED_HOSTS` from C2, and ship `SECURE_SSL_REDIRECT=False` and `SECURE_HSTS_SECONDS=0` for the first deploy — both default to on, and HSTS is hard to walk back once browsers cache it.
- [ ] **A1–A4. Rotate the leaked credentials**: database password, `DJANGO_SECRET_KEY`, `DJANGO_SUPERUSER_PASSWORD` (currently 5 characters), and revoke both Okta client secrets. All four remain valid, and present in git history, until rotated. The Okta secrets do not depend on the deploy — do those first.
- [ ] **D2. Rebuild the image** — `requirements.txt` gained `python-dotenv`.

Phases 2 and 3 — deploy smoke tests and follow-up — are in the handover document.

## Testing status

Django is not installed in the environment where these changes were made. Verification was limited to `py_compile`, YAML parsing, a script confirming all nine POST endpoints carry the CSRF token, and manual review. **No page was rendered and no request was sent.**

Worth exercising before merge: Okta login, all six posting forms, an Excel import against a real workbook, and the diagram pages.

One behaviour change to confirm against real data: empty spreadsheet cells used to reach the database as the literal text `'nan'` because they were interpolated into the SQL. Parameter binding cannot do that, so they are now `NULL`.
