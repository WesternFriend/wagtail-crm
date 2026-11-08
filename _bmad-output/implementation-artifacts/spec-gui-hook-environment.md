---
title: 'Load mise tools for GUI-triggered Git hooks'
type: 'bugfix'
created: '2026-11-08'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

VS Code push fails because prek's Git shim launches successfully via an absolute executable path, but local hook entries cannot find `prek`, `uv`, or other mise tools on the GUI process PATH. Make the shared hook-installation task load the project's mise environment for both commit and push hooks, preserving prek's staged/ref selection, exit status, arguments and stdin. Keep machine-specific paths local to the Git hooks directory, and do not push remotely or change global shell/editor settings.

Given installed project tools and hooks, when the pre-push shim runs with only system directories on PATH and representative ref input, then all selected checks must run successfully, including Python tests. Reinstallation must remain safe and repeatable.

</frozen-after-approval>

## Implementation Notes

- Clean working tree and existing feature branch at start; starting revision `d070ba32793926e13e08ef7f7668cb1deb959751`.
- Inspected both installed prek 0.4.8 shims: fixed PREK path, fallback to PATH, then direct `hook-impl`. Their child system hooks receive no mise environment. Standard mise hook generation still uses bare `mise` on this installed version and would not solve missing GUI PATH.
- No intent gaps or irreversible operations. Small footprint: installer script, mise task, setup documentation and this record. Invoke ordinary `prek install` first, then adapt only the generated exec command to enter the discovered absolute mise executable; validate both templates before editing either.
- Added rollback of previous hook bytes and executable permissions if native installation, adaptation or writing fails. Reject hook path components with leading/trailing whitespace before installation because prek 0.4.8 trims those paths internally.
- Added five regression cases covering repeated installation, executable permissions, shell quoting, argument/stdin forwarding, child failure exit status, restoring existing hooks/removing newly generated hooks on template failure, and whitespace-path rejection.
- Verification: actual pre-push shim with `PATH=/usr/bin:/bin` and representative new-branch ref input passed every selected hook, including pytest, without contacting a remote. An isolated real-prek repository also passed repeat installation and restricted-PATH commit execution with both mise and custom hook directory paths containing spaces. Temporary fixture setup initially needed adjustment to use the installed prek binary directly; no global trust configuration was changed.
- `mise run test`: 18 passed, 2 browser tests deselected; application coverage 94%. Installer Ruff lint/format and repository hooks passed. Hooks reinstalled locally through the finalized task.

## Review Triage Log

- Medium, patched: native `prek install` runs before generated-template validation and can replace working wrappers before an adaptation error. Save previous bytes/modes and restore on installation/adaptation failures; regression cases cover both existing and newly installed hooks.
- Low, patched: Git hook paths with surrounding whitespace can disagree with prek's trimmed path. Preserve Git's output except its final newline and reject unsupported components before mutation. Internal spaces remain supported and verified with real prek.
- Medium, patched: manual smoke tests alone did not retain regression protection for the bootstrap guarantees. Added automated isolated shell execution with a system-only PATH, spaced paths/arguments, stdin and nonzero status, plus repeat installation and rollback checks.
