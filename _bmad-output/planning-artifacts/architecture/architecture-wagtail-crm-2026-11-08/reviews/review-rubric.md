# Rubric review: initial contact profile and first PR

Reviewed 2026-11-08 against the current PRD common-model section, AC-18 refinements, existing Contact model/migration, Wagtail viewset, permission/form tests, demo seed command, and locked dependency versions. This is a planning review, not implementation or conformance certification. No application tests were run.

## Verdict

**Suitable for user review as a brief proposal; make the small clarifications below before implementation.** The artifacts supply real cross-layer rules and one bounded PR. There is no basis for requiring a full platform architecture, importer, export endpoint, or financial design here. Proposed JSON storage and explicit-order formatting are visibly proposals, which is appropriate at this stage.

## Findings

### R1 — Medium: distinguish a contact viewer from a user without contact permission

Location: `FIRST-CONTACT-PR.md:14,22`; `ARCHITECTURE-SPINE.md:61`.

The plan allows history inspection with contact-view permission, but its acceptance case says “a viewer or Wagtail user without contact permissions” cannot obtain protected information through edit/inspect. If “viewer” means a user holding `view_contact`, denying inspect contradicts the stated history surface and the ordinary view capability. If it means an anonymous visitor, that should be explicit. The current tests establish admin-only denial and view-only creation denial; they do not resolve this wording.

Small fix: split the example into anonymous/admin-only users denied contact information, view-only users allowed list/inspect/history but denied mutations, and users with each existing add/change/delete capability allowed only the corresponding action. Include POST denial and CSRF preservation in the selected endpoint checks. This is clarification of existing permissions, not a new permission system.

### R2 — Medium: state which write paths must use the atomic history operation

Location: `ARCHITECTURE-SPINE.md:22,61`; `FIRST-CONTACT-PR.md:9–12`; `devsite/management/commands/seed_demo.py:25–30`.

The shared validation and atomic contact/history rule is good, but the bounded plan does not say how the existing direct ORM demo seed participates. It currently calls `Contact.objects.get_or_create`; ordinary ORM writes do not acquire actor/origin history merely because the Wagtail form uses a shared operation. A form-only implementation could pass staff-edit cases while failing the spine's unqualified write invariant.

Small fix: name the controlled runtime entry points (Wagtail create/edit and demo seeding), require them to use the same validation/history write boundary or explicitly document the synthetic seed exception, and keep the historical-model data migration as its separate baseline-history writer. State the origin for synthetic creation if recorded; do not fabricate a staff actor. Add one rollback case where history persistence fails and the contact change does not commit. The implementation spec can choose the mechanism; a general audit framework is unnecessary.

### R3 — Low: identify the custom form as new work

Location: `FIRST-CONTACT-PR.md:11`; `src/wagtail_crm/views.py:14`.

There is no existing `src/wagtail_crm/forms.py`. The current viewset generates its ordinary form from `form_fields`. “Extend the existing Django form” slightly overstates the code substrate and could obscure that the structured editor needs a new custom form/widget and viewset integration.

Small fix: say “add the custom form/editor and connect it to the existing ModelViewSet.” Field layout and widget details can remain in the implementation spec. This does not require another planning document.

## Rubric assessment

| Criterion | Assessment |
| --- | --- |
| Real consistency rules | Pass. AD-1 connects UI, migration and conversion to one authoritative name and forbids inferred identity. AD-2 bounds meanings, cardinality and mutation-free decoding. AD-3 connects exact migration preservation, provenance, atomic writes and permission continuity. These are stronger than descriptive technology preferences. |
| Enforceable decisions | Pass with R2 clarification. Unsupported input rejection, conflicting structured/full-name rejection, per-row stable UID, preserved integer PKs and non-cascading snapshots are testable. Exact JSONField and rendering choices are appropriately proposed rather than presented as stakeholder decisions. |
| Existing Django/Wagtail fidelity | Pass with R3. Contact's person/organization values, optional email, integer PK, name/email search and `wagtail_crm_contacts` viewset namespace are accurately respected. The lockfile contains Django 5.2.19 and Wagtail 7.4.4. No replacement admin framework or generic entity/property model is introduced. |
| Migration acceptance | Pass for a brief plan. Historical models, permissive-add/backfill/constrain order, distinct UID assignment, exact legacy full-name/email/kind retention, upgrade from 0001 and fresh-database checks are stated. Existing relationships are protected even though the present scaffold defines none. Database field/default and reverse-migration details can remain implementation choices so long as they honor those rules. |
| Edit and preservation acceptance | Pass. Unstructured mononym/multiword/non-Latin examples, explicit surname-first order, repeated surnames, generated full name, preserved historical representations, atomic invalid-input handling and surviving deletion snapshots are concrete. The requirement to preserve prior structure in history or reject a representation-losing edit makes the tradeoff visible. |
| Permission acceptance | Pass with R1. Existing permissions, namespace and guarded inspect-based history are retained. No new history/export route or download authority is implied. The view-only acceptance sentence needs disambiguation. |
| Common-model fidelity | Pass as a proposed subset. JSContact owns the contact profile; person/organization identity, one optional email, international multiline postal text and correspondence/attribution separation match the PRD. The narrowed CLDR role is explicitly disclosed for review rather than silently represented as locale-aware formatting. |
| Interoperability claims | Pass at proposal altitude. The RFC/version and field meanings are named, unknown input fails explicitly, portable helper round-trips are planned, and Schema.org/vCard are bounded mapping notes. RFC 9553 recognizes the selected name/component/separator properties; this review did not exhaustively certify their future serializer. |
| Scoped exclusions | Pass. Source import, additional observations/details, relationships, routing, financial policy, letters, dispatch and broad conversion tooling are clearly deferred. Evidence and issued-name snapshot obligations are retained as future boundaries. A contact Card is explicitly distinguished from FR-16's complete organizational export. |
| Briefness and one PR | Pass. Three decisions and four implementation items are sufficient for this increment. UID/history/migration work follows agreed preservation requirements; it is not speculative platform scope. |

## Review limits and decision boundary

Accepting these documents would accept a technical proposal for the bounded increment; it would not establish AC-18 for the wider product or operational-cycle readiness. Before implementation, the proposed exact profile and storage/form decisions still need acceptance as the documents already say. No additional discovery or architecture expansion is required merely to review them.

The RFC check used the authoritative [RFC 9553 name definition](https://www.rfc-editor.org/rfc/rfc9553.html#section-2.2.1). Standards references and pinning do not replace the independent expected round-trip fixtures already requested by the plan.
