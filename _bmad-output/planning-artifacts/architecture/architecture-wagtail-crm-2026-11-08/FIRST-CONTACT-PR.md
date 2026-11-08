# First contact-management PR

Status: implemented and locally verified on 2026-11-08.

PR title: **Add standards-based contact names and correspondence details**.

Accepted scope: implement directly from this plan. Ordinary name entry remains a plain text field; standards/formatting details stay internal. Structured postal address editing is deferred; one multiline field is sufficient.

Outcome: authorized staff can create, edit and inspect a person or organization using one name editor, one optional email and one optional international postal address. Existing Contacts survive unchanged in meaning. This is a development increment toward the complete acknowledgment cycle.

## Bounded implementation

1. `src/wagtail_crm/models.py` and `migrations/`: implement the companion profile, independent UID and small contact-change history. Keep the existing app/model identity and PKs. Add fields permissively, copy exact legacy name/email/kind data using historical migration models, backfill a distinct UID per row, then enforce constraints. Remove or repurpose the old name storage only after copying and testing preservation; never leave two independently editable names.
2. `src/wagtail_crm/contact_profile.py`: add small validated encode/decode/name-rendering helpers for the selected subset. No new library is required initially. Unsupported properties/cardinality/structure produce explicit errors before mutation. No public import/export endpoint or processor adapter in this PR.
3. Create `src/wagtail_crm/forms.py` and extend `views.py` using Django forms/Wagtail hooks. Staff type a name once into a plain text field. Unchanged names preserve existing structured data; a changed supplied name replaces the current representation and retains previous components/text in history. Internal structured-name edits regenerate the displayed name. No separator/formatting controls, modes, raw JSON, duplicated name, overrides or prompts. One optional multiline address and optional email; clear errors. Preserve list/search/inspect and URLs; history appears within inspect. Form/viewset writes and demo seeding use the shared validated atomic operations.
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

Verification: 77 fast tests and both Chromium tests passed; combined statement/branch coverage reported 95%. `mise run check` and `mise run hooks` passed, including new untracked source files. Fresh/upgrade migration tests passed. The built wheel matches app source and includes migrations/templates while excluding devsite, tests and scripts. Synthetic browser output was visually inspected. The existing development database was not migrated. Independent review findings and fixes are recorded in [implementation triage](reviews/implementation-triage.md).
