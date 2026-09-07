# Fleetcraft

**Evidence-first operating rules for AI coding agents.** Fleetcraft provides Claude Code
skills, agent roles, hooks, and release guidance for model routing, independent
builder/verifier review, screenshot-first design checks, and evidence-backed completion.

> **Preview status — v0.1.1 release candidate.** The self-contained plugin, doctor,
> behavioral tests, and CI workflow are present. This revision is not a tagged release;
> evaluate it from a local clone and do not describe it as published until the release
> commit has passed remote CI and has been tagged.

Fleetcraft is not a benchmark suite and makes no claim to improve a particular model,
reduce token use by a stated amount, or replace human judgment. Its purpose is to make
acceptance criteria and uncertainty explicit.

## What is included

| Path | Purpose |
|---|---|
| `plugins/fleetcraft/skills/` | The installed skills, including Fleetcraft's release and visual-review guidance. |
| `plugins/fleetcraft/agents/` | Builder, researcher, and independent-verifier role contracts. |
| `plugins/fleetcraft/hooks/` | Optional context/diagnostic hooks; their exact behavior is in `hooks/README.md`. |
| `plugins/fleetcraft/skills/doctor/` | Installed `/fleetcraft:doctor` preflight capability. |
| `plugins/fleetcraft/scripts/fleetcraft-doctor.py` | Read-only installed-package preflight for manifests, hook syntax, and the bundled kernel. |
| `tests/` | Standard-library behavioral fixtures, including clean-home execution and malformed inputs. |

## Choose a workflow

| Task | Skill |
|---|---|
| Plan a consequential change before implementation | `/fleetcraft:change-plan` |
| Coordinate implementation and independent review | `/fleetcraft:fleet-orchestrator` |
| Build or refine a product interface | `/fleetcraft:product-interface-craft` |
| Build or refine an acquisition page | `/fleetcraft:growth-web-architect` |
| Implement a supplied visual reference | `/fleetcraft:image-to-code` |
| Review a rendered result against evidence | `/fleetcraft:design-judge` |
| Prepare a durable continuation or handoff | `/fleetcraft:project-handoff` |
| Check an installed package | `/fleetcraft:doctor` |

See [the upgrade inventory](docs/UPGRADE_INVENTORY.md) for what is bundled, optional,
and deliberately deferred. New instructions are not proof of model behavior; use the
[acceptance scenarios](docs/ACCEPTANCE_SCENARIOS.md) to evaluate them in your harness.

## Install and rollback

The supported target is a Claude Code plugin rather than manual copies into a private
configuration directory.
For local evaluation from a clone:

```bash
python3 scripts/selftest-guards.py
python3 scripts/validate-plugin.py
claude --plugin-dir plugins/fleetcraft
```

The marketplace command below is for the published `v0.1.1` release only; it is not an
installation method for this untagged local-development checkout:

```bash
claude plugin marketplace add shubhamsingh-cell/fleetcraft@v0.1.1
claude plugin install fleetcraft@fleetcraft
```

Then run `/fleetcraft:doctor` inside Claude Code and retain the output with the release
or installation evidence.

1. Read [COMPATIBILITY.md](COMPATIBILITY.md) and [SECURITY.md](SECURITY.md).
2. Install only the tagged release; start in audit mode. Strict blocking mode is opt-in
   and may interrupt commands.
3. To roll back, run `claude plugin disable fleetcraft@fleetcraft`, then
   `claude plugin uninstall fleetcraft@fleetcraft`. Remove the marketplace separately
   with `claude plugin marketplace remove fleetcraft` only if it is no longer needed.

The plugin must pass strict validation, clean-home fixtures, and the tag-only
`release-artifact` workflow in the release environment before a release is called
installable. That workflow installs the public immutable tag using Claude Code 2.1.251
with the exact Node 22.22.1 / npm 10.9.4 toolchain, asserts both runtime versions before
installation, runs the installed package doctor and strict-hook fixture,
and byte-compares the resulting cache against `git archive` of `plugins/fleetcraft` at
the push-event commit. It also proves the tag still peels to that commit after public
installation. This is a future, unobserved gate until it runs on an immutable public tag;
it has not run for this untagged candidate. Model-switch behavior is deliberately not
shipped in v0.1.1; it requires a separately installable, validated extension.

## Operating principles

- **Capability matched:** mechanical, independently checkable work can use a lower capable
  tier; judgment-bearing work inherits or exceeds the owner-selected session tier.
- **Telemetry over narration:** model version claims come from harness telemetry where
  available, not from a model saying which model it is.
- **Builders and verifiers are distinct roles:** an executor may self-check, but a final
  acceptance verdict comes from an independent verifier or an explicitly documented
  equivalent process.
- **Durable work is conditional:** use background subagent work only when the active
  harness documents and demonstrates that it can keep the child alive; otherwise the
  parent owns long-lived commands.
- **Hooks are not magic:** context output is a protocol reminder. It is not enforcement
  unless the active hook returns a documented permission decision and the feature is
  explicitly enabled.
- **Proof is a protocol veto:** a claim without a real artifact or an illustrative label
  blocks Fleetcraft's protocol verdict; native platform controls remain the actual
  technical enforcement.

## Evidence and limitations

Read [EVIDENCE.md](EVIDENCE.md) before adopting a rule as fact. It separates author-reported
anecdotes, reproducible repository checks, and planned evaluations. Read
[COMPATIBILITY.md](COMPATIBILITY.md) before enabling features that depend on a Claude Code
version, operating system, optional tool, or plugin capability.

The compatibility matrix distinguishes the one observed local macOS environment from
configured-but-unobserved Linux CI; WSL and native Windows remain unverified. Optional
tools are never assumed to be installed; the active environment must detect them first.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for the evidence and validation required for changes,
and [SECURITY.md](SECURITY.md) for vulnerability reporting. Changes affecting installation,
hooks, or release claims require a clean-install test and independent review.

## Third-party notices and license

Fleetcraft's original contributions are MIT licensed; see [LICENSE](LICENSE). The combined
plugin distribution declares `MIT AND Apache-2.0`: adapted or distilled third-party material
retains its applicable upstream MIT or Apache-2.0 terms. The installed package contains
byte-identical copies of the license and notice ledger.
Source revisions, affected files, notices, and complete license texts are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Release record

See [CHANGELOG.md](CHANGELOG.md). A tagged release should only be announced after the
tag-only release-artifact workflow observes its installation, doctor, hook fixtures,
exact archive comparison, and release-contract checks in CI. Local checks are not a
substitute for that public-tag observation.
