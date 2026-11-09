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
| Desktop working conditions | Editor and Brylie | Confirm Mac/browser/display/accessibility, printing and interruption/resumption needs | Supported UX test setup |
| Support and operations | Business owner and technical maintainer, names TBD | Name account/update/support/backup/recovery owners; agree availability; demonstrate restore | Real-data operational use |
| Retention and deletion | Business owner and technical maintainer, names TBD | Agree evidence, letter, audit and backup retention/deletion arrangements | Real-data operational readiness |

## Asynchronous pilot method

Keep two distinct evidence tracks: synthetic-data UX testing for task completion and understanding, and financial validation against stakeholder-approved source evidence and independently established expected results. Operational readiness requires both. Use restricted handling for real financial evidence; do not place it in the synthetic UX environment or public repository.

1. Stakeholders establish expected outcomes independently of the implementation. Build representative synthetic examples preserving relevant relationships.
2. Brylie iterates locally, then supplies a restricted hosted synthetic environment and brief onboarding. Confirm tested desktop/browser setup.
3. Provide short goal-oriented scenarios without coaching the click sequence. Editor reports confusing steps, questions and unexpected results using brief notes and optional synthetic screenshots. Record actual assistance provided.
4. Compare resulting records and documents against expected outcomes. Ask the Editor to explain amounts, unresolved work, document states and next actions in her own words.
5. Repeat representative work with minimal prompting. Record context loss, help needed, repeated entry and misunderstood statuses; revise and retest affected tasks.

Monthly calls and live observation may supplement this evidence but are not prerequisites. Set quantitative time/assistance targets only after baseline evidence. No pilot has yet been run.

## Representative scenarios

The detailed staff tasks and results are in [acceptance-criteria.md](acceptance-criteria.md), which also lists what is deferred from 0.1.0. Record separate UX and financial verdicts for each; none has yet been run.

| Scenario | Criteria |
| --- | --- |
| Straightforward gift with a fee | AC-01 |
| Patron payment, part gift and part goods or services | AC-02 |
| Invalid or missing charitable amount | AC-03 |
| Payer name or email differs from a contact | AC-05 |
| Repeat and overlapping import | AC-06 |
| Skipped rows, including an unsupported currency | AC-07 |
| Refund, matched and unmatched | AC-08 |
| Reconciliation against PayPal totals | AC-10 |
| Issued letter unchanged by later edits; correction | AC-12, AC-13 |
| Download, failed dispatch and retry | AC-14 |
| Restricted accounts | AC-15 |
| Restore from backup | AC-16 |
| Full cycle with the Editor | AC-17 |

## Release evidence ledger

Before real operational use, record an accountable person, evidence reference, outcome and unresolved issues for each item:

- Skipped rows explained in the preview, and reconciled totals matching PayPal for the pilot period (#12).
- Expected totals, charitable amounts, refund treatment and letter wording confirmed by the bookkeeper.
- Asynchronous task evidence that the Editor completes the cycle, understands amounts and letter states, and escalates finance questions appropriately.
- Access denied to users without permissions, including direct URLs and PDFs.
- Basic keyboard, zoom, labels/errors and non-color status accessibility checks on the supported desktop setup.
- Repeat-import safety, unchanged issued letters, linked corrections and recorded dispatch attempts.
- A tested restore, and confirmed account, update, support and backup ownership.

Pilot subset completion and full annual completion are different outcomes. Closing a cycle with delivery exceptions is deferred (FR-14).

## Development handoff — minimal contacts

Validate the six AC-18 tasks using ordinary fields and Wagtail's actions/history on a separate synthetic database. Include organization-to-person changes requiring staff-entered given/family names, single/multiword/non-Latin names, optional details, validation recovery, search/Inspect, retained deletion activity and permission denial. No automatic splitting or unsplit-person editor is supported.

Record developer verification in PR #2 rather than duplicating its changing check counts here. Synthetic developer testing does not establish Editor acceptance or operational financial validation.
