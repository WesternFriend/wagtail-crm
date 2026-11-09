# Supporting technical and collaboration context

Status: interview notes, 2026-11-08. These guide downstream design; they are not validated deployment choices.

- Existing foundation: reusable Django/Wagtail app and separate synthetic development host. Payment importing, financial review and acknowledgment generation remain planned.
- Maintain processor-neutral records with source-specific adapters; PayPal CSV is first. Initial context ingestion uses documented exports and targeted corrections rather than live website integration.
- Western Friend website payment/order and subscription identifiers are candidate matching connections reported during discovery. Historical availability and join semantics have not been verified. Its AGPL source is a conventions reference; independently author Apache-compatible implementation and assess rights before source reuse.
- CRM deployment is separate from the public website, with independent credentials and private storage. Website accounts do not confer CRM access. Hosting/VPN decisions remain open.
- DigitalOcean App Platform and Spaces are likely candidates proposed by Brylie, pending technical validation; no selection or suitability claim is established.
- Brylie develops locally with synthetic records, then supplies a restricted hosted synthetic test environment. Async feedback is primary because of timezone differences; monthly calls are optional.
- The Editor uses a Mac desktop. Browser, macOS version, display and accessibility preferences remain unknown. Desktop use guides initial UX and browser validation.
- Portability proposal: documented CSV or JSON, PDFs, retained evidence and manifest, preserving stable IDs and relationships while excluding active credentials/session secrets. Exact schema and verification procedure remain to be designed.
- Current draft requirements/architecture/security notes provide background, not stakeholder approval or proof of implemented controls. Scaffold verification from earlier environments must not be treated as current validation.

## Current contact-slice decisions — approved through 2026-11-09

Brylie approved the six staff-task AC-18 criteria and a smaller contact implementation. People always use ordinary Given name/Family name; organizations use Name. Changing organization to person requires staff-entered parts and never splits the organization name automatically. Use Django/Wagtail built-ins for actions, permissions and history. Do not add custom snapshots, revisions, stale-edit/delete controls or a codec. There are no existing installations to migrate. Start the contacts domain app with one fresh initial migration and no baseline activity entries.

This supersedes the former JSON profile, repeated-component editor, separator/line-ending rules and custom history requirements. Standards remain references for a later concrete import/export workflow, not a storage or formatting contract for this increment. Shared contact details never confirm donor attribution. Source-account identity decisions, financial rules, letter snapshots and delivery remain future workflows.

Simplicity and using Django/Wagtail features instead of bespoke equivalents are standing principles across the CRM. Wagtail is the sole UI; no separate frontend is planned. Root AGENTS.md and CLAUDE.md share these guardrails across coding agents.
