# Development and testing

Wagtail is the only application UI. The site root redirects to Wagtail's login page. Build staff features with Wagtail forms, model viewsets and custom admin views where possible; templates and static assets for contact-name controls extend those admin forms, rather than creating a separate frontend.

The local host lets developers run the reusable CRM app inside real Django and Wagtail before building the payment workflow. It uses Django 5.2 LTS and Wagtail 7.4 LTS with dependencies pinned in `uv.lock`. Supported Python versions are declared in `pyproject.toml`; local development and CI use the Python version in `mise.toml`, currently 3.14.

Use `mise tasks` to discover tasks defined in `mise.toml`. The `check` task runs lint, typing, and workflow validation prerequisites before Django checks; browser installation and testing remain explicit. `mise run dev` (alias `mise run run`) starts the loopback development server. Task commands execute from the project root.

## Layout

| Path | Purpose |
| --- | --- |
| `src/wagtail_crm/` | Reusable app, Contact model, migrations, and Wagtail integration |
| `devsite/` | Local host settings, routes, and synthetic-data command; excluded from the wheel |
| `tests/` | Database, form, CSRF, permission, and demo-seed checks |
| `tests/browser/` | Chromium login, contact creation, and unauthorized-access checks |
| `.data/` | Ignored local SQLite database, random development key, and runtime media |
| `mise.toml` | Tool versions and shared setup, quality, test, and development tasks |
| `.github/workflows/checks.yml` | Code quality, Django coverage, and Chromium CI jobs |

Contacts have an independent stable identifier and person/organization contact type. Person entry uses ordinary Given name and Surname fields; either alone is sufficient, with the displayed name generated on save. Multiword and non-Latin values are accepted. There are no component rows, join controls, naming modes or duplicate editable full name. Organizations use one organization-name field. Email and multiline postal address are optional.

Existing/imported full names are not split. Recorded given components populate Given name; recorded surname/surname2 components populate Surname, including repeated components as grouped values. Only full-only names use one ordinary editable Name field. Unchanged grouped values retain every original component, order and separator; edited groups retain unrelated groups and representable formatting. Organizations have a populated Organization name. Stored multiline full names or known groups use ordinary textareas in their applicable fields. Unchanged values preserve the exact original object, including rich structure and CR/LF/CRLF despite browser normalization. Direct Name edits store a full-only replacement and retain old text/components in private history. Clearing the applicable name fields produces a validation error retaining other work. No Current name instructions, blank-preservation fallback or representation controls remain. Richer component editing and structured postal editing are deferred.

Wagtail’s History destination shows changed fields first, with complete before/after snapshots in collapsed details. Inspect links to the same history and omits the internal UUID from routine details. Both history and its results endpoint require contact-view permission; view-only users have no edit action. Existing Wagtail audit records are retained. Supported create/edit/delete operations record private snapshots atomically, and history survives contact deletion. Existing Contacts migrate with their original PKs, exact names, kinds and email values; no name components, correspondence verification or donor attribution are inferred. Contacts remain independent of login accounts, and shared emails do not merge them. Financial models, provider imports, broad conversion tools and email sending remain unimplemented.

## First run

Install [mise](https://mise.jdx.dev/getting-started.html), then run these commands from the repository root:

```bash
mise trust
mise install
mise run install
mise run migrate
mise run demo
mise exec -- uv run --locked python manage.py createsuperuser
mise run dev
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

Before handing off changes, personally complete these flows in the running UI, including existing unsplit names, recorded structured names, single names and validation recovery. Fix confusing interactions directly; do not add schema/formatting instructions around them. Use populated fields appropriate to the recorded data.

Use individually created disposable local accounts for these checks. Wagtail redirects authenticated users without model permissions to its admin home; denial does not necessarily return an HTTP 403. The tests assert that protected data stays unavailable and prohibited writes do not happen.

## Automated checks

```bash
mise run check
mise run test
```

`mise run check` runs Ruff, mypy, actionlint, Django system checks, and migration consistency checks. `mise run test` runs the fast Django suite against an isolated test database and reports coverage; it does not require the development server or a browser. The default test selection explicitly excludes the browser marker.

## Code quality policy

The Ruff policy follows the broad explicit rule families used by the [Western Friend website](https://github.com/WesternFriend/westernfriend.org/blob/main/pyproject.toml): Django conventions, security checks, timezone handling, import hygiene, exception handling, and modern Python syntax. This project additionally enables pytest rules. Generated migrations are excluded from Ruff, and allowances for assertions, expected numeric results, and synthetic passwords are scoped to tests.

Ruff owns Python formatting and import order. Mypy uses the Django plugin and Django 5.2 stubs to check the reusable app and development host, including untyped function bodies. Missing Wagtail typing information is handled by a targeted override rather than suppressing all missing imports. Coverage is initially informational; it does not substitute for the financial and authorization acceptance scenarios.

```bash
mise run format
mise run typecheck
mise install
mise run hooks-install
mise run hooks
mise run hooks-push
```

The repository uses [prek](https://prek.j178.dev/) from `mise.toml`, configured in `prek.toml`. `mise run hooks-install` installs both pre-commit and pre-push Git hooks. Run `mise install` to provision tools and `mise run install` to sync the locked Python environment first. Built-in hooks check YAML, TOML, JSON, XML, whitespace, final newlines, line endings, merge markers, filename portability, symlinks, executable/shebang consistency, private keys, and files larger than 500 KiB. The size check includes existing files. Markdown hard line breaks are preserved.

Use `mise run hooks-install` rather than calling `prek install` directly. The installer makes prek's generated Git shims enter `mise exec` using the local absolute mise executable path. This loads the project tools for VS Code and other GUI Git clients whose `PATH` may omit mise's shims. The machine-specific path stays inside Git's local hooks directory. Hook arguments and pre-push input are preserved. Rerun the task if mise moves or after reinstalling Git hooks; restarting VS Code or changing shell profiles should not be necessary.

Local Python hooks use `uv run --locked` for Django 5.2 API modernization checks, Ruff lint and formatting checks, whole-project mypy, Django system checks, and missing migrations. Workflow files also run actionlint. Dependency metadata changes check lock freshness. Ruff and Django modernization report changes without rewriting Python; use `mise run format` to apply Ruff fixes. File-hygiene hooks can fix whitespace and line endings; inspect and restage their changes before committing. Private-key detection is a basic guard, not a complete credential scanner.

Commit hooks inspect staged files; push hooks additionally run the fast Django test suite when relevant Python/configuration files changed. `mise run hooks` checks tracked **and untracked** nonignored files without staging them; `mise run hooks-push` runs the same selection including fast tests. Direct `prek run --all-files` covers tracked files only. To check an individual new file, use `prek run --files path/to/file.py`. Deleted files are omitted by prek. Browser tests remain an explicit `mise run browser` check.

Installed BMAD tooling in `.agents/`, `.claude/`, `_bmad/`, and `.github/agents/` is excluded from these hooks; project planning documents in `_bmad-output/` remain checked. Ruff also excludes vendored tooling so `mise run check` and hooks share the project lint scope. Run hooks from a Git checkout with mise tools on `PATH`. Neither command stages or commits changes.

## GitHub Actions

The `Checks` workflow runs on pull requests, pushes to `main`, and manual dispatch. Three independent Ubuntu 24.04 jobs install tools through mise and run `mise run install` against `uv.lock`:

- Code quality: `mise run check` and `mise run hooks`.
- Django tests: `mise run test`, including coverage in the job log and a runner-local XML report.
- Chromium: `mise run browser-install -- --with-deps`, then `mise run browser`.

This covers the checks in `mise run hooks-push` while the dedicated test job adds coverage; tests need not run twice in CI. Chromium installs its Linux system libraries as well as the browser. CI tests use synthetic records and isolated test databases, without production credentials or a running development server.

The workflow uses read-only repository permissions, disables persisted checkout credentials, pins external actions to full commit SHAs with release comments, and cancels superseded runs. It has no deployment, external coverage service, or PR-comment automation. Use `mise run workflow-lint` to validate workflow syntax and expressions locally. Website-specific daisyUI checks and HTML formatters are deferred until this package owns frontend templates.

## Browser checks

Install the Playwright browser once, then run the browser suite:

```bash
mise run browser-install
mise run browser
```

Linux CI or a minimal Linux machine may need system browser dependencies:

```bash
mise run browser-install -- --with-deps
```

The browser suite starts Django's static live server and creates its own synthetic staff accounts in an isolated test database. It does not use the local development administrator or require a separately running server. Tests exercise actual login, Wagtail navigation, ordinary person creation/editing, single names, validation, preservation of existing names, organization names, and denial for a user without CRM permissions. Login starts at the root redirect into Wagtail.

If a managed environment supplies Chromium instead of allowing downloads, select it explicitly:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium mise run browser
```

An optional `CRM_SCREENSHOTS_DIR` environment variable captures a synthetic person-form screenshot during the creation/editing check. Do not commit screenshots or other artifacts containing real donor data. Browser installation or launch failures must be reported as blocked checks, not treated as passing or silently skipped.

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
