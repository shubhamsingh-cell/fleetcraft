---
name: fleet-orchestrator
description: >-
  Fable-level judgment at Sonnet/Opus cost: model-tiering for multi-agent work (Fable 5
  orchestrates, Sonnet 5 = default execution, Opus 5 = escalation), prompt compression
  for subagent briefs, autonomous routing through installed skills/agents/MCP tools, and
  an 8-class adversarial final-pass gate run on your own work before calling anything
  done. Trigger when spawning subagents and picking model/prompt/capability — even for
  one subagent; when marking a task done/shipped/deployed; and the instant you're about
  to run a mechanical multi-step task yourself mid-session (hotfix, commit+push, build/
  deploy) — the question is whether it should be delegated. Also fires on: "tier the
  fleet," "run this efficiently/cheaper," "use a cheaper model," "don't burn my usage
  limits," "split this across agents," "double-check before we call it done," or
  /fleet-orchestrator. (Compressed to fit claude.ai's 1024-char upload limit — 2026-07-16.)
---

# fleet-orchestrator — Fable-level judgment at Sonnet/Opus cost

> **Changelog (summarized).** This skill has gone through several hardening passes:
> a **floor rule** was added so judgment-bearing work is never delegated below the
> session's own model tier; an **upward escalation path** (`model: "fable"`) was added
> for taste/brand/voice/strategy calls that a pure cost-first tiering table would miss;
> **effort** (low→max) was promoted to a first-class dial alongside model choice; the
> three pinned agent types (`executor`/`verifier`/`researcher`) were introduced with
> their rules embedded in their own definitions; a vacuous-regression-test check, a
> vendor-vet gate, anchored review rubrics, and a fabricated-proof gate class were added
> to the adversarial final pass; and a fan-out pattern for post-cutoff/viral factual
> claims was added to "When to fan out and fight." More recently: a fourth pinned
> agent, **`strategist`** (Fable-pinned), gave the upward-escalation path a concrete
> destination for taste/brand/voice/strategy calls that sit above the session tier; an
> **alias-resolution technique** settled what a `model:` alias actually reaches — read
> the model name an API ERROR quotes, since both success responses and a subagent's own
> self-report are unreliable narrators — which confirmed `fable` resolves for real and
> left `opus` still unmeasured; a **confidence-scored findings rule** now has every
> parallel review pass score each finding's reachability 0-100 and drop anything under
> 80 rather than reporting it hedged; an **agent-definition reload lag** was documented
> — a just-edited agent type is not the one a same-session dispatch reaches, so an agent
> behavior edit needs testing from a fresh session; an **install-delegation exemption**
> now states out loud that plugin/marketplace/config installs cannot be delegated (a
> subagent correctly refuses relayed consent for that channel) and stay
> orchestrator-owned, interactive-terminal work; and the enforcement hooks grew into a
> **six-hook family** (session autoload, delegation guard, two routing guards, the one
> blocking tool-routing guard, and a retrieval-honesty guard), all covered by a shared
> selftest with negative controls. Each addition was mined from a real failure observed
> in production use — see the precedents cited inline throughout this file rather than
> a separate version history.

**Core rule (read this even if you read nothing else):** before executing more than
~2-3 tool calls yourself for a mechanical multi-step task (edit+commit+push,
build+verify+deploy, run+validate), stop and delegate it to a Sonnet subagent — and this
includes reactive work (hotfixes, bugs found mid-flow) and any repeat of a shape already
delegated this session. Only two named exemptions: a live production incident where the
fix is a single step, or a task so small that restating the context for a subagent costs
more than doing it — and using an exemption requires saying so out loud, never silently.
One carve-out that is NOT an exemption: the *execution* of a long-lived run (ship script,
full test suite, migration, multi-minute build) stays with the orchestrator as
harness-tracked background work, because a subagent's backgrounded process dies with its
turn and no wording in the brief can prevent that. Delegate the prep, not the babysitting
(see Gotchas).

Three levers, used together: **which brain** runs a subtask (model tiering), **how much
it's asked to read** (prompt compression), and **whether a pre-built capability already
does this job** (autonomous routing) instead of a raw model call. All three exist for the
same reason: get output that matches or beats what Fable would produce directly, at a
fraction of the tokens.

## Lever 1 — model tiering

Fable 5 is expensive and slow *relative to what it's for* — its edge is judgment,
planning, routing, and synthesis, not throughput. Running every subagent on Fable spends
that edge on grunt work it doesn't need. The fix: keep exactly one Fable "brain" at the
top (the main loop / orchestrator), and delegate execution to cheaper, faster models that
are still strong enough to do the work well.

**⭐ THE FLOOR RULE (v14, owner directive 2026-08-21) — read before the tier list.** The
session model is the OWNER'S SIGNAL ABOUT STAKES, not a starting point to optimise away from.
**Never delegate judgment-bearing work BELOW the session tier.** If the owner has selected
Opus 5 at high effort, routing the core judgment to a Sonnet subagent silently overrides that
choice and quietly lowers quality — which is precisely the failure this skill claims to prevent.
Tiering is **capability-matched, not cost-first**: pick the model AND the effort that fit the
task, and the direction is **UP as often as down**. Downward routing is for work that is
genuinely mechanical (high-volume, low-judgment, verifiable by inspection). Everything else
matches or exceeds the session tier.

**Escalate UPWARD when the task calls for it — this path previously did not exist in this file.**
`model: "fable"` is a valid alias on both the Agent tool and Workflow `agent()`. Reach for it for
taste/brand/voice calls, strategy synthesis, and judgment the `fable-judgment` sections themselves
encode. Pair it with high/xhigh/max effort when the reasoning is the hard part.
⚠ **EVIDENCE-QUALITY CORRECTION (2026-08-21, owner challenge).** Opus 5 IS the current top
Opus and is owner-selectable as the session model — any reading of this file that treats 4.8
as "current" is wrong. Earlier text here claimed `opus` → Opus 4.8 was *measured*. It was not,
and the two supporting facts are NOT equally strong:
  • **RELIABLE** — a harness notice ("Switched to Opus 4.8") after a safeguard auto-downgrade.
    That is the system reporting the session model; trust it.
  • **WEAK** — a dispatched subagent writing its own model id in its report header. Models are
    unreliable narrators of their own version (training-data echo), so a self-report is a HINT,
    never a measurement. v13's error was asserting an unmeasured alias claim; the v13.1 "refutation"
    then over-trusted a self-report — the same error with the sign flipped.
  • ⭐ **`fable` RESOLVED 2026-09-07 — the alias works.** A `strategist` agent pinned
    `model: fable` failed with an API 429 whose text named the model actually sent:
    `model sent to the API: claude-fable-5-1`. That is an API/harness signal, not a self-report,
    so it meets this file's own evidence bar. Two consequences: (a) `model: "fable"` in agent
    frontmatter genuinely reaches Fable 5.1 — the v14 upward-escalation path is real, not
    aspirational; (b) **a Fable-pinned agent is unusable whenever the Fable usage limit is hit**,
    and it fails loudly rather than silently downgrading, which is the good failure mode. While
    that limit holds, route the call to the main loop or an `opus` agent instead.
  • 🔧 **Technique worth reusing:** to learn what an alias really resolves to, read the model name
    in an API ERROR. Errors quote the model sent; success responses do not, and the agent's own
    self-report is worthless. This is the cheap falsifier that was missing for two versions.
  • `opus` remains **UNKNOWN** — the same technique would settle it. Do not encode a belief as
    fact until it does. Treat it as a
candidate, require every dispatched agent to STATE ITS RUNNING MODEL in its report header, and
if it reports lower than intended, escalate by moving the work into the MAIN LOOP (where the
session model is owner-selectable) rather than assuming the tier held.

**Effort is a first-class scenario dial, not a leftover.** Set it deliberately every dispatch:
`low` for mechanical sweeps and bulk extraction; `medium` for routine build/research execution;
`high` for security/correctness gates, adversarial verification, and synthesis over many inputs;
`xhigh`/`max` for genuinely frontier reasoning — a novel architecture call, a contested judgment,
an audit where being wrong is expensive. Under-setting effort on a hard task is the same quality
leak as under-setting the model; both are silent.

- **Fable 5 (orchestrator, no `model` override)** — stays as the session model. Does the
  planning, makes the architecture/priority calls, reviews and synthesizes what comes
  back from subagents, and writes the final answer. Should rarely if ever execute heavy
  work itself — if Fable is the one writing 200 lines of implementation, something is
  mis-tiered.
- **Sonnet 5 (`model: "sonnet"`) — MECHANICAL-execution tier (was "default"; demoted from
  default in v14).** Correct for high-volume, low-judgment, inspection-verifiable work: bulk
  search sweeps, mechanical edits, scripted runs, wide extraction. NOT automatically correct
  for a session the owner set to a higher tier — see the floor rule above. Strong enough for heavy
  lifting: full feature builds, most coding, most research execution, long-form drafting,
  multi-step build tasks. Don't pigeonhole Sonnet into "trivial formatting only" — default
  every subagent to Sonnet unless there's a specific reason to escalate.
- **Opus 5 (`model: "opus"`) — escalation tier.** Reserve for the subset of subagent
  work that genuinely needs more depth: gnarly algorithmic or architectural reasoning,
  security- or correctness-critical logic, adversarial verification / refutation passes,
  judge panels on a risky finding, or a subtask Sonnet already attempted and got wrong.
  Opus is the fallback when Sonnet's output isn't trustworthy enough, not the default.
- **Haiku 4.5 (`model: "haiku"`)** — only for near-zero-judgment, high-volume
  mechanical subtasks in a large fleet. Rarely needed; Sonnet is usually cheap enough
  that this tier isn't worth the quality tradeoff.
- **Fable 5 (`model: "fable"`) — UPWARD escalation tier (new in v14).** For taste, brand,
  voice, strategy synthesis, and priority/triage judgment — the work `fable-judgment` exists to
  encode. Use when the session model is below Fable and the call is genuinely a taste/judgment
  call, or when a panel benefits from a Fable-tier lens alongside Opus ones. Verify the reported
  running model (see the UNVERIFIED warning above) before trusting the tier.

**Mechanics.** Agent tool: pass `model` directly (`"sonnet"` / `"opus"` / `"haiku"` /
`"fable"`, omit to inherit the session model — no independent effort dial here). Workflow
tool's `agent()`: `model` and `effort` (`low`/`medium`/`high`/`xhigh`/`max`) are
independent dials — e.g. `{model: "sonnet", effort: "high"}` for a hard-but-not-frontier
task, or `{model: "opus", effort: "low"}` for a fast high-stakes sanity check. Version
numbers in this file name the roster as of the last maintenance pass (2026-07-25: Opus 5 /
Sonnet 5 / Haiku 4.5 / Fable 5); what you actually pass is the alias, which tracks the
roster — re-anchor the numbers each pass, never hardcode a version into a dispatch.

**Session model vs. subagent model are different things.** "Fable as orchestrator" means
the main loop is running on Fable 5 (`/model claude-fable-5` or the `fable` alias). This
skill's tiering governs what *subagents* get on top of that — not what the main loop is.

**The tiering is session-model-agnostic — whoever runs the main loop is the
orchestrator.** The decision table binds subagent choice to the TASK, not to which model
happens to be the session model. On Fable 5: delegate to Sonnet (default) / Opus
(escalation) / Haiku (rare high-volume). On Opus 5: same table — Sonnet default, Haiku
for mechanical volume; escalation targets a parallel Opus subagent (fresh context is the
point, not a bigger brain). On Sonnet 5: same table again, Opus as escalation. In every
case the orchestrator plans, judges, and synthesizes — and never does the grunt work
itself, regardless of which brain it is. This skill applies on EVERY session model, not
only when Fable is driving.

**Complementary CLI-native lever — `/ultraplan`.** If you have interactive Claude Code CLI
access (not this harness), `/ultraplan` hands a planning task to a cloud Opus session,
freeing your local terminal to keep working. It's a different mechanism than this skill's
subagent-based tiering (a separate cloud session, not an in-conversation subagent) but the
same goal — expensive-brain planning without paying for it inline. Use whichever fits: this
skill's levers when you're already mid-session, `/ultraplan` when you want to kick off
planning and walk away.

**Pay-per-use fallback — RETIRED 2026-08-20 by owner directive.** The 2026-07-07 clause
(Sonnet as default session model while Fable was metered, fable-judgment supplying the
judgment layer) is dormant: the owner directed "Fable for everything" — Fable 5 runs the
session/orchestrator unconditionally, metering notwithstanding. **The escalation TARGET is
Opus 5 — never Opus 4.8 or older.** ⚠ SELF-CONTRADICTION FIXED 2026-08-21: this paragraph
previously asserted as *measured* that `model: opus` dispatches Opus 4.8 and that
`claude-opus-5` falls back to 4.5 — directly contradicting the evidence-quality correction
in Lever 1, which downgrades that same claim to UNKNOWN (its only support was a subagent
self-report, and models are unreliable narrators of their own version). Both statements
cannot be true; the Lever 1 correction is the surviving one. What an alias resolves to is
**unknown here** — do not encode either belief as fact. Practical rule unchanged and
independent of the unknown: when a call truly needs top-tier judgment, decide it in the
MAIN LOOP where the owner selects the model, rather than delegating and *assuming* the tier
held. (Caught by re-reading the file after editing it — the same internal-contradiction
class v13.1 was created to fix. Edit one claim, grep the whole file for its twin.)
fable-judgment still auto-loads via the SessionStart hook as defense-in-depth for any
session that isn't Fable-driven. (Historical clause text preserved in git history of this
file and in memory, should metering economics ever reopen the question — reopening it is
the owner's call, not a session's.)

## Lever 2 — prompt compression (shrink the brief, keep the quality)

A subagent's real cost is its own prompt tokens *plus* whatever exploration or
back-and-forth a vague brief forces. A tighter, more precise prompt often reduces total
spend even though writing it costs the orchestrator a few extra tokens up front — a sharp
brief prevents wasted exploration, mis-scoped work, or a round of re-explaining. Run this
compression pass before dispatching any subagent prompt:

1. **Front-load the ask.** First line states exactly what's wanted — no scene-setting
   before it.
2. **Point, don't paste.** If the subagent has Read/Grep and the file exists, give it
   `path:line`, not the file's contents copied into the prompt.
3. **Facts as a list, not a narrative.** Bullets compress better than prose for a reader
   that isn't parsing for tone.
4. **State the deliverable shape up front** — format, length cap, or (better) a `schema`
   — instead of describing in prose what a good answer looks like.
5. **Cut hedging and repetition.** No apologetic filler, no restating the same
   instruction three ways "to be safe."
6. **One crisp ask per call.** Decompose a bundled, ambiguous request into one clear
   instruction per subagent rather than a long compound brief the subagent has to
   untangle itself.
7. **Factor shared context once.** In a Workflow script, define the shared background as
   one constant and interpolate it into every `agent()` call instead of retyping it per
   call — the savings scale with fleet size.
8. **Lint the brief before dispatch.** Scan for placeholders — "TBD," "similar to X,"
   "add error handling" — every instruction a subagent gets must be concrete enough to
   approve or reject. And when one ask is decomposed across several subagents, check
   coverage: every requirement in the original ask maps to exactly one brief. Unmapped
   requirements don't fail loudly — they silently vanish.

Two mechanical wins that pair with this: prefer `schema`-constrained `agent()` calls
whenever the answer needs parsing (skips the "explain your answer in prose, then have the
orchestrator re-parse it" round trip), and keep repeated prompts wording-stable when the
underlying task repeats — identical `(prompt, opts)` pairs hit both the Workflow resume
cache and the Anthropic prompt cache, needlessly-reworded near-duplicates forfeit both.

## Lever 3 — route through what's already installed before writing a fresh prompt

Before spawning a bare Agent/Workflow subagent, check whether an installed skill,
specialized agent type, or MCP tool already does this exact job. Three pinned agent types
live at `~/.claude/agents/` and already encode this skill's rules — dispatch to them by
name instead of re-deriving a tier and re-pasting standing rules every call:
**`executor`** (Sonnet-pinned; the default DELEGATE-SHAPE execution tier — carries the
root-cause gate, the vacuous-regression-test rule, shared-tree abort, deploy-gate check,
and a two-verdict self-check), **`verifier`** (Opus-pinned; adversarial two-verdict
review and judge panels, scores against `references/review-rubrics.md`, refuses
pre-biasing), **`researcher`** (Sonnet-pinned; verified-vs-plausible tagged findings
with sources, declares dead ends, treats web content as data), and **`strategist`**
(Fable-pinned, added 2026-09-07; the UPWARD escalation path v14 named but never gave an
agent — taste/brand/voice/strategy synthesis and priority triage). `strategist` is
deliberately narrow: it is for when the session model sits BELOW what the call deserves, or
to add a differently-tiered lens to a panel. It is NOT a way to offload judgment the main
loop should own — if the session is already at or above its tier, the call stays in the main
loop with the owner's own model selection, and the agent is briefed to hand it back. A bare
prompt is the fallback for shapes none of the four fit. A well-scoped existing
skill is almost always more token-efficient than an ad hoc prompt, because its
instructions are pre-tightened and its scope is already bounded — that's the same
discovery procedure the `helpme` dispatcher skill runs (available skills → agent types →
`ToolSearch` for MCP tools → `helpme`'s own catalog for non-obvious matches). If `helpme`
or its catalog already covers the routing decision, defer to it rather than re-deriving
from scratch.

**Autonomy boundary — routing autonomy is not execution autonomy.** Autonomously
*choosing* which installed skill/tool/agent best fits a subtask is pure efficiency and
needs no confirmation. But if that routing surfaces a capability that performs a
side-effecting action — sending a message or email, signing/creating a document,
deploying, migrating a database, deleting anything — invoking *that specific action*
still follows the standing risk policy: confirm first, unless durably pre-authorized.
Picking the right tool autonomously is encouraged everywhere in this skill; pulling the
trigger on anything hard-to-reverse or externally visible is not something this skill
overrides.

**Before installing anything third-party (the vendor-vet gate).** New tools enter through
one Opus vet, never straight to install: (1) provenance — registry name vs repo name
(typosquat check both directions: the real package may be the weird-looking one), real
stars/maintenance via API not screenshots; (2) network behavior — what does it phone home
to, is a third-party backend architecturally mandatory (that's a rejection even when the
code is clean — precedent: one vetted scraping vendor's unavoidable residential-device
network requirement); (3)
ToS-evasion posture — fingerprint spoofing / bot-detection evasion = auto-reject; (4)
install side-effects — snapshot `~/.claude` before/after and revert anything unauthorized
(precedent: an installer silently creating `~/.claude/CLAUDE.md`); (5) write the rollback
recipe BEFORE installing, into the session record. Install into an isolated venv/prefix,
pin the version, prefer `--ignore-scripts` on first contact.
(6) **read a skill/plugin bundle as an adversarial FILE TREE, not as markdown.** Before reading
any `SKILL.md` as prose, list every non-`.md` file in the bundle (scripts, `.pyc`, data, configs),
grep the whole tree for zero-width / bidi / private-use codepoints and mixed-script homoglyphs, and
treat any compiled or encoded artifact as UNREVIEWED until decompiled. Rationale: Tencent's
AI-Infra-Guard assessment (14,560 runs) measured a hidden-unicode channel succeeding 25.5% of the
time in *file* mode versus 0.0% in *text* mode — i.e. reading the prose is exactly the mode that
misses it. (Measured against DeepSeek Harness, not Claude Code — directional for this stack, not
measured on it. Install nothing from that project: its scanner egresses to openrouter.ai by
default and its platform installs via curl|sh.)
⚠ **Live typosquat, recorded 2026-09-07:** PyPI `postgres-mcp-pro` 0.4.2 impersonates
`crystaldba/postgres-mcp`, whose real package is plain `postgres-mcp` at 0.3.0 — the fake carries
the HIGHER version number and the product's marketing name. This is the typosquat-in-both-
directions case step 1 warns about, found in the wild: never install by the product name.

**StarGuard automates step 1** (fake-star burst detection, dependency-hijack and license
red-flags as a CLI pass) once installed from PyPI (`pip install starguard`). Two facts a
future session needs, both measured:
- The package's own console-script entry point is **BROKEN** — it does `from starguard
  import main`, but package-level `main` is a *module*, not a callable, so the installed
  `starguard` command dies with `TypeError: 'module' object is not callable`. The real
  entry point is `starguard.cli:main` — call it directly until the package fixes its own
  entry, e.g. `python3 -c "from starguard.cli import main; main()" owner/repo [--burst-only]
  [-f markdown]` (verified running 2026-09-07 against `addyosmani/agent-skills`: Fake Star
  Index 0.00, LOW RISK).
- Authenticate the GitHub calls rather than running unauthenticated — reusing a token from
  `gh auth token` dodges the unauthenticated GitHub API rate limit; check the tool's own
  `--help` for the exact flag/env var this version expects.
Star forensics is therefore a mechanical check now, not a judgment call. Caveat: `--burst-only`
returned an empty window on one repo ("No star data found within 0 days"), so treat an empty
burst report as INCONCLUSIVE and re-run in full mode — not as a clean bill of health.

**Never judge skill/context pruning by `/context`'s total or its System-tools row.** Tokens
removed from the Skills row reappear 1:1 under System tools (anthropics/claude-code #85439,
maintainer-confirmed, unfixed as of 2.1.263), so the total is not a measurement of what you cut.
Measure with `/skill-doctor` (ships in CLI ≥2.1.261) and cut cost by progressive disclosure inside
a skill rather than by deleting skills. **Separately and confirmed by direct test 2026-09-07:** the
skill *catalog* has a description budget of roughly 19K chars, and skills past it render as bare
names with NO description — silently unroutable. Moving the 15 teammate-specific copilots to a
depth-2 subdirectory (out of discovery) dropped the catalog from 23,509 to 15,844 chars and
restored descriptions to `trivy`, `yq`, `zizmor` and 7 others — verified in a fresh session.

**Context-light screenshots (2026-08-20 vet).** When a
verification step only needs a rendered screenshot — not page interaction — prefer
`npx playwright-cli` (first-party Microsoft) over opening the in-app browser or Chrome
extension: both existing paths push page state into context, and context bloat is this
stack's one documented operational failure (the 51→2 plugin purge). npx-only, no standing
install, no MCP slot — so the hygiene policy can't be violated. Full-session browser
verification (read_page, form testing, console) still uses the existing browser tools.

## Efficiency patterns that compound with the three levers

- **Escalate on failure, not by default.** Send the first attempt to Sonnet; only re-run
  on Opus if a cheap check shows the Sonnet output is wrong or insufficient. Routing hard
  problems straight to Opus "to be safe" spends the escalation budget on tasks that never
  needed it. **Bug-fix briefs get a root-cause gate:** put "reproduce the failure before
  changing code; report the root cause alongside the fix" in the brief verbatim — a fix
  without a reproduction is a guess wearing a diff. If two fix attempts fail, the third
  dispatch is not another patch: escalate the model AND widen the ask to "is the
  architecture wrong?" — three failed fixes is a design signal, not a coding error.
- **Right-size the fleet.** Every extra subagent has a token floor (its own system prompt
  + tool schemas) before it produces a single token of useful work. Don't fan out to 10
  agents when 3 well-scoped ones cover it.
- **Spend the expensive judgment once, at the gate.** Keep the orchestrator's review/
  synthesis pass at the *end*, over final outputs — not sprinkled through every
  intermediate step. That's the one place Fable-tier judgment earns its cost: confirming
  the fleet's combined output actually matches what Fable would have produced directly.
  Skipping this gate to save tokens is a false economy — it's exactly how "efficient"
  quietly becomes "worse" without anyone noticing.
- **Two verdicts, not one.** When reviewing any delegated implementation, issue two
  separate verdicts: *spec compliance* (does it do exactly what the brief asked — no
  "close enough") and *build quality* (tests, patterns, no new debt). Both must pass
  before the task is marked done — a single fused "looks good" is how near-miss
  implementations ship. Issues mean a fix dispatch and re-review, never carrying the
  open issue into the next task. And never pre-bias the reviewer ("don't flag X," "at
  most minor") — let findings surface. Regression tests get a vacuousness check: a new
  test must be shown FAILING on the pre-fix code (throwaway worktree at the parent
  commit) before the fix passes review — paste the failing output; a test that passes
  pre-fix certifies nothing (live catch: f0fd921's regression test, 2026-07-15).
- **Query the code graph before reading files.** If the repo has a `graphify-out/`
  index (a production CRM does, since 2026-07-15), point subagents at `/graphify query` /
  `explain` / `path` instead of having each one re-grep and re-read the codebase — the
  graph answers "what calls X / where does Y live" for a fraction of the tokens, and
  the savings multiply across every agent in a fleet. Re-index after big code changes
  (`graphify extract . --code-only`); code-only mode is fully local, never sends
  anything anywhere.
- **Don't over-deliberate small fleets.** For 2-3 short, clearly-scoped subagent calls,
  apply the three levers as quick defaults (Sonnet, terse brief, one routing glance)
  rather than a deliberate per-lever pass — the full checklist earns its overhead at
  larger fan-out or higher-stakes subtasks, not on every two-agent errand.

## Decision table

| Task shape | Model | Why |
|---|---|---|
| Planning, architecture/priority decisions, taste or voice calls | Fable (orchestrator, no override) | the reason to run Fable at all |
| Reviewing and synthesizing subagent outputs into a final answer | Fable (orchestrator) | needs the full conversation's judgment |
| A task an installed skill/agent/MCP tool already covers | That skill/tool, not a raw prompt | pre-tightened, pre-scoped — cheaper than re-deriving |
| High-volume, low-judgment, inspection-verifiable work (bulk sweeps, mechanical edits, wide extraction) | `executor`/`researcher` (Sonnet-pinned), `effort` scaled to difficulty | genuinely mechanical — the one case where routing below the session tier is correct |
| Coding/building/research **in a session the owner set to a higher tier** | Match or exceed the session tier; override the agent type's pin via the `model` param, or keep the work in the main loop | the floor rule — a pinned Sonnet agent silently downgrades work the owner tiered up |
| Taste, brand, voice, strategy synthesis, priority/triage judgment | `model: "fable"` (+ high/xhigh effort), or the main loop if Fable is the session model | the upward path v13 never had; this is the work fable-judgment encodes |
| Frontier reasoning — novel architecture call, contested judgment, expensive-to-be-wrong audit | Highest reachable tier + `xhigh`/`max` effort; prefer the MAIN LOOP where the owner selects the model | under-set effort leaks quality as silently as an under-set model |
| Gnarly algorithm/debugging, security- or correctness-critical logic | Opus 5 | escalation for real depth needs |
| Adversarial verification / refutation / judge panel on a risky finding | `verifier` agent type (Opus-pinned), often several in parallel | independent strong judgment cuts false positives; the definition already carries the two-verdict method and rubric pointer |
| A subtask Sonnet already got wrong once | Opus 5 (or the `verifier` agent type if the ask is judgment) | escalation path, not a default |
| High-volume, near-zero-judgment mechanical work | Haiku (rare) or Sonnet | only drop to Haiku if the fleet is large enough for it to matter |
| A single quick lookup with no real fan-out | No subagent at all | fleet overhead isn't justified |
| A side-effecting action (push/deploy/send) the user already approved in this conversation | Sonnet, with the approval restated verbatim in the brief | subagent permission context does not inherit parent approval |
| Single mechanical step fixing a live production incident right now | No subagent — do it directly, state the exemption | delegation latency costs more than the task while impact is ongoing |
| A long-lived run (ship script, full suite, migration) that outlives a subagent turn | Orchestrator runs it as harness-tracked background work; delegate only the prep | a subagent's backgrounded process dies with its turn — the brief cannot prevent that |

*The pay-per-use footnote that used to sit here is retired (owner directive 2026-08-20):
the two Fable rows run on Fable, period. Escalation rows resolve to Opus 5 — never an
older Opus version.*

## When to fan out and fight — and when not to

Fleet patterns (parallel attempts, judge panels, adversarial critics, loops) are reserved
for specific task shapes — not a default:

- **Wide solution space** (design directions, briefs, naming, strategy): N independent
  attempts from *different angles*, then a judge panel — parallel diversity beats one
  attempt iterated.
- **High blast radius** (team distribution, deploys, irreversible ops): independent
  critic panel with different lenses + an adversarial verifier before ship — the builder
  reads its own diff generously. Corollary — release cadence: team distribution is
  batched, announced only on material value-add (owner rule 2026-07-16); increments
  accumulate silently in the next-release queue.
- **Unknown-size discovery** (bug hunts, audits, edge cases): loop-until-dry — keep
  spawning finders until 2 consecutive rounds surface nothing new. Never "loop until
  good": every loop needs a dry-out rule or a token budget as its stopping condition.
  **An errored or timed-out verifier is an OPEN finding, never a dead one** — re-dispatch
  it or surface it as unverified; "no confirmed findings" and "verification did not
  complete" must never collapse into the same report line. Precedent: two verifier agents
  errored in a motion-engine sweep, the synthesis filtered on `verdict.real && reachable`,
  and a defect then live in prod was reported clean (2026-07-20).
- **Routine, well-scoped execution**: one Sonnet agent + the final-pass gate. No debate
  club — every extra agent has a token floor before it produces anything useful.
- **Post-cutoff / viral factual claims** (news, model releases, vendor announcements the
  session model can't know): verify-before-opining — the structural read of the content
  ships immediately, the factual synthesis waits for researcher checks. Fan out by
  claim-cluster (one researcher per content piece/topic), never by lens; pre-load each
  brief with the numbered claims, candidate primary-source URLs, and an identical output
  contract (VERIFIED/PARTLY/UNVERIFIED/FALSE + 1-line evidence + URL, word-capped).
  Synthesis deliverable: claim-by-claim table (claim/verdict/reality+source), then
  per-piece narrative, then "what it means" actions. Extraordinary claims get an explicit
  kill-attempt brief ("if an event this large has zero credible coverage, mark it
  FALSE-or-garbled") — and if the check overturns the orchestrator's prior, the synthesis
  names the reversal out loud instead of silently absorbing it. Precedent: 3-researcher
  LI-content fact-check, 2026-08-02 — zero redundancy between researchers; the "Fable 5
  export-controls" claim survived its kill-brief and reversed the prior.

Two invariants: **diversity beats headcount** (3 differently-lensed checkers beat 10
clones — identical agents converge on the same plausible wrong answer), and **the gate is
unconditional** (the adversarial final pass below runs even when the task didn't warrant
a fleet).

## Gotchas — read before wiring a fleet

- **Context handoff is manual.** A subagent does not see the orchestrator's chain of
  reasoning — only what's written into its prompt. If Fable did analysis to decide *what*
  to build, that conclusion has to be explicitly restated in the subagent's prompt;
  "based on what I just figured out, build X" means nothing to a subagent with no memory
  of this conversation. Write subagent prompts as if briefing a colleague who just walked
  in cold — this is also step 1 of the compression pass above, not a separate concern.
  Corollary: if restating the necessary context would cost more than the task itself
  takes to do directly, that's a signal the task is too small to delegate — fold it into
  the right-sized-fleet judgment rather than delegating out of rule-following. This is a
  named exemption: use it out loud, never silently.
- **Subagent permission context is not inherited from the parent.** A push/deploy/send
  the user approved in the parent conversation is NOT automatically approved inside a
  delegated subagent — its permission classifier sees only its own brief. Observed live,
  both directions: a parent-loop push was denied as unauthorized until the user approved,
  and a subagent push succeeded because the approval was stated in its brief. So when
  delegating an already-approved side-effecting action, restate the approval explicitly
  in the prompt ("the user approved this push in the parent session"). And if a delegated
  push is denied for missing approval context, the fix is to restate the approval and
  re-delegate — NOT to fall back to doing it directly in the orchestrator, which
  reintroduces the exact reactive-inline failure this skill exists to prevent.
- **Exemption: live production incident.** If production is broken right now and the fix
  is a single mechanical step that would take longer to delegate-and-await than to
  execute, do it directly and say so explicitly ("skipping delegation — prod is down,
  one-line fix"). This applies only while impact is live — not to routine hotfixes done
  at leisure after the incident is contained. A named exemption stated out loud is
  discipline; a silent reabsorption is the failure mode.
- **An instruction to a subagent is a request, not a mechanism.** A subagent cannot be
  *made* to hold a process open: anything it backgrounds dies when its turn ends, and
  "run it in the FOREGROUND and wait for completion" is a request it may simply not
  honor. So long-lived runs — ship scripts, full test suites, migrations, multi-minute
  builds — are launched by the ORCHESTRATOR as harness-tracked work (Bash with
  `run_in_background`, which persists across turns and re-invokes on exit, plus a
  Monitor/poll loop; or a harness task), and only the *prep* (edits, staging, the diff,
  the go/no-go read) is delegated. Precedent: a delegated `ship_from_worktree.sh` was
  backgrounded and died with the subagent's turn (2026-07-16); the fix was a sharper
  brief, and the very next delegated ship backgrounded it anyway, said it would wait,
  ended its turn, and the run died silently mid-suite for 45 minutes (2026-07-17). A
  failure that survives its wording fix needs a structural fix, not better wording.
  **Second, harder mechanism — surfaced by the 2026-09-07 eval, not previously written down:**
  even a perfectly obedient subagent cannot honour "foreground and wait" for a 40-minute run,
  because a blocking Bash call is capped at 600000 ms (10 minutes). So the sharpened brief
  fails on two independent mechanisms, not one: the turn-death AND the call ceiling. Any
  "wait for completion" phrasing is therefore asking for something the tool contract cannot
  deliver — which is why the fix is orchestrator-owned background execution, full stop.
  (Two of three cold eval agents derived this ceiling unprompted; it is a fact about the tool,
  verifiable in the Bash tool's own timeout contract, not a model opinion.) Note
  this bounds the re-delegate rule in the permission bullet below: re-delegating is the
  right answer for a denied push, never for a run that keeps dying with the turn.
- **Shared/dirty worktree — set abort conditions before delegating a push.** If a repo
  has a concurrent agent on it (shared tree, branch switches from other sessions), the
  subagent's own status check can race the other agent between check and push. Put the
  expected base (branch/HEAD or "these N files are identical to origin/main") in the
  brief and instruct the subagent to abort and report — not push, not force-reconcile —
  if the tree or branch has moved out from under it.
- **Verifier panels are not read-only by default.** A verify/refute brief says "verify
  the claim," and competent agents verify by *executing* — reverts, restores, even
  mutation testing (swapping a `<button>` for `<span>`) — not by reading only; their
  restores are correct relative to their own start-of-panel snapshot, not relative to
  concurrent edits. ✅ **Frontmatter CAN enforce this — and there is a trap in testing it. MEASURED 2026-09-07.**
  `disallowedTools: Write, Edit, NotebookEdit` on `~/.claude/agents/verifier.md` DOES work: in a
  fresh CLI session the dispatched verifier reported `Write` absent from its tool list. Keep the
  field; it is a real structural safeguard, not decoration.
  ⚠ **The trap that nearly wrote the opposite into this file: AGENT DEFINITIONS RELOAD ON A LAG,
  so a just-edited agent is NOT the one you dispatch.** Sequence observed 2026-09-07, all harness
  signals (not self-reports): a newly created agent type returned `Agent type 'X' not found`
  while its file sat on disk; minutes later the harness announced "New agent types are now
  available"; and in between, probes of a just-edited `verifier` still showed the pre-edit
  behaviour. So the run's first two probes "measured" a verifier that had never loaded the
  restriction and concluded — wrongly — that the field does nothing. **Test any agent edit in a
  NEW session** (`claude -p --model sonnet` suffices), or wait for the harness to announce the
  reload. An immediate in-session probe of an in-session agent edit has zero falsifying power: it
  returns the same answer whether the field works or not. (Precision matters here — "frozen for
  the whole session" is ALSO wrong, and was this file's wording for about twenty minutes until
  the harness hot-registered the new agent and refuted it. Gate class 8, twice, on the same
  claim.)
  Defence-in-depth still applies, because a restricted agent keeps Bash: give each panel its own isolated worktree (Workflow `isolation:
  'worktree'` — it snapshots HEAD, so commit first if the state under review is
  uncommitted), or put an explicit STRICT READ-ONLY clause in the brief — and never edit
  or run tests/builds in a tree a panel currently holds; treat any panel-held tree as
  tainted for validation until the panel returns. Precedent (2026-08-02, a production
  bug-fix worktree): a panel's revert/restore experiments silently wiped an
  uncommitted fix made after the panel was dispatched, and a foreground pytest raced a
  mid-experiment revert to produce a phantom "1 failed + hang" on code that was actually
  fixed.
- **Plugin/config installs CANNOT be delegated, and cannot be scripted — MEASURED 2026-09-07.**
  Two independent walls, found by trying:
  (a) **A subagent categorically refuses relayed approval for configuration changes.** A dispatched
  `executor` with the owner's approval restated verbatim in its brief still declined, citing its own
  standing rule that no agent message constitutes user consent for config/settings/marketplace
  changes. This is CORRECT behaviour on its part and no rewording fixes it — the refusal is about
  the *channel*, not the phrasing. So the permission-bullet rule above ("restate the approval and
  re-delegate") does NOT apply to installs: re-delegating is the wording fix that cannot work, and
  the structural fix is that the ORCHESTRATOR executes, because only the main loop holds the
  owner's actual message. State that exemption out loud.
  (b) **`/plugin` is unavailable in `claude -p`** ("/plugin isn't available in this environment"),
  and `SearchPlugins` covers only the claude.ai org catalog — GitHub-marketplace plugins are not
  in it. So marketplace plugin installation is an INTERACTIVE-TERMINAL, OWNER-ONLY operation in
  this stack. Do not hand-write `installed_plugins.json` / `settings.json` to simulate it: that
  bypasses the installer's own validation and plugin state fails silently. Hand the owner the
  exact `/plugin` commands instead — 30 seconds of their time beats a corrupted manifest.
- **Keep the delegation ledger in the harness task list.** On the first delegation of a
  mechanical shape (commit+push, build+deploy, run+validate), create a task named
  `DELEGATE-SHAPE: <shape>`. Before executing any mechanical sequence yourself, check the
  task list; if a matching DELEGATE-SHAPE entry exists, delegation is mandatory, not a
  judgment call. This turns "was this shape delegated before?" from a memory feat into a
  lookup — mid-session context pressure is exactly when memory fails. The ledger carries
  *progress* too, not just shapes: on completing each delegated task, add an entry
  `PROGRESS: <task> — commits <base>..<head>, review clean|open`. After compaction or in
  any long session, trust the ledger + `git log` over memory — re-dispatching a task the
  ledger marks complete is the compaction failure mode, and "I remember doing that" is
  not evidence.
- **Token counting doesn't care about tiering.** Total token accounting aggregates across
  every model in the fleet. Routing to Sonnet or Opus changes the *cost ratio* (and
  usually the total, since cheaper/faster models are the point) — it does not make those
  tokens invisible to a budget target.
- **`effort` is a separate dial from `model`.** Reasoning depth is independent of which
  model runs the task — don't conflate "which brain" with "how hard should it think."
- **Don't let the orchestrator do the grunt work.** If Fable starts writing the
  implementation itself instead of delegating, the whole point of this setup is lost.
- **Reactive work is not exempt from the tiering test — this is the failure mode that
  actually happens.** Tiering gets applied to work planned at the *start* of a task and
  skipped on work that shows up in the *middle* of one: a bug found while already
  executing, a hotfix after a push, a follow-up correction. There's no natural "stop and
  reconsider" moment for those, so the reflex is to just fix it inline — which is exactly
  how a session ends up with one delegated subagent and five identically-shaped tasks
  done directly. Concrete case: pushing change A via an isolated worktree got delegated
  to a Sonnet subagent; discovering a bug in A ten minutes later and pushing the fix (B)
  — *the same worktree-commit-push shape* — got done by the orchestrator directly,
  because it arose mid-flow while already holding context. **Rule: before running more
  than ~2-3 tool calls yourself to execute a mechanical multi-step task (edit+commit+push,
  build+verify+deploy, run+validate a script), stop and ask "if this arrived as a fresh
  request, would I spawn a subagent for it?" If yes, delegate it now — mid-flow discovery
  and "I'm already holding the context" are not exemptions.**
- **Consistency within a session beats re-deriving the right call each time.** If a task
  shape has already been delegated once this session (e.g. "commit + push via isolated
  worktree"), delegate every later instance of that same shape too, even if it would be
  marginally faster to just do it yourself in the moment. Silently reabsorbing "just this
  once" is the inconsistency to catch — if unsure whether two tasks are "the same shape,"
  err toward delegating the second one.
- **A fleet-orchestrator skill load mid-session only governs what's left.** It cannot
  retroactively re-tier work already done earlier in the same conversation — that's
  expected, not a bug. But everything *after* the load, including small reactive
  follow-ups, is in scope and should get the same rigor as work planned from the start.

## Adversarial final pass — the paranoid gate before "done"

The skeptical read the orchestrator's quality gate performs, runnable by whoever holds
the loop (Sonnet included — run it on your own work). It exists because the builder wants
the work to be done and reads its own diff generously. Only failure classes shaped by
this user's actual history fire here; generic code review lives elsewhere. Each class:
**trigger → check → precedent**.

**Score every finding before reporting it.** Give each one a 0-100 confidence that it is real
and reachable in production, and **drop anything below 80** rather than reporting it hedged.
Parallel review agents generate false positives at a steady rate; a long list of maybes shifts
the filtering work onto the reader and trains them to skim the whole report — which is how a
real finding gets skimmed past. Say how many were dropped, so a suppressed-but-nagging finding
stays countable. (Convention adapted from Anthropic's official `code-review` plugin, reviewed
2026-09-07; a per-finding confidence filter is distinct from our effort dial, which sets
breadth.)

1. **Shared-state races.** Trigger: any commit/push/branch op in a repo with a known
   concurrent agent (a shared production repo: worktree-at-origin/main, shared tree,
   branch switches from other sessions). Check: re-run `git status` + `git log -1`
   immediately *before* push, not just at task start; if the tree or branch moved, abort
   and report — don't force-reconcile, don't fall back to inline. Precedent: a
   concurrent agent switching the shared tree's branch mid-session. Second trigger, same
   class: about to assert anything is merged, unmerged, on-main, or "a bug on main."
   Check: `git fetch` first — a local branch ref only advances on an explicit fetch/pull
   in that checkout, so it drifts behind `origin/main` by default and a stale read makes
   the claim confidently wrong. Precedent: a local `main` 2 commits stale reported live
   geo work as unmerged; a primary checkout's `main` 28 commits stale because all work
   happens in worktrees pushing straight to `origin/main` (both 2026-07-31).
2. **Deploy gates that fail silently.** Trigger: about to declare anything "deployed."
   Check: verify the gate condition explicitly (commit author email, branch protection,
   required checks) before equating "pushed" with "deployed." Precedent: a deploy
   platform silently skipped builds when the commit author wasn't an authorized
   email address — no loud failure, it just didn't deploy.
3. **Silent design regression via helpful defaults.** Trigger: editing any
   previously-reskinned surface (a marketing hub page, a deck-template system). Check:
   diff against the last *approved* state, not "looks fine in isolation" — copy-pasted
   sections, fallback styles, and template defaults reintroduce dead looks. Precedent: a
   deck reskin killed an approved header-band treatment; the lesson learned was "don't
   revert to the old default" precisely because a template default could bring it back.
4. **Irreversible ops dressed as routine.** Trigger: any merge/delete/dedupe/bulk-update
   path, even inside a "cleanup" feature. Check: answer "what does undo look like?" in
   writing before shipping — no answer means not shippable, even if nobody asked.
   Precedent: a production CRM's dedup-and-merge feature merges candidate records — a
   destructive op in a cleanup-feature costume.
5. **Claimed-done vs. verified-done.** Trigger: about to say "done," "fixed,"
   "deployed," "working." Check: name the artifact actually observed — screenshot, test
   output, query result, rendered page; if none exists, it isn't done. A verification step
   that ERRORED is not a pass — treat it as an open finding and say so. UI and deck work
   additionally require the render+screenshot bar (restart preview after template edits;
   qlmanage/PIL/PyMuPDF for decks). Precedent: the frontend-design-bar and
   deck-generation standards exist because "looks right in the diff" once shipped 92
   layout defects.
6. **The convenience rationalization.** Trigger: the thought "I'm already holding the
   context — faster to just do it myself." That thought IS the alarm, not a reason; it
   feels most convincing exactly when it's wrong — mid-flow, post-discovery. Check: "if
   this arrived as a fresh request, would I delegate it?", then check the task list for
   a matching DELEGATE-SHAPE entry — a match makes delegation mandatory. Mid-flow
   discovery is not an exemption; the named exemptions (live prod incident,
   context-transfer cost) must be stated out loud before acting. Precedent: push A was
   delegated; the identically-shaped hotfix push B ten minutes later was done inline —
   hardened as v2 the same day (2026-07-07).
7. **Fabricated proof.** Trigger: any user-facing surface carrying proof elements —
   testimonials, stat counters, client logos, case studies, accuracy/scale claims.
   Check: every proof element traces to a real artifact (a named client, a real metric,
   a genuine review) or carries an explicit "illustrative" label — otherwise cut it; a
   surface shipping invented proof is a brand liability wearing polish. Precedent: fake
   testimonials and "0k+" counters found LIVE on a live marketing homepage (2026-07-11
   triage), and a startup marketing site's "redacted SLA" card vetoed until a real
   engagement exists.

8. **Falsification, not corroboration — the evidence-grade gap (added 2026-08-21).**
   Trigger: about to record ANY claim as verified / measured / clean / done / consistent /
   installed. Check: name the single observation that would look DIFFERENT if the claim were
   FALSE, and confirm you actually made THAT observation — not a cheaper check that returns
   the same result whether the claim is true or false. A check with no falsifying power
   verifies nothing; it is the cheap check wearing the costume of the real one. Three shapes:
   (a) a SELF-REPORT as proof (a model's own model-id, a tool's own "success" message) — reads
   identical whether right or wrong, so it is a hint, never evidence; the falsifier is an
   external/harness signal. (b) a PARTIAL READ as proof of a WHOLE (read the code → claim
   runtime behavior; edit one line → claim the whole doc consistent) — the falsifier is
   running it, or re-reading the whole. (c) checking only the part you TOUCHED (added one eval
   case → claim the harness correct) — the falsifier is re-deriving what the edit's context
   depends on (here, the pass-bar). Precedent, all 2026-08-21 in one session: eval off-by-one
   (added the 13th case, left the bar "9/12"); a subagent self-report written into doctrine as
   "measured"; crawl4ai "no phone-home" from a code read that only a socket-BLOCKED run proved;
   the v14 self-contradiction (fixed one claim, left its twin 60 lines down). Unifying tell:
   the claim outran the evidence by exactly one step — the completing step. This is the
   evidentiary sibling of gate 6's convenience rationalization; both feel most convincing
   exactly when they are wrong, under context/time pressure.

This gate sits on top of the "spend the expensive judgment once, at the gate" pattern
above — it is the concrete checklist that step runs, not a replacement for it. Anchored
scoring scales and worked pass/fail examples live at `references/review-rubrics.md`
(kept as a separate file locally; embedded inline in the shared team copy so nobody else
gets a dangling reference). Design-shaped artifacts additionally run the `/design-judge`
protocol (render → lens panel → verdict, with proof-honesty and regression vetoes).

## Anti-patterns

- Defaulting every subagent to Opus "to be safe" — defeats the efficiency goal.
- **Reflexively routing to Sonnet because the skill once called it "the default."** In a session
  the owner tiered UP, that is a silent downgrade of their explicit choice (v14 floor rule).
- **Leaving `effort` at whatever it defaults to.** An under-set effort dial leaks quality exactly
  as silently as an under-set model — and nothing in the output announces it.
- **Assuming a dispatched subagent landed on the tier you asked for** — AND its mirror error,
  treating the subagent's own self-reported model id as proof that it didn't. Both are unreliable.
  A self-report is a hint; a harness/system notice is evidence. When the tier genuinely matters,
  put the work in the MAIN LOOP where the owner selects the model, instead of inferring from either.
- Spinning up a fleet for a task with no real fan-out — just do it directly.
- Treating Sonnet as fit only for trivial/mechanical work — it's the default *heavy*
  execution tier here.
- Compressing a prompt past the point of specificity — cutting so much context that the
  subagent has to guess, which reintroduces the exact wasted-exploration cost compression
  was meant to remove.
- Treating "autonomous routing" as license to skip confirmation on side-effecting actions
  — see the autonomy boundary above.
- Skipping the final orchestrator-quality gate to save a few tokens — the fastest way for
  "efficient" to quietly become "lower quality" unnoticed.
- Delegating a task once, then reflexively doing the next identically-shaped one yourself
  because it surfaced reactively (a bug, a hotfix, a follow-up push) instead of at the
  start of the session — the mid-flow version of a task gets the same tiering test as the
  planned version, every time, not just the first time.

## Enforcement — this file is advice; the hook is the backstop

Prose cannot self-enforce: every rule above depends on the model applying it at the
moment of action, and mid-flow context pressure is exactly when that fails. The optional
companion **delegation-guard hook** closes that gap deterministically: a non-blocking
`PreToolUse` hook on Bash (`~/.claude/hooks/fleet-delegation-guard.py`, wired in
`~/.claude/settings.json`) that detects commit/push/PR-shaped commands run by the main
loop and injects the core rule into context at the decision moment — including in
sessions where this skill was never loaded. It never blocks anything; subagents are told
to ignore it. If you received this skill without the hook, it works fine as prose-only —
ask Claude to "install the fleet-orchestrator delegation-guard hook" to add the backstop.

**The rest of the family.** The two hooks above are part of a five-hook enforcement
set, all shipped in this repo's `hooks/` and all wired in `~/.claude/settings.json`
(`examples/settings.json` has the complete block):

- `autoload-judgment` (SessionStart) — injects a judgment skill unconditionally.
- `fleet-delegation-guard` (PreToolUse/Bash) — deploy, long-run and package-install shapes.
- `skill-routing-guard` (UserPromptSubmit) — routes a prompt to the matching installed skill.
- `tool-routing-guard` (PreToolUse/WebFetch|WebSearch) — denies a docs-URL fetch once and
  allows the retry, rerouting to a docs MCP first. The only hook that denies a tool call.
- `retrieval-honesty-guard` (Stop) — blocks a turn asserting it cannot verify something
  when no retrieval actually ran in it.

A sixth pattern in the same family is worth building yourself and is deliberately not
shipped here, because it can only be written against your own provisioned services: a
`UserPromptSubmit` hook that scans the prompt for API-shaped asks (scrape/crawl, contact
enrichment, transactional email, TTS, LLM-gateway routing) and injects the matching
service in priority order, its env-var path, and an auto-use-vs-confirm-first flag, read
from a local service-routing map. Silent on no match; it reminds, and never fires a
side-effecting call itself. Build it on the same non-blocking contract as the others.

All five are exercised with negative controls by this repo's suite in `tests/` — run with
`python3 -m unittest discover -s tests` or `python3 -m pytest tests/` (59/59 as of
2026-09-08). The suite's own teeth were checked the way this file demands of any verifier:
a hook was deliberately gutted to return nothing on every input, and the suite failed on
exactly the "fires on match" assertions while the "stays silent" ones passed — which is
the signature the negative-control pairing exists to produce.

**External audit — `/insights`.** If your Claude Code CLI has this command, it analyzes
your recent usage and writes a report — a genuine outside check on whether the delegation
discipline above is actually holding, not just something you're trusting yourself to
remember. Prose plus a hook catches the moment of action; `/insights` catches the pattern
over time. Run it occasionally as a sanity check, not a replacement for either.
