# Integration decisions

The integrated candidate starts from `8865f9b49836dadcf60978e7bbe0394022b191d3`
(v0.2 source update) and selectively carries forward the hardening in
`7804f44fc9fcb6a557935ce14125c846c8d1b23a` (PR #1). Both descended from
`bc29addc6d180f798a0297e6ae17085382eb379b`; treating one as the other's successor
would lose capabilities. The old conflicting PR is not a merge recipe.

| Decision | Reason | Acceptance evidence |
|---|---|---|
| Keep root source layout canonical | Preserve current workflows and manual-install users | Existing source tests plus installer checks |
| Generate sparse plugin deterministically | Avoid independently maintained duplicate code/instructions | Parity rejection and isolated install |
| Preserve all eleven useful skills and four roles | Retain debugging, performance and strategy while adding image/doctor | Inventory and dependency checks |
| Port strict-parser and release safeguards | Preserve reproducible edge-case protection | Before/after parser corpus and package contracts |
| Keep routing/honesty checks, repair their evidence rules | Agent dispatch alone is not retrieval; unavailable tools cannot be assumed | Positive and negative hook fixtures |
| Make consequential optional guards explicit | Avoid forcing an unavailable external service | Default/opt-in/retry tests and documented controls |
| Remove private and unverified operating claims | Past local observation is not adopter capability or broad evidence | Source review, notices and scoped scans |
| Separate evaluation levels | Structural tests do not prove live selection or quality uplift | Trace-bound evaluation results and open cases |

## Context record for delegated changes

A useful brief carries the task and acceptance criteria, immutable base revision,
owned files/interfaces, relevant tests, existing authorization, open conflicts and
artifact links. Label external material as untrusted data. Preserve the unresolved
failure and constraints when compressing context; summarize completed investigations.
Measure context size and unnecessary work rather than assuming a universal percentage
of a model's context window guarantees quality.

Review the candidate that will actually ship. A verdict against a different base or
an incomplete artifact set is OPEN. Neither a plan nor a previous review grants
permission for a different side effect.

## Rollback

Before merge, abandon the integration branch without changing main. After merge,
revert the integration commit; do not move existing tags. For a plugin installation,
disable/uninstall the candidate and return to the previously validated version.
The legacy installer must retain backups of replaced files; no automatic settings
migration or credential change is part of this integration.
