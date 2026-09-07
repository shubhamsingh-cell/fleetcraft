# tests/

A stdlib-only `unittest` suite for the five hooks in `hooks/`. No pytest,
no PyYAML, no third-party imports anywhere in this directory.

## What it covers

For each of the five hooks (`autoload-judgment.py`, `fleet-delegation-guard.py`,
`skill-routing-guard.py`, `tool-routing-guard.py`, `retrieval-honesty-guard.py`):

1. **Fail-open / robustness** — empty stdin, `{}`, malformed JSON, missing
   keys, and payloads with unexpected types (wrong JSON type at the top
   level, wrong type on an expected field). Every case asserts the process
   exits 0 and never hangs (every subprocess call runs under a 5s timeout).
2. **Silent on no match** — a realistic payload that should NOT trigger the
   hook produces no injected context.
3. **Fires on match** — a realistic payload that SHOULD trigger it produces
   the specific decision/injection the hook's own source says it should.
   Trigger strings are copied from each hook's regexes/constants (`SHAPES`,
   `LONG_RUN`, `INSTALL` in `fleet-delegation-guard.py`; `CATEGORIES` in
   `skill-routing-guard.py`; `DOCS_URL`/`MSG_*` in `tool-routing-guard.py`;
   `TELLS` in `retrieval-honesty-guard.py`) so the tests track the real
   matchers, not a paraphrase that could drift from them.
4. **`tool-routing-guard`'s deny-then-allow contract**, end to end: the
   first docs-shaped `WebFetch` in a session is denied with rerouting
   instructions; the identical retry in the same session is silently
   allowed; a different `session_id` gets its own fresh deny; and
   `CLAUDE_TOOL_ROUTING_ENFORCE=0` downgrades the deny to a plain reminder.
   The hook's state dir is always pointed at a per-test temp directory via
   `CLAUDE_TOOL_ROUTING_STATE_DIR` — no test ever touches the hook's real
   default (`/tmp/claude-tool-routing-guard`).
5. **`retrieval-honesty-guard`'s transcript logic**, via built temp JSONL
   fixtures: (a) an unverifiability tell with no retrieval tool call that
   turn → blocks; (b) the same tell with a retrieval MCP call, and
   separately with a dispatched subagent (`Task`), in the turn → allows;
   (c) `stop_hook_active: true` → never blocks; (d) a missing or
   nonexistent `transcript_path` → exits 0 silently.
6. **Filesystem isolation, asserted by construction** — every subprocess
   call runs with `HOME` and `TMPDIR` pointed at a fresh
   `tempfile.TemporaryDirectory` (see `IsolatedHookTestCase` in
   `_hook_runner.py`), so no test can read or write the real `~/.claude`.
   `autoload-judgment.py` is the one hook that reads a real skill file
   (`~/.claude/skills/fable-judgment/SKILL.md`, via `Path.home()`, which
   respects `$HOME`) — its tests build a **fake** skill file under the temp
   HOME and cover both the present case (injects, frontmatter/changelog
   stripped) and the absent case (silent), so the suite passes identically
   on a fresh machine with no `~/.claude` at all.

## The negative-control rule, and why it's non-negotiable

A suite that only ever feeds a hook the payload it's supposed to react to
proves nothing: a hook that always stays silent, or always fires, would
pass a happy-path-only suite just as well as a correctly discriminating
one. So every behavioural assertion here ships in a pair — a "fires" test
and a "silent" test on a realistic non-triggering payload — never one
without the other. A hook that always prints nothing fails every "fires"
test while passing every "silent" test; a hook that always fires does the
reverse. Only real discrimination passes both halves.

This was verified for real, not just asserted in the abstract: a copy of
`skill-routing-guard.py` was made in a temp directory outside this repo,
neutered to unconditionally `sys.exit(0)` printing nothing on any input,
and a one-off run pointed `tests/test_hooks.py`'s hook-path resolution at
that copy instead of the real one. Result: the "fires" tests
(`test_fires_tabular_analysis`, `test_fires_doc_extract`) FAILED against
the gutted hook, while the paired "silent" tests and the robustness test
kept passing — exactly the failure signature this rule exists to catch.
The neutered copy was never written into `hooks/` and no longer exists.

## Known bug documented, not hidden

`fleet-delegation-guard.py` has no `isinstance(payload, dict)` guard on its
top-level payload (unlike `skill-routing-guard.py` and
`tool-routing-guard.py`, which both check this). A syntactically valid JSON
payload whose top level isn't a dict (`printf '[]' | python3
hooks/fleet-delegation-guard.py`), or whose `tool_input` is present, truthy,
and not itself a dict/string-command, crashes the process with exit 1
instead of exiting 0. This is real — reproduced directly against the hook,
not inferred. Since this suite may only add files under `tests/` and must
never edit `hooks/`, the two cases are captured as
`@unittest.expectedFailure` tests in `TestFleetDelegationGuard`
(`test_known_bug_nondict_top_level_payload_crashes` and
`test_known_bug_truthy_nondict_tool_input_crashes`), each with a docstring
explaining the root cause, the exact repro command, and the removal
condition. They show up in `-v` output as `expected failure`, so the suite
stays green while the bug stays visible instead of being silently dropped
from coverage. If the hook is ever hardened, these flip to `unexpected
success` (a real suite failure) — the signal to delete the decorator.

## How to run

Both must be run from the repo root (`fleetcraft/`):

```
python3 -m unittest discover -s tests -v
python3 -m pytest tests/ -q
```

`_hook_runner.py` is shared plumbing (subprocess invocation, the
`IsolatedHookTestCase` base class), not a test module — its leading
underscore keeps both runners' default `test_*.py` / `*_test.py`
collection patterns from picking it up.

## Runs with no real `~/.claude` at all

This suite does not depend on any file under the real `~/.claude` (every
hook invocation gets an isolated `HOME`/`TMPDIR`, and `autoload-judgment.py`
is tested against a fake skill file it constructs itself), so it passes
identically on a CI runner that has never seen this machine's `~/.claude`:

```
HOME=$(mktemp -d) python3 -m unittest discover -s tests -q
```
