# examples

## `settings.json` — all five hooks, wired

A complete, valid `~/.claude/settings.json` `hooks` block with every hook in this
repo enabled at once. `hooks/README.md` documents each hook one at a time; this
file is the merged result, which is the thing people actually get wrong.

**It is a template, not a drop-in replacement.** If you already have a
`~/.claude/settings.json`, merge this `hooks` object into it — overwriting the
file wipes your model choice, permissions, and env settings. `scripts/install.sh`
deliberately refuses to edit `settings.json` for you for the same reason.

### The merge that trips people up

Two hooks in this repo listen on `PreToolUse` with **different matchers**
(`Bash` for `fleet-delegation-guard`, `WebFetch|WebSearch` for
`tool-routing-guard`). They are two entries in one `PreToolUse` array — not two
`PreToolUse` keys. A JSON object cannot hold a duplicate key, so writing the
second block separately silently discards the first, and the hook you added most
recently is the only one that runs. That failure is invisible: nothing errors,
the guard is simply never called.

### Verify the wiring actually took

Restarting Claude Code is not evidence that a hook is loaded. Run one directly
and watch it respond:

```bash
echo '{}' | python3 ~/.claude/hooks/autoload-judgment.py
```

Exit code 0 means the hook runs. To confirm the harness is calling it, trigger a
matching event and look for the injected context — `hooks/README.md` lists what
each hook injects and on what. If you see nothing, check that the path in
`command` resolves and that the file is executable.

### Timeouts

Every hook is given `"timeout": 10`. All five are designed to finish in
milliseconds and to fail open, so the timeout is a backstop against a pathological
transcript or filesystem stall, not a tuning knob.
