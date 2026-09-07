# Runtime hooks

Hooks are small, inspectable runtime helpers. Most supply reminders; a reminder is not
an enforcement boundary or proof that a task succeeded. Native tool permissions, branch
rules and deployment controls remain necessary for their respective boundaries.

## Plugin registration and options

The generated `plugins/fleetcraft/hooks/hooks.json` is the registration contract. Change
canonical hook sources and `scripts/build_plugin.py`, regenerate, then run parity and
installed-package checks. Use a fresh session after runtime changes before claiming the
new hooks were loaded.

| Hook | Event | Default and effect |
|---|---|---|
| `autoload-judgment.py` | SessionStart | Plugin injects its compact bundled kernel; `autoload_judgment=false` disables it. Empty/oversized kernels produce a warning without context. |
| `skill-routing-guard.py` | UserPromptSubmit | Adds context for recognized task shapes; does not guarantee skill selection. |
| `fleet-delegation-guard.py` | PreToolUse, Bash or PowerShell | `delegation_mode=audit` adds reminders. Opt-in `strict` asks for publish-shaped or unsupported shell constructs. It is a bounded parser, not a general shell sandbox. |
| `tool-routing-guard.py` | PreToolUse, WebFetch or WebSearch | Reminds by default. `routing_enforce=true` can deny the first matching documentation fetch in a session, allowing a retry if no suitable documentation capability is available. |
| `agent-telemetry.py` | PostToolUse, Agent | Reports model fields supplied by the harness when present; never derives identity from model prose. No model-quality verdict. |
| `completion-gate.py` | TaskCompleted | Disabled unless `completion_gate=true`. Only tasks explicitly marked `[fleetcraft:verified]` receive the evidence-field gate. |
| `evidence-batch.py` | PostToolBatch | Disabled unless `evidence_batch=true`. Summarizes observed tool names without saving prompt/result content. A batch count is not success proof. |
| `retrieval-honesty-guard.py` | Stop | Checks the available transcript for retrieval-related claims and observed retrieval attempts. Agent dispatch alone does not count as retrieval. |

Plugin configuration is exposed through the manifest's `userConfig`; supported harnesses
supply the corresponding `CLAUDE_PLUGIN_OPTION_<UPPERCASE_NAME>` environment variable.
The documentation-routing hook also accepts legacy `CLAUDE_TOOL_ROUTING_ENFORCE`; an
explicit plugin value takes precedence. Tests verify the hook's environment interface;
manifest validation alone does not prove a particular UI supplied an option.

Invalid delegation modes request confirmation. Invalid nonempty completion options keep
opted-in tasks OPEN. An invalid autoload option warns and uses the enabled default when
the kernel itself is valid. Malformed input behavior is hook-specific: do not describe
the whole family as universally fail-open or universally fail-closed.

The completion gate validates field shape, not artifact existence, digest correctness,
execution or semantic quality. A task opting in must include:

```text
[fleetcraft:verified]
Evidence: artifact=<specific artifact identity>; sha256=<64 lowercase hex characters>
Validation: command=<executed command>; result=pass
```

Those placeholders are illustrative, not valid evidence. Independent review must inspect
the actual artifact and check the claimed command/result.

## Legacy manual installation

`bash scripts/install.sh --dry-run` prints the destinations and proposed settings entries.
The installer copies skills, agents, hooks and their helper, backs up changed destinations,
and leaves `settings.json` untouched. Review the printed entries before wiring them into
your configuration. Use either the manual installation or the plugin to avoid duplicates.

The legacy source `autoload-judgment.py` is deliberately different: it reads an optional
local `~/.claude/skills/fable-judgment/SKILL.md` companion and stays silent when absent.
Fleetcraft does not distribute that private companion. The generated plugin replaces this
hook with the self-contained bundled kernel described above.

## Verification scope

Run the repository tests, non-mutating parity check, strict manifests and isolated install
before publishing. The strict parser reproducer retains the same test against an immutable
pre-fix snapshot and the current candidate. A passing hook fixture proves that fixture's
runtime response; it does not establish general model compliance, a global retrieval rate,
or production safety. See [EVIDENCE.md](https://github.com/shubhamsingh-cell/fleetcraft/blob/main/EVIDENCE.md) and [SECURITY.md](https://github.com/shubhamsingh-cell/fleetcraft/blob/main/SECURITY.md).
