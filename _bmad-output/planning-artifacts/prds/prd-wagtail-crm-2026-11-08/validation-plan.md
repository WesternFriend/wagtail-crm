# Discovery and pilot validation plan

Status: proposed, 2026-11-08. No stakeholder sessions, samples, operational approvals, or pilot results have been verified in this interview.

## Evidence collection

All owners below are proposed roles, not accepted assignments. Brylie proposes coordinating requests; replace role placeholders with confirmed names before operational readiness. Keep real donor evidence out of public repository content; retain only synthetic or properly redacted discovery material in approved locations.

| Evidence or decision | Proposed owner | Next action | Blocks |
| --- | --- | --- | --- |
| Workflow and authority | Editor, bookkeeper, Brylie | Confirm participation, business owner, approvals and exception authority; walk through existing process | Operational approval |
| Reporting basis and scope | Editor and bookkeeper | Confirm covered dates, date basis/timezone, accounts, offline sources, deadline and volumes | Coverage and valid issuance |
| Representative PayPal format | Editor/bookkeeper | Supply redacted export retaining matching relationships and edge cases; inspect available fields | Adapter scope and expected results |
| Contacts and subscriptions | Editor, supported by Brylie | Inspect available exports, references, historical completeness and correspondence preferences | Matching, policy evidence and import scope |
| Offline gift source | Bookkeeper | Identify authoritative records, confirmed-gift criteria and stable references; choose capture method if covered | Agreed offline coverage |
| Allocation and refund policy | Bookkeeper with Editor | Confirm historical effective dates, approvals, mixed gifts, partial/cross-year refunds and corrections | Financial review and affected issuance |
| Historical letter and delivery | Editor with finance review | Confirm wording, benefits, signatory, branding, translation needs, delivery tools/preferences | Approved donor communication |
| Closure and exclusions | Confirmed business owner, Editor and bookkeeper | Define acceptable follow-up, exclusion treatment and authority for documented delivery exceptions | Cycle closure |
| Desktop working conditions | Editor and Brylie | Confirm Mac/browser/display/accessibility, printing and interruption/resumption needs | Supported UX test setup |
| Support and operations | Business owner and technical maintainer, names TBD | Name account/update/support/backup/recovery owners; agree availability; demonstrate restore | Real-data operational use |
| Retention and deletion | Business owner and technical maintainer, names TBD | Agree evidence, letter, audit and backup retention/deletion arrangements | Real-data operational readiness |
| Portable record | Brylie, reviewed by Editor/bookkeeper | Document export schema/manifest and verify reconstructed donor history independently of app | Exit and continuity readiness |

## Asynchronous pilot method

Keep two distinct evidence tracks: synthetic-data UX testing for task completion and understanding, and financial validation against stakeholder-approved source evidence and independently established expected results. Operational readiness requires both. Use restricted handling for real financial evidence; do not place it in the synthetic UX environment or public repository.

1. Stakeholders establish expected outcomes independently of the implementation. Build representative synthetic examples preserving relevant relationships.
2. Brylie iterates locally, then supplies a restricted hosted synthetic environment and brief onboarding. Confirm tested desktop/browser setup.
3. Provide short goal-oriented scenarios without coaching the click sequence. Editor reports confusing steps, questions and unexpected results using brief notes and optional synthetic screenshots. Record actual assistance provided.
4. Compare resulting records and documents against expected outcomes. Ask the Editor to explain amounts, unresolved work, document states and next actions in her own words.
5. Repeat representative work with minimal prompting. Record context loss, help needed, repeated entry and misunderstood statuses; revise and retest affected tasks.

Monthly calls and live observation may supplement this evidence but are not prerequisites. Set quantitative time/assistance targets only after baseline evidence. No pilot has yet been run.

## Representative scenarios

The following are proposed test scenarios derived from the interview, not approved financial policy.

Use `acceptance-criteria.md` as the detailed specification: it defines evidence fields, gate/change dependencies, explicit reconciliation checks, numeric fixture premises, import/issuance retry cases, prohibited outcomes and proposed reviewers. This table remains a scenario overview. Record separate UX and financial verdicts; none of these scenarios has yet been run.

| Scenario | Evidence of acceptable behavior |
| --- | --- |
| Straightforward gift | Confirmed donor, approved allocation rule, separate fees, traceable contribution and letter |
| Patron subscription | Applicable approved historical policy visible; missing policy blocks affected issuance |
| Ambiguous payer or gift recipient | Suggestions do not silently confirm attribution; reviewer resolves or escalates |
| Repeat/overlapping import | No duplicate financial effects; previous staff decisions retained |
| Rejected rows and interrupted import | Explained dispositions and visible outcome; safe retry without duplicate effects or lost review decisions |
| Mixed-payment refund or changed source facts | Conflict visible; appropriate review reopened; old evidence preserved |
| Missing offline coverage | Review/drafts continue; incomplete coverage cannot masquerade as issuance readiness |
| Unsupported currency or language need | Original evidence retained; exception and required decision visible; no invented conversion |
| Batch approval and issuance | Preview and explicit scope/version approval correspond to immutable issued artifacts |
| Explicit reconciliation and changed dataset | Independent comparison accounts for records and monetary categories; unexplained differences block acceptance; material change reopens dependent review |
| Repeated/interrupted issuance | No silent duplicate issuance/dispatch; staff can identify outcome and safely recover |
| Correction after issuance | Linked newly approved revision; prior letter and dispatch history unchanged |
| Download, dispatch and retry | Download leaves pending; actual dispatch attestation and separate attempts recorded |
| Missing address/unreachable donor | Follow-up remains visible; any accepted closure preserves undelivered status and other gates |
| Interruption and return | Entered work retained, review state and next action understandable |

## Release evidence ledger

Before real operational use, record an accountable person, evidence reference, outcome and unresolved issues for each gate:

- Agreed scope and complete coverage; explained record dispositions and zero unexplained reconciliation differences.
- Independently checked amounts, attribution, historical policy, refund treatment and letter wording.
- Observed through asynchronous task evidence: routine staff independence, comprehension, appropriate escalation and understandable states.
- Endpoint access controls and private evidence/artifact/export storage, including denial to users without CRM permissions.
- Basic keyboard, zoom, labels/errors and non-color status accessibility checks on the supported desktop setup.
- Repeat-import safety, preserved approvals/decisions, immutable issued documents and correct revision/distribution behavior.
- Complete documented portable export whose donor history can be reconstructed without running the app.
- Successful database/artifact recovery and confirmed account, update, support and backup ownership.

Pilot subset completion and full annual completion are different outcomes. A cycle may be fully distributed or closed with explicitly accepted distribution exceptions under confirmed policy. No distribution exception waives coverage, identity or financial approval.

## Development handoff — running contact walkthrough

Before requesting review, personally exercise the running Wagtail app with synthetic data; automated checks supplement this evidence. Check creating, finding, editing and Inspect for people/organizations, known repeated/multiword names, unknown full names, single names, optional correspondence, and validation recovery. Confirm populated values, ordinary field labels, no formatting/schema controls, retained history and permission denial. Keep production/development donor records out of this walkthrough.

On 2026-11-08 the developer performed this walkthrough in native Brave on the Mac desktop, using a separate temporary SQLite database. Confirmed direct Jordan Sample full-name editing, email and blank-name recovery without re-entry of other work; creation/reopening and surname correction of a split multiword person; surname-only 王 with no optional details; organization creation/editing/search/Inspect; exact retention of a multiline organization name during email edits; recorded repeated given/surname components populated in their appropriate fields and corrected without losing unrelated family components. A normal CRM editor could edit and navigate History; a staff account without CRM permission had no Contacts navigation and direct access was denied. Keyboard movement between name fields worked. Stored outcomes were independently read back, including original snapshots and stable IDs.

The walkthrough removed a duplicate Inspect History link, empty optional-field rows in creation summaries, and organization help that only repeated its field label. These are developer/synthetic observations, not Editor acceptance or financial validation. New features remain paused until usable contact management is finished within its agreed scope. Future address work follows ordinary populated task-appropriate fields without expanding today's multiline-address increment.

The final running-UI pass also confirmed that typing a person name and switching Contact type to Organization carries the draft into Organization name; editing a multiline name survives invalid-email recovery and saves correctly. Final stored outcomes were read back after these actions. The disposable account was signed out, its browser tab closed, and the temporary server stopped. Final automated results: `mise run check` and `mise run hooks` passed; `mise run test` passed 168 tests (10 browser tests deselected), with 95% coverage; `mise run browser` passed all 10 Chromium tests. Wheel verification matched all 15 packaged source/template/static files and included migrations while excluding devsite/tests/scripts. No new migration or existing development database changes were required.
