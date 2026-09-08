# examples

## `settings.json` — all eight registered hooks, wired

A complete, valid `~/.claude/settings.json` `hooks` block with every hook in this
repository registered at once. `hooks/README.md` documents each hook one at a
time; this file is the merged result, which is the thing people actually get
wrong.

**It is a template, not a drop-in replacement.** If you already have a
`~/.claude/settings.json`, merge this `hooks` object into it — overwriting the
file wipes your model choice, permissions, and env settings. `scripts/install.sh`
deliberately refuses to edit `settings.json` for you for the same reason.

### The merge that trips people up

Two hooks in this repo listen on `PreToolUse` with **different matchers**
(`Bash|PowerShell` for `fleet-delegation-guard`, `WebFetch|WebSearch` for
`tool-routing-guard`). They are two entries in one `PreToolUse` array — not two
`PreToolUse` keys. A JSON object cannot hold a duplicate key, so writing the
second block separately silently discards the first, and the hook you added most
recently is the only one that runs. That failure is invisible: nothing errors,
the guard is simply never called.

### Verify the wiring actually took

Restarting Claude Code is not evidence that a hook is loaded. Run one directly
and watch it respond:

```bash
echo '{}' | python3 -B ~/.claude/hooks/autoload-judgment.py
```

Exit code 0 only proves that the process ran. To confirm the harness is calling
it, trigger a matching event and inspect the applicable output or injected
context. No output can be legitimate in audit mode, for a disabled opt-in, or
when the manual `autoload-judgment.py` hook cannot read its optional local
`~/.claude/skills/fable-judgment/SKILL.md` companion. If a matching hook should
have acted but did not, check that the `command` path resolves and the file is
executable.

### Timeouts

Every hook is given `"timeout": 10`. The timeout is a backstop against a
pathological transcript or filesystem stall, not a tuning knob. Hook behavior
is not universally fail-open or fail-closed: `delegation_mode=audit` is the
default and `strict` is opt-in; routing only enforces when
`routing_enforce=true`; and `completion_gate` and `evidence_batch` are disabled
until explicitly enabled. The example's `env` block records those defaults.

`agent-telemetry` has no opt-in setting. The manual
`autoload-judgment.py` hook reads the optional local `fable-judgment` companion
and stays silent when it is absent; it does not bundle the plugin judgment
kernel. The `PostToolBatch` and `TaskCompleted` registrations remain present
while their corresponding options are disabled, so enabling an option later
does not require rewiring the event.
