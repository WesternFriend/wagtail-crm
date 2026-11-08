# Product requirements: annual donor acknowledgments

Status: draft for review. Updated: 2026-11-08.

This document defines the proposed first reporting release. It distinguishes agreed direction from policy and workflow decisions that still need confirmation. The local Contacts scaffold is described in [Development and testing](development.md); the payment and acknowledgment workflow below remains planned.

## 1. Problem and outcome

Western Friend's Editor needs to turn historical payment activity into accurate annual donor acknowledgments. PayPal contains the initial financial data, while bookstore and subscription records provide partial context. Some payments contain both a purchase and a contribution.

The first release succeeds when the Editor can import a complete agreed dataset, account for every source record, resolve donor and allocation exceptions, generate reviewed letters for an explicit period, and record distribution. Repeating the process must not duplicate contributions or silently replace issued letters.

This is a first vertical slice of a broader nonprofit CRM. The initial user outcome determines the scope; future fundraising and payment integrations should build on its records and controls.

## 2. Direction and scope

| Direction | Status |
| --- | --- |
| New Apache 2.0 repository using Django and Wagtail | Agreed |
| Separate CRM deployment with secure staff login | Agreed |
| Loose PayPal integration through an importer | Agreed |
| Processor-neutral core with source-specific adapters | Agreed |
| Editable charitable allocation with amount validation | Agreed |
| Lightweight review and reporting dashboards | Agreed |
| One nonprofit per installation and USD-only reporting initially | Proposed scope limit |
| Calendar-year acknowledgments alongside separate fiscal-period reports | Proposed; reporting policy needs confirmation |
| Downloadable PDFs and manual distribution recording as the first delivery path | Proposed; delivery method needs confirmation |

Future deployment may use a VPN or identity-aware access gateway. The choice of provider and hosting arrangement is deferred. Application authorization and private document access remain requirements regardless of that choice.

Out of scope: a donor portal, campaign management, accounting ledger, bank reconciliation, public contribution forms, subscription fulfillment, live payment synchronization, foreign exchange calculations, and shared multi-organization hosting. Paper gifts and other payment sources require an explicit coverage decision before the first annual run is described as complete.

## 3. Users and access

The primary user is the Editor, who imports, reviews, prepares, and distributes acknowledgments. A finance reviewer may inspect and confirm the same records. A technical administrator manages accounts and configuration.

People and organizations may be donors without having login accounts. A payment's payer, bookstore purchaser, subscriber, gift recipient, and acknowledged donor are distinct roles; the system must not assume they are the same person.

CRM access is granted explicitly. Being a public website user, subscriber, or content editor conveys no CRM permission. The proposed capability matrix is in [Security](security.md).

## 4. Import and source evidence

The Editor selects a configured source account and uploads a supported PayPal activity CSV. The adapter validates the file format, required fields, numeric precision, dates, currency, record types, and identifiers before financial records are applied.

The preview shows counts and totals for new, duplicate, changed, excluded, unsupported, and invalid records. Monetary totals are grouped by currency and record type. Unsupported or malformed rows cannot disappear from reconciliation. Invalid rows block confirmation; any intentionally excluded records retain a reason and source reference.

Confirmation applies the accepted batch atomically. A failure leaves no partially applied financial batch. The batch retains its file digest, adapter version, importer, timestamps, validation results, and row-level provenance under restricted access.

Exact repeat imports create no duplicate financial effects. Overlapping exports also deduplicate through the adapter's logical record identity, not just the file digest. New source observations may change payment status, but they must preserve manual review decisions and flag affected allocations or issued letters for attention.

Raw imports are evidence, not editable payment forms. Retain the source observation history according to an approved retention policy; record corrections and exclusions separately.

## 5. Transaction review and donor matching

The review table includes payment date, source reference, payer, donor, gross amount, currency, fees, charitable amount, derived noncharitable amount, source status, and review status. Search and filters support completing a reporting period.

Imported amounts and identifiers are read-only in the allocation interface. The Editor may set either allocation portion, with the other derived from the gross amount. A blank allocation means unreviewed. A reviewed charitable amount of zero explicitly records a non-donation decision.

Suggestions may use configured product or subscription mappings, but remain visibly distinct from reviewed decisions. The confirmed allocation records its reviewer, time, explanation, and relevant benefit description and valuation. Historical mappings must use the policy applicable to the payment rather than today's subscription price.

Donor matching uses source identifiers and staff-confirmed links. Names and email addresses can suggest matches; they must not silently merge contacts. Store correspondence details independently of shipping details, and show missing contact information as an actionable exception.

For a positive incoming payment, the charitable amount must be between zero and the gross amount inclusive. Once reviewed, charitable and noncharitable portions must sum to gross. Fees remain separate. Apply checks in the user interface, write services, and database where supported by the data layout.

## 6. Refunds, statuses, and reporting periods

Pending, failed, canceled, or otherwise unresolved payments cannot produce new acknowledgments. Transfers, fee records, and other non-payment activity remain accounted for as excluded source records.

Refunds and reversals are linked adjustments with source evidence. They do not overwrite the original payment or automatically inherit a charitable allocation. Partial refunds require an explicit allocation rule or staff review. Cross-period refunds and changes to previously issued statements remain exceptions until the approved correction policy is applied.

Every report displays its exact start and end dates, reporting timezone, source coverage, and unresolved exceptions. Preserve source timestamps and distinguish payment occurrence, source update, import, review, and letter issuance dates. The basis for the acknowledged contribution date must be confirmed before live use.

Fiscal reports and donor acknowledgments are distinct outputs. Western Friend's published FY2023 report covers October through September. The default donor reporting period and the current fiscal calendar still require confirmation.

## 7. Reconciliation and dashboards

The first dashboard is a review queue: unresolved donor identities, unreviewed allocations, changed source records, refund decisions, unsupported currencies, and missing correspondence details.

The second dashboard shows acknowledgment readiness for a selected period: reviewed contribution totals, donors ready for letters, blocked donors, generated drafts, issued letters, and recorded distribution results.

Reconciliation accounts for every source record as an accepted payment or adjustment, a duplicate observation, a documented exclusion, or an unresolved exception. Show record counts and financial totals for each category without combining currencies or conflating gross payments, fees, and contribution totals.

Affected letters remain blocked while their records are unresolved. Any partial run must identify the missing coverage or unresolved donors explicitly. An authorized reviewer records acceptance of the period's reconciliation before final issuance.

## 8. Acknowledgments and distribution

The organization profile holds the confirmed legal name, public name, EIN, correspondence address, contact information, and signatory. Letter wording and applicable benefit valuations are approved before use.

A draft acknowledgment contains donor correspondence details, the organization identity, exact covered period, itemized payment dates and contribution amounts, total contributions, and the appropriate goods-or-services disclosures. Mixed payments need sufficient information to explain the approved contribution and benefit treatment. Do not apply a blanket no-benefits statement to every donor.

Generate letters for eligible donors regardless of whether an individual gift meets a substantiation threshold. IRS acknowledgment and disclosure requirements inform the template; this annual workflow does not replace disclosures required at solicitation or receipt.

The Editor can preview a donor letter and batch summary before final issuance. Issuance freezes the letter content, donor details, included records and allocations, template version, reviewer, timestamp, and document digest. Later corrections create a linked revision and mark the prior version as superseded without rewriting it.

Generated, issued, and distributed are separate states. For the proposed first delivery path, provide individual PDFs, an authorized batch download, and a mailing manifest. Staff can record postal mailing or external email dispatch and any failure. A download alone does not mark a letter as sent; external dispatch records are staff attestations, not proof of receipt. In-app email and automated delivery tracking require a separate scope decision.

## 9. Acceptance scenarios

All people and transactions below are synthetic. Amounts are USD.

| Scenario | Expected result |
| --- | --- |
| A $100 pure gift, a $90 patron payment with an approved $45 charitable allocation and $45 benefit, and an ordinary $20 purchase | Reviewed contribution total is $145, with the relevant benefit disclosure; the ordinary purchase is excluded from contribution totals |
| A completed $100 gift with a $3 processing fee | Gross is $100, fees are $3, and the reviewed contribution remains $100 when no benefits were provided |
| An incoming $100 payment assigned $101 or a negative charitable amount | Every supported write path rejects the allocation |
| Blank allocation versus reviewed $0 allocation | The blank blocks the affected letter; the reviewed zero is an explicit non-donation decision |
| Exact and overlapping repeat imports | No duplicate payments or contribution totals; source provenance remains traceable |
| An imported payment changes from pending to completed, or is later reversed | The existing payment is updated through a new source observation; affected review or issuance is rechecked |
| A partial refund of a mixed payment | The affected acknowledgment is blocked until refund allocation is reviewed |
| Two contacts share a name or email; a subscription is purchased as a gift | No automatic contact merge or reassignment of the donor to the recipient |
| A year-boundary payment or cross-year refund | The configured date policy is explicit; unresolved correction treatment blocks affected issuance |
| A non-USD or malformed record | Visible exception with source reference; no silent conversion or omission |
| An allocation or donor address changes after issuance | The original letter stays unchanged; a linked revision can be generated |
| An unauthorized user requests a donor record, export, or direct PDF URL | Access is denied without leaking donor information |

## 10. Decisions needed before the first operational run

| Decision | Evidence or confirmation needed |
| --- | --- |
| Reporting period and date basis | Editor/finance confirmation of calendar-year acknowledgment versus fiscal reporting, timezone, and contribution date policy |
| Source completeness | Sanitized PayPal export shape, accounts covered, and whether mailed gifts or other channels must be included |
| Historical subscription allocation | Approved plan mappings, benefit valuations, and effective dates |
| Refund corrections | Treatment of partial refunds, cross-year refunds, and already issued letters |
| Donor attribution | Rules for joint gifts, organizational payers, intermediaries, and correspondence names |
| Letter and organization profile | Existing approved letter, legal identity, contact details, disclosures, and signatory |
| Distribution | Postal/external email workflow versus application email, and what completion means |
| Operational ownership | Account administrator, data reviewer, retention policy, backup owner, and deployment controls |

These decisions do not block drafting the application or synthetic-data development. They block presenting unsupported policy assumptions as approved behavior or issuing real letters under those assumptions.

## 11. Sources and related documents

- [Architecture](architecture.md), [Security](security.md), and [Roadmap](roadmap.md).
- [PayPal Activity Download report](https://developer.paypal.com/reports/activity-download/).
- [PayPal Transaction Search reference](https://developer.paypal.com/api/transaction-search/v1/search-get): reporting identifiers and statuses need adapter-specific handling.
- [Western Friend subscription prices](https://westernfriend.org/subscription-prices/): current public evidence of mixed patron payments, not approval of historical mappings.
- [Western Friend FY2023 annual report](https://westernfriend.org/board-documents/fy2023-annual-report/): published fiscal-period context.
- [IRS Publication 1771](https://www.irs.gov/pub/irs-pdf/p1771.pdf) and [quid pro quo disclosures](https://www.irs.gov/charities-non-profits/charitable-organizations/charitable-contributions-quid-pro-quo-contributions): acknowledgment and benefit-disclosure requirements.
