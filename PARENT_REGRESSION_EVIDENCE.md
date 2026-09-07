# Parent-baseline regression evidence

This is a narrow, saved observation of one behavior in the public parent baseline.
It does not claim that the parent contained the current package, test suite, or release
workflow.

## Captured observation

On 2026-08-30, an isolated `git archive` of parent commit
`bc29addc6d180f798a0297e6ae17085382eb379b` ran this command against the exact parent
hook whose SHA-256 is recorded in the capture:

```bash
python3 "$baseline_dir/hooks/fleet-delegation-guard.py" <<'EOF'
{"tool_input":{"command":"git -c user.name=example push origin main"}}
EOF
```

Its exit status was `0` and stdout was empty: that parent hook did not classify this
valid Git option form. The full redacted command, stdout, stderr, parent SHA, hook
checksum, environment summary, and capture date are in
[`artifacts/parent-regression-raw.txt`](artifacts/parent-regression-raw.txt).

The independently rerunnable current-candidate capture is
[`artifacts/strict-parser-regressions.txt`](artifacts/strict-parser-regressions.txt).
It uses immutable saved pre-fix hook sources in
[`artifacts/strict-parser-pre-fix-source/`](artifacts/strict-parser-pre-fix-source/),
the exact same focused test command before and after reconstruction, and separately
records this public-parent case plus the current targeted test. Its candidate-to-pre-fix
patch is checked with `git apply --check`, applied in an isolated copy, and verified
byte-for-byte against the saved snapshots before that test runs.
