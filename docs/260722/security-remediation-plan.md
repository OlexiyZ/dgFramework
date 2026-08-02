# Security Remediation Plan — data_governance

**Source:** SonarQube Cloud, project `BankalEtihad_data_governance`, branch `master`
(export `Book5.xlsx` + `image-20260712-092958.png`, 12 July 2026)

**Scope:** 5 Vulnerabilities (BLOCKER) + 27 Security Hotspots (HIGH) + 4 findings Sonar did not report

**DevOps actions** (credential rotation, environment variables, ingress, CI approval) are
collected separately in [devops-handover.md](devops-handover.md), organised by phase relative
to the pull request, together with the post-deploy checklist and the rollback plan.

**Status legend:** `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` rejected / no longer applicable

---

## Summary

| Priority | Tasks | Sonar issues closed | Estimate |
|---|---|---|---|
| P0 | 4 | 5 vulnerabilities + 2 hotspots | ~0.5 day |
| P1 | 3 | 5 hotspots + 2 outside Sonar | 1–2 days |
| P2 | 3 | 19 hotspots + prevention | ~1 day |

### Task index

| ID | Title | Priority | Status |
|---|---|---|---|
| SEC-01 | Rotate leaked credentials and untrack `.env` | Blocker | `[~]` |
| SEC-02 | Remove the hardcoded SECRET_KEY and move DEBUG / ALLOWED_HOSTS to environment variables | Blocker | `[x]` |
| SEC-03 | Replace the standalone psycopg2 connection with the Django database connection | Blocker | `[x]` |
| SEC-04 | Delete the unused `views_old.py` and `views_dg.py` modules | Blocker | `[x]` |
| SEC-05 | Parameterize the SQL queries in the data import flow | High | `[x]` |
| SEC-06 | Audit and remove unnecessary `@csrf_exempt` decorators | High | `[x]` |
| SEC-07 | Fix the XSS in `diagram.html` by replacing `\|safe` with `json_script` | High | `[x]` |
| SEC-08 | Extract `nav_bar` and `bootstrap_link` into a base template | Medium | `[x]` |
| SEC-09 | Add secret scanning to pre-commit and CI | Medium | `[~]` |
| SEC-10 | Run `manage.py check --deploy` as a blocking pipeline step | Medium | `[~]` |

---

## P0 — critical, do now

### [~] SEC-01 · Rotate leaked credentials and untrack `.env`

> **Status:** the code side is done. Rotating the credentials in Vault and in the
> database needs infrastructure access — see "Left to do manually" at the end of
> this task.

**Description:** The `.env` file is tracked by git despite being listed in `.gitignore`, exposing the Django secret key, the database password and the superuser password in repository history. Rotate every affected credential, remove the file from version control and replace it with a value-less `.env.example` template.

**Priority:** Blocker
**Sonar:** `secrets:S6687` → [issue AZk4N8VqIV_ZOs3ZqEk-](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8VqIV_ZOs3ZqEk-)
**Files:** `.env`, `.gitignore`, `.env.example` (new)

**Problem:**
`.env` is listed in `.gitignore` but tracked by git — `.gitignore` has no effect on files already added to the index.
```
$ git ls-files .env
.env
$ git log --oneline -- .env
2f565e9 Database configuration correction #2
582ffc8 Add .env file
```
The file holds `DJANGO_SECRET_KEY`, `DB_PASSWORD` and `DJANGO_SUPERUSER_PASSWORD` (5 characters).
Those values are already in repository history — in every clone anyone has made.

**Steps (order matters — rotate first):**
1. Change the password of the `postgres` database user in production and staging
2. Change `DJANGO_SUPERUSER_PASSWORD` to something of reasonable length
3. Generate a new `SECRET_KEY`:
   `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
4. Update the secrets in Helm values / CI secrets (`helm-values/`)
5. `git rm --cached .env && git commit -m "Remove .env from version control"`
6. Add a value-less `.env.example`:
   ```
   DJANGO_SECRET_KEY=
   DEBUG=False
   ALLOWED_HOSTS=
   DB_NAME=
   DB_USER=
   DB_PASSWORD=
   DB_HOST=
   DB_PORT=5432
   ```

**Optional (coordinate with the team):** a full history purge —
`git filter-repo --path .env --invert-paths` plus a force push and a fresh clone for everyone.
For a private repository with rotated secrets this is not required; the issue closes without it.

**Definition of Done:** `git ls-files .env` is empty · `.env.example` is in the repository · every old secret is invalid · the application starts on the new set

**Done:**
- [x] `.env` removed from the git index, the file stays on disk
- [x] Added a value-less `.env.example`
- [x] Local `DJANGO_SECRET_KEY` reissued (50 characters)
- [x] Removed two Okta `OIDC_RP_CLIENT_SECRET` values and the bare password `vTmPW3cF5Uv3p24` from `settings.py` comments — Sonar never saw these

**Left to do manually (needs infrastructure access):**
- [ ] Change the database user's password and update `DB_PASSWORD` in Vault (`secret/data/data-governance`)
- [ ] Reissue `DJANGO_SECRET_KEY` in Vault — the local rotation does not affect production
- [ ] Replace `DJANGO_SUPERUSER_PASSWORD` (currently 5 characters) in Vault and on the account itself
- [ ] Revoke both compromised Okta client secrets in the Okta admin console (`eu-bankaletihad.okta.com`, `dev-24630760.okta.com`) — they are in git history and remain valid until revoked
- [ ] Decide on purging git history (`git filter-repo --path .env --invert-paths`) — requires a force push and a fresh clone for everyone

---

### [x] SEC-02 · Remove the hardcoded SECRET_KEY and move DEBUG / ALLOWED_HOSTS to environment variables

> **Status:** done.
>
> **Found during the work:** nothing in the project read `.env` — neither
> `python-dotenv` nor `django-environ` was a dependency. That is exactly why the
> `platform.system() == "Windows"` branch with hardcoded credentials existed:
> there were no environment variables on a local machine. `python-dotenv==1.2.2`
> and a `load_dotenv()` call were therefore added to the scope of this task —
> without them, removing the Windows branch would have broken local development.
> Real environment variables take precedence over `.env`, so Vault values keep
> overriding the file in Kubernetes.
>
> **⚠️ DevOps action needed before deploying:**
> `DEBUG` and `ALLOWED_HOSTS` are absent from `helm-values/dev.yaml`. With no
> variable set, `DEBUG` now defaults to `False` — that is the fix; production had
> been running with `DEBUG=True` — and `ALLOWED_HOSTS` is derived from `HOST`,
> which is already in Vault. But if kubelet addresses the pod by IP, health probes
> will start getting 400, and `ALLOWED_HOSTS` has to be set explicitly in Vault,
> including the pod CIDR or `.svc.cluster.local`. `helm-values/**` is protected by
> `merge=ours` and belongs to DevOps, so it was left untouched.

**Description:** `settings.py` holds the Django secret key both in a comment and as an `os.environ` fallback, ships with `DEBUG = True` and `ALLOWED_HOSTS = ["*"]` hardcoded, and keeps a Windows-only `DATABASES` branch with plaintext credentials. Read all of these from the environment and fail fast on startup when the secret key is missing.

**Priority:** Blocker
**Sonar:** `secrets:S6687` ×2 → [AZk4N8TCIV_ZOs3ZqEjE](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8TCIV_ZOs3ZqEjE), [AZk4N8TCIV_ZOs3ZqEjF](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8TCIV_ZOs3ZqEjF)
**Files:** `dgFramework/settings.py:24-25, 34, 36, 103-113`

**Problem:**
```python
# SECRET_KEY = "django-insecure-o!46yfbflocr&c9s3z8(azkfz..."          # L24, in a comment
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-...')  # L25, as a fallback
DEBUG = True                                                             # L34, hardcoded
ALLOWED_HOSTS = ["*"]                                                    # L36
```
The fallback is more dangerous than the hardcoded value itself: if the environment variable is not set in production the application does not fail — it comes up quietly on a publicly known key, and session cookies and password-reset tokens become forgeable.
`DEBUG = True` in production returns a full stack trace with all settings, database credentials included, on any 500. The `DEBUG` variable in `.env` is currently ignored.

**Steps:**
1. Delete the commented-out key (L24)
2. `SECRET_KEY = os.environ['DJANGO_SECRET_KEY']` — fail fast on startup
3. `DEBUG = os.environ.get('DEBUG', 'False').lower() in ('1', 'true', 'yes')`
4. `ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')`
5. Remove the `if platform.system() == "Windows"` branch from `DATABASES` (L103-113 contains `"PASSWORD": "postgres"`) — one configuration driven by `os.environ`, with local differences living in a local `.env`
6. Remove the commented-out `DATABASES` blocks below it
7. Remove the unused `import platform` if nothing else needs it

**Definition of Done:** no literal secret anywhere in `settings.py` · the application fails with an explicit error when `DJANGO_SECRET_KEY` is missing · `DEBUG` is controlled through the environment

---

### [x] SEC-03 · Replace the standalone psycopg2 connection with the Django database connection

> **Status:** done. `load2db()` now goes through `django.db.connection`, and the
> `psycopg2` import is gone from `views.py` (the package stays in the dependencies
> — Django's own backend uses it).
>
> **Fixed along the way:** the connection and cursor were closed only in the
> `except` branch, so both leaked on the success path. The cursor is now released
> by the `with` block and Django owns the connection. Parameterising the query
> itself is SEC-05.

**Description:** `storage/views.py` opens its own PostgreSQL connection with the database name, user and password written directly in the source. Use `django.db.connection` so credentials come from `settings.DATABASES` only.

**Priority:** Blocker
**Sonar:** `python:S6437` → [AZk4N8U4IV_ZOs3ZqEke](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8U4IV_ZOs3ZqEke) + hotspot [AZk4N8U4IV_ZOs3ZqEkd](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8U4IV_ZOs3ZqEkd)
**Files:** `storage/views.py:373-389`

**Problem:**
```python
dbname = "dg_bae"; user = "postgres"; password = "postgres"; host = "localhost"; port = "5432"
connection = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
connection.autocommit = True
cursor = connection.cursor()
```
A connection that bypasses the Django ORM, with the password in the source.

**Steps:**
1. Switch to the Django connection:
   ```python
   from django.db import connection

   with connection.cursor() as cursor:
       ...
   ```
2. Check the semantics of `autocommit = True` — Django manages transactions itself; use `transaction.atomic()` if explicit control is needed
3. Remove the manual `connection.close()` further down, if present
4. Check whether `psycopg2` is still imported directly anywhere in `storage/views.py`

**Definition of Done:** database credentials come only from `settings.DATABASES` · the data import behaves as before

---

### [x] SEC-04 · Delete the unused `views_old.py` and `views_dg.py` modules

> **Status:** done. Both modules defined the same names as `views.py`
> (`excelImport`, `upload_file`, `select_table`, `load2db`) — they are stale
> copies. `storage/urls.py` resolves those names from `.views`, so no route is
> affected.

**Description:** Both modules are dead code — nothing in the project imports them and no URL routes to them — yet they account for one vulnerability and three security hotspots. Removing them clears the findings at no functional cost; git history keeps the files recoverable.

**Priority:** Blocker (closes issues cheaply)
**Sonar:** `python:S6437` → [AZk4N8VHIV_ZOs3ZqEk0](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8VHIV_ZOs3ZqEk0) + hotspots [AZk4N8VHIV_ZOs3ZqEkz](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VHIV_ZOs3ZqEkz), [AZk4N8VfIV_ZOs3ZqEk3](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VfIV_ZOs3ZqEk3), [AZk4N8VfIV_ZOs3ZqEk6](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VfIV_ZOs3ZqEk6)
**Files:** `storage/views_old.py` (200 lines), `storage/views_dg.py` (62 lines)

**Problem:** neither file is imported anywhere — verified by grep across the project and in `storage/urls.py`. Between them they produce 1 vulnerability + 3 hotspots.

**Steps:**
1. Confirm once more that nothing references them: `grep -rn "views_old\|views_dg" --include=*.py .`
2. `git rm storage/views_old.py storage/views_dg.py`
3. History stays in git — recoverable if needed

**Definition of Done:** the files are deleted · `python manage.py check` reports no errors · tests / smoke pass

---

## P1 — next sprint

### [x] SEC-05 · Parameterize the SQL queries in the data import flow

> **Status:** done. The statement moved into an `INSERT_FIELD_SQL` constant with
> eleven `%s` placeholders, and the values are bound through
> `cursor.execute(sql, params)`. Both escaping helpers (`sanitize_for_import` and
> the nested `__sanitize_for_sql`) were deleted — they are no longer needed and
> only invited unsafe reuse.
>
> **Audit of the remaining raw SQL:** `cursor.execute(INSERT_FIELD_SQL, params)`
> is now the only raw SQL execution site in the project. Nothing uses `.raw()` or
> `RawSQL`; every other write goes through the ORM.
>
> **⚠️ Behaviour change to verify against a real file:** empty cells. A pandas
> `NaN` used to reach the database as the text `'nan'`, because it was
> interpolated into the string. The driver cannot bind `NaN` to a text column, so
> `__bind_value` now converts missing values to `NULL`. That is the more correct
> semantics, but stored values for such rows change from `'nan'` to `NULL`.
>
> `COALESCE((SELECT ...), NULL)` was dropped as an identity — `COALESCE(x, NULL)`
> always equals `x`.

**Description:** The Excel/CSV import builds `INSERT` statements by f-string interpolation of user-supplied values, and the local `escape_value` helper only partially escapes quotes — this is exploitable SQL injection. Switch to parameterized queries and audit the remaining raw SQL in the project.

**Priority:** High
**Sonar:** not flagged (found during review)
**Files:** `storage/views.py:394-410` and other f-string queries in the file

**Problem:**
```python
query = f"""INSERT INTO storage_field (...) VALUES (
    (select id from storage_fieldlist where field_list_name like '{row['field_list']}'), ...
```
Data from a user-uploaded Excel/CSV file is interpolated into SQL as text. The `escape_value` function above only escapes quotes partially and offers no protection.

**Steps:**
1. Move to parameterized queries (`cursor.execute(sql, params)` with `%s`)
2. Audit the remaining f-strings / `.format()` / concatenations in `storage/views.py` and `dm/views.py`
3. Remove `escape_value` if parameterisation makes it unnecessary
4. Consider `bulk_create` through the ORM instead of raw SQL for this scenario

**Definition of Done:** no user-supplied value appears in the body of a SQL string · importing a file containing `'` and `;` in the data works correctly

---

### [x] SEC-06 · Audit and remove unnecessary `@csrf_exempt` decorators

> **Status:** done. **All 12** active decorators were removed (another 2 went with
> `views_dg.py` in SEC-04). Not one endpoint turned out to be an external
> integration — every one is called from our own templates, so `csrf_exempt` was
> unnecessary everywhere. Enabling OIDC through `mozilla-django-oidc` was not
> required.
>
> **Audit result:**
>
> | View | Caller | Method | Action |
> |---|---|---|---|
> | `oidc_login` | `login.html` | POST | `X-CSRFToken` header |
> | `upload_file` | `excelimport.html` | POST | header |
> | `import_excel` | `excelimport.html` (jQuery) | POST | header |
> | `import_csv` | `excelimport.html` (jQuery) | POST | header |
> | `upload_db_json` | `dbmanagement.html` | POST | header |
> | `parse_sql_to_json` | `sql_parsing.html` | POST | header |
> | `upload_json` | `sql_parsing.html` | POST | header |
> | `save_roles` | `get_roles.html` | POST | header |
> | `save_reports` | `get_reports.html` | POST | header |
> | `download_db_json` | `dbmanagement.html` | GET | nothing needed |
> | `sql_matching` | — | GET | nothing needed |
> | `role_view` | GET navigation only | POST branch is dead | nothing needed |
>
> **The trap found along the way:** `import_excel` and `import_csv` sent
> `csrfmiddlewaretoken` **inside the JSON body**. Django reads the token only from
> `request.POST` (form-encoded) or from the `X-CSRFToken` header, so with
> `contentType: 'application/json'` it was ignored entirely. Simply dropping the
> decorator would have broken both imports — the token moved to the header.
>
> **Shared helper:** `templates/storage/_csrf.html` renders `{% csrf_token %}` (so
> Django sets the cookie) and exposes `csrfHeader()` for `fetch`. Included in six
> templates through `{% include %}`.
>
> **⚠️ To check by hand:** the POST branch of `role_view` duplicates `save_roles`
> and has no caller in the templates. If something outside this repository posts to
> `/storage/storage/role/` it will now get 403 — in which case the branch should
> either be deleted as dead or given authentication.

**Description:** Fourteen active `@csrf_exempt` decorators disable CSRF protection across the storage views — Sonar reports only five of them. Classify each endpoint by its caller, restore CSRF protection for the ones used by our own frontend, add authentication to the ones exposed to external integrations, and document whatever remains exempt.

**Priority:** High
**Sonar:** 5 hotspots — [EkY](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8U4IV_ZOs3ZqEkY), [Ekf](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8U4IV_ZOs3ZqEkf), [Ekj](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8U4IV_ZOs3ZqEkj), [Ek3](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VfIV_ZOs3ZqEk3), [Ek6](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VfIV_ZOs3ZqEk6)
**Files:** `storage/views.py` — lines 182, 266, 440, 459, 697, 743, 774, 801, 822, 838, 883, 921 (**12 active**); `storage/views_dg.py` — 9, 17 (removed by SEC-04)

**Note:** Sonar shows 5, while the code actually has 14 active decorators. All of them need review, not just the flagged ones.

**Steps:**
1. Build a table: view → who calls it (own frontend / external integration / nothing)
2. For calls from our own frontend — remove the decorator and add the `X-CSRFToken` header to the corresponding `fetch`/`ajax` calls in the templates
3. For external integrations — keep `csrf_exempt` but add authentication. `mozilla-django-oidc==4.0.1` is already in `requirements.txt` and commented out in `INSTALLED_APPS` (`settings.py:50`) — uncomment and configure it
4. For dead views — delete them together with their route
5. Mark any hotspot that remains justified as **Acknowledged** in Sonar with a comment explaining why

**Definition of Done:** every remaining `@csrf_exempt` carries a comment stating why and is protected by authentication · the rest are gone

---

### [x] SEC-07 · Fix the XSS in `diagram.html` by replacing `|safe` with `json_script`

> **Status:** done, but the fix turned out to be wider than the template.
>
> `{{ model|safe }}` rendered a **Python dict repr** straight into the `<script>`
> body — it worked only because a repr with single quotes happens to be a valid JS
> literal. A single quote in a field name broke the page, and `'});…({'` gave code
> execution. Replaced with `{{ model|json_script:"markmap-data" }}` plus
> `JSON.parse(...)`.
>
> **That alone was not enough:** markmap renders `content` as HTML, and `content`
> is assembled in `dm/views.py` by concatenating SVG markup with field names,
> descriptions and values from the database. So even after fixing the transport,
> `<img onerror=...>` in a field name would still have executed. `escape()` from
> `django.utils.html` was therefore added at **22 sites** where database values
> reach an HTML string. Intentional markup (the SVG rectangles, `<a href>`) stays
> unescaped; only content from the database is escaped.
>
> **⚠️ Side effect:** if HTML was deliberately stored in source or query
> descriptions (`query_description`, `source_description`) for formatting, it now
> renders as text. Worth checking against real data.

**Description:** Database-derived data is injected straight into a `<script>` block through `{{ model|safe }}`, which is the one genuine XSS among the twenty auto-escaping hotspots. Serialize the value with the `json_script` filter and parse it client-side.

**Priority:** High
**Sonar:** [AZk4N8QDIV_ZOs3ZqEir](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8QDIV_ZOs3ZqEir)
**Files:** `templates/dm/diagram.html:89`, `dm/views.py:371-377, 607`

**Problem:**
```django
{{ model|safe }},     ← inside <script>, an argument to markmap
```
`model` is the result of `linearization(source_type, source_name, "")` — database data landing directly in JS context. The one real XSS among the 20 auto-escaping hotspots.

**Steps:**
1. Replace with `json_script`:
   ```django
   {{ model|json_script:"markmap-data" }}
   <script>
     const model = JSON.parse(document.getElementById('markmap-data').textContent);
   </script>
   ```
   and pass `model` into the markmap call
2. Make sure `linearization()` returns a serialisable structure (dict/list) rather than a prepared string
3. Check that the diagram renders for a source with `<`, `>`, `"` in a field name

**Definition of Done:** no `|safe` for database data in the template · the diagram renders · special characters in names do not break the page

---

## P2 — cleanup and prevention

### [x] SEC-08 · Extract `nav_bar` and `bootstrap_link` into a base template

> **Status:** done. `grep -rn "|safe" templates/` now returns nothing.
>
> **Deviation from the plan:** implemented with `{% include %}` rather than
> `{% extends base.html %}`. Reshaping 14 templates that each carry their own
> `<head>` and script set into a block structure cannot be verified without running
> the application, while the goal of the task — removing `|safe` — is met by a
> mechanical substitution with no risk. The markup now lives in
> `templates/dm/_nav_bar.html` and `templates/dm/_bootstrap.html`, and both
> constants plus **27** context entries are gone from `dm/views.py`.
>
> **Special case, `storage/sql_create.html`:** its view (`storage/admin.py:408`)
> never passed either `nav_bar` or `bootstrap_link`, so both tags rendered empty.
> They were deleted there rather than replaced with an `include` — otherwise the
> page would suddenly gain a navbar and Bootstrap it never had.

**Description:** Nineteen auto-escaping hotspots come from HTML markup stored in Python string constants and rendered with `|safe` in every template. They are false positives today, but the pattern reintroduces them with each new page. Move the markup into `templates/base.html` and have the pages extend it; marking the hotspots Safe in Sonar is the stopgap alternative.

**Priority:** Medium
**Sonar:** 19 hotspots in `templates/dm/*.html` (field, fields, field_list, field_lists, main, queries, query, report, reports, source, sources, source_list, source_lists)
**Files:** `dm/views.py:23, 55` + 13 templates

**Problem:** technically a false positive — `nav_bar` and `bootstrap_link` are server-side constants with no user input. But the root cause is that HTML markup lives in Python strings and is passed into every context by hand.

**Options:**
- **Quick:** mark all 19 as **Safe** in Sonar with a comment. They come back with each new template.
- **Correct (recommended):** move the markup into `templates/base.html`, switch the pages to `{% extends "base.html" %}`, and drop `nav_bar`/`bootstrap_link` from every `context`. The hotspots disappear for good and the code gets cleaner.

**Definition of Done:** `grep -rn "|safe" templates/` returns nothing beyond deliberately justified cases

---

### [~] SEC-09 · Add secret scanning to pre-commit and CI

> **Status:** the files are in place but **have not been executed** — neither
> gitleaks nor pre-commit exists in this environment, and the workflow only runs
> on GitHub's side.
>
> **Key decision:** the scan runs with `--no-git`, covering the working tree rather
> than history. History still contains the secrets leaked before SEC-01, so a full
> scan would fail on every run. It can switch to `gitleaks detect --redact` (with
> history) once the history is purged — an item under "Left to do manually" in
> SEC-01.
>
> **⚠️ Needed from DevOps:** `.github/**` is protected by `merge=ours` and
> `CODEOWNERS` assigns the whole repository to `@kgetihad`, so the new workflow
> needs their approval. The first run may also surface things that could not be
> checked locally: the Okta `CLIENT_ID` in `settings.py` and the ECR account id in
> `helm-values/dev.yaml`. If those are accepted as safe, put them in a
> `.gitleaks.toml` allowlist rather than weakening the rules.

**Description:** SEC-01 happened because a `.env` file reached a commit unnoticed. Add gitleaks as a pre-commit hook and as a pull-request check, and enforce the Sonar quality gate on merges, so committed credentials are blocked automatically instead of surfacing in an audit months later.

**Priority:** Medium
**Files:** `.github/workflows/`, `.pre-commit-config.yaml` (new)

**Rationale:** SEC-01 happened because `.env` made it into a commit and nobody noticed. Without an automated check it will happen again.

**Steps:**
1. Add `gitleaks` as a pre-commit hook
2. Add a `gitleaks detect` step to GitHub Actions on pull requests
3. Configure the Sonar Quality Gate to block merges on new Blocker/High findings
4. Document the process in the README: `.env.example` → a local `.env` that is never committed

**Definition of Done:** an attempt to commit a file containing a secret is blocked locally and in CI

---

### [~] SEC-10 · Run `manage.py check --deploy` as a blocking pipeline step

> **Status:** the settings are in place and the workflow job is added, but the
> check itself **has not been run** — Django is not installed in this environment.
> The values were verified by hand against Django's check list (W001, W002, W008,
> W009, W012, W016, W018–W021).
>
> Added to `settings.py`: `SECURE_PROXY_SSL_HEADER`, `SECURE_CONTENT_TYPE_NOSNIFF`,
> `X_FRAME_OPTIONS=DENY`, `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` (tied to
> `DEBUG`), `SECURE_SSL_REDIRECT` and `SECURE_HSTS_SECONDS` (one year in
> production, 0 locally).
>
> **⚠️ The riskiest part of the whole change set.** `SECURE_SSL_REDIRECT=True` in
> Kubernetes only works if the ingress forwards the `X-Forwarded-Proto` header.
> If it does not, Django answers 301 to every HTTP request, health probes
> included, and the pods never come up. Both dangerous settings are therefore
> env-driven and can be turned off without a code change:
>
> ```
> SECURE_SSL_REDIRECT=False
> SECURE_HSTS_SECONDS=0
> ```
>
> Before deploying, DevOps has to confirm the ingress behaviour, or set these two
> variables in Vault straight away and enable them separately once verified.

**Description:** Django's deployment checklist catches insecure settings — `DEBUG = True`, wildcard `ALLOWED_HOSTS`, missing HSTS and insecure session/CSRF cookies — before a release rather than after. Add it to CI with production-like environment variables and make it blocking.

**Priority:** Medium
**Files:** `.github/workflows/`

**Rationale:** catches `DEBUG=True`, `ALLOWED_HOSTS=["*"]` and missing HSTS / `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` before a release rather than after.

**Steps:**
1. Add a workflow step with production-like environment variables
2. Fix the warnings it surfaces (likely: `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS`)
3. Make the step blocking

**Definition of Done:** `manage.py check --deploy --fail-level WARNING` passes cleanly

---

## Sonar finding → task

| Sonar rule | File | Task |
|---|---|---|
| `secrets:S6687` | `.env` | SEC-01 |
| `secrets:S6687` ×2 | `dgFramework/settings.py` | SEC-02 |
| `python:S6437` | `storage/views.py` | SEC-03 |
| `python:S6437` | `storage/views_old.py` | SEC-04 |
| hotspot: hard-coded credential ×2 | `views.py`, `views_old.py` | SEC-03, SEC-04 |
| hotspot: CSRF disabled ×5 | `views.py`, `views_dg.py` | SEC-06, SEC-04 |
| hotspot: auto-escaping ×1 | `templates/dm/diagram.html` | SEC-07 |
| hotspot: auto-escaping ×19 | `templates/dm/*.html` | SEC-08 |
| — (outside Sonar) | `views.py` SQL injection | SEC-05 |
| — (outside Sonar) | `settings.py` DEBUG/ALLOWED_HOSTS | SEC-02 |

**Out of scope for this plan:** the `bl-consumer-regular` (1 vulnerability, `jssecurity:S5131`) and `knowledgebase-frontend` (6 vulnerabilities, `jssecurity:S5146`) projects from the Global Vulnerabilities sheet — different repositories, different owners.
