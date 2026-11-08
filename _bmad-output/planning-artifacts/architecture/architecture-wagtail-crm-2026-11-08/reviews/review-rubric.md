# Planning simplicity review gate

Approved direction: 2026-11-08. This replaces the former profile review; that proposal and its findings remain in Git history.

Before accepting a slice, check:

| Question | Required evidence |
| --- | --- |
| What can we remove? | Remove machinery that does not serve a current staff task. |
| Which real data or caller needs each capability? | Existing records or application code in the same PR; tests alone are insufficient. |
| Has a framework built-in been tried? | Prefer Django/Wagtail model fields, forms, viewsets, actions, permissions and logs. Custom code names the requirement the built-in fails. |
| Do criteria describe staff outcomes? | Observable tasks and results, without storage formats, separators or byte-preservation rules. |
| Is a new rule supported by a real scenario? | No hypothetical formats, importers, generic infrastructure or speculative edge cases. |
| Is this one reviewable concern? | Separate framework upgrades from features where practical. |
| Is the UI ordinary and usable? | Populated task-focused fields and a personal running-app walkthrough. |

Follow root AGENTS.md for shared guardrails and docs/development.md for verification. Contacts uses the six approved AC-18 tasks, Family name, stock Wagtail history, a fresh alpha schema, no migration baseline and deferred concurrent-edit protection. Source imports, export mappings and finance are later work.
