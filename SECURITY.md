# Security

This repo ships Python you install into an AI agent's tool-call path and
markdown you let an agent load into its own context. Both are more
consequential than typical config, and this page is about that, not a
boilerplate disclosure policy.

## Threat model

**Hooks run in your shell, with your privileges, on every matching tool
call.** A `PreToolUse` hook wired to `Bash` sees (or can see) the command
about to run; a `SessionStart` hook runs the moment a session opens. These
are ordinary Python scripts with no sandboxing beyond what your OS gives
any process you launch — they can read your filesystem, make network
calls, and do anything else your user account can do. Installing a hook
from this repo (or any repo) means trusting that script the same way you'd
trust a shell alias or a cron job you didn't write yourself: completely,
because it runs unattended, repeatedly, and by default without asking.

**Skills are instructions injected into an agent's context, and can
therefore steer its behavior.** A `SKILL.md` file isn't executable code,
but it's read by the model and can shape what the model decides to do
next — including, in principle, talking it into running something it
otherwise wouldn't. This repo's skills are prose about judgment (model
tiering, design review, verification discipline); they don't tell an agent
to fetch and run remote scripts or exfiltrate data. But you should verify
that for yourself rather than take a README's word for it, and you should
apply the same read-before-you-trust standard to anything else you load
into an agent's context, from this repo or elsewhere.

**The realistic bad case is not "this repo is malicious."** It's a
subtler one: a hook with a bug that fires on the wrong input, blocks a
tool call it shouldn't, or leaks something into context it shouldn't (a
file path, an env var, a fragment of a command) because an edge case
wasn't handled. That's a correctness bug with security-shaped
consequences, and it's the class of thing `scripts/validate.py` and the
fail-open contract in `hooks/README.md` are built to catch and bound —
not a substitute for reading the code yourself.

## Before you install anything from this repo

- **Read every hook before installing it.** Each one is a few hundred
  lines of plain Python; that's a deliberately small amount to read.
  `hooks/README.md` documents what each one matches, whether it can block
  a tool call (most can't — see below), and its kill-switch/config
  surface if it has one.
- **Prefer `scripts/install.sh --dry-run` first.** It prints exactly what
  would be copied where, and what would be backed up, without writing
  anything. Run the real install only once you're satisfied with what it
  says it will do.
- **`scripts/install.sh` never touches `~/.claude/settings.json`.** It
  prints the JSON block you'd need to paste in yourself, on purpose —
  see that script's own header comment for why a script-driven merge into
  your live settings file is a worse idea than a human doing it.

## Hooks fail open, by design and by default

Every hook here is written to fail open: on a parse error, malformed
input, or any unexpected condition it exits 0 rather than erroring your
turn or denying a tool call. A hook that crashes or hangs instead would
wedge a real session — a worse outcome than a missed reminder.

"Fail open" means *never deny on error*, which is not always the same as
staying silent. `fleet-delegation-guard.py` deliberately emits a short
"shape detection did NOT run — treat this as an unchecked call, not a
cleared one" reminder when it cannot read a payload, precisely so a guard
that has quietly stopped guarding is visible instead of invisible. It still
exits 0 and still denies nothing.

**Two hooks have a blocking path**, and both are documented where they
live rather than left for you to discover:

- `tool-routing-guard.py` denies a documentation-URL fetch *once* and
  allows the immediate retry, so the worst case is one extra round trip,
  never a dead end. It has a kill-switch env var that downgrades the deny
  to a plain reminder.
- `retrieval-honesty-guard.py` blocks a *turn's stop*, not a tool call,
  when the turn asserts it cannot verify something and no retrieval
  actually ran. It never loops: the harness's own re-entry flag short
  circuits it on the second pass.

The other three never deny, block, or modify anything — they only inject
text. Don't assume non-blocking behavior for a hook you haven't read;
`hooks/README.md` states it per hook.

## Reporting a vulnerability

- **Non-sensitive** (a hook's fail-open contract doesn't hold in some
  case you found, a validator check that should fire and doesn't, a skill
  instruction that could be read as directing unsafe behavior): open a
  regular GitHub issue on this repo.
- **Sensitive** (anything you'd rather not describe in public before a
  fix exists): use GitHub's private security advisory feature on this
  repo (the repo's Security tab → "Report a vulnerability") rather than a
  public issue.

There's no bug bounty and no SLA — this is one practitioner's published
setup, maintained on a best-effort basis.

## No warranty

MIT licensed — see `LICENSE`. Provided "as is," with no warranty of any
kind, exactly as the license text says. This is one practitioner's actual
operating setup, sanitized for publication; it is not an audited security
product, and nothing here should be treated as a certification that any
hook or skill is safe for your environment. Read the code. That's the
actual security control.
