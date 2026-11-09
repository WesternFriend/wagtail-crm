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

Simple UX means familiar, task-appropriate fields populated with recorded values, not collapsing known structured data into a text box. Standards guide internal semantics; staff do not assemble schema components, choose separators or manage formatting rules. Apply this principle across the CRM, including future address forms when their agreed scope calls for structured address fields. Names are never split automatically. Finish usable contact management before starting imports or financial features. Before requesting review, the developer must run the app and personally complete creation, finding, editing and inspection for people/organizations, including contact-type changes and single names, optional details and validation recovery; fix confusing interactions directly rather than add instructions around them. This does not expand the current multiline postal-address increment.

## Common contact data and minimum slice

Use Django and Wagtail conventions first, with ordinary fields staff understand. The contact slice supports people with Given name and Family name (either may stand alone), organizations with Name, and one optional email and multiline postal correspondence address. Changing an organization to a person requires staff-entered given and/or family names; the organization name is not split automatically. Names may contain multiword and non-Latin text. Adding a contact establishes no donor, payer, subscriber or recipient role.

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

Each requirement names the 0.1.0 slice issue that delivers it, or is marked deferred. The staff tasks that accept it are in [acceptance-criteria.md](acceptance-criteria.md). A deferred requirement returns only when a real case shows it is needed.

### Intake

- **FR-01 (#5):** Staff import a PayPal Activity Download CSV after previewing it. A repeated file is rejected, and an overlapping file adds only new transactions.
- **FR-20 (#5):** The preview lists each row that will not be imported, with the reason, before staff confirm. A failed import leaves nothing imported. Recovery from an interrupted import is deferred.
- **FR-02 (#6):** Staff create or choose the donor contact while linking a payment. Bulk contact import is deferred until volume shows a need.
- **FR-03:** Deferred. Tracking source coverage by account and date range.
- **FR-04:** Deferred. Mailed or other offline gifts, pending the coverage decision in roadmap step 0.

### Donor and financial review

- **FR-05 (#6):** Staff link each payment to a donor themselves. The PayPal payer name and email stay visible; contacts are never matched, merged or renamed automatically.
- **FR-06:** Merged into FR-05. Escalating disputed attribution is deferred.
- **FR-07 (#5, #6, #7):** The payment list and payment screen show date, payer, gross, fee, net, currency, status, donor, charitable amount and its non-charitable remainder, and any linked refund.
- **FR-08 (#6):** Staff enter the charitable amount, from zero up to the gross. Allocation rules and policy versions are deferred.
- **FR-09 (#6, #7):** Wagtail History records changes to donor links and charitable amounts. A refund is linked to its payment, and an unmatched refund is listed for review. Reopening approvals after a change is deferred.

### Reconciliation, issuance and distribution

- **FR-21 (#8):** For a chosen period, staff compare the imported count, gross, fees, net and refunds with the totals they enter from PayPal, and accept the reconciliation once every payment in the period has a charitable amount and no refund is unmatched. Letters for the period cannot be issued before acceptance.
- **FR-10 (#9):** Staff preview a donor's letter for a period with name, address, each contribution, the goods-or-services value of any mixed payment, and the total, using a plain template.
- **FR-11:** Deferred. Letters are issued one at a time, with no batch approval.
- **FR-12 (#9):** An issued letter keeps its PDF and values when contacts or payments change later. A correction is a new letter linked to the earlier one.
- **FR-22:** Deferred. Recovery from an interrupted or repeated issuance.
- **FR-13 (#10):** Staff download an issued PDF and record each dispatch with channel, date, outcome and note. Downloading does not count as sent.
- **FR-14 (#10):** Staff can list letters that are unsent or whose sending failed. Closing a cycle with delivery exceptions is deferred.

### Privacy, usability and continuity

- **FR-15 (#5–#10):** Wagtail's standard model permissions control who can view and change payments, reconciliations and letters, including direct URLs and PDFs.
- **FR-16:** Deferred. Portable export of the full record. Backups with a tested restore are covered by #13.
- **FR-17 (#11):** The Editor runs one synthetic cycle end to end and confirms the workflow fits their real work.

## Readiness and success evidence

- Every imported record explained; agreed dataset reconciles with zero unexplained differences.
- Every issued contribution traceable to its payment and the charitable amount staff recorded.
- Payments without a charitable amount and unmatched refunds block reconciliation acceptance, and so issuance.
- Repeat imports create no duplicate effects; corrections preserve prior issuance.
- Editor and bookkeeper verify known gifts, mixed payments, ambiguous donors, and refunds against independently established expectations.
- Editor completes representative routine work without developer help, understands amounts and unresolved work, distinguishes previewed, issued and dispatched letters, and recognizes appropriate financial escalation. Demonstrate this primarily through asynchronous testing, with live observation supplementary when practical.
- Verify unauthorized-access prevention and successful recovery before operational use.
- Supported pilot has onboarding, written guidance, named help contact and availability, and named operational owners.

Measure current effort before setting a time-saving target. Guardrails include wrong attribution or amounts, silent omissions, duplicate letters, disclosure, and repeated manual re-entry. Coverage and correctness must not be traded for speed.

See `acceptance-criteria.md` for the staff-task acceptance criteria of each 0.1.0 slice, the items deferred from it, and decisions needed before each capability can be accepted. These do not approve financial policy or named authority. A Contacts screen, importer, or PDF generator alone is a development increment, not completion of this operational release.

## Deferred scope

Live PayPal synchronization, direct website integration, additional processor adapters, application email and automated delivery tracking if external tools suffice, campaigns, portals, fundraising automation, fulfillment, advanced analytics, shared multi-organization hosting, and additional-country reporting rules.

Future enhancement: email issued PDFs directly from the CRM to save the Editor a manual step. This is outside the first cycle; downloadable PDFs and manual external email are sufficient. Revisit after observing the delivery workflow, with sending, confirmation and retry behavior scoped separately.

## Adoption, configuration, and maintenance

Installations may be maintained by nonprofit technical staff, capable volunteers, consultants, or eventually hosting providers. After setup, the Editor operates through the interface with occasional technical support. Affordability includes hosting, maintenance, support, training, and staff time; no cost target is established.

- **FR-18:** Deferred. Staff-managed organization and letter settings; 0.1.0 uses a plain template (#9).
- **FR-19:** Deferred. Allocation policy versions and their approval history.
- **NFR-01 (#13):** Provide documented installation, supported dependencies and tested backup and restore. Upgrade guidance and maintainer handover are deferred until after the pilot. Routine cycles in a supported setup must not require recurring custom patches, database repairs, or developer intervention.
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
