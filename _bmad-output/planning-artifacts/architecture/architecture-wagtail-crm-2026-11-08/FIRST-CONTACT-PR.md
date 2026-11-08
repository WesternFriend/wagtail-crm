---
status: done
baseline_commit: 5055d2f5b4518676c9093aeb3eb47121a81a17af
context: []
---

# First contact-management PR

PR title: **Simplify person entry to ordinary Wagtail name fields**.

The user found the component editor confusing. This accepted scope supersedes the earlier component-row, join and naming-mode UI. Wagtail is the sole UI, including future workflows; the site root redirects to its login page. No separate frontend or new planning layer is needed.

## Current increment

- Adding a person opens one ordinary Wagtail form with Given name and Surname. Neither is individually mandatory; a new person requires at least one nonblank value. Single names, multiword values and Unicode work. Generate the displayed name without duplicate entry. New names use given then surname, with a space when both are present.
- Populate simple existing components only from their recorded meanings. Unchanged saves preserve the exact original object, including ordering and separators. Existing full names, repeated/unsupported components and other names outside the simple editor stay visible as recorded context; blank replacement fields keep them during correspondence edits. Never guess how to split text or force name reconstruction to edit email/address.
- Explicit replacement values preserve the prior name and provenance through existing atomic history. Supported simple-component corrections retain existing formatting where representable. Richer name editing is deferred until demonstrated need.
- Organizations keep one ordinary organization-name field. Only relevant fields and labels are visible for the selected kind. Existing names that a single-line field cannot preserve remain recorded context until explicitly replaced.
- Remove the custom name widget/module, component templates, join controls, naming modes, generated preview and obsolete JS/CSS. A minimal Wagtail form script may toggle person/organization field visibility. Use the existing name representation and services; no migration is required.

## Preservation and permissions

Retain existing Contact PKs, stable UID, kind/email/address values, URLs, search, inspection, migration behavior, private history, stale-edit rejection and add/change/view/delete permissions. No name change establishes identity attribution, financial approval or correspondence readiness. Keep one optional email and multiline international postal address; structured postal editing remains deferred. No database mutation outside isolated tests.

## Representative acceptance

- Given Mary Beth / van Berg, save Mary Beth van Berg; either field alone also saves. Neither has an individual required marker. Both blank for a new person show a clear error and retain correspondence input.
- Given an existing unparsed full name or repeated components, correspondence-only saves preserve the exact stored name. Known surname-first names and supported separators are retained internally without exposing editing controls. Imported text is never parsed automatically.
- Given a supported known component correction or an explicit replacement for an unsupported name, save the generated name and retain the original snapshot in history. Invalid input and stale edits leave stored data/history unchanged.
- Given an organization, show its single name field. Hidden person/organization fields do not leave irrelevant labels behind. Existing multiline organization names survive unrelated browser saves exactly.
- Given staff without CRM permissions, deny access and mutation; view-only and CSRF rules remain unchanged. All UI remains within Wagtail.

## Verification

Run `mise run check`, `mise run hooks`, `mise run test`, and `mise run browser`. Test ordinary inputs, optional/single names, blank validation, multiword/Unicode values, legacy/full/repeated/surname-first/custom-separator preservation, organization names, atomic history and stale edits. Browser tests start at root-to-login and cover actual visible fields, creation/editing, preservation and denial. Inspect a synthetic person-form screenshot. Build a wheel and verify migrations/inspect template/new minimal form script are included, obsolete widget assets are absent, and devsite/tests/scripts are excluded.

## Supporting documents and boundaries

The [contact spine](ARCHITECTURE-SPINE.md), PRD, acceptance criteria, addendum, README and development docs describe the simpler supported editing scope. Prior review evidence remains in Git history and [implementation triage](reviews/implementation-triage.md). Preserve the pre-existing uncommitted Wagtail-only PM edits.

Defer elaborate name editing, structured postal editing, source importing/matching, financial models, policy review, letters/PDF generation, dispatch, direct sending, routing/preferences and broad converters. Passing this increment does not establish operational acknowledgment readiness.

## Review Triage Log

| Finding | Verdict / route | Evidence and result |
| --- | --- | --- |
| Blind-1: recorded context follows original kind | medium / patch | Made context available across kind changes; endpoint and browser transitions preserve the name. |
| Blind-2: multiline preservation across kinds not defined | medium / patch | Explicit kind changes retain the existing recorded name when replacement is blank; tests cover this policy. |
| Blind-3: hidden irrelevant inputs validate | medium / patch | Bound forms disable inactive fields using the posted kind; the minimal script also disables hidden controls. Tests cover inactive nulls and active errors. |
| Blind-4: optional person fields lack combined instruction | low / patch | Added plain help that either name or both may be supplied. |
| Blind-5: organization requirement lacks instruction | low / patch | Added organization-name help; recorded-context help explains preservation where applicable. |
| Blind-6: malformed unsaved name objects fail construction | low / reject | This helper reads a validated stored profile. Malformed internal model instances are outside supported form callers; no new guards or malformed-record editing workflow added. |
| Blind-7: line-break replacements cannot reopen in simple fields | false / reject | The recorded-context fallback deliberately handles values outside single-line editing and preserves them exactly. Added browser coverage confirms no mutation. |
| Blind-8: person newline browser coverage missing | medium / patch | Browser correspondence edits now preserve both unstructured and structured multiline person names, plus multiline organizations. |
| Blind-9: kind-switch drafts/errors unverified | medium / patch | Browser verifies round-trip kind selection, client draft retention, relevant errors, and stored names/kinds. |
| Blind-10: optional field markers unverified | low / patch | Browser asserts neither person input has required attributes or individual required markers. |
| Verification-1: surname correction not exercised | medium / patch | Formatting/history regression now independently corrects given and surname, retaining exact component order and separators. |

The independent edge-case review reported no additional findings. All retained findings were fixed; no new scope or elaborate editor was added.

## Final local verification

`mise run check` and `mise run hooks` passed. Fast tests: **110 passed**, with **95%** combined statement/branch coverage. Chromium: **6 passed**, including ordinary names, single names, validation, legacy preservation, organizations, kind transitions and permission denial. Synthetic person-form screenshot visually checked: only relevant ordinary fields/labels are shown, without component, join or mode controls. Wheel source matches the checkout, includes migration/inspect template/minimal field-visibility script, excludes obsolete editor assets and devsite/tests/scripts. No migration was added or applied; existing development data was not changed.
