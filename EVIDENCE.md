# Evidence register

Fleetcraft separates reproducible evidence from author-reported operational lessons.
Neither should be upgraded into a performance claim without a published evaluation.

| Claim or rule | Evidence class | Public artifact / limitation |
|---|---|---|
| Reproduce before fixing a bug | Protocol rule | Validation must include a captured reproduction and root-cause artifact for the affected change. |
| Regression tests fail on pre-fix code | Protocol rule | Validation must include failing output from an isolated parent worktree. |
| Separate specification and build-quality verdicts | Protocol rule | `plugins/fleetcraft/skills/fleet-orchestrator/references/review-rubrics.md`. |
| Render before visual acceptance | Protocol rule | Current task screenshot/render and, where relevant, approved baseline. |
| Hook/install behavior | Reproducible repository claim | Must be covered by clean-install, doctor, and hook-fixture CI before a release calls it supported. |
| Parent-baseline regression probe | Saved regression artifact | [PARENT_REGRESSION_EVIDENCE.md](PARENT_REGRESSION_EVIDENCE.md) records one isolated parent-archive behavior with exact parent SHA/checksum. It is bounded baseline evidence, not a claim that the parent shipped the current package. |
| Runtime hardening regressions | Independently rerunnable artifact | [`scripts/reproduce-strict-parser-regressions.py`](scripts/reproduce-strict-parser-regressions.py) deterministically derives a candidate-to-pre-fix patch, proves `git apply --check`, reconstructs immutable pre-fix hook snapshots byte-for-byte, and runs the byte-identical focused test module before and after. [`artifacts/strict-parser-regressions.txt`](artifacts/strict-parser-regressions.txt) records normalized environment, input hashes, separate stdout/stderr/exit status, and the exact expected baseline failure names; [`artifacts/strict-parser-pre-fix.reverse.patch`](artifacts/strict-parser-pre-fix.reverse.patch) is the reproducible patch. |
| Historical incidents, current-site captures, and design examples without a linked stored artifact | Author-reported anecdote | Sanitized operational context; not independently reproducible, current-state evidence, or a benchmark. |
| Model quality, token use, or speed | Not established | Fleetcraft makes no comparative or quantitative claim until a reproducible evaluation publishes task set, model/version, prompt, token accounting, raw artifacts, and failure modes. |

## Evidence requirements for future additions

1. Name the exact claim.
2. Link the artifact that could falsify it: test output, trace, screenshot, query, or
   primary source.
3. Record environment/version and date for behavior that can change.
4. Label author report, inference, and verified observation separately.
5. Keep failed checks and counterexamples; do not publish only success cases.

`incident-miner` may draft evidence-backed lessons after its approval gate. A strict
read-only verifier does not write project memory or convert its transient findings into
durable fact.
