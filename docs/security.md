# Security posture and implementation requirements

Status: design requirements, not implemented controls. Updated: 2026-11-08.

## Scope and trust boundaries

The initial deployment serves authorized staff of one nonprofit. It holds donor identities, contact details, source financial records, contribution decisions, and annual letters. Both confidentiality and integrity matter: an incorrect allocation or altered acknowledgment is a security-relevant failure even if no data is disclosed.

The public website is a separate application. Its process must not receive CRM database credentials, storage credentials, session keys, or payment-reporting credentials. Reusing a hostname prefix, code repository, or database server does not itself establish or remove this boundary; actual process privileges and credentials determine access.

Separate databases and restricted roles may share a database server. Shared host or infrastructure administrator access remains a common risk, and containers share host-level dependencies. The hosting design must document which compromises it is intended to contain.

The PayPal export is untrusted input, even when uploaded by a trusted staff member. Donor names, notes, and addresses are untrusted text. Wagtail content-editing access does not automatically authorize CRM access. Technical superusers and infrastructure administrators remain privileged operators, not actors this application can fully constrain.

## Initial capability model

This is a proposed capability matrix, not a requirement to create three separate staff accounts. The Editor may hold both operational and finance capabilities. Ordinary technical administration accounts should receive donor access only when explicitly required; a superuser can override application permissions and must be treated accordingly.

| Capability | Editor | Finance reviewer | Technical administrator |
| --- | --- | --- | --- |
| View donor and payment records | Yes | Yes | Explicit grant |
| Import and classify payments | Yes | Yes | Explicit grant |
| Resolve donor links and refund decisions | Yes | Yes | Explicit grant |
| Accept reconciliation and issue/revise letters | Yes | Yes | Explicit grant |
| Export data and record distribution | Yes | Explicit grant | Explicit grant |
| Manage accounts, roles, and deployment configuration | Explicit grant | Explicit grant | Yes |

Default to denied access. Enforce capabilities on every list, detail, mutation, bulk action, export, download, and future API. Hiding a menu, field, or Wagtail chooser is not sufficient. Avoid granting powerful user-management permissions to ordinary content editors.

## Authentication and session requirements

Before real donor data is used in a hosted environment, provide secure staff authentication, MFA through the application or a supported identity gateway, login throttling, session expiry, and a tested account recovery/removal procedure. Use individual accounts rather than a shared Editor password.

Use HTTPS, secure and HttpOnly session cookies, CSRF protection, and host-scoped cookies with separate session configuration from the public website. Restrict trusted origins; avoid broad cross-subdomain trust. Django documents sibling-subdomain cookie risks, so a CRM subdomain alone is not complete browser isolation.

The specific VPN or gateway is deferred. If a gateway is selected, prevent bypass through an exposed origin and trust authentication/proxy headers only from the configured proxy. Gateway authentication supplements application authorization. A local development mode must be clearly separate from production configuration.

## Private artifacts and controlled processing

Raw imports, PDFs, mailing manifests, backups, and temporary renderer files belong in restricted storage outside public media access. Require authorization before minting any short-lived file URL. Protect direct storage access as well as application routes; use private responses that shared caches cannot retain.

Wagtail's chooser restrictions do not guarantee secrecy. Its document serving configuration also requires protecting direct storage URLs. The first implementation should use dedicated private storage for financial artifacts to make that requirement explicit.

Restrict CSV uploads by size and supported format, bound parser work, and validate values before application. Escape imported text in HTML and PDF content. Protect spreadsheet exports against formula interpretation. Restrict PDF rendering to approved local assets; imported text must not cause arbitrary URL or file fetching. Editable letter content must not enable arbitrary code or executable template expressions.

Validate and freeze correspondence addresses before distribution. Batch exports must be restricted and must not accidentally expose one donor's letter to another. Generating or downloading a file must not implicitly send it.

## Secrets, audit, retention, and recovery

Keep production secrets in deployment configuration or a secrets service, with separate credentials per environment. CSV-only imports need no payment API secrets. Future adapters must request only the capabilities needed and must not share broad payment account credentials with the public site.

Use synthetic data in the public repository, CI, examples, and screenshots. Do not put production exports, real donor letters, or database dumps in GitHub issues or pull requests.

Audit source application, identity mapping, allocation and refund decisions, exclusions, reconciliation acceptance, issuance/revision, exports, and distribution. Include actor, time, record references, and meaningful changes. Restrict the audit trail; avoid full source payloads or contact data in routine logs, error reports, or analytics.

Application audit records are not automatically tamper-proof against administrators. Stronger audit retention can be added if operational requirements justify it. Define retention separately for raw imports, generated artifacts, audit records, and backups, including what happens when storage expires.

Before production use, identify an owner for dependency updates, incident handling, restricted encrypted backups, and recovery. Test restoring data and private artifacts together. Define a method for revoking an account, invalidating its sessions, and rotating exposed credentials.

## Required verification

| Risk | Evidence required |
| --- | --- |
| Unauthorized donor access | Negative tests for anonymous users, users without CRM permissions, direct record IDs, exports, and PDF URLs |
| Bulk action or download bypass | Endpoint-level tests independent of menu visibility |
| Duplicate or concurrent imports | Same-file, overlapping-file, changed-record, and simultaneous-application tests |
| Invalid financial allocation | Tests through forms, importer/write services, and database constraints |
| Source or donor text becoming executable | Escaping, parser bounds, export formula handling, and restricted PDF asset tests |
| Private files becoming public | Hosted checks of direct file access and storage ACLs, not just Django routes |
| Letter alteration or unintended dispatch | Frozen snapshots, explicit revisions, and explicit distribution state transitions |
| Deployment configuration drift | Production settings reviewed with Django's deployment checks; secrets and origin access checked |

This documentation records intended controls. A production release must record which controls are implemented and verified, and resolve any remaining gaps before handling real donor records.

## References

- [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).
- [OWASP CSV injection guidance](https://owasp.org/www-community/attacks/CSV_Injection).
- [OWASP server-side request forgery prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
- [Django deployment checklist](https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/).
- [Django session security](https://docs.djangoproject.com/en/6.1/topics/http/sessions/#session-security).
- [Wagtail permissions](https://docs.wagtail.org/en/stable/topics/permissions.html).
- [Wagtail document security](https://docs.wagtail.org/en/stable/advanced_topics/documents/storing_and_serving.html#security-considerations).
