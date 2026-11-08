# Roadmap

Status: reporting workflow proposed; local development scaffold implemented. Updated: 2026-11-08.

The goal of the first release is one completed, reconciled acknowledgment cycle for Western Friend. There are no delivery-date estimates until the input format and open policies are confirmed.

## Development foundation

The repository includes a runnable `devsite` host with SQLite and the separate reusable `wagtail_crm` app. It has a minimal person/organization Contact model, Wagtail model views, a synthetic seed command, permission and CSRF tests, and a real-browser smoke suite. See [Development and testing](development.md) for commands and the manual UI checklist.

This foundation does not implement payment imports or reporting. Verify browser checks on a machine or CI runner that permits Chromium execution; test PostgreSQL behavior before relying on financial locking or production deployment.

## 0. Confirm the first reporting cycle

Review a sanitized PayPal activity export and an approved historical letter. Confirm the period, reporting timezone/date basis, covered source accounts, historical patron mappings, refund treatment, and delivery workflow. Determine whether mailed gifts or other channels must be included.

Record decisions in the [product requirements](product-requirements.md). Raw donor files remain private and must not be attached to public repository discussions. Synthetic fixtures should reproduce their structure and edge cases.

Exit evidence: a documented import schema, synthetic sample dataset, approved allocation examples, letter requirements, and explicit coverage limitations. Framework scaffolding may proceed while these decisions are resolved.

## 1. Import and inspect payments securely

Create the Django/Wagtail project with pinned compatible dependencies, separate environment configuration, explicit CRM capabilities, and private storage. Add source accounts, staged import batches, source observations, and normalized incoming payment records.

Implement one PayPal CSV adapter and a staff preview/confirmation workflow. Include validation, same-file and overlapping-file duplicate detection, changed-status handling, reconciliation counts, and an inspectable payment list. Imports apply atomically and retain row-level evidence.

Exit evidence: repeat and concurrent imports cannot duplicate payments; malformed and unsupported records stay visible; unauthorized users cannot access records or import artifacts.

## 2. Resolve donors and charitable allocations

Add person/organization contacts, source identity links, the transaction review table, reviewed allocation rules, and an audit trail. Support mixed payments, documented non-donation decisions, and linked refund review. Preserve the difference between source facts, suggestions, and confirmed staff decisions.

Add the review queue and period reconciliation dashboard. Test the same normalization contract with synthetic records from an alternative source without implementing another production processor.

Exit evidence: the synthetic acceptance dataset reconciles; invalid allocations fail on every write path; ambiguous donors, source conflicts, and refunds block affected issuance.

## 3. Preview and issue annual acknowledgments

Add organization/letter configuration, explicit period selection, contribution and benefit line rendering, and PDF previews. Add reconciliation acceptance, atomic issuance snapshots, private batch downloads/manifests, and linked revisions that preserve earlier documents.

Exit evidence: the Editor can trace every letter line back to source evidence and a reviewed decision. The mixed-payment acceptance example totals $145, private downloads are enforced, and later edits do not alter issued artifacts.

## 4. Complete distribution and validate the workflow

Implement the agreed distribution path. The proposed minimal option provides PDFs and manifests, plus staff-recorded postal or external email dispatch/failure. In-app email requires explicit scope, credentials, retry behavior, and tests that prevent unintended or duplicate sends.

Run the complete workflow with synthetic data and the Editor. Then validate a restricted real-data pilot against the existing financial records and approved letter policy. Document exceptions and resolve discrepancies before final issuance.

Exit evidence: the Editor can complete the reporting and distribution cycle, distinguish generated/issued/dispatched states, and revise a letter without losing history.

## 5. Prepare the separate deployment

Choose hosting, network or gateway restrictions, staff MFA/recovery configuration, credential boundaries, private storage, backups, and operational ownership. These decisions may be made earlier if needed for the pilot, but public deployment is not part of the documentation-only starting change.

Verify the [security requirements](security.md) in the actual hosted environment, run Django's production deployment checks, test restoring the database and artifacts, and record any data retention and incident procedures.

Exit evidence: the approved deployment and tested controls can support the first operational run. A VPN or gateway does not replace application permissions or private storage.

## Later candidates

- Additional payment processors or structured offline-gift imports driven by actual source coverage needs.
- Read-only PayPal synchronization, followed by narrowly scoped website integration if useful.
- In-app delivery, if external distribution proves insufficient.
- Additional contact relationships, activities, fundraising views, and fund allocations.
- An installable core package with a thin Wagtail integration once another installation validates the interfaces.

Public donor self-service and multi-organization hosting require separate authorization and threat-model work. They are not implicit consequences of adding a second source adapter.
