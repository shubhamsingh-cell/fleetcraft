# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.3.0 integration candidate — unreleased

- Reconciles v0.2 source workflows and the earlier plugin-hardening candidate.
- Keeps one canonical source tree with a generated, parity-checked plugin.
- Preserves eleven skills and four roles; adds explicit behavior-evaluation machinery.
- Repairs retrieval evidence, optional routing, and unsafe performance instructions.
- Adds source revision/license records, compatibility and reconciliation guidance.
- Separates observed validation from unexecuted or incomplete release/behavior gates.

## [Unreleased]

<!--
  Add new entries above this line, under the matching heading:
  ### Added / ### Changed / ### Deprecated / ### Removed / ### Fixed / ### Security
  When cutting a release, retitle this section `## [x.y.z] - YYYY-MM-DD`
  and start a fresh empty `## [Unreleased]` above it.
-->

## [0.2.0] - 2026-09-08

Second release. Four new skills, a fourth agent contract, two new hooks, and the
repo's own verification harness. Every skill, agent, and hook already published
was also brought up to date with the private setup it was extracted from.

### Added

- **`skills/debugging-and-error-recovery/`** — root-cause debugging: stop
  cleanly, localize a failure to its actual cause instead of patching
  symptoms, and triage bugs that refuse to reproduce.
- **`skills/performance-diagnosis/`** — fix slow software by measurement, not
  guesswork: baselines before changes, N+1 and pool-exhaustion patterns, cache
  design, Core Web Vitals regressions.
- **`skills/change-plan/`** — decision-ready change plans: blast radius,
  staged rollout with acceptance *and* abort criteria, rollback or forward
  recovery, required approvals.
- **`skills/project-handoff/`** — durable state for work outliving a session,
  written for a reader with no memory of the conversation.
- **`agents/strategist.md`** — the upward-escalation tier, for taste, brand,
  voice, and strategy calls that sit above the session model. Deliberately
  narrow: it hands the call back when the main loop already outranks it.
- **`hooks/tool-routing-guard.py`** (`PreToolUse` / `WebFetch|WebSearch`) — the
  family's one deliberate blocker. Denies a documentation-URL fetch once,
  pointing at a docs MCP first; the retry passes. Kill-switch env var downgrades
  it to a non-blocking reminder.
- **`hooks/retrieval-honesty-guard.py`** (`Stop`) — blocks a turn asserting
  "past my cutoff / I can't verify" when no retrieval tool actually ran in it.
  It fires on the sentence, not the topic, and never loops.
- **`tests/`** — behavioural test suite driving every hook as a subprocess over
  real stdin payloads. Every assertion is paired with a negative control, so a
  hook gutted to return nothing fails the suite instead of passing it quietly.
- **`examples/settings.json`** — all five hooks wired in one valid block, plus
  the duplicate-`PreToolUse`-key merge mistake that silently disables a hook.
- Repo-quality scaffolding: `scripts/validate.py` (stdlib-only frontmatter and
  hook-health validator, dynamic glob discovery), `.github/workflows/ci.yml`
  (Ubuntu, Python 3.11/3.12 matrix), `scripts/install.sh` (dry-run-first
  installer with backup-on-differ, never edits `settings.json` directly),
  `CONTRIBUTING.md`, `SECURITY.md`, issue and pull request templates, and
  `.gitignore`.

### Changed

- **`skills/fleet-orchestrator/`** — a fourth pinned agent type
  (`strategist`); an alias-resolution technique (read the model name quoted in
  an API *error*, since success responses don't name it and a subagent's
  self-report is not a measurement); a confidence-scored findings rule
  (score each finding 0-100 for reachability, drop anything under 80 rather
  than reporting it hedged, and say how many were dropped); the
  agent-definition reload lag (a just-edited agent is not the one a
  same-session dispatch reaches, so behaviour edits need a fresh session to
  test); an install-delegation exemption (plugin/marketplace/config installs
  cannot be delegated — a subagent correctly refuses relayed consent, so the
  orchestrator executes and says so); a second, harder mechanism behind
  long-running delegated work dying (a blocking call has a hard timeout
  ceiling, so "wait for completion" asks for something the tool contract
  cannot deliver); an adversarial file-tree step in the vendor-vet gate
  (read a skill bundle as files before reading it as prose — hidden-unicode
  channels survive a prose read); and the five-hook enforcement family.
- **`skills/design-judge/`** — an observed-vs-inferred rule (a screenshot is
  evidence of exactly one viewport, theme, state and moment; a still frame
  cannot establish motion), and a render-package contract for panel dispatch
  so two judges can never score two different captures. Each judge now returns
  `COMPLETE` or `OPEN`, making the errored-lens rule machine-readable.
- **`skills/product-interface-craft/`** — classify an ask as local refinement
  or authorized replacement before editing (an undocumented surface is still
  an approved one), and cover overlay clipping, browser zoom, and focus
  restoration, which fail silently in a source diff.
- **`skills/growth-web-architect/`** — redesign boundaries, and an asset
  authorization and licensing rule distinct from the fabricated-proof veto.
- **`agents/verifier.md`** — `disallowedTools` frontmatter now removes its
  write tools, verified from a fresh session. Documented as defence in depth,
  not a replacement for giving a panel its own worktree, since a restricted
  agent still has a shell. The earlier "measured" claim about what the `opus`
  alias resolves to is retracted and marked unverified.
- **`agents/researcher.md`** — a four-step retrieval ladder that puts docs
  tooling ahead of a generic web fetch.
- **`agents/executor.md`** — query docs tooling before citing any library or
  API behaviour from training memory.
- **`hooks/skill-routing-guard.py`**, **`hooks/fleet-delegation-guard.py`** —
  new routing categories and a package-install detection lane.
- **`README.md`** — restructured: install moved up and routed through
  `scripts/install.sh --dry-run`, inventory split by type, and a section
  documenting how the repo verifies itself.

### Fixed

- **`hooks/fleet-delegation-guard.py` failed closed on a malformed payload.**
  Valid JSON of an unexpected shape — a non-dict top level, a non-dict
  `tool_input`, or a non-string `command` — raised past the parse handler and
  exited 1 with a traceback, silently retiring the guard for that call. This
  is a fail-open violation in a hook whose entire contract is failing open.
  Every wrong shape now routes into the same "shape detection did NOT run —
  treat this as an unchecked call, not a cleared one" reminder that an
  unparseable payload already produced. Found by the new test suite's
  negative controls, not by reading the code.
- Machine-specific runtime paths (personal tool-install and virtualenv
  locations) were baked into shipped hooks, agents, and skills, where they
  resolved to nothing on any other machine. Replaced with bare command names.
- The AI-slop checklist was described as having 87 tells; the shipped file has
  73, distilled from an 87-check upstream source. Corrected here and in the
  README.
- `README.md` credited two of the three upstream sources the skills harvest
  from. The AI-slop checklist's source is now credited alongside them.

## [0.1.0] - 2026-08-24

Initial public release.

### Added

- **`skills/fleet-orchestrator/`** — capability-matched model tiering for
  multi-agent work, prompt compression for subagent briefs, and an 8-class
  adversarial final-pass gate to run before calling anything "done."
- **`skills/design-judge/`** — screenshot-first design review protocol:
  render the real surface, run a multi-lens judge panel, apply hard vetoes
  for fabricated proof and design regressions, then verdict. Ships with an
  73-item AI-slop checklist (distilled from an 87-check upstream source)
  and a harvested anti-cliché catalog.
- **`skills/incident-miner/`** — turns a resolved incident or a hard-won
  bug fix into a durable lessons-log entry or a new/updated skill, with
  read-only evidence gathering and a hard stop for human approval before
  anything is written.
- **`skills/growth-web-architect/`** — architecture and audit guidance for
  marketing/acquisition landing pages: conversion mechanism first,
  proof-integrity vetoes, responsive matrix, reduced-motion and keyboard
  states, accessibility pass.
- **`skills/product-interface-craft/`** — building product UI (dashboards,
  onboarding, settings, tables) with a deliberate design direction,
  complete interaction states, and rendered desktop/mobile validation.
- **`agents/executor.md`** — heavy-execution subagent contract:
  root-cause-gated bug fixes, regression tests proven failing on pre-fix
  code, shared-tree push safety, two-verdict self-check.
- **`agents/researcher.md`** — research subagent contract:
  verified-vs-plausible tagging on every finding, sources required, dead
  ends declared instead of papered over.
- **`agents/verifier.md`** — adversarial verification contract: reviews
  delegated work by trying to refute it, and reports its own running
  model so tier assumptions get checked, not trusted.
- **`hooks/autoload-judgment.py`** (`SessionStart`) — deterministically
  injects a judgment skill into every session's starting context, so
  discipline doesn't depend on the model remembering to load it.
- **`hooks/fleet-delegation-guard.py`** (`PreToolUse` / `Bash`) — catches
  deploy/commit-shaped commands in the main loop and injects the
  delegation rule at the exact moment it's about to be broken.
- **`hooks/skill-routing-guard.py`** (`UserPromptSubmit`) — routes
  document/share/design/exec-message prompts to the matching installed
  skill instead of an ad hoc answer.

[Unreleased]: https://github.com/shubhamsingh-cell/fleetcraft/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/shubhamsingh-cell/fleetcraft/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/shubhamsingh-cell/fleetcraft/releases/tag/v0.1.0
