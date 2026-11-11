# Wagtail CRM

An open-source nonprofit CRM built with Django and Wagtail, starting with payment imports, donation reconciliation, and annual donor acknowledgments.

Wagtail's staff interface is the application's only UI. The site root redirects to Wagtail login; additional workflows belong inside Wagtail wherever possible. There is no separate public frontend.

## Status

Alpha contact-management foundation; there are no existing installations. The reusable app runs inside a local Django/Wagtail host with SQLite, synthetic contacts, ordinary Given name/Family name fields, optional email and multiline postal editing, Wagtail activity history, permission-controlled views, a PayPal activity CSV import with preview, donor linking with charitable amounts, refunds linked to their payments, period reconciliation against PayPal totals, and donor acknowledgment letters with corrections. Dispatch records, financial controls and reporting dashboards are still planned. Production authentication hardening and deployment have not been completed.

## Run locally

Install [mise](https://mise.jdx.dev/getting-started.html), then run from the repository root:

```bash
mise trust
mise install
mise run install
mise run migrate
mise run demo
mise exec -- uv run --locked python manage.py createsuperuser
mise run dev
```

Open <http://127.0.0.1:8000/admin/> and select **Contacts**. Set your own local login credentials; no default administrator password is shipped. This host is for synthetic local data and is not a production settings module.

```bash
mise run check
mise run hooks-install
mise run hooks
mise run test
mise run browser-install
mise run browser
```

Old alpha databases from the former app label must be recreated/reseeded; there is no cross-label migration path. Keep a backup or select a fresh database file.

See [Development and testing](docs/development.md) for setup details, browser prerequisites, the optional PostgreSQL connection, and the manual UI checklist.

Run `mise tasks` to list available tasks. `mise install` provisions tools; `mise run install` installs the project's locked Python dependencies.

## First use case

Western Friend's Editor needs to prepare annual donor acknowledgments from historical payment records. The first release will let authorized staff:

1. Import a PayPal activity CSV and inspect validation and duplicate detection results.
2. Identify donors and review each payment's charitable and noncharitable portions.
3. Reconcile imported records, refunds, and exceptions for an explicit reporting period.
4. Preview and generate itemized donor letters, then record their distribution and any revisions.

The target is one nonprofit per installation, a separate staff application, and USD reporting initially. Other processors should be able to map into the same core data model. Their integrations are outside the first release.

## Documentation

| Document | Purpose |
| --- | --- |
| [Product requirements](_bmad-output/planning-artifacts/prds/prd-wagtail-crm-2026-11-08/prd.md) | Requirements, acceptance criteria, and open policy decisions |
| [Development and testing](docs/development.md) | Runnable host, SQLite setup, manual UI checks, and browser tests |
| [Architecture](docs/architecture.md) | Where architecture decisions and deployment boundaries are recorded |
| [Security](docs/security.md) | Trust boundaries, permissions, private artifacts, and release checks |
| [Roadmap](docs/roadmap.md) | Implementation increments and evidence needed for the first operational run |

## Development approach

One distribution contains one Django app per domain. Install the contacts app as `wagtail_crm.contacts` (label `wagtail_crm_contacts`); the package lives in `src/wagtail_crm/`; `devsite/` is a separate local host and is excluded from the package wheel. The current framework pair is Django 6.1.3 and Wagtail 8.1, with exact dependency versions in `uv.lock`. We track current stable compatible releases; upgrades are verified with the same local and CI checks. Processor normalization, financial decisions, and document generation will remain distinct modules within one application.

The CRM will have its own database credentials, application secrets, sessions, and private file storage. It will initially exchange data through reviewed imports. Public website accounts and access to its content editor will not automatically grant CRM access.

## Contributing

Begin with the product requirements and open decisions. Use synthetic fixtures for development, examples, screenshots, and tests. Do not include donor exports, real letters, credentials, or production database copies in commits, issues, or pull requests.

New contributions must be compatible with this repository's license. No implementation has been copied from Western Friend's existing website; any future source reuse requires checking its licensing and the relevant rights.

## License

[Apache License 2.0](LICENSE).
