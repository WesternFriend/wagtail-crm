---
title: Wagtail CRM — north star and first operational slice
status: draft
created: 2026-11-08
updated: 2026-11-08
---

# Product direction

Working draft. Brylie approved the [product brief](product-brief.md) as product direction on 2026-11-08; it is the one statement of the north star, first useful release, boundaries and pilot approach. This PRD holds the 0.1.0 requirements, readiness evidence and open decisions. Neither confirms stakeholder authority, financial policy or operational readiness.

Architecture decisions that span increments are in the [architecture spine](../../architecture/architecture-wagtail-crm-2026-11-08/ARCHITECTURE-SPINE.md).

## Common contact data and minimum slice

Use Django and Wagtail conventions first, with ordinary fields staff understand. The contact slice supports people with Given name and Family name (either may stand alone), organizations with Name, and one optional email and multiline postal correspondence address. Changing an organization to a person requires staff-entered given and/or family names; the organization name is not split automatically. Names may contain multiword and non-Latin text. Adding a contact establishes no donor, payer, subscriber or recipient role.

The approved staff tasks are [AC-18](acceptance-criteria.md#ac-18--minimum-contact-management). Views, history and concurrency follow AD-2 in the architecture spine.

Contact completeness remains separate from donor attribution and delivery readiness. Shared names, addresses or emails do not merge identities. Future confirmed source mappings stay within source/account scope; conflicting evidence requires review. Exact delivery practice remains unresolved; downloadable PDFs, external sending tools and recording actual dispatch are the agreed direction for later increments.

### Future standards and export

Established standards should guide future interoperability when an actual importer or exporter exists. JSContact, CLDR, vCard and Schema.org remain references for that work. Define supported mappings and any losses against real source data then; this slice has no codec, formatting policy or standards-conformance claim. Do not prescribe future storage representations through acceptance criteria.

## First operational outcome

The first useful release is described in the [product brief](product-brief.md). The reporting period, deadline, volumes, covered accounts and delivery practice are still unknown; mailed checks are in scope (#25); see [Evidence and decisions still needed](#evidence-and-decisions-still-needed).

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
- **FR-04:** Staff record mailed checks by hand, and they count on letters like PayPal payments (#25). Other offline gifts stay deferred.

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

See Boundaries in the [product brief](product-brief.md). Emailing issued PDFs from the CRM is a later candidate in the [roadmap](../../../../docs/roadmap.md).

## Adoption, configuration, and maintenance

Who maintains installations and what affordability covers are in the [product brief](product-brief.md).

- **FR-18:** Deferred. Staff-managed organization and letter settings; 0.1.0 uses a plain template (#9).
- **FR-19:** Deferred. Allocation policy versions and their approval history.
- **NFR-01 (#13):** Provide documented installation, supported dependencies and tested backup and restore. Upgrade guidance and maintainer handover are deferred until after the pilot. Routine cycles in a supported setup must not require recurring custom patches, database repairs, or developer intervention.
- **NFR-02:** Support keyboard operation, readable content at increased zoom, clear labels and actionable errors, and status explanations that do not depend on color. Initial UX and browser validation target desktop use on the Editor's Mac; exact browser, OS, display, and accessibility preferences require confirmation.

## Pilot learning and collaboration

The pilot question and the asynchronous, synthetic-data method are in the [product brief](product-brief.md) (Pilot and next evidence). UX testing and financial validation are separate tracks; operational readiness needs both.

## Evidence and decisions still needed

Proposed discovery coordinator: Brylie; not yet stakeholder-confirmed. Obtain a historical letter, representative redacted PayPal export, contact/subscription records, and mailed-check examples. Redaction must retain matching relationships and financial edge cases. Observe the Editor's current workflow and representative tasks; bookkeeper supplies authoritative records and expected results.

Confirm period/date basis/timezone, coverage, volume/deadline, historical subscription valuations, refund/cross-year corrections, donor attribution edge cases, wording/signatory/branding, delivery preferences, exclusion and closure policy, approval authority, retention/deletion, and support/recovery ownership. Each operational prerequisite needs a named owner and next action before readiness can be declared. Hosting and VPN choices remain open; DigitalOcean App Platform and Spaces are candidates, not validated. The Western Friend website's AGPL source is a reference for conventions only; assess rights before reusing any of it.

## Document status

This draft is not stakeholder approval, a finalized PRD, or evidence of implemented behavior.

## References

- [PayPal Activity Download report](https://developer.paypal.com/reports/activity-download/) and [Transaction Search reference](https://developer.paypal.com/api/transaction-search/v1/search-get): reporting identifiers and statuses.
- [Western Friend subscription prices](https://westernfriend.org/subscription-prices/): current public evidence of mixed patron payments, not approval of historical mappings.
- [Western Friend FY2023 annual report](https://westernfriend.org/board-documents/fy2023-annual-report/): the fiscal year runs October to September; the donor reporting period still needs confirmation.
- [IRS Publication 1771](https://www.irs.gov/pub/irs-pdf/p1771.pdf) and [quid pro quo contributions](https://www.irs.gov/charities-non-profits/charitable-organizations/charitable-contributions-quid-pro-quo-contributions): acknowledgment and benefit-disclosure requirements for letters (#9).
