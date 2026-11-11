# Minimum operational release — acceptance criteria

Each criterion reads "staff do X and see Y". AC-18 covers the contact increment. AC-01 to AC-17 cover the 0.1.0 acknowledgment cycle, and each names the slice issue that delivers it.

Run the criteria on synthetic data. Amounts are synthetic USD fixture values, not approved policy. Before the real-data pilot (#12), the bookkeeper confirms the expected totals independently of the app. Keep real donor files out of the repository.

## 0.1.0 acknowledgment cycle

| Case | Slice | Staff task | Observable result |
| --- | --- | --- | --- |
| AC-01 | #5, #6 | Import a completed $100 gift with a $3 fee, link it to a donor and record $100 as charitable | The payment shows gross $100, fee $3, net $97 and charitable $100. The fee does not reduce the contribution. |
| AC-02 | #6, #9 | For the same donor, record $45 of a $90 patron payment and $0 of a $20 purchase as charitable, then preview the year's letter | Each payment shows its non-charitable remainder ($45 and $20). The letter shows the $100 gift, and the $90 patron payment with $45 charitable and $45 for goods or services. It totals $145 charitable; the purchase is not listed. |
| AC-03 | #6 | Enter a charitable amount above the gross, or below zero; leave another payment blank | The form explains the error and keeps the entered values, and nothing is saved. The blank payment appears under "needs charitable amount"; a saved $0 does not. |
| AC-05 | #6 | Link a payment whose PayPal name or email differs from, or matches, an existing contact | The PayPal payer name and email stay visible on the payment. No contact is merged, renamed or linked without staff choosing it. |
| AC-06 | #5 | Upload a CSV, upload the same file again, then upload a file that overlaps it | The repeat upload is rejected. The overlapping file adds only the new transactions, and existing donor links and charitable amounts are unchanged. |
| AC-07 | #5 | Upload a file containing a malformed amount, an unsupported status and a EUR row | The preview lists each skipped row with its reason. Nothing is dropped silently, and no USD value is invented. |
| AC-08 | #7 | Open a payment that has a linked refund; separately, find a refund whose payment was not imported | The payment shows the refund and the adjusted charitable amount for staff to review. The unmatched refund is listed as needing review. |
| AC-10 | #8 | Choose a period (whole UTC days), enter PayPal's totals for the same UTC range, and accept the reconciliation | Count, gross, fees, net and refunds appear next to the entered totals, and any difference is shown. Staff can accept only when every payment in the period has a charitable amount and no refund is unmatched. Letters cannot be issued until staff accept; History shows who accepted and when. |
| AC-12 | #9 | Issue a donor's letter, then edit the contact's address and one payment | The issued PDF and its stored values do not change. |
| AC-13 | #9 | Issue a correction for an issued letter | A new letter is linked to the earlier one, and the earlier PDF is still available. |
| AC-14 | #10 | Download an issued letter, record a failed email dispatch, then a successful postal dispatch | Downloading alone leaves the letter unsent. Both attempts are listed with channel, date, outcome and note. Unsent and failed letters can be listed. |
| AC-15 | #5–#10 | Sign in as a user without payment or letter permissions and open payment, letter and PDF URLs directly | Access is denied and nothing changes. Wagtail's standard model permissions govern access. |
| AC-16 | #13 | Restore the pilot backup into a fresh environment | The same contacts, payments and letter PDFs are present. |
| AC-17 | #11 | The Editor runs one period end to end on synthetic data: import, link donors, review refunds, reconcile, issue and record dispatch | The Editor completes the cycle using the keyboard and browser zoom, and confirms it fits their real work. Problems found are fixed or filed as issues. |

### Deferred from 0.1.0

Each item returns only when a real case shows it is needed.

- AC-04 (approved historical split policies): staff enter the charitable amount directly in #6.
- AC-09 (offline/mailed-gift coverage): waits on the coverage decision in roadmap step 0.
- AC-11 (batch approval and version invalidation): 0.1.0 issues letters one at a time.
- Reopening an accepted reconciliation after later imports, and recovering from an interrupted import or issuance: Django transactions and ordinary Wagtail behavior are accepted for now.
- Refund splits beyond reducing the contribution, the portable-export half of the earlier AC-16, delivery-exception closure authority, and the evidence contract, gate-dependency matrix and reconciliation bridge from the earlier draft. Git history keeps that draft.

## AC-18 — Minimum contact management

Approved by Brylie; organization-to-person wording updated on 2026-11-09. These staff tasks supersede the earlier name-profile, formatting, custom-history and concurrency criteria. They do not approve imports, exports or financial workflows.

| Case | Staff task | Observable result |
| --- | --- | --- |
| AC-18-01 | Add a person | Enter Given name, Family name, or both in one ordinary Wagtail form; single, multiword and non-Latin names work without duplicate entry. |
| AC-18-02 | Add an organization | Enter one Name without person-name fields. |
| AC-18-03 | Change an organization to a person | Enter a given name, family name, or both; the organization name is not split automatically. |
| AC-18-04 | Edit a contact | Change name, contact type, optional email and postal address in one form; validation explains errors and retains entered work. |
| AC-18-05 | Review activity | Use Wagtail History to identify actions, users and times. Activity for deleted contacts remains available through Wagtail Site history. |
| AC-18-06 | Use restricted accounts | Accounts without contact permissions cannot view or change contacts. Wagtail's standard model permissions govern access. |

Concurrent-edit protection is deferred; ordinary Wagtail last-save-wins behavior is accepted for this slice. There are no existing installations to migrate. The contacts app begins with a fresh initial migration and no per-record migration history entries.

### Future interoperability

Use established contact standards when a concrete import/export workflow needs mappings. JSContact, vCard, Schema.org and CLDR remain references for that later design; this slice supplies no codec or conformance claim. Donor attribution, source/account mappings, delivery readiness and issued-document snapshots remain separate future tasks.

## Decisions needed for 0.1.0

| Decision | Owner | Needed before |
| --- | --- | --- |
| Reporting period (default: calendar year) | Editor | Reconciliation (#8) |
| Timezone for the period | Brylie | Decided: periods run from UTC midnight to UTC midnight; time zones only change how dates are displayed (#8) |
| Refund treatment beyond reducing the contribution | Bookkeeper | Refund review (#7) on real data |
| Expected totals for the pilot period, confirmed independently of the app | Bookkeeper | Pilot (#12) |
| Letter wording for the goods-or-services value of a mixed payment | Bookkeeper | Real letters (#12). The plain #9 template shows a "Goods or services" column for each payment until then |

## Development increments versus release completion

Use these criteria to bound implementation increments. An increment can be accepted for its defined synthetic behavior while real policy remains unresolved, provided that limitation is explicit and real issuance stays unavailable. A passing component test, balanced PayPal dataset or generated PDF does not complete the operational cycle. Full release acceptance requires the agreed coverage, financial, communication, distribution, privacy, usability and continuity evidence in the [PRD](prd.md).
