---
title: Wagtail CRM — north star and first operational slice
status: draft
created: 2026-11-08
updated: 2026-11-08
---

# Product direction

Interview-based working draft. Stakeholder authority and operational policies remain unconfirmed. This document supplements the existing `docs/` drafts; it does not silently replace or approve them.

Brylie approved `product-brief.md` as product direction on 2026-11-08 after clarifying usability, delivery-exception closure, separate UX/financial validation, and source independence. The detailed PRD remains a draft; that approval does not confirm stakeholder authority, financial policies, or operational readiness.

## North star

An affordable, maintainable, Apache-licensed nonprofit CRM that organizations can operate and adapt themselves. Organizations control their data and hosting. Private, portable records and traceable decisions let successors continue the work without reconstructing undocumented history.

Western Friend is the first customer. Its Editor needs annual donor acknowledgments from PayPal activity loosely connected to bookstore and subscription records. Matching donors, interpreting mixed payments, and refunds are investigation hypotheses, not observed workflow findings.

Long-term success means independent organizations in multiple countries completing their own workflows, maintaining installations, and contributing improvements. The international Wagtail community is an initial audience. Languages, currencies, address formats, and local reporting policies develop incrementally with actual adoption. International support is not an initial compliance claim.

The initial interface and standard letters are English; calculations and reporting support USD only. Preserve international donor names and correspondence details. Unsupported currencies retain original values as visible unresolved exceptions; never invent exchange rates or silently discard them. Other-language needs require an approved translation or external correspondence process and remain open until adequately addressed. Substantial demand should trigger scope review.

PayPal is the first supported source; core donor and contribution records remain processor-neutral. Source-specific adapters must not make the core dependent on PayPal identifiers or rules.

Wagtail CMS is the sole UI for CRM workflows. Use its navigation, forms, actions, permissions and interaction conventions as the shared staff experience. Extend Wagtail's admin for workflow-specific screens wherever possible; a separate frontend or public CRM pages are outside the intended product scope. The site root redirects to Wagtail login. This constraint applies to future imports, review, reconciliation and acknowledgment workflows as well as contact management.

Simple UX means familiar, task-appropriate fields populated with recorded values, not collapsing known structured data into a text box. Standards guide internal semantics; staff do not assemble schema components, choose separators or manage formatting rules. Apply this principle across the CRM, including future address forms when their agreed scope calls for structured address fields. Existing unknown structure stays directly editable without guessing. Finish usable contact management before starting imports or financial features. Before requesting review, the developer must run the app and personally complete creation, finding, editing and inspection for people/organizations, including legacy unsplit and single names, optional details and validation recovery; fix confusing interactions directly rather than add instructions around them. This does not expand the current multiline postal-address increment.

## Common contact data and minimum slice

Use Django and Wagtail conventions first, with ordinary fields staff understand. The contact slice supports people with Given name and Family name (either may stand alone), organizations with Name, and one optional email and multiline postal correspondence address. Existing unsplit names remain directly editable and are never guessed apart. Names may contain multiword and non-Latin text. Adding a contact establishes no donor, payer, subscriber or recipient role.

The approved staff tasks are [AC-18](acceptance-criteria.md#ac-18--minimum-contact-management). Use Wagtail's standard create/edit/delete actions, permissions, History and Site history. Do not build a parallel audit model, revision workflow, snapshot display or concurrency mechanism for this slice. Last-save-wins is accepted; concurrent-edit protection is deferred until demonstrated need. There are no existing installations; the alpha contacts app starts with a fresh initial migration and no migration-baseline history entries.

One distribution contains one Django app per domain. Contacts owns contact records; later finance, imports and letters may depend on contacts, while contacts imports none of them. No shared core or generic audit app is needed now.

Contact completeness remains separate from donor attribution and delivery readiness. Shared names, addresses or emails do not merge identities. Future confirmed source mappings stay within source/account scope; conflicting evidence requires review. Exact delivery practice remains unresolved; downloadable PDFs, external sending tools and recording actual dispatch are the agreed direction for later increments.

### Future standards and export

Established standards should guide future interoperability when an actual importer or exporter exists. JSContact, CLDR, vCard and Schema.org remain references for that work. Define supported mappings and any losses against real source data then; this slice has no codec, formatting policy or standards-conformance claim. Do not prescribe future storage representations through acceptance criteria.

## First operational outcome

The Editor completes one agreed annual acknowledgment cycle: collect source records and correspondence context, import and resolve duplicates, confirm donors, review charitable allocations and refunds, reconcile, approve and issue letters, distribute through agreed tools, and record dispatch. The resulting record explains inclusions, exclusions, unresolved work, source evidence, decisions, and corrections.

The reporting period, deadline, volumes, covered accounts, offline gifts, and delivery practice are unknown. A prior request mentioned the prior fiscal year; acknowledgment dates must be confirmed independently.

## Users and proposed authority

- Brylie leads product and technical development and proposes coordinating discovery.
- The Editor proposes operational workflow and donor-facing approval, and provides walkthroughs and examples.
- The bookkeeper identifies authoritative financial records and validates reconciliation, allocations, refunds, and independently expected results.
- Before real issuance, Editor approval should be supported by confirmed financial review.
- Business ownership approves access; a designated maintainer implements it. Technical administration alone is not financial approval.

These responsibilities require confirmation. Account administration, updates, backups, recovery, support, exception approval, and cycle-closure authority need named owners.

## Minimum vertical slice requirements

### Intake and coverage

- **FR-01:** Import an agreed PayPal export through a repeatable staff-operated process. Repeated and overlapping records must not duplicate financial effects. Every imported record has an explained disposition.
- **FR-02:** Bring in correspondence and subscription context through documented exports and targeted correction. Retain confirmed information across transactions and letters. Bulk contact import depends on observed volume. Routine operation must not require developer queries or widespread re-entry.
- **FR-03:** Track confirmed coverage by source, account, and date range separately from reconciliation. Permit review and drafts while coverage is incomplete. Final donor issuance requires confirmed relevant coverage; unknown mailed gifts may prevent that confirmation. A limited acknowledgment requires explicit scope and wording approval.
- **FR-04:** If mailed gifts are covered, capture them through an adequate CSV import or controlled entry after inspecting bookkeeping records. Retain donor, amount/currency, policy-relevant date, method, stable source reference, confirmation, allocation context, and entry/review actors. Preserve private evidence references and duplicate warnings. Use the same downstream workflow as processor records.
- **FR-20:** Account for rejected or unsupported rows without silent omission: retain an authorized source/row reference, reason, and resolution state. Show whether an import was staged, applied, failed, or remains uncertain after interruption. Retrying must not duplicate financial effects or overwrite reviewed decisions. Exact application boundaries and duplicate identity rules require documented adapter evidence and acceptance cases before implementation is accepted.

### Donor and financial review

- **FR-05:** Compare candidate contacts with payer identity, source identifiers, transaction references, and confirmed relationships. Names and emails support suggestions; ambiguity requires confirmation. Donor attribution remains distinct from gift-recipient identity.
- **FR-06:** Preserve source references automatically for routine confirmations. Discrepancies require supporting evidence and explanation. Unresolved attribution requires escalation to the bookkeeper or donor through an established contact route.
- **FR-07:** Present payments, donor, gross, separate fees, charitable amount, derived noncharitable remainder, and review state, with source, subscription, and refund details available.
- **FR-08:** Approved rules may suggest allocations; record the applicable policy/version. Patron splits require historical plan and approved valuation evidence. Missing policy creates an exception. Overrides require explanation and appropriate financial review. Enforce amount bounds through every supported write path.
- **FR-09:** Preserve prior evidence and decisions. Changes record actor, time, changed values, rationale, and supporting evidence. Reimports preserve staff decisions and flag material conflicts. Material attribution, amount, or benefit changes reopen affected approvals; minor contact changes do not reopen unrelated financial review. Mixed-payment refunds require an approved rule or explicit financial review.

### Approval, issuance, and distribution

- **FR-21:** Provide an explicit reconciliation review for an identified dataset version and scope. Compare source counts and monetary totals with authoritative comparison records, distinguishing gross, fees, net, refunds, reviewed charitable amounts, noncharitable amounts, and currencies rather than treating them as interchangeable totals. Explain every record disposition and difference with evidence. Record reviewer, time, scope, comparison references, and unresolved differences. Acceptance requires zero unexplained differences; any explained difference still needs authorized treatment. Reconciliation does not establish source completeness. Material changes reopen affected reconciliation and dependent approvals. The exact comparison procedure and authority remain stakeholder decisions.
- **FR-10:** Preview the exact letter with correspondence details, period, itemized contributions, benefits, total, and signatory. Provide private evidence explaining coverage, payments, allocations, and refunds.
- **FR-11:** Summarize coverage, reconciliation, ready/blocked donors, exclusions/reasons, missing delivery details, and the exact proposed batch. Support individual exception review and explicit version-bound batch approval of routine ready letters. Record actor, time, scope, and versions. Content changes reopen letter approval; financial changes reopen affected financial approval.
- **FR-12:** Preserve issued letters and distribution history. Content corrections create linked, newly approved revisions. Corrective dispatch is explicit; retrying an unchanged letter creates another attempt.
- **FR-22:** Issuance must identify the approved document versions and its outcome. Repeated or interrupted requests must not silently create duplicate issuance or dispatch. Staff can determine which letters were issued and safely resolve pending/failed outcomes. Define the issuance event, recovery behavior, and handling of superseded versions awaiting dispatch before accepting the issuance increment; detailed proposals and open decisions are in `acceptance-criteria.md`.
- **FR-13:** Provide downloadable, printable PDFs and a manifest for external delivery, including manual email through existing tools. Dispatch records identify version, channel, destination, date, actor, and available evidence reference. A staff attestation is not proof of receipt. Generation/download never records dispatch, including when the PDF is intended for manual email. Exact delivery practice still needs Editor confirmation.
- **FR-14:** Keep failed delivery and missing destinations visible. Distinguish fully distributed from closed with accepted distribution exceptions. Follow-up and closure authority require agreement. Distribution exceptions cannot bypass coverage, attribution, or financial gates.

### Privacy, usability, and continuity

- **FR-15:** Grant explicit CRM permissions independently of website accounts, with separate sensitive capabilities for exports, issuance, and account management. Protect evidence, letters, exports, and backups. Trust privileged infrastructure operators explicitly.
- **FR-16:** Export the complete retained organizational record: contacts/identities, payments/refunds/allocations, evidence/references, policies/reviews, letters/revisions, approvals/audit, and distribution attempts. Preserve relationships, stable IDs, currencies, and dates in documented CSV or JSON plus PDFs/evidence and a manifest. History must be understandable without running the CRM. Exclude active credentials and session secrets.
- **FR-17:** Guide routine work with a short workflow, everyday labels, useful next actions, explained calculations and blocks, preserved entered work, and low-effort confirmations. Keep evidence/history accessible. Explain when to involve finance. Validate through the Editor's asynchronous task evidence, supplemented by live observation when practical.

## Readiness and success evidence

- Every imported record explained; agreed dataset reconciles with zero unexplained differences.
- Every issued contribution traceable to source evidence and approved allocation.
- Unresolved identities, material allocation/refund issues, or inadequate coverage block affected issuance.
- Repeat imports create no duplicate effects; corrections preserve prior issuance.
- Editor and bookkeeper verify known gifts, mixed payments, ambiguous donors, and refunds against independently established expectations.
- Editor completes representative routine work without developer help, understands amounts and unresolved work, distinguishes draft, approved, and dispatched letters, and recognizes appropriate financial escalation. Demonstrate this primarily through asynchronous testing, with live observation supplementary when practical.
- Verify unauthorized-access prevention, complete portable exports, and successful recovery before operational use.
- Supported pilot has onboarding, written guidance, named help contact and availability, and named operational owners.

Measure current effort before setting a time-saving target. Guardrails include wrong attribution or amounts, silent omissions, duplicate letters, disclosure, and repeated manual re-entry. Coverage and correctness must not be traded for speed.

See `acceptance-criteria.md` for draft gate dependencies, invalidation rules, concrete synthetic examples, evidence requirements, and decisions needed before each capability can be accepted. These refine acceptance precision without approving financial policy or named authority. A Contacts screen, importer, or PDF generator alone is a development increment, not completion of this operational release.

## Deferred scope

Live PayPal synchronization, direct website integration, additional processor adapters, application email and automated delivery tracking if external tools suffice, campaigns, portals, fundraising automation, fulfillment, advanced analytics, shared multi-organization hosting, and additional-country reporting rules.

Future enhancement: email issued PDFs directly from the CRM to save the Editor a manual step. This is outside the first cycle; downloadable PDFs and manual external email are sufficient. Revisit after observing the delivery workflow, with sending, confirmation and retry behavior scoped separately.

## Adoption, configuration, and maintenance

Installations may be maintained by nonprofit technical staff, capable volunteers, consultants, or eventually hosting providers. After setup, the Editor operates through the interface with occasional technical support. Affordability includes hosting, maintenance, support, training, and staff time; no cost target is established.

- **FR-18:** Authorized staff can manage organization details, supported reporting settings, correspondence preferences, controlled letter content, and supported role assignments. Financial amounts derive from reviewed records, not editable letter prose.
- **FR-19:** Supported allocation policies use understandable validated options, effective dates, and approval history. A designated financial reviewer approves policy versions; configuration alone does not establish approval. The Editor applies approved policies. Preserve the versions used for issued documents.
- **NFR-01:** Provide documented installation, supported dependencies, predictable upgrade guidance, tested backup/recovery, and maintainer handover guidance. Routine cycles in a supported setup must not require recurring custom patches, database repairs, or developer intervention.
- **NFR-02:** Support keyboard operation, readable content at increased zoom, clear labels and actionable errors, and status explanations that do not depend on color. Initial UX and browser validation target desktop use on the Editor's Mac; exact browser, OS, display, and accessibility preferences require confirmation.

## Pilot learning and collaboration

Primary learning question: after brief onboarding, can the Editor own the supported workflow, explain results, recognize uncertainty, and involve finance appropriately without developer intervention? Source correctness, coverage, and privacy remain mandatory gates rather than tradeoffs for usability. Independent adoption by another nonprofit is a later test.

Brylie first iterates locally with representative synthetic data, then provides a restricted hosted synthetic test environment when ready for Editor feedback. Give short, goal-oriented scenarios and a simple way to report confusing steps, unexpected results, and questions. Brief notes and optional synthetic screenshots, together with inspection of resulting records, provide primary task evidence. Repeat representative work with minimal prompting and record help, lost context, misunderstood states, and unnecessary repetition. Cross-timezone progress must work asynchronously; monthly calls are optional supplements.

Synthetic-data UX tests establish usability and understanding. Financial validation separately compares results with stakeholder-approved source evidence and independently established expected results. Both are required for operational readiness; neither substitutes for the other. Protect any restricted real evidence and keep it outside public repository content and synthetic UX environments.

Confirm the Editor's browser/macOS/display setup and accessibility preferences, and investigate switching among records, PDFs, email and printing, interruptions, connectivity and pause/resume needs before setting numeric time or assistance targets. See `validation-plan.md` for evidence and readiness tracking.

New adapters, unsupported allocation methods, substantial document-layout changes, and additional-country reporting requirements may need developer support. Introduce common configuration as adoption provides evidence; avoid requiring organization-specific forks for supported routine work.

## Evidence-driven scope changes

Assess exception frequency, effort, and consequences with the Editor and bookkeeper. Rare exceptions may use controlled manual handling; substantial repeated work can justify essential bulk capabilities. Expand the release where necessary to complete the agreed outcome, or explicitly reconsider that outcome when evidence makes it unachievable.

A deliberately agreed pilot subset must have complete coverage within its stated limits. Completing it does not complete the wider annual obligation; remaining work stays visible. Unverifiable identities, amounts, coverage, or financial policy delay affected operational use. A deadline cannot override these controls.

## Evidence and decisions still needed

Proposed discovery coordinator: Brylie; not yet stakeholder-confirmed. Obtain a historical letter, representative redacted PayPal export, contact/subscription records, and mailed-gift examples if covered. Redaction must retain matching relationships and financial edge cases. Observe the Editor's current workflow and representative tasks; bookkeeper supplies authoritative records and expected results.

Confirm period/date basis/timezone, coverage, volume/deadline, historical subscription valuations, refund/cross-year corrections, donor attribution edge cases, wording/signatory/branding, delivery preferences, exclusion and closure policy, approval authority, retention/deletion, and support/recovery ownership. Each operational prerequisite needs a named owner and next action before readiness can be declared. Hosting and VPN choices remain open.

## Document status

This draft captures the interview so far. It is not stakeholder approval, a finalized PRD, or evidence of implemented behavior. Architecture, UX details, and implementation sequencing remain downstream work. The discovery log preserves interview provenance.
