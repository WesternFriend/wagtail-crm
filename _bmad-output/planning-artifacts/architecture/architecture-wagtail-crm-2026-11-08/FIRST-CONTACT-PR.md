---
status: done
baseline_commit: 5c02fbe1bf9bc5896eff63dd3d1d55a3778776de
context: []
---

# First contact-management PR

Status: implemented and locally verified, including structured-name editing.

PR title: **Add standards-based contact names and correspondence details**.

Accepted scope: implement directly from this plan. Unknown structure uses a plain full-name field. Known structure uses separately editable, repeatable name components; the full name is generated, never independently maintained. Standards details stay internal. Structured postal address editing is deferred; one multiline field is sufficient.

Outcome: authorized staff can create, edit and inspect a person or organization using one name editor, one optional email and one optional international postal address. Existing Contacts survive unchanged in meaning. This is a development increment toward the complete acknowledgment cycle.

## Bounded implementation

1. `src/wagtail_crm/models.py` and `migrations/`: implement the companion profile, independent UID and small contact-change history. Keep the existing app/model identity and PKs. Add fields permissively, copy exact legacy name/email/kind data using historical migration models, backfill a distinct UID per row, then enforce constraints. Remove or repurpose the old name storage only after copying and testing preservation; never leave two independently editable names.
2. `src/wagtail_crm/contact_profile.py`: add small validated encode/decode/name-rendering helpers for the selected subset. No new library is required initially. Unsupported properties/cardinality/structure produce explicit errors before mutation. No public import/export endpoint or processor adapter in this PR.
3. `src/wagtail_crm/forms.py`, `widgets.py`, widget templates and static files extend Wagtail's existing create/edit forms. Unknown structure uses supplied text without parsing. Confirmed names use repeatable typed components, ordering controls and a read-only generated full name. Exact supported joins and separator parts are retained; invalid submissions preserve entered work. Explicitly returning to supplied text retains earlier structure in history. There is no independently editable generated name, raw JSON UI or separate frontend. Optional multiline postal text and email retain normal validation. Preserve list/search/inspect, URLs and permissions; mutations use the shared atomic operations.
4. `devsite/management/commands/seed_demo.py`, `tests/`: update synthetic examples; test migration from `0001_initial`, profile preservation, edits/history, forms and denied endpoints. Extend the existing Chromium contact test for the edited fields and validation. Update development docs only for actual behavior.

Keep the existing contact add/change/view/delete permissions. Editing correspondence does not confirm donor attribution. Contact-history access requires contact-view permission; no general history/export API or new staff role. History snapshots retain the contact UID independently of a nullable contact link, so ordinary deletion cannot cascade away previous evidence. Retention policy is outside this increment.

## Representative acceptance examples

- Given a legacy Contact, migration preserves its PK, exact name/email/kind and existing relationships; it gains a unique stable UID and no invented structure or confirmation.
- Given `Sukarno`, `Mary Beth van Berg`, or `王小明` supplied as a full name, saving and profile round-trip preserve that name without parsing it.
- Given ordered `surname=王`, `given=小明`, separator empty, render `王小明`; editing given to `大明` renders `王大明` without another name edit. Repeated `surname=Rivera`, `surname=Barrientos` after `given=Diego` render `Diego Rivera Barrientos` with spaces. Preserve multiword components and previous values. Transition from supplied text to confirmed components retains the supplied text in history; a component-losing edit must preserve prior structure in history or fail before mutation.
- Given an organization with no email/address, staff can save it; adding a multiline international address requires no U.S. state or ZIP. Shared emails do not merge records. Existing migrated email values are preserved, without inventing verification.
- Given no contact permissions, inspect/history/mutation are denied. View-only permits inspect/history but denies mutations; add/change/delete remain separately enforced, with existing CSRF protection. Successful create/update/delete records actor/time and old/new snapshots atomically; invalid input changes neither contact nor history. Deletion retains history. Migration uses a system baseline, not a fabricated staff approval.

## Verification and exclusions

Run `mise run check`, `mise run hooks`, `mise run test`, and `mise run browser`. Test fresh/upgrade migrations and profile round-trips, including empty/space/explicit punctuation separators, malformed components, and a preserved legacy email that cannot encode. Confirm search and one-name editing. No production data or migrations are used during planning.

Exclude structured postal address editing, financial models/workflows, PayPal imports/matching, policy review, letters/PDF generation, dispatch, direct email sending, routing/preferences, multiple addresses, and broad interoperability tooling. Passing these cases does not establish operational-cycle readiness.

Initial foundation verification: 77 fast tests and both Chromium tests passed; combined statement/branch coverage reported 95%. `mise run check` and `mise run hooks` passed, including new untracked source files. Fresh/upgrade migration tests passed. The built wheel matches app source and includes migrations/templates while excluding devsite, tests and scripts. Synthetic browser output was visually inspected. The existing development database was not migrated. Independent review findings and fixes are recorded in [implementation triage](reviews/implementation-triage.md).

## Structured-name follow-up — completed

The latest user clarification supersedes the plain-only editor limitation above. Structured-name editing is part of this increment; do not add another planning layer.

Implement straightforward separate fields for confirmed name components in `src/wagtail_crm/forms.py` with a small custom Django widget/template/static script if needed. Reuse the existing validated JSContact name object (ordered, repeated typed components) and shared atomic history operations; no need for fixed first/middle/last columns or a new migration. Support arbitrary repeated given/surname/surname2 components and multiword values, explicit ordering, surname-first and non-Latin names, including names joined without spaces. Preserve existing explicit separator components and exact supported formatting when reopening and saving. Expose only the controls necessary to edit these cases, with ordinary keyboard-operable buttons and labels, no raw JSON. Unknown structure remains a supplied full name; never split it automatically. When components are used, show the generated full name as a read-only preview, not another editable source of truth. Staff may explicitly return to a supplied name, retaining previous structure in history. Invalid submissions preserve entered parts and leave storage/history unchanged. Existing permissions, stale-edit checks, email/address editing and exact legacy migration behavior must remain intact. No finance, sending or structured postal changes.

Update affected form/endpoint tests and add Chromium coverage for creating and editing structured names, repeated/multiword components, zero-space surname-first names, automatic generated-name updates and plain-name preservation. Test invalid parts, history across representation changes and structured data surviving unrelated edits. Run check/hooks/fast tests/browser, visually inspect a synthetic structured editor screenshot, and verify the wheel includes new templates/static files. Reconcile README/development/accepted contact spine and relevant requirements with actual editor behavior, without expanding scope. No public imports or deployment changes. Do not commit or push from the implementation agent.

## Review Triage Log

Structured-editor independent review (each finding classified before grouping):

| ID | Verdict / route | Evidence and disposition |
| --- | --- | --- |
| Blind-1 | medium / patch | Returning from unchanged valid parts overwrites a manually corrected supplied draft; preserve that draft and test the transition. |
| Blind-2 | medium / patch | Single-line controls strip supported CR/LF on save; preserve exact stored values across browser round-trips. |
| Blind-3 | medium / patch | Widget ignores Django error/help attributes and targets a hidden input in structured entry; connect errors to visible controls and a focusable target. |
| Blind-4 | medium / patch | Reordering can disable the focused movement button; move focus to an enabled control after updating. |
| Blind-5 | low / patch | JavaScript trim and Python strip disagree on U+0085/U+FEFF; align the small client nonempty check. |
| Blind-6 | low / patch | Without JavaScript the editor offers nonworking dynamic controls without explanation; add an explicit JavaScript-required fallback message. |
| Blind-7 | medium / patch | Repeated control labels lack row context; add numbered accessible groups and update them after movement. |
| Blind-8 | medium / patch | Browser tests bypass movement and explicit separators; test these handlers and persisted results. |
| Edge-1 | medium / patch | Independently confirmed CR/LF loss in structured controls; covered by the same preservation fix as Blind-2. |
| Edge-2 | medium / patch | Custom field removed CharField null validation; reject nulls in full names, components and separators before database writes. |
| Verification-1 | medium / patch | No test executes either movement handler; extend Chromium coverage for both directions and saved order. |
| Verification-2 | medium / patch | Endpoint tests construct separator payloads directly; exercise the actual widget, preview, unrelated save and conversion through Chromium. |

All findings are bounded implementation or verification corrections; no new policy or planning increment is required.

Final verification: `mise run check` and `mise run hooks` passed; 104 fast tests passed with 96% combined statement/branch coverage; all five Chromium scenarios passed. A further targeted Chromium run verified the final textarea-padding correction. Wheel contents include byte-matching widget templates, CSS, JS and migrations, excluding devsite/tests/scripts. All review findings above were fixed and covered by targeted regressions; none were deferred. Synthetic structured-editor output was visually inspected. No database migration was added or applied.

Wagtail CMS is the only UI. The development root redirects directly to the named Wagtail login route; browser scenarios start at that root. Future features should use Wagtail extension points wherever possible.
