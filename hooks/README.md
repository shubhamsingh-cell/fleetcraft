# hooks

<!-- DRAFT copy — final copy pass pending -->

Three Claude Code hooks that implement the same pattern: **non-blocking
context injection**. None of these hooks ever deny, block, or modify a tool
call. Each one runs at a specific point in the session lifecycle, looks at
what's about to happen, and — only on a match — prints a small JSON payload
that gets appended to the model's context as a reminder. On no match, or on
any internal error, every hook stays completely silent and exits 0.

This pattern exists because prose guidance (a skill's `SKILL.md`) cannot
self-enforce: a rule written in a skill file only works if the model happens
to recall and apply it at the exact moment of action, and that's precisely
when context pressure and mid-flow momentum cause rules to get silently
skipped. A hook closes that gap deterministically — it fires on every
matching tool call or prompt, in every session, whether or not the
companion skill was ever loaded.

Design rules every hook here follows:

- **Never block.** These are reminders, not gates. A false positive costs
  nothing but a few tokens of injected context; a hook that blocks on a
  false positive breaks the session.
- **Default to silence.** No match → no output, ever. A hook that "cries
  wolf" on unrelated calls gets ignored (or worse, gets uninstalled) —
  silence on the common case is what keeps the rare, real reminder
  credible.
- **Fail toward reminding, not toward hiding.** If a hook can't parse its
  input payload, it still emits something (usually a note that shape
  detection didn't run) rather than going silent — a hook that fails
  silently is indistinguishable from a hook that saw nothing worth
  flagging, and would stop guarding forever without anyone noticing.
- **Tell subagents to ignore what doesn't apply to them.** Some reminders
  (e.g. "delegate this to a subagent") only make sense for the main
  orchestrator loop; a dispatched subagent executing its own delegated
  brief is told explicitly to disregard that class of reminder.

## The three hooks

### `autoload-judgment.py` — SessionStart

Reads a companion skill file's body (minus its YAML frontmatter and any
changelog/version-history block) and injects it into every new session's
starting context automatically. This exists to solve a specific problem:
some judgment or taste guidance is meant to apply regardless of which model
is driving a session, but a skill can only be *auto-loaded* by the harness
under specific routing conditions — there's no way for a skill to detect
"the session is running on a lower-context-budget model, inject me
unconditionally." A `SessionStart` hook sidesteps that entirely: it doesn't
try to detect anything, it just always injects.

The frontmatter-stripping and changelog-stripping logic is deliberately
conservative — if the source file's shape ever changes unexpectedly (no
`# ` heading, no `## ` section, a changelog block that isn't a clean
blockquote), the hook falls back to injecting the *entire* untouched body
rather than risk silently serving a mutilated version of the guidance. It
fails toward more context, never less.

Point `SKILL` at whatever companion skill file you want auto-loaded every
session; the path in this repo's copy is illustrative.

### `fleet-delegation-guard.py` — PreToolUse (Bash)

Watches every Bash tool call for two shapes:

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

Subagent detection is asymmetric on purpose: a subagent executing a
delegated deploy-shaped command is the *intended* end state, so it gets a
much shorter reminder (just a secrets-preflight nudge); a subagent running
a long-lived command is itself the bug, so that branch nags hardest
regardless of caller.

### `skill-routing-guard.py` — UserPromptSubmit

Scans the user's incoming prompt for a small number of tightly-scoped task
shapes (tabular-file analysis, office-document extraction, a
share/export/publish action, a "is this ready to ship" design question, a
message being drafted for an audience outside the current session) and, on
a match, reminds the model which installed skill or convention to route
through instead of solving the problem ad hoc.

Every category requires **two independent gates** — an intent verb *and*
an unambiguous object (a file-extension token, an audience phrase, a
design-surface noun) — specifically to avoid false-firing on ordinary code
discussion that happens to mention a filename or a person's title. A cheap
"this looks like source code" suppressor further vetoes matches that are
really about existing code rather than a local data/document file. Default
to silence is the same governing principle as the other two hooks: a
missed reminder costs little, a hook that fires on unrelated prompts trains
the user to ignore it.

## Wiring these in

Copy the three files into `~/.claude/hooks/`, then register each one under
the matching event in `~/.claude/settings.json` (`SessionStart`,
`PreToolUse` scoped to the `Bash` tool, and `UserPromptSubmit`
respectively). Adjust the hardcoded skill/reference paths inside each
script to match wherever you've installed the companion skills in this
repo — the paths shipped here assume the standard `~/.claude/skills/...`
layout described in the top-level README.
