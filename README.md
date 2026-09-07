# fleetcraft

[![CI](https://github.com/shubhamsingh-cell/fleetcraft/actions/workflows/ci.yml/badge.svg)](https://github.com/shubhamsingh-cell/fleetcraft/actions/workflows/ci.yml)

**Judgment infrastructure for AI coding agents** — model tiering, adversarial
verification gates, and design QA, packaged as installable Claude Code skills,
agent definitions, and hooks.

Most agent tooling helps agents *write more code*. This kit is about the other
problem: getting agent output you can actually trust — which model tier gets
which subtask, how delegated work gets verified before it's called "done,"
how a design regression gets caught before it ships, and how a hard-won fix
becomes a durable lesson instead of a repeat incident.

Everything here was extracted from a working production setup — multiple live
products, real deploys, real incidents — then sanitized for publication. The
war stories inside are anonymized but real: every rule in these files exists
because its absence once caused a specific, dated failure.

## Install

Look before you leap — the hooks are Python that will run inside your agent's
tool-call path:

```bash
git clone https://github.com/shubhamsingh-cell/fleetcraft.git && cd fleetcraft
./scripts/install.sh --dry-run
```

Dry run prints exactly what it would write and changes nothing. When it looks
right:

```bash
./scripts/install.sh
```

Skills go to `~/.claude/skills/`, agents to `~/.claude/agents/`, hooks to
`~/.claude/hooks/`. Anything that already exists and differs is backed up to
`<path>.bak.<timestamp>` rather than overwritten. `--skills-only`,
`--agents-only`, and `--hooks-only` narrow the install.

The installer deliberately does **not** edit `~/.claude/settings.json` — a bad
merge into a live config breaks your session, so wiring the hooks stays your
call. It prints the JSON to paste; `examples/settings.json` has the complete
five-hook block, and `hooks/README.md` documents each event, matcher, and
kill-switch.

Paths referenced *inside* skills and hooks assume the standard `~/.claude/...`
layout; adjust if yours differs.

## What's in here

### Skills

| Path | Purpose |
|---|---|
| `skills/fleet-orchestrator/` | The core: capability-matched model tiering for multi-agent work (which brain runs what, and why the session model is a floor, not a ceiling), prompt compression for subagent briefs, and an 8-class adversarial final-pass gate to run before calling anything "done." |
| `skills/design-judge/` | Screenshot-first design review: render the real surface, run a multi-lens judge panel, apply hard vetoes (fabricated testimonials/stats/logos, design regressions), then verdict. Ships a 73-item AI-slop checklist and a harvested anti-cliché catalog. |
| `skills/debugging-and-error-recovery/` | Root-cause debugging: stop cleanly, localize the failure to its actual cause instead of patching symptoms, and handle bugs that refuse to reproduce. |
| `skills/performance-diagnosis/` | Fix slow software by measurement, not guesswork — baselines before changes, N+1 and pool-exhaustion patterns, cache design, Core Web Vitals regressions. |
| `skills/change-plan/` | Decision-ready change plans: blast radius, staged rollout with acceptance *and* abort criteria, rollback or forward recovery, required approvals. |
| `skills/project-handoff/` | Durable state for work that outlives a session — written for a reader with no memory of the conversation, so the next session resumes instead of re-deriving. |
| `skills/incident-miner/` | Turns a resolved incident or painful bug hunt into a durable lessons-log entry or a new skill — read-only evidence gathering, hard stop for human approval before anything is written. |
| `skills/growth-web-architect/` | Architect/audit marketing landing pages: conversion mechanism first, proof-integrity vetoes, responsive matrix, reduced-motion and keyboard states, accessibility pass. |
| `skills/product-interface-craft/` | Build product UI (dashboards, onboarding, settings, tables) with a deliberate design direction, complete interaction states, and rendered desktop/mobile validation. |

### Agent definitions

| Path | Purpose |
|---|---|
| `agents/executor.md` | Heavy-execution contract: root-cause-gated bug fixes, regression tests proven failing on pre-fix code, shared-tree push safety, two-verdict self-check. |
| `agents/verifier.md` | Adversarial verification: reviews delegated work by trying to *refute* it. Write tools removed via `disallowedTools` frontmatter — defence in depth, not a substitute for giving a panel its own worktree. |
| `agents/researcher.md` | Research contract: verified-vs-plausible tagging on every finding, sources required, dead ends declared instead of papered over, and a retrieval ladder that puts docs tooling ahead of a generic web fetch. |
| `agents/strategist.md` | The upward-escalation tier, for taste/brand/voice/strategy calls that sit *above* the session model. Deliberately narrow: it hands the call back if the main loop already outranks it. |

### Hooks

Prose can't self-enforce. Four of these inject context at the decision moment;
one deliberately blocks. All fail open — a crashing guard must never wedge a
session.

| Path | Event | Behaviour |
|---|---|---|
| `hooks/autoload-judgment.py` | `SessionStart` | Injects a judgment skill into every session's context, so discipline doesn't depend on the model remembering to load it. |
| `hooks/fleet-delegation-guard.py` | `PreToolUse` (Bash) | Catches deploy/commit/long-run/package-install shapes in the main loop and injects the delegation rule at the moment it's about to be broken. |
| `hooks/skill-routing-guard.py` | `UserPromptSubmit` | Routes document/share/design/docs-shaped prompts to the matching installed skill instead of an ad hoc answer. |
| `hooks/tool-routing-guard.py` | `PreToolUse` (WebFetch\|WebSearch) | **The one blocker.** Denies a documentation-URL fetch *once*, pointing at a docs MCP first; the retry passes. Kill-switch downgrades it to a reminder. |
| `hooks/retrieval-honesty-guard.py` | `Stop` | Blocks a turn that claims "past my cutoff / I can't verify" when no retrieval actually ran in it. The tell is the sentence, not the topic. |

## The ideas, in one paragraph each

**Tiering is capability-matched, not cost-first.** One expensive model plans,
routes, and synthesizes; cheaper models execute; escalation goes *up* as well
as down. The session model the owner picked is a stakes signal — never
silently delegate judgment-bearing work below it. And never trust a
subagent's self-reported model id: it's a hint, not a measurement. To learn
what a `model:` alias really resolves to, read the model name quoted in an API
*error* — success responses don't name it and the agent itself doesn't know.

**The builder reads its own diff generously.** So "done" passes through an
adversarial gate: shared-state races, silently-failing deploy gates, design
regressions via helpful defaults, irreversible ops dressed as routine
cleanup, claimed-done vs. verified-done, the "I'm already holding the
context" rationalization, fabricated proof, and — the master rule — for every
claim, name the observation that would look *different if the claim were
false*, and confirm you actually made that observation.

**Prose can't self-enforce.** Skills are advice; the moment of failure is
mid-flow, under context pressure, exactly when advice gets skipped. The hooks
are small deterministic scripts that re-inject the rule at the decision
moment.

**Not knowing is a conclusion, not an opening move.** "I can't verify that"
is only honest *after* retrieval was attempted and reported. Asserting it
while holding working search tools is the specific failure
`retrieval-honesty-guard` exists to catch — and it catches it on the sentence,
because the topic is never the tell.

**Proof is sacred.** Any user-facing surface with testimonials, counters,
logos, or case studies either traces every element to a real artifact or
labels it illustrative — or it doesn't ship. This rule is enforced by a hard
veto in `design-judge`, not by good intentions.

## How this repo is verified

A repo whose entire thesis is "verify before you claim" would be absurd
without its own gate, so:

- `scripts/validate.py` — stdlib-only. Checks every skill and agent's
  frontmatter, compiles every hook, feeds each one an empty payload to prove
  it exits cleanly, and fails the build on absolute local paths. Run it before
  opening a PR.
- `tests/` — behavioural tests driving each hook as a subprocess over real
  stdin payloads. **Every assertion ships with a negative control**: each
  "stays silent" test is paired with a "actually fires" test on a triggering
  payload, so a hook gutted to return nothing fails the suite instead of
  passing it quietly. That pairing is the same vacuous-test rule the skills
  apply to everything else, turned on the tests themselves.
- `.github/workflows/ci.yml` — runs both on every push and pull request.

## Honest limitations

- These are opinionated operating rules, not a framework — the only code is
  the hooks and the test/validation harness around them. Value scales with how
  much multi-agent delegation you actually do.
- Skill/hook wiring targets Claude Code. The *ideas* (tiering floor,
  adversarial gates, proof vetoes, retrieval honesty) port to any agent
  harness; the packaging doesn't yet.
- No benchmarks are claimed. The evidence base is one production setup's
  documented incidents, which is exactly one data point more than vibes.
- Several skill descriptions exceed the ~500-character budget the validator
  warns about. Claude Code's skill catalog has a finite description budget and
  skills past it can render without descriptions; if you install many skills,
  that's the knob to watch.

## Contributing

The bar here is a real precedent, not a good idea — see `CONTRIBUTING.md`.
Security posture and how to report a vulnerability: `SECURITY.md`.

## Attribution

`design-judge` and `growth-web-architect` include harvested, credited
material from [taste-skill](https://github.com/Leonxlnx/taste-skill) (MIT) and
pattern references from
[web-designer-plugin](https://github.com/MickeyAlton33/web-designer-plugin)
(MIT). The AI-slop checklist is distilled from
[anti-slop](https://github.com/miqdadbadjuber/anti-slop) (MIT). Attribution
and fetch dates are marked inline in the affected sections.

## License

MIT — see `LICENSE`. Copyright (c) 2026 Shubham Singh Chandel.
