# Reconciliation against agreed contact inputs

Date: 2026-11-08. Scope: document reconciliation only; no implementation or standards-conformance validation was performed.

## Verdict

The proposed spine and first PR plan largely preserve the agreed scope and are suitable for user review. They do not authorize implementation. No major return to naming modes, duplicate names, preference controls, financial workflows or broad interoperability tooling was found. Before implementation, resolve the bounded omissions below, especially deletion/history behavior and the name-representation transition. Keep those resolutions short rather than expanding this into a general contact platform.

Sources examined: the PRD's “Standards-based common data models” section (FR-23), AC-18 and its identity/name/correspondence refinements, the full addendum, `src/wagtail_crm/models.py`, `views.py`, initial migration, and existing contact permission/form tests. Compared against `ARCHITECTURE-SPINE.md` and `FIRST-CONTACT-PR.md` in the parent directory. References below identify document sections rather than assuming implementation already exists.

## Findings requiring clarification

### 1. Deletion remains an explicit unresolved design decision

The addendum requires explicit deletion rules. The spine requires retained old/new values and atomic history; the PR plan correctly identifies that existing deletion must be checked, but does not say what happens to the contact's history when an authorized user deletes it. The existing Wagtail viewset exposes the ordinary delete route, and tests already exercise denied access to that route. A future history relation with cascading deletion could erase the evidence the plan promises.

Smallest resolution: state the proposed behavior for an authorized deletion, the resulting history retention, and which existing delete permission and route behavior is preserved. Add one corresponding acceptance example. Do not silently disable deletion, add a new role, or introduce a retention platform. Product review should see any proposed change to existing delete behavior before implementation.

### 2. One editor is preserved, but becoming structured is underspecified

AD-1 and PR item 3 explicitly reject modes, prompts, duplicate names and correspondence overrides. However, “when confirmed structure exists” describes editing already structured names without explaining how an initially unstructured name acquires supported confirmed components (AC-18-N03). AD-2 also requires explicit component order/separators, which must not accidentally become mandatory extra staff configuration for ordinary entry.

Smallest resolution: include one plain example of the same editor progressing from supplied full text to staff-supplied known components/order, with the original text retained in history, no inferred splitting, and no second full-name entry. Identify how order/separators are expressed without requiring routine configuration. This is a clarification for review, not a recommendation to add a mode control or automatic conversion prompt.

### 3. Repeated surnames and representation-change preservation need explicit fixtures

AC-18 expressly includes repeated surname components, multiword given/surname components, and changes of internal representation retaining known structure and provenance (N01–N04). The plan mentions multiword components and preventing silent loss, but its concrete structured example contains only one surname and one given component. The component-kind list alone does not establish repeated-component cardinality or expected rendering.

Smallest resolution: list a repeated-surname expected round-trip/rendered result and a full-text-to-components transition preserving the supplied text. Also specify the permitted result of an attempted components-to-unstructured edit: preservation or explicit rejection before mutation, rather than silent collapse. These are selected-profile fixtures within the PR's existing verification scope.

### 4. CLDR is pinned but its actual formatting responsibility is narrowed

The agreed division says CLDR governs generated formatting using known structure/locale. The spine pins CLDR but proposes preserving explicit JSContact order/separators and deferring locale-driven patterns. This is a reasonable small-profile proposal, but a reference/version pin alone does not show CLDR formatting behavior or justify the narrowed application.

Smallest resolution: label this explicitly as the proposed initial formatting limitation, state why explicit known ordering is sufficient for the selected examples, and avoid claiming locale-aware CLDR formatting is implemented. Do not add locale selection/configuration without demonstrated need. The exact technical standards mapping still requires its own correctness review; this reconciliation does not validate RFC or CLDR details.

### 5. Provenance is adequate for local edits only if its boundary stays explicit

AD-3 preserves migration/staff origin, actor/time and old/new values, and the PR correctly excludes imports. That is a bounded local history mechanism. It must not later be treated as the complete source-observation/suggestion/confirmation model: the agreed bundle separates those concepts and retains other imported email addresses as evidence. The current plans do not explicitly carry forward that latter requirement, although they defer imports and additional details.

Smallest resolution: one boundary sentence stating that future source adapters must retain original source representations and additional emails as evidence, separate from canonical correspondence and donor attribution. Also state that legacy migration preserves observed values without a fabricated human confirmation. The existing “no invented human reviewer” rule already supplies most of this. No importer or evidence framework belongs in this PR.

### 6. Permission intent is sound; clarify the proposed history surface

The spine preserves namespace, codenames and endpoint enforcement. The PR proposes history access under contact-view permission, says there is no general history API, and tests direct history requests, but never names whether history is embedded in inspect or has a dedicated internal route. This leaves a small scope ambiguity rather than evidence of a permission regression.

Smallest resolution: choose the smallest existing inspect-based presentation or explicitly identify the proposed internal route and guard. Preserve current anonymous/admin-only denial, view-only mutation denial, add/change/delete separation and CSRF protection. Contact-view permission must not grant a new download/export capability. Existing tests are inspection evidence only; they were not run during this review.

## Constraints retained successfully

| Agreed constraint | Evidence in the proposed artifacts | Assessment |
| --- | --- | --- |
| Brief selected profile and one bounded PR | Three spine decisions; four implementation items; explicit exclusions | Retained; avoid adding more architectural machinery to resolve the findings. |
| One person/organization per contact; independent identity | AD-1, UID mapping, kind mapping and legacy preservation | Retained; UUID layout is a proposal, not an approved implementation choice. |
| One authoritative name entry, no inferred splitting | AD-1; name table; PR item 3 and unstructured examples | Retained, with transition clarification above. |
| No modes/prompts/extra configuration or independent correspondence names | AD-1 and PR item 3 | Retained; explicit separator handling must respect this constraint. |
| Exact legacy names, kinds, emails, identifiers and relationships | AD-3; PR migration sequence and legacy acceptance example | Retained. Existing integer PKs/routes remain; new UIDs supplement them. |
| Previous values and provenance; no invented migration reviewer | AD-3; name-change acceptance example | Retained for this increment, subject to explicit deletion behavior. |
| One optional email/address; incomplete international records valid | AD-2; PR editor and organization/address example | Retained; no U.S.-specific requirements or inferred preferences. |
| Contact completeness and donor attribution remain distinct | AD-1; blank-details rule; PR correspondence note | Retained. |
| No channel inference/routing or required delivery preferences | Deferred work and PR exclusions | Retained; contact details do not establish delivery readiness. |
| Existing Wagtail permissions and ordinary CRUD behavior | AD-3; PR permission statement, preserved URLs and denied-endpoint tests | Intent retained; history surface and deletion remain to settle. |
| Issued name snapshots remain immutable | PR defers letters/issuance and does not modify artifacts | No present conflict; add a short future invariant reference to AC-18-N06 rather than implementing issuance. |
| Bounded interoperability with explicit loss | Mapping notes, unsupported-input rejection and converter deferral | Retained as planning scope. Schema.org ContactPoint and vCard RFC 6350 are not explicitly named in the mapping paragraph, although the agreed division names them; include them as mapping references or explicitly deferred details, without adding converters. |

## Scope judgment

UIDs, minimal local change history, validated profile helpers, migration fixtures and endpoint checks are justified by the agreed requirements. They are not scope creep simply because the scaffold lacks them. Public import/export endpoints, source adapters, broad relationships, multiple contact details, routing, dispatch and financial behavior remain excluded appropriately. No new library is required by the proposal; the decision to use no additional library should remain an explicit reviewed choice alongside dependency/license considerations.

The contact-only Card deliberately excludes audit/source evidence; that is compatible with this bounded PR provided it is never described as the complete organizational portability export required by FR-16. Unsupported internal helper input can be rejected before mutation; retaining imported unsupported observations belongs to future adapter work and must not be mistaken for optional data preservation once import exists.

The smallest useful revision is a few boundary sentences plus three concrete examples: authorized deletion/history retention, becoming structured without a second name entry, and repeated surnames/representation preservation. Exact JSONField layout, history model, component editor, standard pins and formatting rules remain proposals for the user's review. No code or migrations should be implemented on the strength of this reconciliation alone.
