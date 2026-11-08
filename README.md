# Wagtail CRM

An open-source nonprofit CRM built with Django and Wagtail, starting with payment imports, donation reconciliation, and annual donor acknowledgments.

Wagtail's staff interface is the application's only UI. The site root redirects to Wagtail login; additional workflows belong inside Wagtail wherever possible. There is no separate public frontend.

## Status

Contact-management foundation. The reusable app runs inside a local Django/Wagtail host with SQLite, synthetic contacts, ordinary given-name/surname fields, optional email and multiline postal editing, private change history, and permission-controlled views. Contact names and internal interchange helpers follow a bounded JSContact profile. The payment importer, financial controls, reporting dashboards, and letter generation are still planned. Production authentication hardening and deployment have not been completed.

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
| [Product requirements](docs/product-requirements.md) | User workflow, scope, acceptance scenarios, and open policy decisions |
| [Development and testing](docs/development.md) | Runnable host, SQLite setup, manual UI checks, and browser tests |
| [Architecture](docs/architecture.md) | Core records, adapter contract, and financial invariants |
| [Security](docs/security.md) | Trust boundaries, permissions, private artifacts, and release checks |
| [Roadmap](docs/roadmap.md) | Implementation increments and evidence needed for the first operational run |

## Development approach

The reusable package lives in `src/wagtail_crm/`; `devsite/` is a separate local host and is excluded from the package wheel. The starting framework pair is Django 5.2 LTS and Wagtail 7.4 LTS, with exact dependency versions in `uv.lock`. Processor normalization, financial decisions, and document generation will remain distinct modules within one application.

The CRM will have its own database credentials, application secrets, sessions, and private file storage. It will initially exchange data through reviewed imports. Public website accounts and access to its content editor will not automatically grant CRM access.

## Contributing

Begin with the product requirements and open decisions. Use synthetic fixtures for development, examples, screenshots, and tests. Do not include donor exports, real letters, credentials, or production database copies in commits, issues, or pull requests.

New contributions must be compatible with this repository's license. No implementation has been copied from Western Friend's existing website; any future source reuse requires checking its licensing and the relevant rights.

## License

[Apache License 2.0](LICENSE).
