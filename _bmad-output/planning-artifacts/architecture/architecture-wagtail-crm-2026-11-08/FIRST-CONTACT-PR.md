---
status: done
route: oneshot
baseline_commit: dfc2f2a43bb11490779eeb2ea69d7f183a295c09
context: []
---

<frozen-after-approval>

## Intent

Implement Brylie's approved smaller contact slice: one distribution with a contacts Django app, ordinary given/family/unsplit/organization name columns, familiar Wagtail editing and standard Wagtail history/permissions. Delete JSON codecs, custom history/snapshots/services, revision locking and their tests. Add AGENTS.md/CLAUDE.md simplicity guardrails and the planning YAGNI gate. No existing installations require migration; use a fresh initial migration, retain old local database files untouched, and document recreation/reseeding. Family name is the label; no migration baseline. Approved six staff-task AC-18 criteria replace the earlier implementation-specific rules. Future standards mappings/concurrency remain deferred. Do not start imports, finance or letters.

</frozen-after-approval>

## Implementation Notes

- All six pending decisions were explicitly resolved by the user. Stock Wagtail actions already log atomically; no additional log-data or change-display layer is required by the user's framework-only clarification.
- Keep this as one small domain implementation, replacing/deleting code rather than creating another planning layer. Verify check/hooks/test/browser, empty SQLite/PostgreSQL migration+seed, package contents and a personal running-UI walkthrough. Record line counts and update PR #2.

## Result and verification

- Replaced the former top-level app with `wagtail_crm.contacts`, label `wagtail_crm_contacts`, and one fresh initial migration. Kept UUIDs, ordinary name/contact columns, derived searchable names, existing contact URLs and native model permissions. No existing installations need an upgrade path; the original local SQLite file remained byte-for-byte unchanged.
- Removed the JSON codec, services, custom history/snapshots/templates, revision counter, stale-edit/delete protection and tests of those removed features. History uses Wagtail actions/user/time, without custom before/after data. Concurrent-edit protection and import/export mappings are deferred. No migration-baseline entries.
- Only two small framework extensions remain: Inspect preserves postal-address line breaks, and a menu hook exposes Wagtail's existing Site history report to CRM staff without page permissions. The report itself retains Wagtail permission filtering.
- Added root AGENTS.md, a CLAUDE.md pointer, and the planning simplicity gate. Reconciled the six approved AC-18 tasks and supporting requirements with the implementation.
- On Python 3.14: `mise run check` and `mise run hooks` passed; `mise run test` passed **30 tests**, **94% branch-aware coverage**; `mise run browser` passed **5 Chromium scenarios**. An independent PostgreSQL 15 fast run passed **30 tests**. Empty SQLite and PostgreSQL 15 migrations and synthetic seeding passed. The disposable PostgreSQL container was stopped afterward.
- Built the wheel and verified its source bytes, new migration and namespaced JavaScript; development host, tests and retired modules/templates are excluded.
- Personally walked the running UI in Brave on a Mac as a normal CRM Editor with no page permissions: login, single/non-Latin person name, blank optional details, invalid-email recovery, populated edit fields, search/Inspect, standard History, directly editable unsplit name, organization creation/edit/Inspect and Reports → Site history. A separate restricted account lacked Contacts navigation and was denied direct access. Automated Chromium additionally verified type changes, name-error recovery and deletion activity. This is synthetic developer evidence, not Editor acceptance or financial validation.
- Physical Python/JavaScript/HTML lines, including migrations: `src/` **1,190 → 229**, `tests/` **2,800 → 648**, compared with pre-reduction head `dfc2f2a43bb11490779eeb2ea69d7f183a295c09`. The originally reviewed `d9f8a715edc2b6f6cd77b56d0ac4f6f7ccb84a01` had 1,143 and 2,604 respectively; these totals differ from the review's approximate added-line counts.

## Review Triage Log

One independent review; no additional review layers. All six actionable findings were patched:

- Medium: obsolete AC-18 interoperability row still required unsupported mappings; removed it in favor of the approved staff tasks.
- Medium: obsolete standards-profile approval blocker contradicted the reduced scope; removed it from current decisions.
- Low: dangling FR23 reference left the acceptance introduction inconsistent; corrected the introduction.
- Medium: current validation handoff still claimed removed components/custom snapshots and old test counts; replaced it with current evidence.
- Medium: existing-contact type changes lacked a browser regression; added person → organization → unsplit person coverage.
- Medium: Site history results/CSV privacy needed direct coverage; verified deleted-contact labels remain inaccessible without contact permissions using an independent authenticated client. An initial failure came from reusing the editor's flash-message cookie, not report leakage; the isolated client passes without an application workaround.

Original review findings 1, 2, 6 and 7 no longer describe retained code: the JSON validation/codec, legacy backfill migrations and multiline name editor were deleted. Finding 8's custom Inspect template was also removed; native fields with a small line-break renderer provide the required result. Findings 3–5 are satisfied by stock CRUD views, one form field definition and Wagtail's own labeled history actions. The user's later approval explicitly supersedes earlier stale-delete protection and before/after-history proposals.
