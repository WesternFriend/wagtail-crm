# Consistency review

Verdict: small semantic amendments recommended before implementation. The profile and first PR are substantially aligned and appropriately bounded. Exact field layout can remain in the implementation spec. The remaining issues concern observable behavior that two otherwise compliant implementers could implement differently.

Reviewed ARCHITECTURE-SPINE.md and FIRST-CONTACT-PR.md, with the current Contact model/viewset as context. This review does not assess external standards correctness or expand the increment.

## 1. Medium — The name editor has no complete transition contract

Evidence: spine AD-1 (line 38) prohibits naming-mode controls; PR item 3 (line 11) requires text for unknown structure, component entries for known structure, and replacing editable full text when components are entered. The acceptance example (line 20) allows a component-losing edit if history preserves the old structure.

Implementer A exposes an Add component action alongside the text editor, switches authority on the first valid component, and permits deleting all components to return to an unstructured text editor. Implementer B exposes a component-building section, switches only after a complete valid set is submitted, and rejects the removal of all components. Both avoid a mode selector and duplicate authoritative names; both satisfy the stated component-loss/history alternative. They produce different capabilities for ordinary staff and different authority when a partial component edit is submitted.

Bounded amendment: define what action begins component entry, when it becomes authoritative, and whether/how staff return to unstructured text. Specify that an incomplete attempted transition cannot discard the current name. This can be one short paragraph and two acceptance examples; it does not require a widget design or a storage decision.

## 2. Medium — Explicit ordering/separators need a canonical supported contract

Evidence: spine mapping (line 50) permits components, isOrdered, defaultSeparator and separator components, requiring explicit order/separators. PR item 3 says row order expresses order and existing separators are retained; examples (line 20) establish empty and space separators but not how a new structured name obtains them.

Implementer A requires an explicitly supplied separator for every newly created structured name and rejects a component-only submission. Implementer B gives new rows a visible default space separator, treats their order as explicit, and encodes isOrdered=true/defaultSeparator=' '. Both can claim the UI collected explicit ordering, yet one permits staff to create the space-separated example directly and the other requires another entry. They can also disagree whether explicit separator components replace or supplement a default separator.

Bounded amendment: specify the allowed structured representation and separator precedence, including the form's initial separator and how empty separators are entered. Add one concrete encoded fixture for each existing structured example and one mixed-separator fixture or explicitly reject that combination. This settles shared semantics without fixing JSONField layout.

## 3. Medium — Snapshot retention does not settle creation/deletion events

Evidence: spine AD-3 (line 61) requires old/new values, actor/time and origin, and survival after deletion. PR lines 9, 14 and 22 preserve independent history but only explicitly require actor/time for edits.

Implementer A creates a baseline migration snapshot, an initial create snapshot, edit snapshots, and a deletion snapshot with actor/time and an absent new state. Implementer B records the migration baseline and subsequent edits, retains those on deletion, but records neither a staff creation event nor who deleted the contact. Both retain previous evidence and can satisfy the literal edit/deletion examples; their audit evidence differs materially.

Bounded amendment: enumerate which of migration/create/update/delete produce history, define absent old/new state for lifecycle events, and say whether deletion itself must be recorded atomically. State whether timestamps on migration records denote migration time. No general audit platform or post-delete history route is needed.

## 4. Low — The viewer acceptance example is ambiguous beside view permission

Evidence: PR line 14 permits contact-history access with contact-view permission; line 22 says 'a viewer or Wagtail user without contact permissions' cannot disclose protected information through edit/inspect requests.

Implementer A reads 'viewer' as a user with contact-view only and denies inspect, following the literal acceptance sentence. Implementer B permits inspect/history to that user and only denies edit, following the explicit permission rule. The likely intended behavior is B, but the example can drive contradictory permission tests.

Bounded amendment: replace this example with an explicit small permission matrix: no contact permissions denies inspect/history/edit; view-only permits inspect/history and denies mutation; add/change/delete retain their existing action enforcement. Do not introduce new roles or permissions.

## Areas already consistent

- Structured components are authoritative; full rendering is derived, conflicting supplied full values fail, and unstructured names are not parsed. There is no second editable correspondence name.
- Email and postal address are optional; missing details cannot block creation or imply readiness or attribution. One minor implementation-spec decision remains: define whether whitespace-only optional values count as absent, and consistently omit absent maps on encode while preserving exact migrated values as required.
- Legacy migration preserves PK/name/email/kind and uses distinct independent UUIDs, while the acceptance examples require stable UIDs. A future decoder-to-record update or identity-matching policy is unnecessary here because decoding is pure and no endpoint/importer is introduced. Ensure the implementation spec makes UID read-only on ordinary staff edits.
- History has independent UID retention and a nullable link; ordinary deletion must not cascade history. Whether orphaned history is later exposed is outside this PR and need not add a route now.
- No payment, import UI, email delivery, deployment, or configuration expansion is needed to resolve these findings.
