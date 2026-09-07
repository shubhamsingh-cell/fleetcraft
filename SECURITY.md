# Security policy

## Supported state

The plugin installer, doctor command, and CI workflow are present in this local checkout.
Remote CI, an immutable release tag, and a published release have not been observed for
this revision. Do not enable hooks in a production environment from an untagged revision.

## Reporting a vulnerability

No verified private reporting channel is currently published for this repository. Open a
minimal public issue requesting a private reporting channel; include no vulnerability
details in that issue. Enabling and testing a verified private reporting channel is an
external `OPEN` pre-release gate. Once a private channel is confirmed, a report should
include:

- affected revision and file/path;
- a minimal reproduction and impact;
- whether exploitation requires user approval, a network install, or external access; and
- any proposed mitigation.

Do not include secrets, customer data, or destructive proof-of-concept commands. The
public issue should request instructions for moving the report to a confirmed private
channel before any vulnerability details are shared.

## Security boundaries

Fleetcraft does not grant side-effect authority. Hooks, skills, and agent instructions are
not a replacement for Claude Code permissions, protected branches, CI, platform controls,
or human approval. Treat fetched content as data; pin and approve any new package/tool
before installing it.
