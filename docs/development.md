# Development and testing

This is an alpha project with no existing installations. Wagtail is its only UI; the root redirects to Wagtail login. Use Django/Wagtail built-ins first. Contact fields are ordinary columns; stock actions, permissions and history provide the workflow.

Django 6.1.3 and Wagtail 8.1 are locked in `uv.lock`. Python support is declared in `pyproject.toml`; mise and CI use Python 3.14. SQLite 3.37+ is the default; PostgreSQL requires 15+ and the optional driver.

## Setup

```bash
mise trust
mise install
mise run install
mise run migrate
mise run demo
mise exec -- uv run --locked python manage.py createsuperuser
mise run dev
```

Open <http://127.0.0.1:8000/admin/>. The seed command creates three synthetic contacts and a CRM Editors group (contacts, plus payment view and import), without creating logins or default passwords. It is repeatable and refuses to run outside DEBUG. Assign CRM Editors to a separately created staff account.

These local settings use HTTP, loopback and DEBUG; they do not establish production readiness. Email uses a console mailer. Keep donor data, credentials, generated documents and backups private; develop with synthetic data. Runtime database/key/media files live in ignored `.data/`.

## Fresh alpha schema

The distribution is `wagtail_crm`; install the Django app `wagtail_crm.contacts`, label `wagtail_crm_contacts`. It has one fresh `contacts/migrations/0001_initial.py`. Old databases using the former `wagtail_crm` app label are not upgraded or imported. Keep any old local file as a backup and select a fresh SQLite database, or recreate and reseed your disposable development database. Do not remove migration records to force compatibility.

For a fresh database without touching the existing default file:

```bash
export DATABASE_URL=sqlite:////absolute/path/to/new-alpha.sqlite3
mise run migrate
mise run demo
mise exec -- uv run --locked python manage.py createsuperuser
mise run dev
```

People use Given name and Family name, either alone or both. Organizations use Name. Changing an organization to a person requires staff-entered Given name and/or Family name; the organization name is never split automatically. Email and multiline postal address are optional. Standard Wagtail History records actions, users and times; deleted contact activity remains in Reports → Site history. A menu hook exposes that existing report to CRM staff without page permissions. A small Inspect extension preserves postal-address line breaks; other views use framework defaults.

There is no bespoke audit model, snapshot display, migration-baseline entry or optimistic locking. Concurrent editing follows Wagtail last-save-wins; protection is deferred. Import/export mappings, complex name formatting and structured address editing remain later work.

## Payments

`wagtail_crm.payments` (label `wagtail_crm_payments`) imports PayPal Activity Download CSVs. Payments → Import PayPal CSV uploads a file and previews the rows to import and the rows skipped, each with a reason; nothing is saved until staff confirm, and confirmation saves every new row in one transaction or none. Transaction ID is the identity, so an overlapping file adds only new transactions and a repeated file has nothing to confirm. Skipped rows are shown, not stored. Between preview and confirm the uploaded text waits in the staff member's database session; it is removed on confirm, cancel, a new upload or session expiry.

Imported: `Completed` rows in USD whose Transaction Event Code is T00xx with Balance Impact Credit (received) or T11xx with Debit (refunds and reversals). Skipped with a reason: other statuses, outgoing T00xx payments, withdrawals and other codes, other currencies, malformed amounts or dates, and TimeZone values other than US abbreviations (PST/PDT, MST/MDT, CST/CDT, EST/EDT) or UTC/GMT. These assumptions come from PayPal's documentation; #12 confirms them against a real export. Synthetic fixtures are in `tests/fixtures/paypal/`; upload `activity.csv` to try the flow.

Imported values are read-only: the stock list, Inspect and History views show them, and the Edit form has no fields until donor linking (#6). CRM Editors can view and import, not change or delete. Times are stored in UTC. Each staff member sees them in the zone chosen under Account → Preferences → Current time zone (Wagtail's built-in preference; `WAGTAIL_USER_TIME_ZONES` can limit the choices), otherwise in `TIME_ZONE`, which stays UTC. Which zone decides reporting-period boundaries, for example whether a gift late on December 31 Pacific time counts in that year, is an open decision for reconciliation (#8).

## Layout and package boundary

| Path | Purpose |
| --- | --- |
| `src/wagtail_crm/` | Distribution package, not a Django app |
| `src/wagtail_crm/contacts/` | Contact model/form, Wagtail integration, initial migration and namespaced static asset |
| `src/wagtail_crm/payments/` | Payment model, PayPal CSV reader, import view and Wagtail integration |
| `devsite/` | Synthetic development host and demo command; excluded from the wheel |
| `tests/` | Staff-task, permission, model/form, seed and hook tests |
| `tests/browser/` | Chromium tests using Django's isolated static live server |

Payments does not depend on contacts yet; later finance/letters apps may depend on contacts; contacts imports no sibling domain or development host. No shared core or generic audit app exists. Build with `mise exec -- uv build --wheel`; verify migrations/static files are included and devsite/tests are excluded.

## Checks and manual walkthrough

```bash
mise run check
mise run hooks
mise run test
mise run browser-install
mise run browser
```

`check` runs Ruff, mypy, actionlint, system checks and migration drift. `test` runs fast pytest/Django tests with coverage, excluding browser tests. Browser tests exercise real Wagtail login, person/organization creation and editing, optional details, validation recovery, contact-type changes and single names, search/Inspect/history, deletion activity and denied access. They use synthetic accounts and their own database; no separate server is needed. Linux may need `mise run browser-install -- --with-deps`. A managed Chromium can be selected with `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`. Optional `CRM_SCREENSHOTS_DIR` saves a synthetic form screenshot; do not commit private data.

Before requesting review, personally run these tasks in the application: create/find/edit/Inspect a person and organization; reopen known fields populated; change an organization to a person without automatic name splitting; save a single name and blank optional details; recover from invalid email/name errors; view standard History and Site history; verify a staff account without contact permission cannot access contact records. For payments, as a CRM Editor: import `tests/fixtures/paypal/activity.csv` and check the preview's counts and reasons, confirm, Inspect the refund, upload the same file again and see nothing to confirm, then import `activity-overlap.csv`. Fix confusing interactions directly instead of adding instructions.

## Tools, hooks and CI

`mise tasks` lists commands; `mise install` provisions tools and `mise run install` synchronizes the lock. Use `mise run format` for Ruff fixes. Ruff owns formatting/imports, mypy checks the app and host with Django stubs, and missing upstream typing uses targeted overrides. Coverage is informational, not financial validation.

Install Git hooks with `mise run hooks-install`. The installer makes generated prek shims enter the local absolute mise executable, so VS Code and other GUI Git clients load the same tools. Machine-specific paths remain in `.git/hooks`; reinstall if mise moves. Hook arguments and pre-push input are preserved.

`mise run hooks` covers tracked and untracked nonignored files; `mise run hooks-push` also runs fast tests. Commit hooks inspect staged files. Plain `prek run --all-files` covers only tracked files. Hooks check file hygiene, conflicts, private keys, size, lock freshness, Django API modernization, Ruff, mypy, system checks and migrations. Inspect/restage any hygiene fixes; commands do not stage or commit. Installed BMAD tooling is excluded; project planning files remain checked. Browser tests stay explicit.

GitHub Actions runs the same locked mise tasks in three Ubuntu 24.04 jobs: quality/hooks, fast tests/coverage and Chromium. Actions are SHA-pinned, repository permissions are read-only, checkout credentials are not persisted, and superseded runs are cancelled. There is no deployment or external coverage upload.

## PostgreSQL and dependency updates

```bash
mise exec -- uv sync --locked --extra postgres
DATABASE_URL=postgresql://crm:local-only@127.0.0.1:5432/crm_dev mise run migrate
DATABASE_URL=postgresql://crm:local-only@127.0.0.1:5432/crm_dev mise run test
```

Use a disposable database and a role that can create the test database. The host enables `django.contrib.postgres` for that backend. SQLite tests do not establish PostgreSQL financial locking behavior; verify it when those workflows exist.

Track current stable compatible releases. Review upstream compatibility/release notes, update minor-series constraints deliberately, run `mise exec -- uv lock --upgrade`, then install and run all checks. CI uses the same lock. Wagtail currently bounds django-taggit and django-treebeard; Playwright bounds pyee. Keep upstream compatibility constraints rather than forcing unrelated major versions.

For later operational installations, back up database/private files and rehearse upgrades and recovery against a copy before migration. Framework system checks can access configured databases, so set DATABASE_URL to the intended disposable database first. Refresh collected static assets after deployed upgrades.
