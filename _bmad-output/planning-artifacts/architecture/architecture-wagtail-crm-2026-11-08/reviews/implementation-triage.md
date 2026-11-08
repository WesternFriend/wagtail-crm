# Contact implementation review

Three independent reviews covered the implementation diff, edge cases and verification gaps. All actionable findings were addressed; none require a new planning increment.

| Finding | Resolution and evidence |
| --- | --- |
| Stale contact writes could overwrite newer edits (two reviewers). | Shared writes check revisions; forms carry a hidden token. Regression cases reject stale and missing tokens without changing stored data. |
| A contact deleted during editing could cause an unhandled error. | Shared writes raise a validation error; create/edit/delete views present normal errors. Tests cover deleted records and service failures. |
| Partial saves could overwrite a newer name; empty `update_fields` should do nothing. | Name projections update only when requested. Both cases have regression tests. |
| Database routing was not consistently respected. | Shared transactions, reads, writes and history use the selected alias; migration uses its schema-editor alias. Multi-database deployments were not exercised locally. |
| Failed history insertion left the Python instance unsuitable for retry (two reviewers). | Restore primary key, revision and model state on rollback; test a successful retry after simulated failure. |
| Kind-only changes were unclear in history. | Show previous/current kind and test the inspect response. |
| Structure-only changes with identical rendered names were unclear. | Explain that the name structure changed; preserve the snapshots and test this case. |
| History retrieval was unbounded. | Paginate at 20 entries; test navigation. |
| Form initialization lost explicit initial values or unsaved structured names. | Respect explicit initial values and render unsaved names; both tested. |
| Delete endpoint lacked assertions for its final history entry. | Assert the final snapshot, actor, deletion action and retained history. |
| Correspondence-only changes lacked exact snapshot assertions. | Test previous/current email and postal values independently of name edits. |

An additional input check rejects conflicting supplied full names instead of silently discarding them. No separator controls, name modes or structured postal editors were added.

Final local verification: `mise run check`, `mise run hooks`, 77 fast tests (95% coverage), and two Chromium tests passed. Wheel source/migration/template contents match the checkout; development host, scripts and tests are excluded. Browser screenshot inspected with synthetic data. The existing development database remains untouched. PostgreSQL concurrency and operational acknowledgment readiness are outside this increment.
