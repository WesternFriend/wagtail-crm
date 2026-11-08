# Simplicity gate

Apply the simplicity rules in the root [AGENTS.md](../../../../../AGENTS.md) to every planning review. Check each proposal:

- Which existing data or production caller needs this? Test fixtures alone are not evidence of need.
- What can be removed? Reject speculative codecs, shared infrastructure and edge-case machinery until a real scenario requires them.
- Is each acceptance criterion a staff task with a visible result? Storage formats and normalization stay out.
- Does it duplicate, conflict with or contradict a Django or Wagtail built-in? Use the built-in. Custom code needs a named requirement the built-in fails, stated in the PR.
- Does it mix concerns, such as a dependency upgrade with feature work? Split it where practical.
