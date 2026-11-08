---
title: 'Resolve contact-management PR review findings'
type: 'refactor'
created: '2026-11-08'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Check and fix the supplied PR #2 findings on feat/contact-management, preserving the agreed ordinary Wagtail UX and existing data/history. Simplify name derivation and duplicated forms/views, recover invalid stored names in the edit form, label history actions/origins, fold unreleased migration 0003 into 0002, and use Wagtail's Inspect fields for postal address. Add query-count and invalid-name regressions; run check/hooks/test/browser and update the PR description. Questions about organization conversion and stale deletion require the user's answers before changing those behaviors.

</frozen-after-approval>

## Implementation Notes

- Clean baseline `d9f8a715edc2b6f6cd77b56d0ac4f6f7ccb84a01`; PR #2 targets main. Existing development database must stay untouched while the unreleased migrations are consolidated. Validate only fresh/disposable copies.
- Keep decoded-import full/component conflict rejection. Model persistence derives display/full from recorded components without reading the original name. UID validation/immutability remains in clean; it still needs the stored UID, but save no longer calls clean. Document query counts and avoid adding a cache or second validation API merely to hide that required check.
- Pending user choices asked asynchronously; all other findings are authorized. No import or financial feature work.

- User confirmed both choices: organization conversion stores full text and keeps prior structure in history; stale-delete protection belongs in this increment. Added a required hidden revision to the ordinary Wagtail confirmation form; malformed/missing/stale submissions cannot delete, and a stale failure redirects to fresh confirmation with an explanation.
- Consolidated migration choices/labels and kind metadata in 0002; deleted 0003. Kept immutable historical migration literals instead of importing live enums. A developer with an already-applied old schema must rehearse on a fresh database/pre-0002 copy; no original database is rewritten.

## Review triage log

All supplied implementation findings were confirmed and fixed. The requested elimination of the full original-name lookup was applied; a targeted UID lookup remains in clean to honor the simultaneously requested immutability rule. No name-derivation lookup or save-time clean remains.

| ID | Finding | Verdict and resolution |
| --- | --- | --- |
| U1 | Repeated name validation/read in save | Medium, patched pure derivation and standard full_clean/service validation; service edit is 7 queries including transaction statements; direct existing-model save performs one UPDATE and no SELECT. Decode still rejects imported full/component conflicts. |
| U2 | Invalid stored name crashes edit | Medium, patched validation-first initialization and empty ordinary Name/Organization name repair input. Invalid saves retain work and do not change storage/history. |
| U3 | Duplicate create/edit methods | Low, patched shared typed Django FormMixin. |
| U4 | Duplicate unused form field declarations | Low, removed viewset form_fields, restricted Meta to model fields and retained ordinary ordering with field_order. |
| U5 | Magic action/origin strings and raw labels | Low, added TextChoices, service enum members and display labels. Migration uses frozen literal choices, not live model imports. |
| U6 | Redundant unreleased migration | Low, folded 0003 metadata and choices into 0002, deleted 0003; drift check and fresh migration regression pass. Existing databases untouched; development reset/rehearsal caveat documented. |
| U7 | Repeated multiline widget logic | Low, consolidated helper and split initialization/inactive-field responsibilities without new controls. |
| U8 | Custom Inspect address markup | Low, postal address is a native Inspect field with escaped line breaks. Removed the override template/selector; retained history_url context required for Wagtail's native History link. |
| UQ1 | Person components survive organization conversion | User confirmed conversion to full-only organization name; previous structure retained in history. Patched and tested. |
| UQ2 | Delete confirm ignores intervening changes | User requested protection now. Required hidden revision, locked comparison, atomic rejection and fresh confirmation added. |
| R1 | Explicit multiline initial override can get text input | Low, patched widget selection to use effective initial; regression for person and organization. |
| R2 | Direct existing save/no-read guarantee lacked proof | Medium verification gap, added one-query UPDATE regression with edited components. |
| R3 | full_clean UID immutability lacked direct test | Medium verification gap, added field-specific full_clean failure and unchanged persisted UID assertion. |
| R4 | Stale delete Wagtail audit rollback untested | Medium verification gap, assert no delete log on rejection and exactly one on fresh confirmation. |
| R5 | Delete-history failure rollback untested | Medium verification gap, inject failure and verify contact, CRM history and Wagtail log are unchanged. |
| R6 | Malformed organization repair untested | Medium verification gap, parameterized malformed JSON and empty names across both kinds, retaining old evidence. |
| R7 | Rejected repair state could be hidden by later repair | Medium verification gap, assert exact name/email/revision/history before the successful followup. |

## Verification

- `mise run check` and `mise run hooks`: passed; mypy checks 16 source files; Django system and migration drift checks clean.
- `mise run test`: 186 passed, 11 browser tests deselected, 96% coverage.
- `mise run browser`: 11 Chromium scenarios passed, 186 fast tests deselected, including stale-delete/reconfirmation.
- Fresh disposable SQLite database migrated through 0002 and seeded successfully. Existing development database remained byte-unchanged.
- Personal native Brave/Mac smoke pass: invalid legacy row opens, blank-name validation/recovery, native multiline Inspect layout, readable History labels, second-tab edit invalidates open deletion confirmation and preserves the contact; cancel returns to Contacts. Synthetic account signed out, own tabs closed and temporary server stopped.
- Independent review findings addressed as above; no remaining feature-policy question or deferred fix from this request.
