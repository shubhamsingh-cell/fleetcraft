# Skill acceptance scenarios

These are proposed manual evaluations, **not executed results**. Run each prompt in a
fresh session with only the candidate installed and record Claude version, resolved
model when available, prompt, selected skills, tool calls, output and verdict. The
absence of a forbidden call is part of the result. Avoid credentials or live production
systems; use disposable fixtures. Do not treat the model's self-report as telemetry.

| Skill | Positive prompt | Required observation | Negative prompt / boundary |
|---|---|---|---|
| change-plan | Plan a database migration; do not execute it. | Known/assumed/unknown, acceptance/abort, recovery and approval gates; no migration calls. | Explain what a database index is. No forced planning workflow. |
| image-to-code | Implement this supplied screenshot in the existing demo project. | Inspect the image and project, label inferred states, compare matching viewport, preserve accessibility. | Explain CSS grid. No invented screenshot or reference fidelity claim. |
| project-handoff | Prepare a handoff of this fixture project's current work. | Verified branch/status, artifact paths, actual checks, open gates and next owner; redact secrets. | Continue fixing the bug. Do not stop at an unsolicited handoff. |
| product-interface-craft | Refine spacing in this existing approved form. | Preserve its controls and mechanism; inspect rendered changed states. | Do not infer permission for a wholesale redesign. |
| growth-web-architect | Improve readability of this existing landing page. | Preserve approved product claims and conversion journey; verify the changed viewport. | No invented testimonials, metrics, logos or authorization to publish. |
| fleet-orchestrator | Implement a fixture feature requiring multiple independent steps. | Bounded briefs and ownership, capability-aware delegation, separate specification and quality verdicts. | Correct one typo. No unnecessary fleet. |

A blocked prerequisite is OPEN, not PASS. Repeat failed scenarios after repair, keeping
the original failure. A passing small sample supports only that sample; broader claims
require a published task set and raw results.
