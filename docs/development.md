# Development and testing

The local host lets developers run the reusable CRM app inside real Django and Wagtail before building the payment workflow. It uses Django 5.2 LTS and Wagtail 7.4 LTS with dependencies pinned in `uv.lock`. Supported Python versions are declared in `pyproject.toml`; Python 3.12 is the initial CI baseline.

## Layout

| Path | Purpose |
| --- | --- |
| `src/wagtail_crm/` | Reusable app, Contact model, migrations, and Wagtail integration |
| `devsite/` | Local host settings, routes, and synthetic-data command; excluded from the wheel |
| `tests/` | Database, form, CSRF, permission, and demo-seed checks |
| `tests/browser/` | Chromium login, contact creation, and unauthorized-access checks |
| `.data/` | Ignored local SQLite database, random development key, and runtime media |
| `.github/workflows/checks.yml` | Separate Django and Chromium CI jobs |

The current Contact model is deliberately small: a display name, person/organization type, and optional email. Contacts are independent of login accounts, and shared email addresses do not automatically merge them. Financial models and the PayPal adapter are not implemented yet.

## First run

Install a supported Python and [uv](https://docs.astral.sh/uv/getting-started/installation/), then run these commands from the repository root:

```bash
uv sync --locked
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py createsuperuser
uv run python manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000/admin/> and sign in with the credentials you chose. **Contacts** appears in the Wagtail navigation. The seed command adds three synthetic contacts and a **CRM Editors** group, but creates no login accounts. It can be rerun without duplicating those contacts and refuses to run with `DEBUG` disabled.

SQLite needs no separate database service. The host creates its local data directory and a private random development key automatically. The database, key, media, browser artifacts, and virtual environment are not repository content. Email uses the console backend; only use synthetic development data.

The server binds to loopback by default. These settings intentionally use local HTTP and `DEBUG=True`; production settings, MFA, login throttling, private financial artifact workflows, and deployment controls remain separate work.

## Manual UI checklist

1. Start the host, open `/admin/`, and verify that signed-out visitors are sent to the login page.
2. Sign in with your local administrator and open **Contacts**. Confirm the three synthetic entries appear.
3. Add a person or organization, edit it, and inspect the record. Verify an invalid email stays on the form with an error.
4. Create a local staff user in Wagtail and assign **CRM Editors**. Verify that user can manage contacts without being a superuser.
5. Give another local staff user Wagtail admin access without CRM permissions. Verify Contacts is absent and direct `/admin/crm/contacts/` access returns to the admin home with an access-denied message.
6. Sign out and verify the contact list is no longer accessible.

Use individually created disposable local accounts for these checks. Wagtail redirects authenticated users without model permissions to its admin home; denial does not necessarily return an HTTP 403. The tests assert that protected data stays unavailable and prohibited writes do not happen.

## Automated checks

```bash
make check
make test
```

`make check` runs Ruff, mypy, Django system checks, and migration consistency checks. `make test` runs the fast Django suite against an isolated test database and reports coverage; it does not require the development server or a browser. The default test selection explicitly excludes the browser marker.

## Code quality policy

The Ruff policy follows the broad explicit rule families used by the [Western Friend website](https://github.com/WesternFriend/westernfriend.org/blob/main/pyproject.toml): Django conventions, security checks, timezone handling, import hygiene, exception handling, and modern Python syntax. This project additionally enables pytest rules. Generated migrations are excluded from Ruff, and allowances for assertions, expected numeric results, and synthetic passwords are scoped to tests.

Ruff owns Python formatting and import order. Mypy uses the Django plugin and Django 5.2 stubs to check the reusable app and development host, including untyped function bodies. Missing Wagtail typing information is handled by a targeted override rather than suppressing all missing imports. Coverage is initially informational; it does not substitute for the financial and authorization acceptance scenarios.

```bash
make format
make typecheck
uv run pre-commit install
make hooks
```

The pre-commit hooks check YAML, TOML, JSON, whitespace, final newlines, merge markers, case conflicts, and oversized added files, then run Django API modernization and Ruff. Hooks use the same locked uv environment as CI. Run hooks from a Git checkout; `--all-files` covers tracked files, so add new files to Git before checking them.

The GitHub workflow has independent code-quality, Django, and Chromium jobs, read-only repository permissions, pinned action revisions, and no PR-comment automation or external coverage service. Website-specific daisyUI checks and HTML formatters are deferred until this package owns frontend templates.

## Browser checks

Install the Playwright browser once, then run the browser suite:

```bash
uv run playwright install chromium
make browser
```

Linux CI or a minimal Linux machine may need system browser dependencies:

```bash
uv run playwright install --with-deps chromium
```

The browser suite starts Django's static live server and creates its own synthetic staff accounts in an isolated test database. It does not use the local development administrator or require a separately running server. Tests exercise actual login, Wagtail navigation, creating a contact, and denial for a user without CRM permissions.

If a managed environment supplies Chromium instead of allowing downloads, select it explicitly:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium make browser
```

An optional `CRM_SCREENSHOTS_DIR` environment variable captures a synthetic Contacts screenshot after the successful creation check. Do not commit screenshots or other artifacts containing real donor data. Browser installation or launch failures must be reported as blocked checks, not treated as passing or silently skipped.

## PostgreSQL and database portability

SQLite is the local default. To exercise an available disposable PostgreSQL database, install the optional driver and supply its connection URL:

```bash
uv sync --locked --extra postgres
DATABASE_URL=postgresql://crm:local-only@127.0.0.1:5432/crm_dev uv run python manage.py migrate
DATABASE_URL=postgresql://crm:local-only@127.0.0.1:5432/crm_dev uv run pytest
```

The example credentials describe a disposable database you provision locally; they do not configure a production service. Django's test runner needs a role permitted to create its test database. Use the same `DATABASE_URL` for a server process that should use that database.

SQLite does not provide PostgreSQL-equivalent locking and concurrency behavior. Add PostgreSQL CI coverage before implementing concurrent financial writes or relying on row locks. Passing SQLite checks alone does not validate the eventual production database.

## Package boundary

`uv build --wheel` builds the reusable app without `devsite` or the repository's tests. Keep host-specific configuration and demo commands in `devsite`; avoid imports from it inside `wagtail_crm`. Another Django project should be able to install the app and register its Wagtail integration without adopting this development host.
