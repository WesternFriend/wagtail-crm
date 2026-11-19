---
title: Rehearse a PayPal reporting period
type: feature
created: '2026-11-19'
status: done
route: oneshot
---

<frozen-after-approval>

## Intent

Give the Editor a reproducible Activity Download and independent figures to take from import through dispatch. Give staff a procedure for comparing one real PayPal export with the same fields in the restricted pilot.

</frozen-after-approval>

## Implementation Notes

Use a standalone, fixed-seed Faker script and the existing CRM Editors group. Keep the Editor's observations and the restricted pilot results open on #11 and #12.

The synthetic Editor run imported 101 rows, skipped the pending payment and matched all five PayPal figures. The due list showed $275 for Alex after the partial refund and mailed check. The issued letter left the due list and supported a failed dispatch, successful retry and correction.

## Review Triage Log

- Medium, fixed. AC-17 calls for the Editor to use the keyboard and browser zoom during the rehearsal.
- Medium, fixed. Roadmap step 4 includes failed and superseded letters. The rehearsal now includes a failed attempt, retry and correction.
- Medium, fixed. The pilot acceptance decisions assign independent confirmation of expected totals to the Bookkeeper. The guide now names that owner.
