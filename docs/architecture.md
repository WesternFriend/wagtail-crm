# Architecture

## Domain-app decision — 2026-11-08

One project and one distribution (`wagtail_crm`) contain one Django app per domain, labelled `wagtail_crm_<domain>`. Contacts is `wagtail_crm.contacts` (`wagtail_crm_contacts`). Later domains may depend on contacts; contacts imports no sibling domain. Do not introduce a shared core or generic audit app without a demonstrated need. There are no sibling domain apps yet, so import-linter adds no value at this stage.

The initial contact slice uses plain columns and Wagtail ModelViewSet, standard actions, permissions, ModelLogEntry and History. Use framework features before bespoke models/views/templates. No JSON name codec, custom snapshots, RevisionMixin or concurrency layer is required. Other records and financial controls below are future architecture, not capabilities implemented by this slice.: first vertical slice

For implemented contact semantics and fields, use the [accepted contact architecture spine](../_bmad-output/planning-artifacts/architecture/architecture-wagtail-crm-2026-11-08/ARCHITECTURE-SPINE.md). It supersedes contact-shape proposals here. Financial and deployment sections below remain proposals.

Status: proposed implementation design. Updated: 2026-11-08.

The [product requirements](product-requirements.md) define behavior. This document proposes a small design for implementing that behavior; class names and file layout may change as the first real export is inspected.

## Application and deployment boundaries

Use one Django project with Wagtail's staff interface. Organize core financial/contact logic, source adapters, and presentation into distinct modules. These are code boundaries within one application; separate services and repositories are unnecessary for the first slice.

The CRM is deployed independently of westernfriend.org, with separate secrets, database credentials, sessions, and private storage. Its initial input is a reviewed file import. It has no public donor API and does not need direct access to the public website database.

Processor integrations map to the core model. Western Friend-specific plan mappings and letter policy remain configuration or source-specific rules. Avoid foreign keys or required imports into the public website's order, account, or subscription models; retain external references and the evidence needed for reporting instead.

One nonprofit per installation is the proposed first scope. Wagtail's site selection must not be used as an assumed tenant authorization boundary. Shared multi-organization hosting would require a separate design and isolation tests.

## Proposed core records

| Record | Responsibility |
| --- | --- |
| OrganizationProfile | Legal and correspondence identity, reporting settings, approved letter configuration |
| Contact | Person or organization with correspondence details; no login account required |
| ExternalIdentity | Staff-confirmed mapping between a contact and a source-account identity |
| SourceAccount | Processor or source type and merchant/account reference; CSV use requires no payment API credentials |
| ImportBatch | File digest, source account, adapter version, actor, times, validation report, application status |
| SourceRecord | Restricted original row/observation, batch and row reference, logical source key, disposition, and linked core record |
| Payment | Normalized incoming payment, status, gross amount, currency, dates, source references, donor link, and allocation review fields |
| Refund | Linked refund or reversal, magnitude, currency, source evidence, and reviewed contribution adjustment |
| Acknowledgment | Issued snapshot of the donor, period, financial lines, benefit disclosures, template, and PDF; linked revision history |
| DistributionRecord | Staff-recorded external dispatch or later provider attempt, channel, status, actor, and times |
| AuditEvent | Changes to identity links and allocation decisions, exclusions, issuance, exports, and permission-relevant actions |

Start with one reviewed charitable allocation per incoming payment, stored alongside the payment amount so basic bounds can be enforced by a database check. Derive the noncharitable portion instead of maintaining a second independently editable value. Keep allocation changes in the audit history.

Multiple funds, campaigns, or child allocation rows can be introduced when needed. If allocations later span rows, their sum requires transactional enforcement; a simple same-row check cannot validate a cross-row aggregate.

## Source adapter contract

An adapter performs parsing, validation, identity derivation, and normalization. It must not decide that an unreviewed payment is a charitable contribution solely because it arrived through a payment processor.

The normalized input contract carries:

- Source account and adapter version; batch and original row references.
- A stable logical record identity derived according to the source's semantics.
- Record kind, direction, normalized status, and the original source status.
- Relevant occurrence, completion, and source-update timestamps with timezone information.
- Amounts represented with decimals and explicit currency; original values and signs remain in the raw observation.
- Payer identifiers and contact suggestions, separate shipping/recipient details where available.
- Parent payment, refund, order, subscription, or other external references where present.

Unknown kinds or statuses become visible exceptions. Preserve enough original context to investigate without placing sensitive payloads in normal application logs.

Use separate identity rules for files, logical financial records, and source observations. A file digest prevents reapplying the exact same file. A source-account-scoped logical key deduplicates overlapping exports. The adapter must distinguish multiple reporting records that share a transaction ID; PayPal documents that this can occur. A payload hash alone cannot identify a logical payment across status updates.

For the first source, implement one documented PayPal activity export format against a sanitized sample. Do not claim compatibility with every PayPal CSV locale or report variant. Add adapter contract tests and demonstrate the same contract with synthetic non-PayPal records; a second production processor is deferred.

## Import application and changed source facts

Stage and validate before creating canonical financial records. Apply a confirmed batch in a database transaction. Database uniqueness plus serialized or locked writes must protect against two simultaneous imports creating the same logical payment.

Retain subsequent observations rather than editing the earlier raw rows. A normalization update may change provider facts, but it must preserve a staff-reviewed donor link or allocation. A material change marks the affected review as conflicted and blocks new issuance until resolved. Already issued snapshots remain immutable and are linked to the correction workflow.

Keep the raw evidence, normalized provider facts, and staff decisions distinguishable in the code and the user interface even when some fields share a database row.

If a changed source amount would violate a saved allocation bound, retain the new observation as an unresolved conflict until the payment and allocation can be resolved atomically. Do not discard the observation or bypass the database constraint.

## Money, allocation, and status rules

| Rule | Enforcement |
| --- | --- |
| Money uses decimal arithmetic and currency-specific precision | Parser, model/write service, and fixtures; no binary floats |
| Incoming gross payment is positive | Validation and database check |
| An unreviewed charitable amount may be null | Explicit workflow state; null does not imply zero |
| Charitable amount, when present, is between zero and gross | Form/service validation and same-row database check |
| Reviewed allocation requires an amount, reviewer, time, and explanation; a positive charitable allocation also requires a confirmed donor | Review service with model/database checks where practical |
| Noncharitable amount equals gross minus charitable | Derived value, available only when allocation exists |
| Source fees and net receipts do not redefine gross or the allocation split | Separate fields and source-specific sign normalization |
| Refund currency matches its linked payment, and cumulative refunds cannot exceed supported original value | Atomic refund application with locking and explicit exception handling |
| A charitable refund adjustment cannot exceed its refund amount or the remaining approved charitable portion of the original payment | Atomic refund review with cumulative allocation checks |
| Only reconciled, reviewed, eligible payment/adjustment lines can be issued | Issuance service, not a UI-only check |

Use Django `CheckConstraint` and `UniqueConstraint` where applicable. Model `save()` does not call `full_clean()` automatically; import and other programmatic paths must use the explicit validation/write service. Cross-row checks require an atomic implementation rather than an ordinary check constraint.

A mixed payment's noncharitable remainder is not automatically an approved fair-market valuation. Store the benefit description, valuation, and applicable policy evidence separately when needed for the acknowledgment wording. Negative refund amounts do not pass through the positive-payment allocation rule.

USD-only issuance is the proposed initial limit. Preserve and flag other currencies without calculating exchange rates or aggregating unlike amounts.

Store timezone-aware timestamps, normalize instants to UTC, and display them in the configured reporting timezone. Use an inclusive start and exclusive end for internal period queries, converting the user-facing covered dates explicitly. Never infer a source timezone from the application server or replace the contribution date with the import date.

## Wagtail interface and artifacts

Wagtail CMS is the only application UI. The site root redirects to the Wagtail login page. Additional features should use Wagtail's admin extension points wherever possible; no separate public frontend or parallel Django UI is planned.

Use ordinary Django models exposed through Wagtail `ModelViewSet` and custom review/import/issuance views. Permissions apply to the underlying endpoints and services, including direct document downloads and exports. Record state transitions explicitly; saving a model should not silently send letters or issue financial documents.

Editors may change controlled letter content, such as introduction and closing text. Financial lines, conditional disclosures, and calculations come from reviewed records and versioned application logic. Do not offer arbitrary executable template editing.

Store raw imports, manifests, and generated PDFs in dedicated private storage. Wagtail can provide the interface without placing donor artifacts in the public website's document library. Authorized downloads use access checks; identifiers and filenames provide no authorization.

Freeze issuance in an atomic operation against the reviewed record versions. Snapshot every financial line and relevant policy/template version. Preserve the generated artifact and its digest so a later source update or renderer change cannot silently change an issued letter. Distribution is a separate action; external dispatch is recorded as an attestation.

## References

- [Product requirements](product-requirements.md) and [Security](security.md).
- [Django constraints](https://docs.djangoproject.com/en/6.1/ref/models/constraints/).
- [Django model validation](https://docs.djangoproject.com/en/6.1/ref/models/instances/#validating-objects).
- [Wagtail model viewsets](https://docs.wagtail.org/en/stable/extending/generic_views.html).
- [PayPal reporting identifiers and statuses](https://developer.paypal.com/api/transaction-search/v1/search-get).
