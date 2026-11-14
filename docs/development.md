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

Open <http://127.0.0.1:8000/admin/>. The seed command creates three synthetic contacts and a CRM Editors group (contacts, plus payment view, import and edit), without creating logins or default passwords. It is repeatable and refuses to run outside DEBUG. Assign CRM Editors to a separately created staff account.

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

Imported values are read-only. The Edit page shows them under From PayPal, and staff set only the donor and the charitable amount. The donor is chosen, or created, in Wagtail's contact chooser, which uses the Contacts form and its rules. The charitable amount runs from 0 to the amount received (the gross); blank means it still needs deciding, and 0 means none of the payment is a gift. The fee never reduces it, and the non-charitable amount is the gross minus the charitable amount. Refunds (PayPal event codes T11xx) take neither value. A refund is matched to its original payment through Reference Txn ID when the page is shown, not stored, so a refund imported before its payment links once the payment arrives. A payment's Edit and Inspect pages list its refunds and the adjusted charitable amount: the charitable amount plus the (negative) refund total, never below 0 and blank while the charitable amount is blank. The list's Refunded column sums them, and the Unmatched refund filter lists refunds whose original payment is not imported. Database constraints hold both rules for every writer, not only the Edit page. The list filters Needs donor and Needs charitable amount cover received payments only. A contact with linked payments cannot be deleted. Re-importing never changes these decisions, because known transaction IDs are skipped. Imports write no per-payment log entries, so a payment's History starts with staff edits; the success message reports the count imported. CRM Editors can view, import and edit payments, not delete them. Times are stored in UTC. Each staff member sees them in the zone chosen under Account → Preferences → Current time zone (Wagtail's built-in preference; `WAGTAIL_USER_TIME_ZONES` can limit the choices), otherwise in `TIME_ZONE`, which stays UTC. Reporting periods also run in UTC, from midnight on the start date to midnight after the end date, so a gift at 11:30 p.m. Pacific time on December 31 counts in the next year.

Payments → Record check enters a mailed check: the date received, check number, amount, donor and charitable amount, all required. It is stored as a payment with no fee, dated noon UTC on the date received so it shows that date in every US time zone and falls on that UTC day. It counts toward the donor's letter like a PayPal payment, and its letter line reads "Check" and the number. Check numbers aren't unique: two banks can print the same number, so only PayPal Transaction IDs are. Entering the same check twice is not blocked; it shows twice in the list and on the letter preview. A PayPal row is skipped as already imported only if a PayPal row has its ID, and a refund matches only a payment from its own source, so a check number never matches a PayPal row. Staff correct a check on its Edit page, and History keeps each change; an issued letter keeps its values, so a correction letter is needed if one is affected. The list's Source filter separates checks from PayPal rows, and search finds a check by number.

Reconciliations → Add compares a period's imported totals with the totals staff enter from PayPal's report for the same UTC range: the count, gross, fees and net of completed USD payments received, and refunds, with PayPal's signs. Each difference is shown. Mailed checks are not in PayPal's report, so they are left out of the comparison and listed below it with their count and gross. Staff can accept only when every received payment in the period has a charitable amount and no refund in it is unmatched; accepting records the totals in the History entry, and an accepted reconciliation cannot be changed. Letters can be issued only for an accepted reconciliation. CRM Editors can add, edit and view reconciliations, not delete them.

## Letters

`wagtail_crm.letters` (label `wagtail_crm_letters`) issues a donor's acknowledgment letter for an accepted reconciliation. Letters → Issue letter takes a donor and a period; Preview PDF opens the letter in a new tab without saving anything, and Issue letter saves it. The letter lists the donor's received payments in the period with their received, charitable (adjusted for refunds) and goods-or-services amounts, and the charitable total; payments with nothing charitable after refunds are left out. Issuing is refused while any of the donor's payments in the period needs a charitable amount, when the donor has no contributions in it, and for a second original letter for the same donor and period. The letter's date is the UTC day it was issued, the same basis as the period.

Letters → Donors due a letter lists, for an accepted period (the latest by default), each donor whose charitable total for the period is at least the threshold and who has no letter for it yet, with that total and an Issue letter link that fills in the issue form. The total is the letter's own: the same function computes both. A correction never brings a donor back to the list. The threshold is the `WAGTAIL_CRM_LETTER_THRESHOLD` setting, a decimal amount (default `250.00`). That default is a placeholder: the amount, and whether the rule is per year or per gift, wait on the Bookkeeper ([#26](https://github.com/WesternFriend/wagtail-crm/issues/26)). Issue letter links show only to staff who can issue letters.

Issuing renders the PDF with ReportLab and saves the letter with the values it shows in a transaction; the PDF file is written just before the row, so an interrupted issue can leave an unused file in the `letters` storage (recovery is deferred). History shows one entry, "Issued letter". Issued letters cannot be edited or deleted, by superusers either: a permission policy refuses both. Issue correction on a letter's page issues a new letter for the same donor and period from the current data, linked to the earlier one; each letter can be corrected once, so corrections form one chain. Correcting a letter that was already corrected, from an old link or a second tab, explains which letter to correct instead. PDFs are kept in the `letters` storage (`.data/letters/` here), outside `MEDIA_ROOT`, and served only by Download PDF, which checks the letter's view permission and marks the response private and uncacheable. CRM Editors can issue and view letters.

Staff send letters themselves and record each attempt: Record dispatch on a letter's page takes the channel (post or email), the date (today in UTC by default), the outcome (sent or failed) and a note, which a failed attempt requires (a database constraint holds that for every writer). The letter's page lists its dispatches, and the Letters list shows each letter's dispatch status with a Dispatch filter: Not sent, Sending failed, Sent or Superseded. Any sent dispatch makes a letter sent, even after a failed attempt; a letter replaced by a correction is Superseded and drops out of Not sent, though a dispatch can still be recorded for it. Downloading a PDF records nothing. A dispatch can be edited to fix a mistake, and History keeps the edit, but it stays on its letter and cannot be deleted, by superusers either. CRM Editors can record, edit and view dispatches.

## Layout and package boundary

| Path | Purpose |
| --- | --- |
| `src/wagtail_crm/` | Distribution package, not a Django app |
| `src/wagtail_crm/admin_views.py` | `CRMViewSet`: Wagtail's delete, history, usage and inspect views, checking permission before they look the record up |
| `src/wagtail_crm/contacts/` | Contact model/form, Wagtail integration, initial migration and namespaced static asset |
| `src/wagtail_crm/payments/` | Payment model, PayPal CSV reader, import and check views, and Wagtail integration |
| `src/wagtail_crm/letters/` | Letter model, PDF template and Wagtail integration |
| `devsite/` | Synthetic development host and demo command; excluded from the wheel |
| `tests/` | Staff-task, permission, model/form, seed and hook tests |
| `tests/browser/` | Chromium tests using Django's isolated static live server |

Payments depends on contacts for the donor; letters depends on contacts and payments; contacts imports no sibling domain or development host. No shared core or generic audit app exists. Build with `mise exec -- uv build --wheel`; verify migrations/static files are included and devsite/tests are excluded.

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
