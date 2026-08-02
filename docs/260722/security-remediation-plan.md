# Security Remediation Plan — data_governance

**Джерело:** SonarQube Cloud, проєкт `BankalEtihad_data_governance`, гілка `master`
(вигрузка `Book5.xlsx` + `image-20260712-092958.png` від 12.07.2026)

**Обсяг:** 5 Vulnerabilities (BLOCKER) + 27 Security Hotspots (HIGH) + 4 знахідки поза Sonar

**Легенда статусів:** `[ ]` не почато · `[~]` в роботі · `[x]` готово · `[-]` відхилено/не актуально

---

## Зведення

| Пріоритет | Тасок | Закриває Sonar issues | Оцінка |
|---|---|---|---|
| P0 | 4 | 5 vulnerabilities + 2 hotspots | ~0.5 дня |
| P1 | 3 | 5 hotspots + 2 поза Sonar | 1–2 дні |
| P2 | 3 | 19 hotspots + превентив | ~1 день |

### Task index (EN)

| ID | Title | Priority |
|---|---|---|
| SEC-01 | Rotate leaked credentials and untrack `.env` | Blocker |
| SEC-02 | Remove the hardcoded SECRET_KEY and move DEBUG / ALLOWED_HOSTS to environment variables | Blocker |
| SEC-03 | Replace the standalone psycopg2 connection with the Django database connection | Blocker |
| SEC-04 | Delete the unused `views_old.py` and `views_dg.py` modules | Blocker |
| SEC-05 | Parameterize the SQL queries in the data import flow | High |
| SEC-06 | Audit and remove unnecessary `@csrf_exempt` decorators | High |
| SEC-07 | Fix the XSS in `diagram.html` by replacing `\|safe` with `json_script` | High |
| SEC-08 | Extract `nav_bar` and `bootstrap_link` into a base template | Medium |
| SEC-09 | Add secret scanning to pre-commit and CI | Medium |
| SEC-10 | Run `manage.py check --deploy` as a blocking pipeline step | Medium |

---

## P0 — критичне, робити зараз

### [~] SEC-01 · Ротація секретів і вилучення `.env` з git

> **Статус:** код-частину виконано. Ротація креденшлів у Vault та в БД потребує
> доступу до інфраструктури — див. «Залишилось вручну» в кінці таски.

**EN title:** Rotate leaked credentials and untrack `.env`
**EN description:** The `.env` file is tracked by git despite being listed in `.gitignore`, exposing the Django secret key, the database password and the superuser password in repository history. Rotate every affected credential, remove the file from version control and replace it with a value-less `.env.example` template.

**Пріоритет:** Blocker
**Sonar:** `secrets:S6687` → [issue AZk4N8VqIV_ZOs3ZqEk-](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8VqIV_ZOs3ZqEk-)
**Файли:** `.env`, `.gitignore`, `.env.example` (новий)

**Проблема:**
`.env` присутній у `.gitignore`, але трекається git-ом — `.gitignore` не діє на файли, вже додані в індекс.
```
$ git ls-files .env
.env
$ git log --oneline -- .env
2f565e9 Database configuration correction #2
582ffc8 Add .env file
```
У файлі: `DJANGO_SECRET_KEY`, `DB_PASSWORD`, `DJANGO_SUPERUSER_PASSWORD` (5 символів).
Значення вже в історії репозиторію — у кожного, хто робив clone.

**Кроки (порядок важливий — спочатку ротація):**
1. Змінити пароль користувача БД `postgres` на боєвому й тестовому оточеннях
2. Змінити `DJANGO_SUPERUSER_PASSWORD` на нормальної довжини
3. Згенерувати новий `SECRET_KEY`:
   `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
4. Оновити секрети в Helm values / CI secrets (`helm-values/`)
5. `git rm --cached .env && git commit -m "Remove .env from version control"`
6. Додати `.env.example` без значень:
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

**Опціонально (координувати з командою):** повне очищення історії
`git filter-repo --path .env --invert-paths` + force push + переклонування у всіх розробників.
Якщо репозиторій приватний і секрети ротовані — не обов'язково, issue закриється й без цього.

**Definition of Done:** `git ls-files .env` порожній · `.env.example` у репо · всі старі секрети недійсні · застосунок стартує на новому наборі

**Зроблено:**
- [x] `.env` вилучено з індексу git, файл залишився на диску
- [x] Додано `.env.example` без значень
- [x] Локальний `DJANGO_SECRET_KEY` перевипущено (50 символів)
- [x] Видалено з `settings.py` два `OIDC_RP_CLIENT_SECRET` від Okta і пароль `vTmPW3cF5Uv3p24`, що лежали в коментарях (Sonar їх не бачив)

**Залишилось вручну (потрібен доступ до інфраструктури):**
- [ ] Змінити пароль користувача БД і оновити `DB_PASSWORD` у Vault (`secret/data/data-governance`)
- [ ] Перевипустити `DJANGO_SECRET_KEY` у Vault — локальна ротація на прод не впливає
- [ ] Замінити `DJANGO_SUPERUSER_PASSWORD` (поточний — 5 символів) у Vault і в самому обліковому записі
- [ ] Відкликати обидва скомпрометовані Okta client secret в адмінці Okta (`eu-bankaletihad.okta.com`, `dev-24630760.okta.com`) — вони в історії git і чинні, доки їх не відкликати
- [ ] Вирішити щодо очищення історії git (`git filter-repo --path .env --invert-paths`) — потребує force push і переклонування у всіх

---

### [x] SEC-02 · Прибрати хардкоджений SECRET_KEY, перевести DEBUG/ALLOWED_HOSTS на env

> **Статус:** виконано.
>
> **Знахідка під час роботи:** `.env` у проєкті не читався ніким — ні `python-dotenv`,
> ні `django-environ` не було в залежностях. Саме тому й існувала гілка
> `platform.system() == "Windows"` з хардкодженими креденшлами: на локальній машині
> env-змінних просто не було. Тому в обсяг таски додано `python-dotenv==1.2.2` і
> виклик `load_dotenv()` — інакше видалення Windows-гілки зламало б локальну розробку.
> Реальні env-змінні мають пріоритет над `.env`, тож у Kubernetes значення з Vault
> продовжують перекривати файл.
>
> **⚠️ Перед деплоєм — потрібна дія DevOps:**
> `DEBUG` і `ALLOWED_HOSTS` відсутні в `helm-values/dev.yaml`. Тепер `DEBUG` без
> змінної дефолтиться у `False` (це і є фікс — раніше прод працював з `DEBUG=True`),
> а `ALLOWED_HOSTS` виводиться з `HOST`, який у Vault уже є. Але якщо kubelet
> звертається до поду за IP, health-проби почнуть отримувати 400 — тоді треба явно
> задати `ALLOWED_HOSTS` у Vault, включно з pod CIDR або `.svc.cluster.local`.
> `helm-values/**` захищений `merge=ours` і належить DevOps, тому я його не чіпав.

**EN title:** Remove the hardcoded SECRET_KEY and move DEBUG / ALLOWED_HOSTS to environment variables
**EN description:** `settings.py` holds the Django secret key both in a comment and as an `os.environ` fallback, ships with `DEBUG = True` and `ALLOWED_HOSTS = ["*"]` hardcoded, and keeps a Windows-only `DATABASES` branch with plaintext credentials. Read all of these from the environment and fail fast on startup when the secret key is missing.

**Пріоритет:** Blocker
**Sonar:** `secrets:S6687` ×2 → [AZk4N8TCIV_ZOs3ZqEjE](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8TCIV_ZOs3ZqEjE), [AZk4N8TCIV_ZOs3ZqEjF](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8TCIV_ZOs3ZqEjF)
**Файли:** `dgFramework/settings.py:24-25, 34, 36, 103-113`

**Проблема:**
```python
# SECRET_KEY = "django-insecure-o!46yfbflocr&c9s3z8(azkfz..."          # L24, у коментарі
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-...')  # L25, як fallback
DEBUG = True                                                             # L34, хардкод
ALLOWED_HOSTS = ["*"]                                                    # L36
```
Fallback небезпечніший за сам хардкод: якщо env-змінна не проставилась у проді, застосунок не впаде — тихо підніметься з публічно відомим ключем, і session cookies та password-reset токени стають підробними.
`DEBUG = True` у проді віддає повний стектрейс з усіма settings (включно з креденшлами БД) на будь-якій 500-ці. Змінна `DEBUG` з `.env` зараз ігнорується.

**Кроки:**
1. Видалити закоментований ключ (L24)
2. `SECRET_KEY = os.environ['DJANGO_SECRET_KEY']` — fail-fast на старті
3. `DEBUG = os.environ.get('DEBUG', 'False').lower() in ('1', 'true', 'yes')`
4. `ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')`
5. Прибрати гілку `if platform.system() == "Windows"` у `DATABASES` (L103-113 містить `"PASSWORD": "postgres"`) — одна конфігурація з `os.environ`, локальні відмінності живуть у локальному `.env`
6. Прибрати закоментовані блоки `DATABASES` нижче
7. Прибрати невикористаний `import platform`, якщо більше ніде не потрібен

**Definition of Done:** у `settings.py` немає жодного літерального секрету · застосунок падає з явною помилкою без `DJANGO_SECRET_KEY` · `DEBUG` керується через env

---

### [x] SEC-03 · Прибрати окреме psycopg2-підключення з хардкодженими креденшлами

> **Статус:** виконано. `load2db()` тепер працює через `django.db.connection`,
> імпорт `psycopg2` з `views.py` прибрано (пакет лишається в залежностях — його
> використовує сам бекенд Django).
>
> **Побічно виправлено:** з'єднання і курсор закривалися лише в гілці `except`,
> тобто при успішному імпорті текли. Тепер курсор звільняє `with`-блок, а
> з'єднанням керує Django. Параметризація самого запиту — окремо в SEC-05.

**EN title:** Replace the standalone psycopg2 connection with the Django database connection
**EN description:** `storage/views.py` opens its own PostgreSQL connection with the database name, user and password written directly in the source. Use `django.db.connection` so credentials come from `settings.DATABASES` only.

**Пріоритет:** Blocker
**Sonar:** `python:S6437` → [AZk4N8U4IV_ZOs3ZqEke](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8U4IV_ZOs3ZqEke) + hotspot [AZk4N8U4IV_ZOs3ZqEkd](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8U4IV_ZOs3ZqEkd)
**Файли:** `storage/views.py:373-389`

**Проблема:**
```python
dbname = "dg_bae"; user = "postgres"; password = "postgres"; host = "localhost"; port = "5432"
connection = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
connection.autocommit = True
cursor = connection.cursor()
```
Підключення в обхід Django ORM з паролем у коді.

**Кроки:**
1. Замінити на з'єднання Django:
   ```python
   from django.db import connection

   with connection.cursor() as cursor:
       ...
   ```
2. Перевірити семантику `autocommit = True` — Django керує транзакціями сам; якщо потрібен окремий контроль, використати `transaction.atomic()`
3. Прибрати ручний `connection.close()`, якщо є нижче по коду
4. Перевірити, чи `psycopg2` ще імпортується напряму десь у `storage/views.py`

**Definition of Done:** креденшли БД беруться лише з `settings.DATABASES` · імпорт даних працює як раніше

---

### [x] SEC-04 · Видалити мертвий код `views_old.py` і `views_dg.py`

> **Статус:** виконано. Обидва модулі визначали ті самі імена
> (`excelImport`, `upload_file`, `select_table`, `load2db`), що й `views.py` —
> це старі копії. `storage/urls.py` бере їх з `.views`, тож маршрути не зачеплені.

**EN title:** Delete the unused `views_old.py` and `views_dg.py` modules
**EN description:** Both modules are dead code — nothing in the project imports them and no URL routes to them — yet they account for one vulnerability and three security hotspots. Removing them clears the findings at no functional cost; git history keeps the files recoverable.

**Пріоритет:** Blocker (закриває issue дешево)
**Sonar:** `python:S6437` → [AZk4N8VHIV_ZOs3ZqEk0](https://sonarcloud.io/project/issues?id=BankalEtihad_data_governance&issues=AZk4N8VHIV_ZOs3ZqEk0) + hotspots [AZk4N8VHIV_ZOs3ZqEkz](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VHIV_ZOs3ZqEkz), [AZk4N8VfIV_ZOs3ZqEk3](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VfIV_ZOs3ZqEk3), [AZk4N8VfIV_ZOs3ZqEk6](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VfIV_ZOs3ZqEk6)
**Файли:** `storage/views_old.py` (200 рядків), `storage/views_dg.py` (62 рядки)

**Проблема:** обидва файли не імпортуються ніде — перевірено grep-ом по всьому проєкту та `storage/urls.py`. Разом генерують 1 vulnerability + 3 hotspots.

**Кроки:**
1. Ще раз підтвердити відсутність посилань: `grep -rn "views_old\|views_dg" --include=*.py .`
2. `git rm storage/views_old.py storage/views_dg.py`
3. Історія залишається в git — за потреби відновлюється

**Definition of Done:** файли видалені · `python manage.py check` без помилок · тести/смоук проходять

---

## P1 — наступний спринт

### [x] SEC-05 · SQL injection в імпорті даних

> **Статус:** виконано. Запит винесено в константу `INSERT_FIELD_SQL` з 11
> плейсхолдерами `%s`, значення передаються через `cursor.execute(sql, params)`.
> Обидва хелпери екранування (`sanitize_for_import` і вкладений
> `__sanitize_for_sql`) видалено — вони більше не потрібні й лише провокували
> небезпечне повторне використання.
>
> **Аудит решти raw SQL:** `cursor.execute(INSERT_FIELD_SQL, params)` — тепер
> єдине місце виконання сирого SQL у проєкті. `.raw()` і `RawSQL` не
> використовуються ніде, решта запису йде через ORM.
>
> **⚠️ Зміна поведінки, яку треба перевірити на реальному файлі:** порожні
> клітинки. Раніше `NaN` з pandas потрапляв у БД як текст `'nan'`, бо підставлявся
> в рядок. Тепер драйвер не може прив'язати `NaN` до текстової колонки, тож
> `__bind_value` конвертує порожні значення в `NULL`. Це коректніша семантика,
> але значення в базі для таких рядків зміняться з `'nan'` на `NULL`.
>
> `COALESCE((SELECT ...), NULL)` прибрано як тотожність — `COALESCE(x, NULL)`
> завжди дорівнює `x`.

**EN title:** Parameterize the SQL queries in the data import flow
**EN description:** The Excel/CSV import builds `INSERT` statements by f-string interpolation of user-supplied values, and the local `escape_value` helper only partially escapes quotes — this is exploitable SQL injection. Switch to parameterized queries and audit the remaining raw SQL in the project.

**Пріоритет:** High
**Sonar:** не позначено (знайдено при рев'ю)
**Файли:** `storage/views.py:394-410` та інші f-string запити в файлі

**Проблема:**
```python
query = f"""INSERT INTO storage_field (...) VALUES (
    (select id from storage_fieldlist where field_list_name like '{row['field_list']}'), ...
```
Дані з Excel/CSV, завантаженого користувачем, підставляються у SQL текстовою інтерполяцією. Функція `escape_value` вище робить лише часткове екранування лапок і не захищає.

**Кроки:**
1. Перевести на параметризовані запити (`cursor.execute(sql, params)` з `%s`)
2. Аудит решти f-string / `.format()` / конкатенацій у `storage/views.py` і `dm/views.py`
3. Прибрати `escape_value`, якщо після параметризації вона стає непотрібною
4. Розглянути `bulk_create` через ORM замість raw SQL для цього сценарію

**Definition of Done:** жодного користувацького значення в тілі SQL-рядка · імпорт файлу з `'` та `;` у даних працює коректно

---

### [x] SEC-06 · Аудит 15 входжень `@csrf_exempt`

> **Статус:** виконано. Знято **всі 12** активних декораторів (ще 2 пішли разом
> з `views_dg.py` у SEC-04). Жоден ендпоінт не виявився зовнішньою інтеграцією —
> усі викликаються з наших власних шаблонів, тож `csrf_exempt` не був потрібен
> ніде. OIDC через `mozilla-django-oidc` вмикати не довелося.
>
> **Результат аудиту:**
>
> | В'юха | Викликач | Метод | Дія |
> |---|---|---|---|
> | `oidc_login` | `login.html` | POST | заголовок `X-CSRFToken` |
> | `upload_file` | `excelimport.html` | POST | заголовок |
> | `import_excel` | `excelimport.html` (jQuery) | POST | заголовок |
> | `import_csv` | `excelimport.html` (jQuery) | POST | заголовок |
> | `upload_db_json` | `dbmanagement.html` | POST | заголовок |
> | `parse_sql_to_json` | `sql_parsing.html` | POST | заголовок |
> | `upload_json` | `sql_parsing.html` | POST | заголовок |
> | `save_roles` | `get_roles.html` | POST | заголовок |
> | `save_reports` | `get_reports.html` | POST | заголовок |
> | `download_db_json` | `dbmanagement.html` | GET | нічого не потрібно |
> | `sql_matching` | — | GET | нічого не потрібно |
> | `role_view` | тільки GET-переходи | POST-гілка мертва | нічого не потрібно |
>
> **Пастка, яку знайшов по дорозі:** `import_excel` і `import_csv` слали
> `csrfmiddlewaretoken` **у тілі JSON**. Django читає токен лише з `request.POST`
> (form-encoded) або з заголовка `X-CSRFToken`, тож при `contentType:
> 'application/json'` він ігнорувався повністю. Просте зняття декоратора зламало б
> обидва імпорти — токен переведено в заголовок.
>
> **Спільний хелпер:** `templates/storage/_csrf.html` — рендерить `{% csrf_token %}`
> (щоб Django виставив куку) і дає `csrfHeader()` для `fetch`. Підключений у шести
> шаблонах через `{% include %}`.
>
> **⚠️ Що перевірити руками:** POST-гілка `role_view` дублює `save_roles` і не має
> викликача в шаблонах. Якщо на `/storage/storage/role/` ходить щось поза репозиторієм,
> воно отримає 403 — тоді цю гілку треба або видалити як мертву, або дати їй
> автентифікацію.

**EN title:** Audit and remove unnecessary `@csrf_exempt` decorators
**EN description:** Fourteen active `@csrf_exempt` decorators disable CSRF protection across the storage views — Sonar reports only five of them. Classify each endpoint by its caller, restore CSRF protection for the ones used by our own frontend, add authentication to the ones exposed to external integrations, and document whatever remains exempt.

**Пріоритет:** High
**Sonar:** 5 hotspots — [EkY](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8U4IV_ZOs3ZqEkY), [Ekf](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8U4IV_ZOs3ZqEkf), [Ekj](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8U4IV_ZOs3ZqEkj), [Ek3](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VfIV_ZOs3ZqEk3), [Ek6](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8VfIV_ZOs3ZqEk6)
**Файли:** `storage/views.py` — рядки 182, 266, 440, 459, 697, 743, 774, 801, 822, 838, 883, 921 (**12 активних**); `storage/views_dg.py` — 9, 17 (знімається через SEC-04)

**Примітка:** Sonar показує 5, у коді фактично 14 активних декораторів. Розбирати треба всі, не лише позначені.

**Кроки:**
1. Скласти таблицю: в'юха → хто викликає (власний фронтенд / зовнішня інтеграція / нічого)
2. Для викликів з власного фронтенду — прибрати декоратор, додати заголовок `X-CSRFToken` у відповідні `fetch`/`ajax` виклики в шаблонах
3. Для зовнішніх інтеграцій — залишити `csrf_exempt`, але обов'язково додати автентифікацію. `mozilla-django-oidc==4.0.1` уже в `requirements.txt`, у `INSTALLED_APPS` закоментований (`settings.py:50`) — розкоментувати й налаштувати
4. Для мертвих в'юх — видалити разом з маршрутом
5. Хотспоти, що залишились обґрунтовано, позначити в Sonar як **Acknowledged** з коментарем-обґрунтуванням

**Definition of Done:** кожен `@csrf_exempt`, що лишився, має коментар з причиною і захищений автентифікацією · решта видалені

---

### [x] SEC-07 · XSS у `diagram.html`

> **Статус:** виконано, але фікс виявився ширшим за шаблон.
>
> `{{ model|safe }}` рендерив **Python-repr словника** прямо в тіло `<script>` —
> працювало це лише тому, що repr зі одинарними лапками випадково є валідним
> JS-літералом. Одна лапка в назві поля ламала сторінку, а `'});…({'` давало
> виконання коду. Замінено на `{{ model|json_script:"markmap-data" }}` +
> `JSON.parse(...)`.
>
> **Але цього мало:** markmap рендерить `content` як HTML, а `content` збирається
> в `dm/views.py` конкатенацією SVG-розмітки з назвами полів, описами й значеннями
> з БД. Тобто після фікса транспорту `<img onerror=...>` в назві поля все одно
> виконався б. Тому додано `escape()` з `django.utils.html` — **22 місця**, де
> значення з БД потрапляють у HTML-рядок. Навмисна розмітка (svg-прямокутники,
> `<a href>`) лишається неекранованою, екранується лише вміст із бази.
>
> **⚠️ Побічний ефект:** якщо в описах джерел чи запитів (`query_description`,
> `source_description`) навмисно зберігали HTML для форматування, він тепер
> показуватиметься як текст. Треба глянути на реальних даних.

**EN title:** Fix the XSS in `diagram.html` by replacing `|safe` with `json_script`
**EN description:** Database-derived data is injected straight into a `<script>` block through `{{ model|safe }}`, which is the one genuine XSS among the twenty auto-escaping hotspots. Serialize the value with the `json_script` filter and parse it client-side.

**Пріоритет:** High
**Sonar:** [AZk4N8QDIV_ZOs3ZqEir](https://sonarcloud.io/security_hotspots?id=BankalEtihad_data_governance&hotspots=AZk4N8QDIV_ZOs3ZqEir)
**Файли:** `templates/dm/diagram.html:89`, `dm/views.py:371-377, 607`

**Проблема:**
```django
{{ model|safe }},     ← всередині <script>, аргумент markmap
```
`model` = результат `linearization(source_type, source_name, "")` — дані з БД, що потрапляють напряму в JS-контекст. Єдиний справжній XSS з 20 hotspots групи auto-escaping.

**Кроки:**
1. Замінити на `json_script`:
   ```django
   {{ model|json_script:"markmap-data" }}
   <script>
     const model = JSON.parse(document.getElementById('markmap-data').textContent);
   </script>
   ```
   і передати `model` у виклик markmap
2. Переконатися, що `linearization()` повертає серіалізовану структуру (dict/list), а не готовий рядок
3. Перевірити рендер діаграми на джерелі з `<`, `>`, `"` у назві поля

**Definition of Done:** у шаблоні немає `|safe` для даних з БД · діаграма рендериться · спецсимволи в назвах не ламають сторінку

---

## P2 — прибирання й превентив

### [ ] SEC-08 · Прибрати 19 hotspots `nav_bar|safe` / `bootstrap_link|safe`

**EN title:** Extract `nav_bar` and `bootstrap_link` into a base template
**EN description:** Nineteen auto-escaping hotspots come from HTML markup stored in Python string constants and rendered with `|safe` in every template. They are false positives today, but the pattern reintroduces them with each new page. Move the markup into `templates/base.html` and have the pages extend it; marking the hotspots Safe in Sonar is the stopgap alternative.

**Пріоритет:** Medium
**Sonar:** 19 hotspots у `templates/dm/*.html` (field, fields, field_list, field_lists, main, queries, query, report, reports, source, sources, source_list, source_lists)
**Файли:** `dm/views.py:23, 55` + 13 шаблонів

**Проблема:** технічно false positive — `nav_bar` і `bootstrap_link` є серверними константами без користувацького вводу. Але причина в тому, що HTML-розмітка живе в Python-рядках і передається в кожен контекст вручну.

**Варіанти:**
- **Швидкий:** позначити всі 19 як **Safe** у Sonar з коментарем. Повернуться при додаванні нового шаблону.
- **Правильний (рекомендовано):** винести розмітку в `templates/base.html`, сторінки перевести на `{% extends "base.html" %}`, видалити `nav_bar`/`bootstrap_link` з усіх `context`. Хотспоти зникають назавжди, код чистішає.

**Definition of Done:** `grep -rn "|safe" templates/` не повертає нічого, крім свідомо обґрунтованих випадків

---

### [ ] SEC-09 · Secret scanning у CI та pre-commit

**EN title:** Add secret scanning to pre-commit and CI
**EN description:** SEC-01 happened because a `.env` file reached a commit unnoticed. Add gitleaks as a pre-commit hook and as a pull-request check, and enforce the Sonar quality gate on merges, so committed credentials are blocked automatically instead of surfacing in an audit months later.

**Пріоритет:** Medium
**Файли:** `.github/workflows/`, `.pre-commit-config.yaml` (новий)

**Обґрунтування:** SEC-01 стався тому, що `.env` потрапив у коміт і ніхто не помітив. Без автоматичної перевірки повториться.

**Кроки:**
1. Додати `gitleaks` як pre-commit hook
2. Додати крок `gitleaks detect` у GitHub Actions на PR
3. Налаштувати Sonar Quality Gate на блокування merge при нових Blocker/High
4. Задокументувати в README процес: `.env.example` → локальний `.env`, який ніколи не комітиться

**Definition of Done:** спроба закомітити файл з секретом блокується локально й у CI

---

### [ ] SEC-10 · `manage.py check --deploy` у пайплайні

**EN title:** Run `manage.py check --deploy` as a blocking pipeline step
**EN description:** Django's deployment checklist catches insecure settings — `DEBUG = True`, wildcard `ALLOWED_HOSTS`, missing HSTS and insecure session/CSRF cookies — before a release rather than after. Add it to CI with production-like environment variables and make it blocking.

**Пріоритет:** Medium
**Файли:** `.github/workflows/`

**Обґрунтування:** ловить `DEBUG=True`, `ALLOWED_HOSTS=["*"]`, відсутність HSTS / `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` ще до релізу.

**Кроки:**
1. Додати крок у workflow з продакшн-подібними env-змінними
2. Виправити warnings, які він покаже (ймовірно: `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS`)
3. Зробити крок блокуючим

**Definition of Done:** `manage.py check --deploy --fail-level WARNING` проходить чисто

---

## Трасування Sonar → таска

| Sonar rule | Файл | Таска |
|---|---|---|
| `secrets:S6687` | `.env` | SEC-01 |
| `secrets:S6687` ×2 | `dgFramework/settings.py` | SEC-02 |
| `python:S6437` | `storage/views.py` | SEC-03 |
| `python:S6437` | `storage/views_old.py` | SEC-04 |
| hotspot: hard-coded credential ×2 | `views.py`, `views_old.py` | SEC-03, SEC-04 |
| hotspot: CSRF disabled ×5 | `views.py`, `views_dg.py` | SEC-06, SEC-04 |
| hotspot: auto-escaping ×1 | `templates/dm/diagram.html` | SEC-07 |
| hotspot: auto-escaping ×19 | `templates/dm/*.html` | SEC-08 |
| — (поза Sonar) | `views.py` SQL injection | SEC-05 |
| — (поза Sonar) | `settings.py` DEBUG/ALLOWED_HOSTS | SEC-02 |

**Не входить у цей план:** проєкти `bl-consumer-regular` (1 vulnerability, `jssecurity:S5131`) та `knowledgebase-frontend` (6 vulnerabilities, `jssecurity:S5146`) з аркуша Global Vulnerabilities — інші репозиторії, інші власники.
