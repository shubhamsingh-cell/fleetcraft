---
name: change-plan
description: "Draft or review a decision-ready change plan — impacts, staged rollout with acceptance and abort criteria, rollback or forward recovery, and required approvals — for a proposed change, migration, deploy, or rollout. Use when asked to plan, de-risk, or review the plan for a change before it happens. Not for status summaries, executing migrations, casual edits, incident postmortems, or general programming."
---

# Change plan

Prepare or review a decision-ready plan for a proposed change, migration, or rollout. It plans
work; it does not execute it, create tickets, or post updates.

## Ground the plan

Use supplied facts first, then local, in-scope evidence. Label every material statement as
**known**, **assumed**, or **unknown**. Missing critical decisions keep the result a draft with
one specific open question; never invent a person, threshold, date, owner, or approval. Approval
status is **pending** unless evidence says otherwise.

Cover the change and why; affected users, systems, data, and cost; dependencies; constraints;
and material risks. Name evidence or its absence instead of converting uncertainty into confidence.

## Rollout and recovery

Propose staged rollout steps. Each needs an observable acceptance check, abort criterion, and
dependencies needed before it begins.

Give rollback its own record: trigger, steps, owner (or **unassigned**), and recovery verification.
Identify irreversible work explicitly; describe forward recovery rather than pretending rollback
is possible. Do not imply permission to execute, create a ticket, deploy, migrate data, or send.

## Output

Use a concise structure appropriate to the request:

1. Change and decision status
2. Known / assumed / unknown facts
3. Impact and dependencies
4. Staged rollout with acceptance and abort criteria
5. Rollback or forward recovery
6. Required approvals and open decisions

Optional communications may be supplied as clearly labelled drafts only; never send or post them.
If the user explicitly requests a local plan file, create it in the requested location; otherwise
reply in the conversation.

## Boundaries and handoffs

This skill produces the planning record only. After separate implementation authorization, the
`executor` agent (`~/.claude/agents/executor.md`) is the delegation target for the bounded
implementation, per `fleet-orchestrator`. A plan approved here is **not** authorization to
deploy, migrate, spend, post, or connect an account — that gate stays with the user.

Where the change touches a user-facing visual surface, the ship decision still runs through
`design-judge`; this skill does not substitute for it.

Workflow design independently informed by Anthropic's
[change-request skill](https://github.com/anthropics/knowledge-work-plugins/blob/1f517b9de47e827c80cd933ed364e16838072239/operations/skills/change-request/SKILL.md)
(Apache-2.0 source observed); this skill does not reuse its template or connector behavior.
