---
status: done
baseline_commit: 236a0ea555ffb42fe525623837e9d946fe243fbb
context: []
---

# Contact-management refinement

PR title: **Clarify contact details and unify Wagtail history**.

The user confirmed the ordinary person/organization forms through synthetic testing and requested four targeted refinements. Keep that form layout, Wagtail-only UI, optional given-name/surname fields, generated displayed names, and exact preservation of imported/unstructured names. No further naming controls or redesign.

## Implemented scope

1. Emphasize “Current name: Pat Morgan” with a short blank-fields-preserve-it note. Escape supplied values, retain canonical names, and never split them automatically.
2. Use the existing Wagtail History destination from edit and Inspect. Native History table/pagination shows changed fields first, preserving before/after values, actor/date/origin, structure-only and whitespace-only changes. Complete original snapshots remain in closed, keyboard-accessible disclosures with contextual accessible labels. Retain Wagtail's original audit records, without presenting a competing history. View-only users can return to Inspect and get no edit action. Both history and results require contact-view permission.
3. Label kind as Contact type across forms/list/filter/Inspect/history while retaining underlying kind/person/organization values. The metadata-only 0003 migration records this label and proper contact-change names for native pagination. It has not been applied to the existing development database.
4. Omit the UUID from routine Inspect fields; preserve independent UID and every stored snapshot. Avoid repeating unchanged fields in visible update summaries.

## Acceptance and verification

- Existing full/repeated names remain intact during correspondence edits. Current-name context and short notes are visible; no extra naming controls are introduced.
- Edit and Inspect link to the same History URL. Changed name/type/email/address values appear in summaries; unchanged fields remain only in the complete snapshots. Created and migrated records render safely; structural/whitespace changes remain explainable. Supplied text is escaped.
- Native pagination links and results replacement show the selected records. History queries remain bounded as rows increase. Snapshot disclosures stay closed until explicitly opened.
- View-only staff may see history/results and return to Inspect, without edit links. No-view staff, including add-only/change-only/delete-only, are denied private history/results.
- Existing PK, UID, names, history and Wagtail log entries survive the label migration. Existing development records and the user's stopped server remain untouched.

Final local results: `mise run check` and `mise run hooks` passed; **135 fast tests passed at 96% combined statement/branch coverage**; **7 Chromium scenarios passed**. Synthetic current-name and history screenshots were visually inspected. The wheel matches app source and includes the new label migration and history template, excluding devsite/tests/scripts. No local migrations were applied.

## Review Triage Log

| Finding | Verdict / route | Evidence and disposition |
| --- | --- | --- |
| Blind-1: actor profiles may cause N+1 queries | low / patch | Eager-loaded actor profiles; bounded-query regression passes. |
| Blind-2: whitespace-only changes look identical | medium / patch | Added a concise explanation while preserving exact values in snapshots; tested. |
| Blind-3: new English labels lack translation markers | low / reject | The confirmed first-release CRM interface is English. Broader localization is deferred to demonstrated need; this refinement makes no locale-aware CRM label claim. |
| Blind-4: view-only history lacks return-to-contact breadcrumb | medium / patch | Added Inspect breadcrumb without an edit action; tested. |
| Blind-5: rendered pagination/results navigation unverified | medium / patch | Chromium follows Next/Previous, verifies records and URL, and checks the selected-page results fragment. |
| Blind-6: restricted permission combinations unverified | medium / patch | Explicit add-only/change-only/delete-only denial tests cover both endpoints. |
| Blind-7: creation/baseline rendering unverified | medium / patch | Added complete collapsed-snapshot and meaningful-summary cases, including Initial record labeling. |
| Blind-8: disclosures lack accessible row context | low / patch | Accessible labels include action/date/change identity; visible labels remain concise and closed by default. |
| Verification-1: changed postal address absent from summary tests | medium / patch | Both endpoints now verify escaped multiline old/new address values outside details, with unrelated fields omitted. |

The independent edge-case review found no additional issues. All retained findings were fixed. Visual inspection also corrected the native pagination plural and made the requested snapshot disclosures visibly actionable using Wagtail's existing button styles. No new UI system or audit platform was introduced.

## Boundaries

Wagtail remains the sole UI; root redirects to its login. More elaborate name editing, structured postal editing, importing/matching, financial workflows, letters, dispatch and direct sending remain deferred. These synthetic checks do not establish stakeholder authority, financial policy or operational acknowledgment readiness. Requirements, acceptance criteria and supporting development docs reflect these refinements.
