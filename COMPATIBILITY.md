# Compatibility

Fleetcraft targets Claude Code. It is not a portability promise for every agent harness.
This matrix separates local observations from configured-but-unobserved CI. It does not
imply support merely because a configuration file parses.

| Environment or capability | Observed fact / status | Fallback |
|---|---|---|
| Local macOS environment | **Observed 2026-08-30:** Python 3.9.6 and Claude Code 2.1.241. This is one local observation, not a support guarantee. | Re-run the repository checks in the target environment. |
| Linux CI matrix | **Configured, not observed:** `.github/workflows/verify.yml` selects Python 3.9, 3.11, and 3.13; pins Node 22.22.1 (which bundles npm 10.9.4); asserts both exact versions; and installs lockfile-pinned Claude Code 2.1.251. No remote CI result has been observed for this revision. | Do not claim Linux support until the exact commit has passed remote CI. |
| Local Node 24 / npm 11 | Unverified for plugin installation and release validation. | Do not make a compatibility claim from the local Node/npm versions; use the configured CI toolchain until a local fixture is recorded. |
| WSL | Unverified. | Use the Markdown skills without hooks until a WSL fixture passes. |
| Native Windows | Unverified. | Use the Markdown skills without hooks until a native-Windows fixture passes. |
| Core Markdown skills and agent-role guidance | Claude Code with skills/agents support | Use the documents as manual operating guidance. |
| Hook runtime | A compatible `python3` interpreter is required; only the local macOS Python 3.9.6 observation is recorded above. | Use the Markdown skills without hooks. |
| Plugin strict validation | Verify with the installed Claude Code release before calling a plugin “strictly validated.” | Do not make the strict-validation claim. |
| `Agent` telemetry: `resolvedModel` | Optional; verify the field in the installed runtime | Record model resolution as unverified. |
| `Agent` telemetry: `modelsUsed` | Optional; verify the field in the installed runtime | Use any available verified telemetry field; otherwise record unverified. |
| Batch evidence reminder | `PostToolBatch` plus `evidence_batch: true` | Leave disabled; name evidence artifacts manually. |
| Model-switch behavior | Deliberately not shipped in v0.1.1 | Do not emulate a model-switch guarantee with prompt text; require a separately installable, validated extension. |
| Background subagent work | Optional; verify durable child execution in the installed harness | Parent owns long-lived commands. |
| Bash hook matchers | Local macOS observation only; Linux CI is configured but unobserved; WSL is unverified. | Use the Markdown skills without hooks. |
| PowerShell tool classification | Matcher presence is not native Windows hook-execution evidence; native Windows is unverified. | Use manual workflow until a Windows fixture passes. |
| Playwright screenshots | Already-installed, project-pinned `@playwright/cli` or available browser tooling | Do not fetch via bare `npx`; use a browser tool or obtain approval for a pinned install. |

## Feature detection rules

- A version check is not a substitute for behavior checks. Record the actual command,
  hook event, telemetry field, or render artifact used in a release decision.
- Optional local tools, MCP servers, and skills must be detected before a Fleetcraft
  workflow names them. Missing prerequisites are an `OPEN` gate, not a hidden fallback.
- Use `context: fork` only for repeatable read-only review/research/design work where
  shared starting context is intentional. Do not use it as a substitute for independent
  verification or fresh external evidence.
- Agent `skills` preloads are optional. Preload the smallest relevant skill set and list
  it in the agent’s configuration; a workflow must still work or fail clearly when the
  preload capability is unavailable.

See the official Claude Code documentation for [hooks](https://code.claude.com/docs/en/hooks),
[subagents](https://code.claude.com/docs/en/sub-agents), and
[plugin references](https://code.claude.com/docs/en/plugins-reference). Revalidate this
matrix before a release that upgrades Claude Code compatibility.
