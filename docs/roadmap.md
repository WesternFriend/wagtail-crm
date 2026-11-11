# Roadmap

Status: reporting workflow proposed; local development scaffold implemented. Updated: 2026-11-11.

The goal of the first release is one completed, reconciled acknowledgment cycle for Western Friend. There are no delivery-date estimates until the input format and open policies are confirmed.

## Development foundation

The repository includes a runnable `devsite` host with SQLite and the `wagtail_crm.contacts` domain app in one reusable distribution. It has a minimal person/organization Contact model, Wagtail model views, a synthetic seed command, permission and CSRF tests, and a real-browser smoke suite. See [Development and testing](development.md) for commands and the manual UI checklist.

The `wagtail_crm.payments` app imports PayPal activity CSVs with a preview (#5) and lets staff link each payment to a donor with its charitable amount (#6), shows refunds next to the payments they refund (#7), reconciles a period's totals against PayPal's (#8), and issues a donor's acknowledgment letter for an accepted reconciliation (#9); dispatch records are not implemented yet. Verify browser checks on a machine or CI runner that permits Chromium execution; test PostgreSQL behavior before relying on financial locking or production deployment.

## 0. Confirm the first reporting cycle

Review a sanitized PayPal activity export and an approved historical letter. Confirm the period, reporting timezone/date basis, covered source accounts, historical patron mappings, refund treatment, and delivery workflow. Determine whether mailed gifts or other channels must be included.

Record decisions in the [PRD](../_bmad-output/planning-artifacts/prds/prd-wagtail-crm-2026-11-08/prd.md). Raw donor files remain private and must not be attached to public repository discussions. Synthetic fixtures should reproduce their structure and edge cases.

Exit evidence: a documented import schema, synthetic sample dataset, approved allocation examples, letter requirements, and explicit coverage limitations. Framework scaffolding may proceed while these decisions are resolved.

## 1. Import and inspect payments securely

Staff upload a PayPal Activity Download CSV, preview the rows to import and the rows skipped with a reason, and confirm; all new rows are saved in one transaction or none (#5). Transaction ID is the identity, so repeated and overlapping files add only new payments. Imported values are read-only in a Wagtail payment list.

Exit evidence: repeat and concurrent imports cannot duplicate payments; skipped rows are explained in the preview; unauthorized users cannot see or import payments.

## 2. Resolve donors and charitable allocations

Staff link each payment to a donor contact and record its charitable amount, from zero to the gross (#6). Refunds are linked to their original payment and unmatched refunds are listed (#7). For a chosen period, staff compare imported totals with PayPal's and accept the reconciliation (#8).

Exit evidence: the synthetic acceptance dataset reconciles; invalid charitable amounts fail on every write path; payments without a charitable amount and unmatched refunds block reconciliation acceptance.

## 3. Preview and issue acknowledgment letters

Staff preview a letter for one donor and an accepted reconciliation's period: the donor's name and address, each contribution with its charitable and goods-or-services amounts, and the charitable total. Issuing stores the PDF and the values it shows, so later edits to the contact or payments do not change it (AC-12). A correction is a new letter linked to the earlier one, whose PDF stays available (AC-13). Letters are issued one at a time with a plain template; organization configuration and batch issuing wait for a real need (#9).

Exit evidence: the mixed-payment example totals $145, a letter cannot be issued before its period is accepted, issued PDFs are served only to staff with letter permissions, and later edits do not alter issued letters.

## 4. Complete distribution and validate the workflow

Implement the agreed distribution path. Downloadable PDFs and manifests, plus staff-recorded postal or external email dispatch/failure, are sufficient for the first cycle. The Editor may manually email PDFs through existing tools; exact delivery practice still needs confirmation. Downloading a PDF does not record dispatch. Application email sending is outside the first cycle; a later enhancement would require explicit scope, credentials, retry behavior, and tests that prevent unintended or duplicate sends.

Run the complete workflow with synthetic data and the Editor. Then validate a restricted real-data pilot against the existing financial records and approved letter policy. Document exceptions and resolve discrepancies before final issuance.

Exit evidence: the Editor can complete the reporting and distribution cycle, distinguish generated/issued/dispatched states, and revise a letter without losing history.

## 5. Prepare the separate deployment

Choose hosting, network or gateway restrictions, staff MFA/recovery configuration, credential boundaries, private storage, backups, and operational ownership. These decisions may be made earlier if needed for the pilot, but public deployment is not part of the documentation-only starting change.

Verify the [security requirements](security.md) in the actual hosted environment, run Django's production deployment checks, test restoring the database and artifacts, and record any data retention and incident procedures.

Exit evidence: the approved deployment and tested controls can support the first operational run. A VPN or gateway does not replace application permissions or private storage.

## Later candidates

- Concurrent contact-edit protection, only if staff collisions demonstrate a need; the alpha uses standard Wagtail last-save-wins behavior.
- Contact import/export mappings designed against actual source data; no codec or JSContact storage profile is required now.

- Additional payment processors or structured offline-gift imports driven by actual source coverage needs.
- Read-only PayPal synchronization, followed by narrowly scoped website integration if useful.
- Email issued PDFs directly from the CRM to save the Editor a manual step, after validating the actual delivery workflow. Downloadable PDFs and manual external email suffice for the first cycle.
- Additional contact relationships, activities, fundraising views, and fund allocations.
- An installable core package with a thin Wagtail integration once another installation validates the interfaces.

Public donor self-service and multi-organization hosting require separate authorization and threat-model work. They are not implicit consequences of adding a second source adapter.
