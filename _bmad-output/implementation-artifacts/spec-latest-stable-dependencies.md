---
title: 'Use current stable dependencies'
type: 'chore'
created: '2026-11-08'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Keep the CRM on the latest stable compatible dependencies, including Django and Wagtail, instead of the previous LTS-only constraints. Refresh the reproducible lock, corresponding tooling and current documentation; preserve existing records and the completed contact UX. Do not start imports, financial features or deployment.

</frozen-after-approval>

## Implementation Notes

- Clean baseline: `11fccf850e07ad879a90bb784c36ef2dcadc5212`. Freeform dependency maintenance, no epic/story. No unresolved intent choices or irreversible actions; existing local database stays untouched.
- Official PyPI and release documentation checked on 2026-11-08: Django 6.1.3, Wagtail 8.1, django-stubs 6.1.2, mypy 2.4.1. Existing Python >=3.12,<3.15 remains compatible; local/CI Python stays 3.14. Other direct runtime/test tools are already latest stable. Hatchling 1.33.0 is already admitted by the build requirement.
- Small footprint: `pyproject.toml`, `uv.lock`, Django API hook target in `prek.toml`, README/development notes and current architecture framework table/references. Existing CI runs the same locked mise tasks; no new workflow required. Preserve historical review reports and migration provenance.
- Use latest stable minor-series constraints and refresh all permitted transitive packages. Keep pytest and contact forms unchanged unless verification demonstrates a compatibility fix is necessary.
- Validate locked sync, lint/types/hooks/system/migration checks, all fast and Chromium tests, wheel build and migration preservation against a disposable SQLite copy. Never migrate or seed the user's database. Read Wagtail 8.0/8.1 and Django 6.0/6.1 upgrade considerations; no custom page models, permission policies, internal admin APIs or removed Django APIs found in the app.

- Lock upgraded Django 5.2.19→6.1.3, Wagtail 7.4.4→8.1, django-stubs 5.2.9→6.1.2, mypy 1.19.1→2.4.1 and draftjs-exporter 5.2.0→7.3.1, adding the new upstream-required dependencies. Audited all 64 locked registry packages: only Wagtail-constrained taggit/treebeard and Playwright-constrained pyee lag their newest major versions; constraints retained.
- Updated Django API hook to 6.1. New mypy/plugin traversal needs targeted missing-stub exclusions for treebeard/modelsearch/modelcluster/taggit alongside Wagtail; application typing remains checked. Removed now-default DEFAULT_AUTO_FIELD setting and replaced deprecated development EMAIL_BACKEND with MAILERS console backend. No application form/view/template changes were required.
- Main Python 3.14: locked sync, check/hooks, 168 fast tests with 95% coverage and 10 Chromium scenarios pass, no warnings. Python 3.12 and 3.13 each install the lock and pass the same 168 fast tests. Fresh SQLite migration/seed succeeds. Existing 5.2/7.4 database copy migrates through Wagtail's new API-token migration; all CRM rows, IDs/history, user/group assignments and CRM permissions match the baseline. Original DB SHA-256 is unchanged. Optional PostgreSQL driver sync succeeds.
- Personal native Brave/Mac walkthrough on a separate fresh synthetic database: root/login, Contacts navigation, person creation and invalid-email recovery, populated reopening, correction to a single name, search/Inspect, history before/after, direct unknown-name correction and organization-only editing. Signed out, closed the walkthrough tab and stopped the server.

- Exercising the optional PostgreSQL path exposed a real Django 6.1 system-check error: Wagtail's search fields/indexes require django.contrib.postgres. The development host now conditionally registers it only for the PostgreSQL engine, retaining driver-free SQLite setup. No new model migration is needed. PostgreSQL tests are rerun after this fix; do not confuse pytest passing without management checks with validated host setup.

## Review Triage Log

| ID | Finding | Verdict and evidence |
| --- | --- | --- |
| R1 | PostgreSQL minimum server version missing | Medium, patched docs with PostgreSQL 15 minimum; local PostgreSQL 15 verification added. |
| R2 | SQLite minimum/library inspection missing | Low, patched docs with SQLite 3.37 minimum and interpreter inspection command; local SQLite 3.50.4. |
| R3 | Django check can access the existing configured database | Low, patched ordering instructions: select DATABASE_URL before checks. Original DB checksum verified unchanged. |
| R4 | Database-copy selection lacks concrete command | Low, patched docs with SQLite consistent backup and explicit DATABASE_URL shell example. |
| R5 | Cross-framework preservation evidence missing from existing migration tests | Medium, addressed with actual 5.2/7.4 database-copy upgrade and exact comparison of all CRM rows, identifiers/history and existing permission assignments. A new test duplicating that temporary verification is unnecessary. |
| R6 | Declared Python 3.12/3.13 not tested on this upgrade | Medium, patched verification: isolated locked installs and 168 passing fast tests on each; CI remains on 3.14. |
| R7 | PostgreSQL verification stops at driver installation | Medium, actual disposable PostgreSQL 15 checks/migrations/tests added; fixed exposed missing contrib.postgres registration. |
| R8 | django-upgrade minimum does not support target 6.1 | False: currently locked/minimum 1.33.0 explicitly lists 6.1 in --help and successfully runs the updated hook. Raising it would invent a nonexistent newer release. |
| R9 | Rollback needs matching code/lock/database/files | Low, patched docs to require the matching backup/revision, identify baseline and rehearse on a copy. |

## Final verification

- `mise run install` (`uv sync --locked`): passes. All direct runtime/dev dependencies at current stable compatible releases.
- `mise run check` and `mise run hooks`: pass; mypy checks 16 source files; no schema migration drift.
- `mise run test`: 168 passed, 10 browser tests deselected, 95% coverage, no warnings on Python 3.14.
- `mise run browser-install` and `mise run browser`: Chromium installed; 10 passed, 168 fast tests deselected, no warnings.
- `uv run --python 3.12 --isolated --locked pytest` and equivalent 3.13: 168 passed each.
- Optional PostgreSQL: locked driver install passes; disposable PostgreSQL 15 container passes the shared check task, all migrations and 168 fast tests with conditional contrib.postgres registration. Container stopped/removed after verification; no persistent PostgreSQL data.
- Fresh synthetic SQLite migration/seed and personal Brave walkthrough pass. Existing database-copy upgrade preserves all CRM rows/history/UIDs and auth assignments; original database hash remains unchanged. The original local database still needs `mise run migrate` before starting the upgraded host.
- Wheel build, framework requirements, source inclusion/isolation and `git diff --check` pass.
- Independent review findings patched or refuted as logged; no deferred feature work or unresolved compatibility blockers. The three upstream compatibility-limited transitive major versions remain documented. No push or deployment.
