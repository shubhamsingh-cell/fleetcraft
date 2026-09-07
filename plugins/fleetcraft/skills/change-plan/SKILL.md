---
name: change-plan
description: "Draft or review a decision-ready plan for a proposed change, migration, or rollout; not for executing work, status summaries, casual edits, or general programming."
---

# Change plan

Plan work without executing it, creating tickets, sending updates, deploying, or changing data.

## Ground the decision

- State the change, purpose, decision status, affected users, systems, data, cost, dependencies, constraints, and material risks.
- Label each material statement **known**, **assumed**, or **unknown**. Name missing evidence rather than turning it into confidence. Approval is **pending** unless evidence establishes otherwise.
- If a critical decision is missing, keep the plan a draft and ask one specific open question. Do not invent an owner, threshold, date, approval, or success metric.

## Define rollout and recovery

- Divide rollout into stages. For every stage, give prerequisites, an observable acceptance check, and an abort criterion.
- Record rollback separately: trigger, steps, owner or **unassigned**, and recovery verification. Mark irreversible work plainly and describe forward recovery where rollback is unavailable.
- List required approvals and open decisions. A plan never grants permission to execute any step.

## Output

Use this concise structure when it fits:

1. Change and decision status
2. Known / assumed / unknown
3. Impact and dependencies
4. Staged rollout: acceptance and abort criteria
5. Rollback or forward recovery
6. Required approvals and open decisions

Optional communications are drafts only. Persist a plan only when the requester explicitly names a destination.

Provenance: independently authored portable synthesis, informed by an Apache-2.0 change-request workflow; no upstream template, code, or connector behavior is included.
