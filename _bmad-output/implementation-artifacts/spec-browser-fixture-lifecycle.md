---
title: 'Keep synchronous Django setup outside the Playwright event loop'
type: 'bugfix'
created: '2026-11-08'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

The new GitHub Actions browser job must run the existing Chromium checks successfully. Their class-wide Playwright startup currently leaves an event loop active during synchronous Django ORM setup and teardown, causing both checks to fail before testing the interface.

Scope Playwright to browser interaction inside each test, after database setup and before database assertions/teardown. Preserve permission checks, synthetic accounts, screenshot support, real static live-server behavior and Django's async-safety guard. Given the installed Chromium browser, running `mise run browser` must pass both tests without disabling async safety.

</frozen-after-approval>

## Implementation Notes

- Investigation: `tests/browser/test_contacts.py` starts the sync Playwright API in `setUpClass`; Django ORM work in `setUp` and database flush in teardown fail with `SynchronousOnlyOperation` while that loop remains active. Playwright BrowserContext supports context-manager cleanup.
- No intent gaps, irreversible operations, production changes or new dependencies. Footprint: browser test lifecycle and this record; CI/configuration work already authorized in the surrounding task remains preserved.
- Working-tree changes were explicitly authorized by the ongoing user requests; preserve unrelated product-discovery edits. Starting revision: `0e6b948dfd30a5058a210bd6b6db38febe1190dd`.
- Replaced class-wide Playwright lifetime with a per-interaction context manager; ORM setup/assertions and Django teardown now run outside its event loop. Navigation failures subsequently produced only test failures, with no async-safety teardown errors, confirming exception cleanup.
- Actual rendered Wagtail login labels include a required-field asterisk. Updated label locators to allow that marker while retaining strict Playwright uniqueness checks. This resolves an additional selector failure exposed after startup was repaired.
- Verified Wagtail's installed generic CreateView uses the button label `Create`; corrected the creation selector from `Save`. No application behavior changed.
- Final verification: `mise run browser` passed both tests (13 nonbrowser cases deselected); `mise run test` passed 13 tests (2 browser cases deselected), coverage 94%; `mise run check`, `actionlint .github/workflows/checks.yml`, and repository hooks passed. Hosted Ubuntu execution remains pending a push/PR update. No async-safety bypass was added.

## Review Triage Log

- Low, deferred: mise tool selectors remain `latest`, matching the existing user-selected setup. `uv.lock` and action SHAs are pinned, but tool updates can change behavior; exact tool pins or mise.lock are a separate maintenance improvement.
- Low, rejected: retaining coverage XML as an artifact is optional; coverage remains visible in the job log and the documentation explicitly says XML is runner-local. Adding artifact infrastructure is unnecessary for the requested checks.
- Low, deferred: browser traces/failure screenshots would improve diagnosis; existing screenshot support captures successful creation only. Current failure call logs were sufficient to identify the lifecycle and selector defects.
- False: failure-path cleanup is verified by the intermediate browser run, which timed out in both login interactions without any Django teardown errors. Both nested context managers unwind on exceptions; async safety remains enabled.
- Low, deferred: declared Python 3.12/3.13 support is not yet covered by the CI job, which deliberately uses mise's current local Python 3.14. A supported-version matrix is a future compatibility enhancement.
- Low, deferred: action update automation is absent. SHA comments identify releases for manual maintenance; adding Dependabot is separate from executing the same local checks.
- False for the current repository: filename batching cannot currently split the hook input; the entire NUL-delimited file list is 25,108 bytes, below the macOS xargs command buffer. No case-conflicting pair was demonstrated. Revisit argument selection if the repository grows substantially.
- Low, patched: added `mise trust` to the initial README and development setup commands so a new checkout can enable project configuration before installing tools.
- False: the in-progress spec status was accurate while implementation and browser verification were ongoing; final status and results are recorded after completion rather than claimed early.
- False: no current caller uses the instance's page after its context closes. The two test bodies and login helper use it only within `browser_page()`; a yielded-page API is an optional style change rather than a demonstrated bug.
