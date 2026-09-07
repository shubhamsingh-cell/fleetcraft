# Fleetcraft plugin hooks

Fleetcraft v0.1.1 is a self-contained Claude Code plugin. The runtime no
longer reads a private `~/.claude` skill path or assumes local helper binaries.
Load it for development with:

```bash
claude --plugin-dir /path/to/fleetcraft/plugins/fleetcraft
```

The plugin discovers this directory's `skills/`, `agents/`, and
`hooks/hooks.json`. Hook entrypoints run with Python 3.9+ and only use the
standard library. Run `python3 scripts/fleetcraft-doctor.py` from an installed
package before relying on its hook wiring.

## Behavior

- `SessionStart`: injects the bundled `judgment-kernel.md`, kept under Claude
  Code's 10,000-character hook-output limit. Set `autoload_judgment` to false
  at plugin enablement to disable it. An invalid value is visibly warned about
  and retains the safe default (enabled); the warning and the injected kernel
  are emitted together as one parseable hook-response JSON object.
- `PreToolUse` (`Bash|PowerShell`): classifies publish-shaped commands. In the
  default `audit` mode it records a non-blocking reminder for the next model
  decision. In `strict` mode it returns a real `permissionDecision: ask` for
  every matching publish action, including one issued by a delegated agent; it
  does not pretend an advisory message blocked a command. Strict mode covers
  only the command shapes this hook can classify; it is not a sandbox or a
  replacement for Claude Code's native permission controls. A malformed
  payload, invalid nonempty `delegation_mode`, a lexer failure (such as an
  unmatched quote or trailing escape), unsupported/dynamic shell
  grammar, or bounded-recursion uncertainty fails closed with an ask. In audit
  mode those same cases are only non-blocking context, including malformed JSON
  payloads. `git` help and dry-run
  exemptions are recognized only as options before `--`; `git commit -m x --
  --help` and `git push origin -- -n` remain guarded. `git push -n`/`--dry-run`
  is ignored as a genuine dry run, while `git commit -n` and `--no-verify`
  remain guarded because they can create a real commit.
- `UserPromptSubmit`: supplies narrow routing reminders without claiming that
  private machine-specific tools are installed.
- `TaskCompleted`: disabled by default. When enabled, it only gates task
  descriptions that opt in with `[fleetcraft:verified]`; such tasks need
  structured evidence and validation fields before they can close:
  `Evidence: artifact=<path-or-URL>; sha256=<64 lowercase hex characters>` and
  `Validation: command=<executed command>; result=pass|passed|success|0`.
  Empty, sentinel, and placeholder values (for example `TODO`, `N/A`, or
  `test output`) are rejected. This gate only establishes an identifiable
  artifact and a reported command result; syntax cannot prove semantic truth,
  so it does not replace review of whether that evidence supports completion.
  An invalid nonempty `completion_gate` value fails safe for opted-in verified
  tasks instead of silently turning the gate off.
- `PostToolUse` (`Agent`): reports harness-owned `resolvedModel` and `modelsUsed`
  telemetry when those fields exist. Model narration is never treated as resolution.
- `PostToolBatch`: disabled by default. With `evidence_batch` enabled, indexes only
  completed tool names for the next request; it does not inspect/persist results or
  certify completion.
`delegation_mode`, `autoload_judgment`, `completion_gate`, and `evidence_batch`
are declared as plugin `userConfig` values. Claude Code
exports them only to hooks as `CLAUDE_PLUGIN_OPTION_*`; Fleetcraft reads those
environment variables inside Python and never interpolates a user-supplied
value into a shell command.

Every bundled path uses hook exec form (`command` plus `args`), so plugin-root
paths are passed as one argument without platform shell re-parsing.

## Installed-package check

```bash
python3 scripts/fleetcraft-doctor.py
```

## Maintainer checks

The following commands exist only in a source checkout (not in the installed sparse
package), and are run from that checkout's root:

```bash
python3 scripts/selftest-guards.py
python3 scripts/validate-plugin.py
python3 scripts/clean-install-smoke.py
```

The latter two commands require a current local Claude Code installation. CI runs all
three maintainer checks; strict plugin validation and tag-cache comparison are release gates.
