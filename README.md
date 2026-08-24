# fleetcraft

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

## What's in here

| Path | Type | Purpose |
|---|---|---|
| `skills/fleet-orchestrator/` | Skill | The core: capability-matched model tiering for multi-agent work (which brain runs what, and why the session model is a floor, not a ceiling), prompt compression for subagent briefs, and an 8-class adversarial final-pass gate to run before calling anything "done." |
| `skills/design-judge/` | Skill | Screenshot-first design review: render the real surface, run a multi-lens judge panel, apply hard vetoes (fabricated testimonials/stats/logos, design regressions), then verdict. Ships with an 87-tell AI-slop checklist plus a harvested anti-cliché catalog. |
| `skills/incident-miner/` | Skill | Turns a resolved incident or painful bug hunt into a durable lessons-log entry or a new skill — read-only evidence gathering, hard stop for human approval before anything is written. |
| `skills/growth-web-architect/` | Skill | Architect/audit marketing landing pages: conversion mechanism first, proof-integrity vetoes, responsive matrix, reduced-motion and keyboard states, accessibility pass. |
| `skills/product-interface-craft/` | Skill | Build product UI (dashboards, onboarding, settings, tables) with a deliberate design direction, complete interaction states, and rendered desktop/mobile validation. |
| `agents/executor.md` | Agent | Heavy-execution subagent contract: root-cause-gated bug fixes, regression tests proven failing on pre-fix code, shared-tree push safety, two-verdict self-check. |
| `agents/researcher.md` | Agent | Research subagent contract: verified-vs-plausible tagging on every finding, sources required, dead ends declared instead of papered over. |
| `agents/verifier.md` | Agent | Adversarial verification contract: reviews delegated work by trying to *refute* it, and reports its own running model so tier assumptions get checked, not trusted. |
| `hooks/autoload-judgment.py` | Hook | `SessionStart` — deterministically injects a judgment skill into every session's context, so discipline doesn't depend on the model remembering to load it. |
| `hooks/fleet-delegation-guard.py` | Hook | `PreToolUse` (Bash) — catches deploy/commit-shaped commands in the main loop and injects the delegation rule at the exact moment it's about to be broken. |
| `hooks/skill-routing-guard.py` | Hook | `UserPromptSubmit` — routes document/share/design/exec-message prompts to the matching installed skill instead of an ad hoc answer. |

## The ideas, in one paragraph each

**Tiering is capability-matched, not cost-first.** One expensive model plans,
routes, and synthesizes; cheaper models execute; escalation goes *up* as well
as down. The session model the owner picked is a stakes signal — never
silently delegate judgment-bearing work below it. And never trust a
subagent's self-reported model id: it's a hint, not a measurement.

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
moment. Non-blocking by design: they remind, they never veto.

**Proof is sacred.** Any user-facing surface with testimonials, counters,
logos, or case studies either traces every element to a real artifact or
labels it illustrative — or it doesn't ship. This rule is enforced by a hard
veto in `design-judge`, not by good intentions.

## Quickstart

```bash
git clone https://github.com/shubhamsingh-cell/fleetcraft.git && cd fleetcraft

# Skills → user-level skill directory
cp -r skills/* ~/.claude/skills/

# Agent definitions → user- or project-level
cp agents/*.md ~/.claude/agents/

# Hooks → copy, then wire each to its event in ~/.claude/settings.json
cp hooks/*.py ~/.claude/hooks/
```

See `hooks/README.md` for the settings.json wiring (`SessionStart`,
`PreToolUse` matcher on `Bash`, `UserPromptSubmit`) and the non-blocking
context-injection pattern the three hooks share.

Paths referenced *inside* skills and hooks assume the standard `~/.claude/...`
layout; adjust if yours differs.

## Honest limitations

- These are opinionated operating rules, not a framework — there's no code to
  run except the three hooks. Value scales with how much multi-agent
  delegation you actually do.
- Skill/hook wiring targets Claude Code. The *ideas* (tiering floor,
  adversarial gates, proof vetoes) port to any agent harness; the packaging
  doesn't yet.
- No benchmarks are claimed. The evidence base is one production setup's
  documented incidents, which is exactly one data point more than vibes.

## Attribution

`design-judge` and `growth-web-architect` include harvested, credited
material from [taste-skill](https://github.com/Leonxlnx/taste-skill) (MIT) and
pattern references from
[web-designer-plugin](https://github.com/MickeyAlton33/web-designer-plugin)
(MIT). Attribution and fetch dates are marked inline in the affected sections.

## License

MIT — see `LICENSE`. Copyright (c) 2026 Shubham Singh Chandel.
