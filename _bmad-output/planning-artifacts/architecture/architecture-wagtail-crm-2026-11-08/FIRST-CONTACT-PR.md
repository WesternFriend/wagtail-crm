---
status: done
route: oneshot
baseline_commit: f8ddc2d67351d33f67cfd052992ccd51b9218b0d
context: []
---

<frozen-after-approval>

## Intent

Finish the approved contact slice by removing the unsplit-person path: people always use Given name/Family name, organizations use Name, and changing organization to person requires staff-entered parts without automatic splitting. Keep ordinary Wagtail forms, permissions and history. Pin BigAutoField in the reusable app. Delete obsolete design/review records and update AC-18 and current guidance. Preserve the existing built-in duplication rule and standing simplicity checklist. No imports, finance, schema changes or operational-data reset.

</frozen-after-approval>

## Implementation Notes

- All four supplied findings were checked against the clean branch. The built-in duplication rule and status-free rubric were already corrected in f8ddc2d67351d33f67cfd052992ccd51b9218b0d; retain those edits.
- Reuse this short build record rather than add a planning layer. Verification details belong in PR #2. Run check/hooks/test/browser and personally inspect the changed type-switch workflow against a separate synthetic database.
- Completed the form/type-switch regressions, pinned app-local BigAutoField and removed the superseded review artifacts and contact-design memlog entries. No migration was generated. Independent review found no actionable issue; exact verification and personal running-UI evidence are recorded in PR #2.
