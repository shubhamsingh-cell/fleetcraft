# Compatibility

Version numbers identify observed environments, not permanent compatibility promises.
Re-run the checks for the exact candidate and target harness.

| Surface | Status and verification |
|---|---|
| Canonical Markdown skills/roles | Readable independently; automatic selection depends on the harness. |
| Source hook tests | Standard-library fixtures exercise individual hooks; they are not a live-agent evaluation. |
| Generated Claude plugin | Generated from canonical sources; parity, strict manifest validation and isolated installation are separate checks. |
| Local evaluation runtime | macOS, Python 3.9.6, Claude Code 2.1.263; an isolated authenticated print session was observed on 2026-09-08. |
| Live model identity | Read from actual CLI stream telemetry. The validated live smoke traces reported `claude-sonnet-5`; do not infer other model identities or relative quality. |
| Linux | Require exact-commit CI; old main/PR success does not certify the integrated candidate. |
| Native Windows/WSL | Unverified; do not infer support from PowerShell matcher text. |
| Third-party MCP/services | Optional and environment-specific. A named provider is not necessarily installed, connected or authorized. |
| Skill baseline | Compare equal fixtures and harness flags with Fleetcraft absent. An all-skills-disabled control also disables CLI built-ins and is reported separately. |
| Tagged release | Require immutable public-tag installation/archive verification; a source branch is not a release. |

The legacy installer and plugin loader are alternative paths; avoid double loading them.
Manual settings edits, persistent plugin installation and production rollout remain adopter
actions. Local fixture installation during tests must use isolated configuration.

CLI flags used by the live harness are validated against the installed CLI and recorded
with results. A flag appearing in help establishes availability, not successful isolation;
initialization events and observed tool calls provide that evidence.
