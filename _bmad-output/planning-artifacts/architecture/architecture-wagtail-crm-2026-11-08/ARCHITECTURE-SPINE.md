# Architecture spine

Decisions that span increments. Each slice's behavior is in the [PRD](../../prds/prd-wagtail-crm-2026-11-08/prd.md) and its [acceptance criteria](../../prds/prd-wagtail-crm-2026-11-08/acceptance-criteria.md); deployment boundaries are in [Security](../../../../docs/security.md).

## AD-1 — One distribution, one Django app per domain

The `wagtail_crm` distribution holds one app per domain, labelled `wagtail_crm_<domain>`: `wagtail_crm.contacts`, `wagtail_crm.payments` and `wagtail_crm.letters`. Dependencies point toward the domain that owns the data: payments depends on contacts for the donor, letters on contacts and payments; contacts imports no sibling. Add no shared core or generic audit app without a concrete need.

## AD-2 — Stock Wagtail views, history and permissions

Wagtail is the only UI. Use `ModelViewSet`, its standard actions, `ModelLogEntry` history and model permissions. Write a custom view only where Wagtail has no equivalent flow, and name that gap in the PR. Concurrent edits are last-save-wins until staff collisions show a need.

## AD-3 — Source facts stay separate from staff decisions

Imported source values are `editable=False` and change only through an import. Staff decisions, such as the donor and charitable amount, are ordinary editable fields beside them. Model `clean()` gives staff field errors; database constraints also hold the money rules for every writer.

## AD-4 — Store UTC, display in each user's time zone

Store timestamps in UTC (`TIME_ZONE` stays UTC). Each staff member sees them in their Wagtail time zone preference. Reporting periods run from UTC midnight to UTC midnight too; time zones only change how dates are displayed.

## AD-5 — Issued documents are stored snapshots in private storage

An issued letter stores its PDF and the values it shows; it is never edited, and a correction is a new record linked to the earlier one. Generated files live in a named private storage outside `MEDIA_ROOT` and are served only through a view that checks the model's view permission, with private, uncacheable responses.
