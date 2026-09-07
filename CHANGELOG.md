# Changelog

This project follows Keep a Changelog style. A version is released only after the
documented tag-verification workflow has run successfully for that immutable tag.

## Unreleased — 0.1.1 hardening

### September 7 integration

- Added portable change-planning, image-to-code, and project-handoff skills.
- Refined delegation thresholds, task ownership, compressed briefs, and independent
  specification/build-quality verdicts without pinning provider-specific model IDs.
- Added approved-baseline and refinement guardrails to product and acquisition work.
- Added a public upgrade inventory and positive/negative acceptance scenarios.
- Recovered the previously unpublished plugin hardening below; this remains an
  untagged release candidate until the documented release gates pass.

### Changed

- Replaced contradictory model/version doctrine with a telemetry-first routing policy.
- Replaced the absolute subagent long-run prohibition with a bounded, version-aware
  background-child policy.
- Restated hooks and design vetoes as protocol guidance unless a documented runtime
  permission decision or CI control enforces them.
- Preserved builder/verifier separation for iterative visual review.
- Corrected WCAG large-text guidance and scoped Playwright usage to pinned tooling.
- Corrected the anti-slop checklist description to the observable 73 Markdown entries
  and 11 overlap annotations; removed unsupported private-path and Aceternity vocabulary
  provenance.

### Added

- Compatibility, evidence, contributor, security, and third-party notice documents.
- An eight-class completion-gate reference shared by the verifier and orchestrator.
- A self-contained Claude Code plugin, GitHub marketplace catalog, doctor, clean-home
  runtime fixtures, and CI workflow.
- A tag-only release-artifact workflow that installs the public tag with Claude Code
  2.1.251 under the exact Node 22.22.1/npm 10.9.4 toolchain (asserting both versions),
  runs its installed doctor and strict-hook fixture, and
  byte-compares its cache with `git archive` of `plugins/fleetcraft` at the immutable
  push-event commit before and after rechecking the public tag target.
- Opt-in strict delegation decisions, completion gating, batch evidence reminders, and
  optional runtime telemetry/configuration that must be verified in the installed harness
  before it is enabled or relied on.

### Pending release gates

- Remote CI must pass on the exact published commit.
- The tag-only `release-artifact` workflow must pass for the immutable public tag; this
  is a future, unobserved gate and has not yet run for this untagged candidate.
- Maintainer must confirm the release diff and third-party provenance record.
- Create the immutable release tag only after those observations are recorded.
- A verified private vulnerability-reporting channel must be enabled and tested before
  release; it is currently an external `OPEN` gate.
