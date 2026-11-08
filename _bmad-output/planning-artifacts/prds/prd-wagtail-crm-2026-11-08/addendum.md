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

- Brylie requires established, explicitly selected standards for common models (people, organizations, addresses and related contact data/relationships), with source adapters mapping into that baseline. See FR-23 and AC-18. Standards/versions/profile/library selection remains open; document it before extending the scaffold, including mappings, international/incomplete-data behavior and justified departures.
