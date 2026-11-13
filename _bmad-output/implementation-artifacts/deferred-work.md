# Deferred work

- source_spec: `_bmad-output/implementation-artifacts/spec-browser-fixture-lifecycle.md`
  summary: Decide whether to pin mise tool versions or add a mise lockfile.
  evidence: Current user-selected latest tool selectors allow tooling drift independently of uv.lock and action SHA pins.

- source_spec: `_bmad-output/implementation-artifacts/spec-browser-fixture-lifecycle.md`
  summary: Add retained browser failure diagnostics if CI troubleshooting requires them.
  evidence: Existing screenshots cover successful contact creation; failed selector calls currently retain console call logs but no trace or failure image.

- source_spec: `_bmad-output/implementation-artifacts/spec-browser-fixture-lifecycle.md`
  summary: Consider automated updates for pinned GitHub Actions revisions.
  evidence: Verified action SHA pins include release comments but currently rely on manual update maintenance.
