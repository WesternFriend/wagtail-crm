# Technical source review

Reviewed 2026-11-08: `ARCHITECTURE-SPINE.md` and `FIRST-CONTACT-PR.md`, against primary references and current repository files. Scope is the proposed bounded contact profile, not an implemented converter or full standards conformance.

## Verdict

**Pass with implementation clarifications.** No source contradiction requires changing the architecture. The proposed limits are clearly identified as application choices. Two details belong in the implementation spec and fixtures before code is accepted.

## Standards checks

- **Pass — envelope/identity:** `@type: "Card"`, string `version: "1.0"`, mandatory `uid`; UUIDv4 URNs follow recommendations. `individual`/`org` are valid. Independent application IDs are compatible. [RFC 9553 §§2.1.1–2.1.9](https://www.rfc-editor.org/rfc/rfc9553.html#section-2.1)
- **Pass — names:** `name.full`, `name.components[]`, `name.isOrdered`, `name.defaultSeparator` are correct. Components require `kind`/`value`; repeated kinds are not prohibited. `surname2` specifically conveys secondary-surname semantics; repeated `surname` is legal. Full-only names are valid. Explicit ordering, generated full values, and conflict rejection are profile restrictions. [§2.2.1](https://www.rfc-editor.org/rfc/rfc9553.html#section-2.2.1)
- **Clarification — separators:** require `isOrdered: true`; a separator overrides the default, may be empty, and cannot appear consecutively. Components need a nonseparator. Unordered names forbid separators/defaultSeparator. Define these fixtures explicitly; the spine does not contradict them. [§2.2.1](https://www.rfc-editor.org/rfc/rfc9553.html#section-2.2.1)
- **Pass — details:** `emails`/`addresses` are ID-keyed maps; `correspondence` is an application key, not standardized delivery intent. One entry is a restriction. Email `address` requires RFC5322 addr-spec. Address `full` alone is valid; no parsed components required. [§2.3.1](https://www.rfc-editor.org/rfc/rfc9553.html#section-2.3.1), [§2.5.1](https://www.rfc-editor.org/rfc/rfc9553.html#section-2.5.1)

Rejecting unsupported properties is appropriate for this expressly restricted internal decoder. It must not be presented later as general JSContact validation. No complete converter is claimed here.

**Pass — CLDR pin:** the linked immutable revision identifies CLDR 49, UTS #35 revision 79, dated 2026-10-21. It discusses names with multiple words, multiple surnames and locale-driven formatting. Deferring locale selection and patterns while retaining explicit component order is consistent with the document's stated application limitation. There is no claim to implement CLDR formatting. [Pinned Unicode reference](https://www.unicode.org/reports/tr35/tr35-79/tr35-personNames.html)

**Pass — future vCard references:** RFC 9555 supplies conversion rules; RFC 9554 supplies vCard extensions and updates RFC 6350. The spine correctly treats these as future work with losses to be documented, rather than completed mappings. [RFC 9555](https://www.rfc-editor.org/rfc/rfc9555.html), [RFC 9554](https://www.rfc-editor.org/rfc/rfc9554.html)

## Repository and framework checks

- **Pass — locked versions:** `uv.lock` lines 252–253 and 1015–1016 contain Django 5.2.19 and Wagtail 7.4.4 respectively. `pyproject.toml` admits Django `>=5.2,<5.3`, Wagtail `>=7.4,<7.5`; these are compatible with the proposed documentation versions.
- **Pass — actual starting model:** `src/wagtail_crm/models.py` has `display_name`, two-value `kind`, and optional `email`; `0001_initial.py` uses a `BigAutoField` PK. Retaining model identity/PKs while adding a separate UID is a feasible extension. The planned kind translation matches current `person`/`organization` values.
- **Minor wording correction:** there is currently no `src/wagtail_crm/forms.py`. The plan should create it and extend the currently generated form, rather than imply an existing custom form. `views.py` already uses `ModelViewSet`, the stated namespace/prefix, name/email search and enabled inspect view.
- **Pass — custom editing and inspect:** Wagtail supports a plain Django form, `get_form_class()` customization, and a configurable inspect view class/template. Thus a component widget and private history within inspect fit the existing framework. There is no need for a generic property framework or new UI library. [Generic views](https://docs.wagtail.org/en/v7.4/extending/generic_views.html), [Viewsets](https://docs.wagtail.org/en/v7.4/reference/viewsets.html)
- **Pass — migration shape:** staged nullable addition, per-row backfill and later unique/non-null enforcement follow Django's guidance for adding unique UUID fields. Historical migration models are the correct mechanism. [Unique-field migrations](https://docs.djangoproject.com/en/5.2/howto/writing-migrations/#migrations-that-add-unique-fields), [Historical models](https://docs.djangoproject.com/en/5.2/topics/migrations/#historical-models)
- **Implementation obligation — validation:** bounded `JSONField` objects fit Django, but JSON serializability does not validate the contact schema. Explicit shared validation is needed as proposed; `save()` does not automatically call `full_clean()`. Verify the non-form write operation too. [JSONField](https://docs.djangoproject.com/en/5.2/ref/models/fields/#jsonfield), [Model validation](https://docs.djangoproject.com/en/5.2/ref/models/instances/#validating-objects)

## Clarification to carry into the implementation spec

**Legacy email preservation versus strict profile encoding:** the existing `EmailField` and database schema do not prove every stored string passed form validation. Direct ORM writes may bypass validation. The architecture promises exact preservation, so migration must not normalize or reject old values merely because the new exchange validator disallows them. Specify the behavior when encoding a preserved invalid value, such as an explicit encoding error without mutating the contact. This is a possible legacy-data edge case, not evidence of an invalid value in this repository. Add one targeted fixture; no production-data inspection is required.

No code, schemas, or planning deliverables were modified during this review. No conformance test or runtime implementation was evaluated.
