# hooks

<!-- DRAFT copy — final copy pass pending -->

Five Claude Code hooks that implement the same underlying pattern:
**non-blocking context injection**. Four of the five never deny, block, or
modify a tool call — they run at a specific point in the session lifecycle,
look at what's about to happen, and, only on a match, print a small JSON
payload that gets appended to the model's context as a reminder. On no
match, or on any internal error, they stay completely silent and exit 0.

The fifth, `tool-routing-guard.py`, is the family's one deliberate
exception: on a narrow, near-deterministic match (a documentation URL) it
actually denies the first matching call in a session, rather than just
reminding. That departure is scoped as tightly as possible — see its own
section below for why a reminder wasn't enough there and everywhere else it
still is.

This pattern exists because prose guidance (a skill's `SKILL.md`) cannot
self-enforce: a rule written in a skill file only works if the model happens
to recall and apply it at the exact moment of action, and that's precisely
when context pressure and mid-flow momentum cause rules to get silently
skipped. A hook closes that gap deterministically — it fires on every
matching tool call, prompt, or turn-end, in every session, whether or not
the companion skill was ever loaded.

Design rules every hook here follows:

- **Default to silence.** No match → no output, ever. A hook that "cries
  wolf" on unrelated calls gets ignored (or worse, gets uninstalled) —
  silence on the common case is what keeps the rare, real reminder
  credible.
- **Never block — with exactly one named exception.** Four of the five
  hooks are reminders, not gates: a false positive costs nothing but a few
  tokens of injected context, and a hook that blocks on a false positive
  breaks the session. `tool-routing-guard.py` blocks once, on one narrow
  shape, specifically because a reminder measurably wasn't moving the
  number it exists to move (see its section below) — every other match in
  every other hook stays reminder-only.
- **Fail toward reminding or toward silence, depending on the stakes.** A
  hook whose job is to catch a rare but expensive failure (a silently-dead
  deploy gate) fails LOUD on a parse error, so a broken hook is visible
  rather than indistinguishable from "nothing to flag." A hook whose job is
  a high-frequency nudge (page-by-page web fetching, an unverified claim)
  fails SILENT on error, because the cost of a missed nudge is one skipped
  reminder, and the cost of noisy failure on a frequent trigger is the
  whole hook getting ignored. Each section below states which contract that
  hook uses.
- **Tell subagents to ignore what doesn't apply to them.** Some reminders
  (e.g. "delegate this to a subagent") only make sense for the main
  orchestrator loop; a dispatched subagent executing its own delegated
  brief is told explicitly to disregard that class of reminder.

## The five hooks

### `autoload-judgment.py` — `SessionStart`

```json
{
  "SessionStart": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "python3 ~/.claude/hooks/autoload-judgment.py",
          "timeout": 10
        }
      ]
    }
  ]
}
```

**Matches:** every new session, unconditionally — there is no filter to
match, it fires on `SessionStart` every time.

**Blocks or injects:** injects only. Reads a companion skill file's body
(minus its YAML frontmatter and any changelog/version-history block) and
puts it into the new session's starting context automatically. This exists
to solve a specific problem: some judgment or taste guidance is meant to
apply regardless of which model is driving a session, but a skill can only
be *auto-loaded* by the harness under specific routing conditions — there's
no way for a skill to detect "the session is running on a
lower-context-budget model, inject me unconditionally." A `SessionStart`
hook sidesteps that entirely: it doesn't try to detect anything, it just
always injects.

**Kill-switch / config surface:** none as an env var — the extension point
is the `SKILL` path constant at the top of the file, which you point at
whatever companion skill file you want auto-loaded every session (the path
shipped here is illustrative). The frontmatter- and changelog-stripping
logic is deliberately conservative: if the source file's shape ever changes
unexpectedly (no `# ` heading, no `## ` section, a changelog block that
isn't a clean blockquote), the hook falls back to injecting the *entire*
untouched body rather than risk silently serving a mutilated version of the
guidance. It fails toward more context, never less.

### `fleet-delegation-guard.py` — `PreToolUse` (matcher: `Bash`)

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "python3 ~/.claude/hooks/fleet-delegation-guard.py",
          "timeout": 10
        }
      ]
    }
  ]
}
```

**Matches:** every `Bash` tool call, filtered by regex against the command
string, into three shapes:

1. **Deploy-shaped commands** (`git commit`/`push`, `gh pr create`, a
   deploy CLI invocation, a webhook POST) — reminds the main loop that
   mechanical multi-step execution should generally be delegated to a
   subagent, unless a named exemption applies and is stated out loud.
2. **Long-lived runs** (a ship script, a full test suite, a multi-minute
   build/migration) — reminds in the *opposite* direction: these should
   **never** be delegated to a subagent, because a subagent's backgrounded
   process dies when its turn ends and no amount of careful prompt wording
   prevents that. This shape gets the sharper warning because it's the one
   that fails silently and expensively if gotten wrong.
3. **Package-installing commands** (`npm install <pkg>`, `pip install
   <pkg>`, `brew install`, etc. — added after a 2026-08-27 audit found the
   vendor-vet skills had zero invocations in 30 days despite being
   installed) — reminds that a package-bearing install should go through
   the vendor-vet gate first. Deliberately excludes a bare lockfile restore
   (`npm install` with no package name, `pip install -r requirements.txt`)
   so routine dependency restores stay silent.

Subagent detection on the deploy-shaped branch is asymmetric on purpose: a
subagent executing a delegated deploy-shaped command is the *intended* end
state, so it gets a much shorter reminder (just a secrets-preflight nudge);
a subagent running a long-lived command is itself the bug, so that branch
nags hardest regardless of caller.

**Blocks or injects:** injects only, on all three shapes.

**Kill-switch / config surface:** none. On a payload it cannot parse, it
does not go silent — see the fail-loud contract above — it emits a
"shape detection did not run, treat this as unchecked" notice instead, so a
broken hook stays visible rather than silently guarding nothing.

### `skill-routing-guard.py` — `UserPromptSubmit`

```json
{
  "UserPromptSubmit": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "python3 ~/.claude/hooks/skill-routing-guard.py",
          "timeout": 10
        }
      ]
    }
  ]
}
```

**Matches:** the incoming user prompt (plus, for one category, the current
working directory), scanned for a small number of tightly-scoped task
shapes: tabular-file analysis, office-document extraction, a
share/export/publish action, a "is this ready to ship" design question, a
message being drafted for an audience outside the current session, a
library/API documentation question, a codebase-structure question in a repo
that already has a `graphify-out/` index, and lesson-capture phrasing
("turn this into a lesson", "so we don't hit this again"). On a match, it
reminds the model which installed skill or convention to route through
instead of solving the problem ad hoc.

Every file-shaped category requires **two independent gates** — an intent
verb *and* an unambiguous object (a file-extension token, an audience
phrase, a design-surface noun) — specifically to avoid false-firing on
ordinary code discussion that happens to mention a filename or a person's
title. A cheap "this looks like source code" suppressor further vetoes
matches that are really about existing code rather than a local
data/document file; the library-docs and graphify categories deliberately
skip that suppressor because their trigger language is inherently
code-shaped, and vetoing on code signals there would suppress every true
positive.

**Blocks or injects:** injects only, on any of the nine categories.

**Kill-switch / config surface:** none. Default to silence is the same
governing principle as the rest of the family: a missed reminder costs
little, a hook that fires on unrelated prompts trains the user to ignore
it.

### `tool-routing-guard.py` — `PreToolUse` (matcher: `WebFetch|WebSearch`)

```json
{
  "PreToolUse": [
    {
      "matcher": "WebFetch|WebSearch",
      "hooks": [
        {
          "type": "command",
          "command": "python3 ~/.claude/hooks/tool-routing-guard.py",
          "timeout": 10
        }
      ]
    }
  ]
}
```

**Matches:** every `WebFetch`/`WebSearch` call, into three nudge classes,
each firing at most once per session (tracked by marker files keyed on
session id):

- **`websearch-alternatives`** — any `WebSearch` call: reminds that
  registered search MCPs return structured results with page content in
  one call, skipping the search-then-fetch round trip.
- **`docs-url-context7`** — a `WebFetch` whose URL looks documentation-shaped
  (`docs.*`, `/docs/`, `readthedocs`, MDN, `/reference/`, …): reminds (or,
  see below, enforces) that a docs MCP serves current, version-pinned
  library docs without page-by-page fetching.
- **`page-by-page-firecrawl`** — the 3rd+ `WebFetch` this guard has itself
  observed in the session: reminds that a multi-page crawl/extract tool
  covers a site in one call instead of N.

**Blocks or injects — this is the one deliberate exception in the family.**
`websearch-alternatives` and `page-by-page-firecrawl` are reminder-only,
same contract as every other hook here. `docs-url-context7` is different:
the **first** docs-shaped `WebFetch` in a session is **denied** outright,
with the rerouting instructions in the denial reason, rather than merely
reminded past. This exists because the reminder-only version of this exact
nudge was measured and found not to work: an audit over 30 days found
roughly 2 calls to the documentation MCP against ~1,083 built-in web calls,
i.e. the reminder was being read and not acted on. A deny can promise a
compliance rate; a reminder cannot. The mechanism is narrow and
self-healing by design: the marker that causes the deny is written before
the deny is returned, so if the docs MCP genuinely doesn't cover the page,
simply re-issuing the identical `WebFetch` passes automatically — worst
case is one denied call per session, never a dead end. This is deliberately
**not** generalized to `WebSearch` or the page-by-page class: forcing those
would misfire on legitimate single lookups, where the "correct alternative"
isn't as close to deterministic as "library docs → docs MCP."

**Kill-switch / config surface:**
- `CLAUDE_TOOL_ROUTING_ENFORCE=0` downgrades the `docs-url-context7` deny
  back to a reminder — the escape hatch for the family's one blocking path.
- `CLAUDE_TOOL_ROUTING_STATE_DIR` overrides where the once-per-session
  marker files live (defaults under the system temp dir); mainly useful for
  running this hook's self-test in isolation from a real session's state.

**Error contract:** silent on any internal error, exit 0 — same choice as
the other reminder-only hooks, not the fail-loud choice of the delegation
guard. This hook's worst failure mode is crying wolf across a long research
session, and a missed nudge costs one reminder, not a silently-dead deploy
gate.

### `retrieval-honesty-guard.py` — `Stop`

```json
{
  "Stop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "python3 ~/.claude/hooks/retrieval-honesty-guard.py",
          "timeout": 10
        }
      ]
    }
  ]
}
```

**Matches:** the assistant's own final turn text, scanned for
unverifiability tells — "past my cutoff," "I can't verify/confirm/check,"
"as of my last training," "without access to the internet," and similar
phrasing — walked back only to the start of the current turn (the last real
user message), not the whole transcript. A match only counts if **no**
retrieval tool (a docs MCP, a search/crawl MCP, `WebSearch`/`WebFetch`, a
dispatched research subagent, or a Bash/Skill call whose payload invokes a
retrieval CLI) ran anywhere in that same turn.

**Blocks or injects:** blocks — but only the turn's stop, and only once.
This is a `Stop` hook, not a `PreToolUse` hook, so there is no tool call to
deny; instead it returns `{"decision": "block", "reason": ...}`, which
sends the assistant back with instructions to actually run the retrieval
ladder before finishing. It checks the harness's own `stop_hook_active`
flag first and returns immediately if set, so it can never loop the turn
twice, and it writes a marker keyed on `session_id` + the flagged text so
even a re-run of the same response can't ping-pong. In the family's
terms this reads as a second blocking path, but it is a much softer one
than `tool-routing-guard`'s deny: it never stops a tool from running, only
asks the model to redo the last step of its own turn once.

**Kill-switch / config surface:** none by env var. The safety net here is
architectural rather than a flag: it **fails open on every error** —
`json.loads` failures, a missing transcript path, any exception anywhere in
`main()` — via a top-level `try/except` that always `sys.exit(0)`s. The
docstring states this as the design contract explicitly: "a guard that
crashes must never wedge a session."

## Wiring these in

Copy the five files into `~/.claude/hooks/`, then register each one under
the matching event in `~/.claude/settings.json` using the snippets above
(`SessionStart`, `PreToolUse` scoped to `Bash`, `UserPromptSubmit`,
`PreToolUse` scoped to `WebFetch|WebSearch`, and `Stop`). Multiple hooks on
the same event merge into that event's array rather than replacing it — see
`fleet-delegation-guard.py` and `tool-routing-guard.py` above, which both
register under `PreToolUse` with different matchers.

Adjust the hardcoded skill/reference paths inside each script to match
wherever you've installed the companion skills in this repo — the paths
shipped here assume the standard `~/.claude/skills/...` layout described in
the top-level README. `tool-routing-guard.py` and `retrieval-honesty-guard.py`
additionally assume `context7`, `tavily`, and `firecrawl` MCP servers are
registered; without them, their reminders still fire but point at tools
that aren't there, so either register those MCPs or edit the message text.
