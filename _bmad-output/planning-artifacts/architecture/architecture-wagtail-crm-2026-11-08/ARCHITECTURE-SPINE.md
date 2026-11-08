# Contact-management architecture

Approved simplification: 2026-11-08. This supersedes the earlier JSON name profile and custom history/revision design, retained only in Git history and historical review notes.

## AD-1 — One distribution, one Django app per domain

One project and distribution package, `wagtail_crm`, contains domain apps labelled `wagtail_crm_<domain>`. Contacts lives in `wagtail_crm.contacts`, label `wagtail_crm_contacts`. Future finance/imports/letters may depend on contacts; contacts imports no sibling domain. Keep Contact-specific behavior here. No shared core, generic audit app or import-linter configuration is needed before another domain exists.

## AD-2 — Ordinary contact columns and forms

Contact has kind, given_name, family_name, name, optional email/postal_address, UUID uid and derived stored display_name. The display uses name when present, otherwise the given/family values. People use Given name/Family name; an existing unsplit name uses Name. Organizations use Name. Never infer a split. Wagtail forms handle validation and retain entered work. A small script only shows/disables applicable fields. No name modes, codecs, components, formatting controls or correspondence routing.

## AD-3 — Use Wagtail history and permissions

Use ModelViewSet and stock create/edit/delete/history actions and ModelLogEntry. Site history retains activity for deleted contacts. Do not add RevisionMixin, a parallel audit model, change-summary UI or custom snapshots. Standard Wagtail permission behavior applies. Concurrent-edit protection is deferred; last-save-wins is accepted for this alpha slice.

## Initial schema and boundaries

There are no existing installations. One fresh `wagtail_crm.contacts` initial migration creates the final Contact schema. Development databases from the old app layout must be recreated/reseeded; no migration baseline or old-label preservation path is claimed. Existing local files are not deleted by tooling without an explicit reset action.

Wagtail is the only UI; retain URL namespace wagtail_crm_contacts and crm/contacts prefix. Postal address remains multiline text. An Inspect extension is justified only for displaying its line breaks; all remaining views use the framework defaults.

## Future interoperability

Design JSContact/vCard/Schema.org mappings and CLDR formatting only when an actual import/export workflow requires them. They are references, not a current codec or storage contract. Financial rules, source mappings, letters, delivery and production deployment remain later increments.

## Frameworks

Django 6.1.3 and Wagtail 8.1, locked in uv.lock. See docs/development.md for verification. Framework-first simplicity and the staff-task acceptance criteria govern future additions.
