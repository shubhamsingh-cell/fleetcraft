# Skill activation: measurement, containers, token economy

> Research brief, read-only session, 8 Sep 2026. Every claim below is tagged
> **[VERIFIED]** or **[PLAUSIBLE]**; untagged prose is analysis, not a fresh claim.

The measurement problem is solved — Claude Code ships a harness with a real control
arm, sitting behind one environment variable. The container problem is solved too: some
action-gating skills are the wrong shape for their job.

## The three things that change what you build

1. **Prefer the first-party harness to a bespoke one — with one caveat.**
   `claude plugin eval --ablation with-without` runs every case twice — with and without
   the plugin — and `tool_used: Skill` is a first-class grader. **[VERIFIED]** The gate is
   early-access; `CLAUDE_CODE_WALNUT_SPIRE=1` opens it. **Caveat, observed 2026-10-11:** on
   a machine authenticated by interactive login, the sandboxed run ended
   `partial: auth_failed` and scored nothing (see "A run that measured nothing" below).
2. **Action-gating skills aren't failing — they're mis-containered.** Anthropic's own
   shipped guidance says side-effect workflows should carry
   `disable-model-invocation: true` and be user-triggered. Skills are a knowledge
   container; nothing except a hook fires without model choice, and hooks cannot
   initiate. A PreToolUse deny hook is already the correct ceiling — a permission rule
   is a cleaner, surface-independent floor.
3. **`/skill-doctor` answers the token-economy question directly** — "which loaded
   skills go unused and what they cost in context, so you can prune them."

## Q1 — Measurement

### Yes — and it's first-party, sandboxed, and has a baseline arm

An earlier report of a broken skill-eval script (`skill-creator/scripts/run_eval.py`
in `anthropics/skills`) is real and unmerged since 2026-06-10 **[VERIFIED via `gh api`]**.
That script is not the platform's eval harness, and its breakage says nothing about the
harness that matters.

The real harness is `claude plugin eval`, a CLI subcommand. Its help text is explicit
about ablation **[VERIFIED — read from the shipped binary and `--help`]**:

> "Run a no-plugin baseline arm and report the score delta (none | with-without;
> default: with-without whenever a plugin resolves) — under with-without, graders
> marked with-only, incl. `tool_used: Skill`, are a plugin-fired indicator rather than
> part of the score."

#### The gate — measured live

It is early-access. In an empty temp directory:

```
$ claude plugin eval .
`plugin eval` is currently in early access

$ CLAUDE_CODE_WALNUT_SPIRE=1 claude plugin eval .
No eval cases found under /private/var/folders/...   # gate open, reached case discovery
```

Both commands run as shown, 2026-09-08. The statsig flag is `tengu_walnut_spire`; the
env var satisfying the same gate from a recent CLI build is **[PLAUSIBLE]**.

#### A run that measured nothing

Discovery is not execution. On 2026-10-11 (Claude Code 2.1.263) a real run of one case
(`--case math --runs 1 --ablation with-without`, `--no-publish`, `--max-cost-usd 1.00`)
**discovered and schema-accepted the case** — name, graders, arms and model all populated —
and then ended with `partial: true`, `partialReason: "auth_failed"`, `costUsd: 0`. The
sandboxed agent's own error was `exit 1: Not logged in · Please run /login`: the runner
starts each agent in a fresh config directory, so an interactive login on the host is not
inherited. **[VERIFIED — observed]**

Two consequences worth encoding in any suite you write:

- **Check `partial` and `partialReason` before reading any score.** The same JSON reported
  `overallScore: 0.5` for a run in which no agent ever executed.
- **A negative-control grader passes vacuously when nothing ran.** A `tool_used` grader with
  `min: 0, max: 0` ("must NOT call this tool") is satisfied by an agent that never started.
  Pair every negative control with an outcome grader that can only pass if the agent
  actually answered — here, a `regex` for the correct answer, which is why that run scored
  0.5 and not 1.0.

How to authenticate the sandbox (for example whether an API-key environment variable is
passed through) is **not documented** in the embedded reference, was **not attempted** here
— it would mean handing a credential to the harness and spending API money — and remains
open. Until it is resolved, treat these 12 cases as schema-valid and discoverable, not as
a measured activation rate.

#### The grader schema

Six grader types, from the authoring reference embedded in the binary **[VERIFIED]**. A
case is a directory under `evals/` with `prompt.md` + `graders/*.md`, or one
`case.yaml`.

| type | Required frontmatter | Scores by | Cost |
|---|---|---|---|
| `tool_used` | `tool`, `input_match`, `min`, `max`, `arm` | Whether a tool was called — this is the activation metric | Free |
| `regex` | `pattern`, `target`, `match` | Matching the final message / trace / files | Free |
| `tool_order` | `before`, `after` | Relative order of two tool calls | Free |
| `file_exists` | `path`, `exists` | A file created during the run | Free |
| `llm` | `focus`, `weight`; body = rubric | A judge model's verdict (default haiku) | Paid |
| `baseline` | `baseline_file`, `criteria` | Comparison against a recorded answer | Paid |

**The trap that costs a week:** omitting `arm:` on a `tool: Skill` grader makes it
**display-only** — dropped from the baseline arm, flagged `[with-only, not scored]`,
counted in neither numerator nor denominator. That is deliberate. Adding `arm:` starts
scoring a check the baseline can never pass and inflates measured uplift. The schema
rejects `weight: 0`, so omitting `arm:` is the mechanism. **[VERIFIED — binary +
trailofbits/skills `yara-authoring/evals/README.md`]**

Anthropic's own eval-authoring interview goes further: "Grade outcomes, not
trajectories… Do NOT make it the only grader for a case." For a publishable quality
number, pair `tool_used` with outcome graders. For the narrow question "did this skill
fire?", the display-only indicator (no `arm:`) is exactly right and is reported per run.

#### What practitioners actually use

Three real methods, in descending order of trust:

- **`claude plugin eval`** — sandboxed (isolated `.claude.json`, its own HOME and cwd
  under `/tmp`), `--runs` defaults to 3, `--json` gives per-run scores, `--threshold`
  exits 1 for CI. The isolation matters: the `goal-prompt` suite records that "before
  isolation, baselines that had read the skill off disk scored up to 1.00."
  **[VERIFIED]**
- **A Daytona-sandbox harness** (Scott Spence) — parses `claude -p --output-format
  stream-json` for `tool_use` blocks named `Skill`. 22 prompts × 5 hook configs × 2 runs
  on Sonnet 4.5, plus 24 adversarial edge cases, ~$5.59 total. **[VERIFIED — numbers
  below]**
- **UiPath `coder_eval`** — Apache-2.0, ~122 stars, actively pushed, has a literal
  `skill_triggered` criterion plus an A/B experiment layer and a CI gate. **[VERIFIED
  via `gh api`]**

#### The number that reframes a ~50% activation baseline

Spence measured activation across hook configurations. A plain UserPromptSubmit nudge
is his "simple" arm.

| Hook config | Run 1 | Run 2 | Latency | False positives on 5 non-matching queries |
|---|---:|---:|---:|---|
| none (control) | 55% | 50% | 8.7s | — |
| simple nudge | 59% | 50% | 8.6s | — |
| type-prompt | 55% | 41% | 9.6s | — |
| forced-eval | 100% | 100% | 10.7s | 0 — caught all 5 |
| llm-eval | 100% | 100% | 6.4s | 4 of 5 hallucinated |

Sonnet 4.5, 22 prompts per run. **[VERIFIED]** —
[scottspence.com](https://scottspence.com/posts/measuring-claude-code-skill-activation-with-sandboxed-evals).
Forced-eval makes the model state YES/NO per skill before it may implement; the
commitment step is what closes the gap. Spence's own conclusion: activation is keyword
matching, not semantic matching — "$state" hits every time, "my component re-renders
too much" misses entirely.

**Why not simply switch to forced-eval:** Spence ran 4 skills. A larger roster (dozens
of skills) makes forced enumeration — one YES/NO line per skill before every prompt — a
large, unbudgeted per-turn output tax on every trivial request. The honest
recommendation is to scope it: fire forced enumeration only over the handful of skills
that gate real actions, and only on prompts whose shape matches, then measure the
variant with the ablation harness rather than by intuition.

## Q2 — Containers

### Two premises about tool/skill containers are out of date

**"MCP tool (always in the tool list)" is no longer true.** Current Claude Code defers
tool schemas: `isToolSearchEnabled`, `deferredToolsCount`, `tool_search_tool_bm25` and
`ToolSearchDescriptionCache` are all present in the shipped binary **[VERIFIED]**, and
MCP tools arrive deferred by default. First-party framing: "Some of our tools are
'deferred loading,' which means the agent must search for their full definitions using
ToolSearch before using them." An MCP tool now costs a name until retrieved — cheaper
than assumed, but it also loses the guaranteed-visibility property that made it
attractive for must-fire work.

**Subagent `skills:` preload does what you'd hope, with one hard constraint.** It
"injects full skill content directly into a subagent's context at startup" and runtime
invocation stays available **[VERIFIED — code.claude.com/docs/en/sub-agents]**. The
constraint: skills with model invocation disabled cannot be preloaded. So
`disable-model-invocation: true` and `skills:` preload are mutually exclusive — a skill
cannot be locked to manual use and also force-fed to an agent.

### The decision rule

The organizing question is not "how important is this?" — it is **who decides that it
runs**.

| Capability shape | Container | Fires without model choice? | Always-on token cost |
|---|---|---|---|
| Knowledge the model should apply when relevant | Skill | No — model-selected (~50–55% baseline) | ~150 tok median (cap 1,536 chars) |
| Knowledge a specific delegated job must have | Subagent `skills:` preload | Yes, at agent startup — but spawning the agent is still model-chosen | 0 until spawn, then full body |
| An action with side effects (deploy, commit, publish) | Skill + `disable-model-invocation: true` | Never — user types `/name`. This is the documented intent. | ~150 tok |
| A precondition that must hold before an action | Hook (PreToolUse deny) | Yes — deterministic, but can only restrict, never initiate | 0 |
| A hard prohibition, surface-independent | Permission rule — `Skill(name)`, `Tool(param:value)` | Yes — declarative, not subject to hook matcher gaps | 0 |
| Capability the model should call mid-task | MCP tool | No — and now deferred behind ToolSearch | name only, until retrieved |
| A human-initiated procedure | Slash command | Yes — 100%, because a human typed it | shared budget |

**The lever that is often unused:** permission syntax now supports `Tool(param:value)`
"to match a tool's input parameters (with `*` wildcard), e.g. `Agent(model:opus)` to
block Opus subagents," and a later fix addressed "`Skill(name)` deny rules not covering
a nested skill listed as `<dir>:name`." **[VERIFIED — anthropics/claude-code
CHANGELOG.md via `gh api`]**

This matters because PreToolUse deny is *surface-dependent* (several tracked CLI
issues), and Grep/Glob don't exist as tools in `claude -p` at all. Permission rules are
evaluated by the permission system rather than a hook matcher, so they don't inherit
that class of gap. They cannot *force* a skill to run either — but for the half of a
guard that says "this must not proceed," a declarative rule is a sturdier floor than a
matcher pattern. Worth testing as belt-and-braces under a hook like
`skill-enforce-guard.py`, not as a replacement.

### Why action skills never fire — design intent, not a bug

The pattern (knowledge skills fire cold; action-gating skills never do, even with
rewritten task-first descriptions) matches Anthropic's stated design exactly. Shipped
guidance **[VERIFIED]**:

> "Both the user (`/<skill-name>`) and Claude can invoke skills by default. For
> workflows with side effects (e.g., `/deploy`, `/fix-issue 123`), add
> `disable-model-invocation: true` so only the user can trigger it."

And the container framing itself: "Think of skills as lightweight guides to let Claude
find information when needed… It's best when skills encode particular opinions,
knowledge, or best practices." **[VERIFIED —
claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models]**

Rewriting an action-gating skill's description to be task-first cannot fix this: the
model isn't declining it, it's the wrong shape for a container selected by relevance.
**Recommendation:** keep such skills for the *knowledge* half (how to use the tool),
move the *gate* entirely into the hook + permission layer, and stop paying listing
budget for a trigger that will not fire.

## Q3 — Token economy

### The "ruled out" conclusion holds at 1M context — and breaks in every subagent

The stated mechanism is confirmed exactly **[VERIFIED —
code.claude.com/docs/en/settings-reference]**: `skillListingBudgetFraction` defaults to
`0.01`; `skillListingMaxDescChars` defaults to `1536` and caps the *combined*
`description` + `when_to_use` text; on overflow Claude Code "drops the descriptions of
the least-used skills, so Claude can still invoke those skills but is less likely to
choose one on its own."

Two refinements worth keeping in mind. First, these are two independent failure modes —
the fraction budget overflowing (everything degrades to bare names) and the 1,536-char
per-entry cap truncating one fat description regardless of total budget. Different
causes, different fixes. Second, there is an escape hatch:
`SLASH_COMMAND_TOOL_CHAR_BUDGET` sets a raw character count and skips the fraction
calculation entirely **[VERIFIED]**.

#### Measured

Reading every `SKILL.md` and agent frontmatter and summing `description` +
`when_to_use` bytes, against stock `skillListingBudgetFraction` / `skillOverrides`
defaults and a 1M context window:

| Component group | n | Bytes | ≈ Tokens | Note |
|---|---:|---:|---:|---|
| User skills | 32 | 16,405 | 4,101 | — |
| Enabled-plugin skills | 2 | 1,650 | 412 | one plugin is 1,296 B alone |
| **Skills subtotal — the budgeted line item** | **34** | **18,055** | **4,513** | — |
| User agents | 4 | 1,008 | 252 | lean — 209–323 B each |
| Enabled-plugin agents + commands | 10 | 1,997 | 499 | — |

Only 4 plugins were installed and enabled per `claude plugin list`. Anthropic's own
projection via `claude plugin details` puts those 4 at ~833 always-on tokens total
**[VERIFIED]** — close to the 911-token byte estimate, which validates the ÷4
approximation.

**The finding that actually matters:** the budget is `1% × context`. At a 1M context
window that is 10,000 tokens against a 4,513-token roster — the "ruled out" conclusion
is correct for that session. But a 200K-context session gets 2,000 tokens — the roster
above is 2.3× over that. And a recent fix addressed a bug where `model: fable`-style
agents "ignor[ed] the `[1m]` tag… and silently ran with a 200K context window"
**[VERIFIED — changelog]**. Any subagent, any `claude -p` run, any CI invocation that
lands on a 200K context silently drops descriptions least-invoked-first.

**This produces a death spiral precisely where activation is weakest.** Skills like
`graphify`, `gitleaks`, and `design-judge` are by definition the least-invoked. They are
first against the wall when the budget overflows, which makes them less likely to be
chosen, which keeps them least-invoked. A ~50% activation figure averaged over many
sessions may be averaging two different regimes. **Before anything else, re-run that
measurement with the context window pinned** — otherwise the budget is being measured,
not the description.

#### The levers, ranked

1. **Run `/skill-doctor` first.** It shows which loaded skills go unused and what they
   cost in context. It needs an interactive session. **[VERIFIED — changelog]**
2. **`skillOverrides`, four states** **[VERIFIED]**: `on` (default) · `name-only` (name
   to the model, no description) · `user-invocable-only` (hidden from the model, `/name`
   still works) · `off` (hidden from both). `user-invocable-only` is the exact tool for
   action skills — it reclaims their description bytes while keeping the slash command.
   Hard limit: "Plugin skills are not affected by `skillOverrides`. Manage those through
   `/plugin` instead."
3. **Compress descriptions; delete examples.** Anthropic removed 80%+ of Claude Code's
   own system prompt "with no measurable loss on our coding evaluations," and the
   specific finding is that examples "actually constrain them to a certain exploration
   space" — actively harmful in a routing description whose whole job is recognising
   unfamiliar phrasings. **[VERIFIED]**
4. **Raise the fraction.** `"skillListingBudgetFraction": 0.02` costs ~10K tokens at 1M
   and buys headroom at 200K. Cheapest possible mitigation, one line.

#### Separate axis, bigger number: what a skill costs when it fires

Everything above is about *descriptions*, which are always-on. The other half of the
bill is the skill *body*, which loads on invocation. A recent changelog entry states,
verbatim: "Reduced the context cost of loading the built-in `claude-api` skill from
~200k+ tokens to ~25k by loading reference docs on demand." **[VERIFIED — CHANGELOG.md
via `gh api`]**

That is an 87% cut on Anthropic's own reference skill, achieved purely by splitting a
fat `SKILL.md` into a thin body plus `references/` loaded on demand. It costs nothing in
activation, because the description is untouched.

Measured on one real, privately maintained 34-skill roster. These are **not** the skills
shipped in this repository (the shipped `fleet-orchestrator` is ~12.9 KB), and the private
skills are labelled by role rather than name.

| Skill body (role) | Bytes | ≈ Tokens on invoke | Aux files |
|---|---:|---:|---:|
| orchestration / delegation policy | 64,127 | 16,031 | 1 |
| code-graph query | 38,358 | 9,589 | 9 |
| personal chief-of-staff workflow | 22,636 | 5,659 | 11 |
| SEO / AEO audit | 22,332 | 5,583 | 0 |
| design-review protocol | 16,321 | 4,080 | 1 |
| judgment / triage doctrine | 15,151 | 3,787 | 5 |

**The orchestration skill was the one to fix.** It carried a 64 KB body behind a single
aux file and governed every delegation decision, so it paid ~16,031 tokens each time it
fired, often. The SEO audit held 22 KB with zero reference files, so all of it was
inline. Both are the clearest instances of the exact pattern Anthropic fixed in their own
skill. **[measured read-only, 2026-09-08]**

#### What the big collections do

The answer is deflating: the famous ones aren't big. `anthropics/skills` ships 19 skill
directories; `obra/superpowers` ships 14 in core and pushes extras into a separate
opt-in marketplace **[VERIFIED via `gh api`]**. Reputation came from curation depth, not
breadth. The one genuinely large collection
(`alirezarezvani/claude-skills`) splits into ~78–83 separately-installable
domain-scoped plugins — and it has to, because a publisher *cannot* use
`skillOverrides` on their own plugin skills. Splitting is the only lever they have.

One worked example is a vendor teardown **[PLAUSIBLE — one vendor's self-reported
numbers, method described in detail and internally consistent]**: 29,260 → 2,498
always-on tokens, 91.5%. Its headline finding is worth checking against any roster —
the weight was in *agents*, not skills: 15,660 of 29,260 tokens (54%) from 31 agent
files, median skill description only 150 tokens. A lean, few-agent setup (roughly
250 tokens total across 4 agents) has already avoided this particular trap.

## Q4 — Sweep

### The best recent tooling improvements came from the changelog already on disk

The strongest candidates found while sweeping for third-party tooling are first-party
features shipped into the binary and not yet adopted into a working setup.

| Source | Stars | License | Pushed | The one idea worth taking | Verdict |
|---|---:|---|---|---|---|
| Claude Code (first-party) | — | — | installed | `/skill-doctor` — which loaded skills go unused and what they cost. Answers the token-economy question directly. | use now |
| Claude Code (first-party) | — | — | installed | `--safe-mode` starts with CLAUDE.md, plugins, skills, hooks and MCP all disabled — a true C0 control arm for an eval suite, with nothing uninstalled. | use now |
| Claude Code (first-party) | — | — | installed | `Tool(param:value)` + `Skill(name)` permission rules — declarative gating that sidesteps PreToolUse surface-dependence. | adopt-idea |
| Claude Code (first-party) | — | — | installed | `claude-api prompt-audit` — audits prompts and tool descriptions "for patterns written for older models." Points at the description-compression job directly. | adopt-idea |
| [UiPath/coder_eval](https://github.com/UiPath/coder_eval) | 122 | Apache-2.0 | 2026-09-07 | A `skill_triggered` criterion + A/B experiment layer + scheduled CI job, so a skill that quietly stops triggering fails a build. Cross-harness. | install-candidate |
| [trailofbits/skills](https://github.com/trailofbits/skills) | 7,006 | CC-BY-SA-4.0 | 2026-09-02 | The best public corpus of real `plugin eval --ablation` suites (19 `case.yaml` files, 42 plugins). Read their grader conventions before writing new ones. | adopt-idea |
| [spences10/svelte-claude-skills](https://github.com/spences10/svelte-claude-skills) | 220 | **none** | 2026-09-07 | The forced-eval hook: evaluate → commit → activate. 100% activation, zero false positives. | adopt-idea only |
| Claude Code (first-party) | — | — | installed | `archive` plugin source: install over HTTPS with optional SHA-256 pinning, no git or npm. A supply-chain-clean install path for a vendor-vet gate. | adopt-idea |

All star counts, licenses and `pushed_at` dates from `gh api repos/OWNER/REPO`, not
README badges. `spences10/svelte-claude-skills` has no license file, so the code is
all-rights-reserved: take the pattern, do not copy the script. Nothing in this table
uses a `curl|sh` installer or an unpinned `npx -y github:`. `coder_eval` installs via
pinned `uv tool install` / `pip`, never handles model credentials ("Coder Eval never
supplies model access"), and needs no third-party backend — but its usage telemetry is
on by default (anonymous; no prompts or file contents; disable with
`TELEMETRY_ENABLED=false`). Worth flagging for a vendor-vet gate rather than
auto-rejecting it.

#### Other first-party items worth a look

- `PreModelSwitch` / `PostModelSwitch` hook events — block, confirm or annotate a model
  switch. A natural home for a fleet-tiering policy that currently lives in a skill that
  must be chosen.
- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` — forces the subagent model over per-spawn *and*
  agent-definition overrides.
- `claude plugin validate --json` — machine-readable validation for a CI gate over a
  skill roster.
- Subagent caps: 20 concurrent, 200 per session, both overridable.

**Two first-party features that require an Enterprise plan:** inference hooks — a
server-side allow/deny verdict at the *inference* boundary, cryptographically signed,
structurally stronger than any local PreToolUse hook — and automated skill/plugin
security scanning. Both are Enterprise-plan beta and unavailable on Pro/Max accounts
**[VERIFIED locally]**. They are the only features found that genuinely break the
"hooks can only tighten, never force" ceiling.

#### Third-party, ranked

A breadth sweep surfaced further candidates; most are downgraded on re-verification: a
repo with 0–3 stars, 0 forks and 0 watchers is not an install candidate for a stack with
a vendor-vet gate, however good the README looks. The *ideas*, though, are worth taking.

| Repo | ★ | Forks | License | Pushed | The one idea worth taking | Verdict |
|---|---:|---:|---|---|---|---|
| [headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom) | 69,787 | 5,388 | Apache-2.0 | 2026-09-07 | Local, reversible compression of tool output before it reaches the model. Real adoption (7.7% fork ratio). But it sits between tools and the model — a lossy layer under a retrieval stack. | install-candidate — pilot only |
| [JeongJaeSoon/agent-guard](https://github.com/JeongJaeSoon/agent-guard) | 26 | 0 | MIT | 2026-09-07 | Intercept secrets at the tool boundary — before a `.env` read enters context — rather than at commit time. Strictly earlier than a commit-time gitleaks gate. | adopt-idea |
| sjgant80-hub/konomi-ablate | 0 | 0 | MIT | 2026-08-08 | **Joint ablation.** Leave-one-out alone is unsound when two clauses cover for each other — each then looks individually removable. Directly applicable to a multi-case eval and to pruning skill descriptions. | idea only — created and abandoned same day |
| YauheniPo/aissert | 1 | 0 | MIT | 2026-08-03 | **Judge-drift canaries.** Control arms test the system; nothing tests whether the judge has drifted. A real hole in most evals. | idea only |
| hamodywe/skillsonar | 1 | 0 | MIT | 2026-08-11 | Deterministic offline detection of description collisions between skills — no model sampling, so no flakiness. At dozens of skills, collisions exist; this is a day of work to write. | idea only — see typosquat note |
| Edmonds-Commerce-Limited/claude-code-hooks-daemon | 3 | 0 | MIT | 2026-09-07 | Persistent socket daemon instead of per-invocation hook scripts: hot-reload without a session restart. Fixes the real pain of iterating on a hook family. | idea only — architecture change, no adoption |

**Vendor-vet finding — a live typosquat.** A second repo named `skillsonar` exists under
an auto-generated-looking username, created one day after the original, same name and
concept, zero stars. Neither should be installed regardless of which idea is taken.
Separately, the sweep found a wave of same-day 0-star repos wearing a
`claude-code-hooks`-style topic tag with near-identical AI-generated descriptions,
including one outright pirated-software lure. Topic tags are being gamed — a durable
lesson worth a line in a vendor-vet gate.

**Rejected outright:** `MikkoParkkola/glyphdown` and `mherod/swiz` — both PolyForm
Noncommercial, unusable for commercial work regardless of merit. `Jwuthri/Tracely-ai`
(1,217★, MIT) — good idea (promote production failures into hermetic CI regression
cases) but self-hosting demands Postgres + ClickHouse + Redis + MinIO + API + worker +
UI, which fails a mandatory-backend rule. `Emasoft/perfect-skill-suggester` — ~703 MB
repo shipping stray `.trashcan/` dirs; hygiene reject. `ruvnet/ruflo` (71,313★) — a whole
competing orchestration framework, lateral not upward.

## Dead ends and what was not covered

- **Unresolved:** a session's skill count as reported by the client UI and the plugin
  count as reported by `claude plugin list` can diverge if a client supplies and locks
  its own session components. This was not reconciled read-only, so the 4,513-token
  skills figure above is a floor, not necessarily the total for every session. If a
  client-supplied set adds another ~4–6K tokens, a roster may be near or over the
  10,000-token budget even at 1M context — which would move the Q3 conclusion.
  `/skill-doctor` settles this in one command.
- **Not verified: no first-party skill-count ceiling exists.** Anthropic's framing runs
  the other way — "Claude uses it to choose the right Skill from potentially 100+
  available Skills." There is no documented maximum, and "router/dispatcher" appears
  nowhere in first-party skills docs. A dispatcher-style skill is a community-shaped
  convention, not a documented mitigation.
- **Not verified: two widely-repeated claims could not be stood behind.** A claim that
  40 of 47 tested skills "made the output worse" could not be traced to its original
  source. A claim of an "MCP study shows 3.6× selection rate improvement" from
  front-loading trigger keywords cites no actual study; treat as marketing copy.
  Neither is load-bearing here.
- **Not covered:** `claude plugin eval` was not run against any live skill roster —
  this was a read-only session; the harness spends money and writes a results
  directory. The forced-eval hook was not measured at scale (the 100% figure above is
  Spence's, on 4 skills); the scoping caveat for larger rosters is reasoning, not
  measurement. `VoltAgent/awesome-agent-skills`, `ComposioHQ/awesome-claude-skills`, and
  `ruvnet/RuView` were not verified — high star counts, but it could not be confirmed
  whether they are real installable rosters or link-lists. The Agent SDK's programmatic
  skill-invocation APIs and org-level `skillOverrides` via managed settings were not
  examined. The ÷4 bytes-per-token conversion is an approximation; it agreed with the
  first-party `plugin details` projection to within ~9% on the one sample
  cross-checked.
- **Caveat: don't read the star counts as a quality signal.** Every star count came
  from `gh api repos/OWNER/REPO`, not a badge, but several are implausibly large for
  the category. Fork-to-star ratios are consistent with organic growth (6–15%), so
  they're reported as the API returned them rather than dismissed — but metadata alone
  can't rule out inflation, and star count was not used as a ranking input. The ranking
  above is by fit; where a repo has 0–3 stars that is stated and downgraded, because
  absence of adoption is itself information for a vendor-vet gate.

### If you do four things

1. **Split a large skill body (e.g. `fleet-orchestrator`'s 64 KB body) into a thin body
   plus on-demand reference files.** Biggest measured number in this brief, ~16,031
   tokens every time such a skill fires, on a skill that can fire constantly. The
   recent first-party `claude-api` fix is the template. This is independent of every
   activation question and pays immediately.
2. **Run `/skill-doctor`** in an interactive terminal. It settles the roster-size
   question and names unused skills — the input to every other decision here.
3. **Set `skillOverrides` to `user-invocable-only`** for action skills that provably
   never fire, and pin the context window before re-measuring anything.
4. **Build one eval case per must-fire capability** —
   `CLAUDE_CODE_WALNUT_SPIRE=1 claude plugin eval . --ablation with-without --runs 3`,
   using `tool_used: Skill` with `arm:` omitted, alongside one outcome grader.

---

Compiled 8 September 2026 from the shipped Claude Code binary, `gh api`, and
first-party Anthropic documentation. Every repository fact was read from the GitHub API
rather than a README badge. Local measurements were run read-only; nothing was
installed and no configuration was changed.
