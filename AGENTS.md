# Working in this repository

- Build only for data that exists or that code in the same PR produces. Hypothetical formats and future importers do not justify today's complexity.
- Add a converter, codec, or service layer only when application code in the same PR calls it. Tests alone do not establish a need.
- Use Django and Wagtail built-ins for the features they provide, including model viewsets, generic views, history, and permissions. Do not build features that duplicate, conflict with, or contradict them. Custom code must fill a named staff requirement the built-in does not meet; explain that gap in the PR without recreating the built-in feature.
- Present ordinary, populated, task-focused Wagtail fields. Standards guide the model; staff should not assemble schema components or manage formatting rules.
- Write acceptance criteria as staff tasks and observable results. Keep storage formats, normalization, and implementation choices out of them.
- Every planning or code review asks what can be removed as well as what is missing. New rules need a demonstrated scenario, not a hypothetical one.
- Prefer one small PR per concern. Separate framework upgrades from feature work when practical so each can receive focused review.
- In admin views, nothing in `setup()` or what it calls (such as `get_panel()`) may raise or read a record before `dispatch()` checks permission, and every view that serves CRM data names its `model` so a permission policy applies. Wagtail's generic object views look the record up in `setup()`, so CRM viewsets extend `CRMViewSet` for them; `tests/test_permission_sweep.py` checks every CRM admin URL.
- Use one distribution, with one Django app per domain and labels `wagtail_crm_<domain>`. Dependencies point toward the domain that owns the data; contacts must not depend on later finance, imports, or letters apps. Do not add a shared core or generic audit app without a concrete need.
- Preserve existing records until the user explicitly authorizes a reset or migration strategy. Use synthetic data for development and screenshots; keep donor data and secrets out of the repository.
- Follow [docs/development.md](docs/development.md) for setup, mise tasks, and verification. Before requesting review of workflow changes, run the app and personally check the affected staff tasks; passing tests alone is insufficient UX evidence.
