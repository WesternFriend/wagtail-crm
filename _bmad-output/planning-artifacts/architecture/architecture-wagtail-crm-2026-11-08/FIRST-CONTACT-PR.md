---
status: done
baseline_commit: 99ab49df47629016ea1ab4149bd10fd57ed98990
context: []
---

# Finish ordinary populated contact forms

The user rejects the blank-name preservation process and requires usable contact management before any further feature work. Implement directly within the existing Wagtail layout; no new planning layer, naming modes, formatting controls or configuration.

## Accepted behavior

- New people have ordinary Given name and Surname fields, neither individually required, with at least one nonblank value. Reopen them populated from recorded components; generate the displayed name without duplicate entry.
- Known structured names, including repeated given/surname/surname2 components, stay in the appropriate populated Given name/Surname fields. Staff edit grouped values naturally; do not split their typed text into components. Preserve exact original objects on unchanged saves and preserve unrelated components and representable ordering/separators on edits. If adding a previously absent name group, use the ordinary default given-before-surname order without moving or splitting existing recorded components.
- Existing names with genuinely unknown structure use one ordinary populated editable Name field. No blank replacement fields, Current name note, hidden preservation semantics or inferred split. Direct edits retain the old data/history. Emptying the applicable name produces an ordinary error and retains other entered work.
- Organizations use one populated Organization name field and no visible person-name fields. Existing multiline values use an ordinary textarea in the applicable field; normalize browser line endings for comparison, retaining exact unchanged source objects. No custom JSON transport.
- Keep ordinary Contact type, inactive-field behavior, optional email/multiline postal data, Wagtail-only UI, stable IDs, history, permissions, CSRF and stale-edit guards. Keep canonical History and complete snapshots; remove a duplicate Inspect History link and empty optional creation-summary rows found during the actual UI walkthrough. Use Changed by rather than exposing the actor field name. Remove organization help that only repeats its label.

## Scope and source map

`forms.py` maps ordinary inputs to the existing validated JSContact name object; `views.py` and the minimal existing form script expose relevant fields through Wagtail. Templates retain the current layout. No migration, import, financial feature, direct sending, data cleanup by inferred splitting, or mutation of existing development records. Existing unknown names stay editable while component conversion awaits confirmed data. Standards remain internal; future address/data forms use familiar appropriate fields populated with known values, without expanding today's agreed multiline-address scope.

Update source, endpoint/browser tests, requirements/acceptance and development notes. Remove obsolete blank-preservation assertions. Preserve all preceding Contact type/history refinements. No commit or push from the implementation agent.

## Acceptance and verification

Run `mise run check`, `mise run hooks`, `mise run test`, `mise run browser`, and wheel isolation/source matching. Verify new/single/multiword/Unicode names; populated unknown and structured representations; repeated components, exact line endings, direct edits, validation recovery, unchanged unrelated data/history, organization/type transitions, proper field visibility, permissions, canonical History and snapshots. No new schema or development-record writes.

Before requesting user review, personally run the app and complete creation/finding/editing/Inspect in a real browser. The native Brave walkthrough used a separate temporary synthetic SQLite database and confirmed unknown Jordan Sample direct editing, blank-name/email error recovery without re-entry, new split multiword people, surname-only 王, organization creation/edit/search/Inspect, optional details, exact multiline preservation and known repeated components in normal fields. A normal CRM editor edited records; staff without CRM permission had no navigation and direct access was denied. Stored outcomes confirmed original names, stable IDs and unrelated family components were preserved. The walkthrough directly fixed duplicate History navigation and empty history rows. No existing development records were touched.

Keep imports and financial workflows paused. Finish and report usable contact management, running-UI evidence, exact checks and remaining limits; do not ask for another redesign review or add instructions around confusing controls.

## Review triage log

Independent blind, edge-case and verification-gap reviews were completed. The edge-case reviewer returned no findings. All implementation findings below were resolved; no blocking findings remain.

| ID | Finding | Decision and resolution |
| --- | --- | --- |
| B1 | Concurrent representation changes could hide submitted work | Patch: retain submitted field shape and values on a stale edit, block the write; regression tests. |
| B2 | Adding a name group could inherit punctuation/empty/newline join | Patch: ordinary space at the new boundary; preserve existing internal formatting; regression cases. |
| B3 | Switching contact type after editing could discard the draft | Patch: carry edited name to an untouched applicable destination while retaining independent drafts; browser case and personal walkthrough. |
| B4 | Changed repeated surname/surname2 group lacked coverage | Patch: test both kinds, preserve unrelated given components and original snapshots. |
| B5 | Interleaved groups lacked reconstruction coverage | Patch: test group replacement without orphan/adjacent separators. |
| B6 | Clearing an entire repeated group lacked coverage | Patch: test valid remaining name and preserved history. |
| B7 | Actual multiline edit and validation recovery lacked browser coverage | Patch: browser regression plus personal running-UI verification. |
| B8 | Null character validation on full Name lacked coverage | Patch: verify normal field errors and no write. |
| B9 | Repeated-name documentation appeared under unrelated sections | Patch: consolidate into the applicable name-profile sections. |
| B10 | Completion plan needed final executed results and evidence link | Reject as a code finding: completion bookkeeping in the specification. Final results recorded below and linked to the existing validation plan. |
| V1 | Repeated surname replacement test gap (same issue as B4) | Patch: covered by the B4 regression cases. |

Final inspection additionally fixed moving a single recorded name between given and surname when the original group is cleared: no leading/trailing separator is introduced, and history retains the original. Two regression cases pass. Synthetic demo people now have explicitly authored given/surname values; existing seeded records are never rewritten or inferred.

## Final verification

- `mise run check`: passed Ruff, format, mypy (16 source files), actionlint, Django system checks and migration drift check; no migration changes.
- `mise run hooks`: passed repository hooks, including all tracked and untracked eligible files.
- `mise run test`: 168 passed, 10 browser tests deselected, 95% coverage.
- `mise run browser`: 10 Chromium tests passed, 168 non-browser tests deselected; synthetic screenshots saved outside the repository.
- `uv build --wheel`: passed; all 15 packaged source/template/static files match current sources byte for byte; migrations included, devsite/tests/scripts excluded.
- `git diff --check`: passed.
- Personal native Brave/Mac walkthrough and stored-outcome readback: [validation evidence](../../prds/prd-wagtail-crm-2026-11-08/validation-plan.md#development-handoff--running-contact-walkthrough). Includes create/find/edit/Inspect, optional details, single/unknown/repeated names, multiline errors, type-switch drafts, normal staff and denied users. Disposable session signed out and server stopped; existing database untouched.

Remaining bounded limitations: no inferred splitting or component-conversion tool for unknown historical names; richer component controls and structured address editing are deferred. This finishes contact management within its current scope, not Editor acceptance or financial validation. Imports and financial workflows remain paused. No push or PR creation.
