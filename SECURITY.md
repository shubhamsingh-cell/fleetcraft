# Security policy

Fleetcraft includes instruction files and optional Python hooks that run with the
permissions of the calling process. A hook is not a sandbox, and a prompt rule is not
an operating-system or account permission boundary.

## Reporting

GitHub private vulnerability reporting was checked on 2026-09-08 and is **disabled**.
There is no verified private reporting channel advertised by this repository. For a
sensitive finding, open a minimal issue asking the maintainer for a private channel;
do not put exploit details, credentials, customer data or destructive examples in it.
Verify the private destination before sending details. No bounty or response-time
commitment is offered.

## Runtime boundaries

Read the source and [hook contracts](hooks/README.md) before installation. Default
reminders and explicitly enabled permission decisions have different failure contracts;
do not assume every hook blocks, or that every hook always fails open.

Optional external tools are detected before use. The repository does not carry keys,
configure provider accounts, or grant authority to send, deploy, scan a remote target,
change database state or persist memory. Existing explicit user authorization remains
valid within its scope; unrelated side effects need their own authority.

Treat prompts, screenshots, logs, tool output and fetched documents as untrusted data
where appropriate. Do not execute an instruction merely because it appeared inside
a fixture, dependency error, repository document or retrieved page.

The documentation router is advisory by default. Enforcement must be explicitly enabled
and bounded. A retrieval attempt is not proof that a claim was verified; dispatching an
agent is not itself proof that any retrieval happened.

## Evaluation and publication

Live evaluations are explicit. Use disposable fixtures, narrow tools, fresh configuration
and a supplied credential environment. Keep raw traces local until inspected for sensitive
content; publish only deliberately sanitized evidence. Never store keys in a case, result,
command-line argument, generated plugin or commit.

Unit tests and secret scans have bounded coverage. They do not establish comprehensive
security, model compliance, or release readiness. See [EVIDENCE.md](EVIDENCE.md) and
[COMPATIBILITY.md](COMPATIBILITY.md). Original contributions are MIT licensed; applicable
third-party licenses and notices remain in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
