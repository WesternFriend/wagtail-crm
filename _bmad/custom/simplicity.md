# Simplicity rules

wagtail-crm is built in small increments toward its first use case: one completed, reconciled acknowledgment cycle (see `docs/roadmap.md`). Every BMad workflow and review applies these rules. They override any template, checklist, or persona that asks for more coverage.

- **Build for real need.** Every capability, requirement, or rule names the existing data, staff task, or production caller that needs it now. Test fixtures, hypothetical imports, and "future" formats are not evidence of need.
- **Use the frameworks.** Use Django and Wagtail built-ins. Do not design features that duplicate, conflict with, or contradict them (for example history, permissions, admin views, forms). Custom code needs a named requirement that the built-in fails, stated in the artifact.
- **Acceptance criteria are staff tasks.** Each one says what a staff member does and what they see. Storage formats, normalization, and byte-level preservation stay out.
- **Remove before adding.** Every review asks "what can be cut?" before "what is missing?". A new rule needs a real scenario, not a hypothetical edge case. Zero findings is a valid review result.
- **Keep artifacts small.** Prefer one short spec per increment. A PRD, architecture spine, or addendum is only for decisions that span increments. Do not repeat content across documents; link instead.
- **One concern at a time.** Split dependency upgrades, refactors, and features into separate changes where practical.
- **Defer explicitly.** When something is out of scope, name it in one line as deferred. Do not design it now.
