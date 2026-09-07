---
name: project-handoff
description: Write or resume a durable state record for long-running work: objective, status, blockers, next actions, decisions, and rejected alternatives.
---

# Project handoff — durable state, not a status summary

A status summary tells someone what happened. A handoff lets a session with **no memory of
this conversation** resume the work correctly. Write for that reader: cold, competent, and
about to make decisions from your file.

## Which convention applies — check before creating anything

1. **Existing project with an established state file** — keep it. If the repo already has
   `SESSION_HANDOFF.md`, `docs/STATE.md`, `NOTES.md`, or similar, write there. **Never
   introduce a second state system beside an existing one**; two half-true state files are
   worse than one stale one, because now the reader has to adjudicate.
   Find it first: `ls docs/ 2>/dev/null; git ls-files | grep -iE 'state|handoff|decisions|notes'`.
2. **New project** — create the owner's default trio, only the ones the work actually needs:
   - `docs/STATE.md` — active objective, status, blockers, next actions.
   - `docs/DECISIONS.md` — decisions made, alternatives rejected, and why.
   - `docs/LESSONS.md` — recurring mistakes and their durable fixes.
3. **Not a project at all** (a one-off task, a question answered) — write nothing. A handoff
   file for work that ends today is clutter that will be stale by Thursday.

## Resuming: read before you act

When picking work back up, read the state file **and** verify it against reality before
trusting it — a handoff is a claim about the past, not a measurement of the present:

- `git log --oneline -15` and `git status` — what actually landed vs. what the file says landed.
- `git fetch` before asserting anything is merged, unmerged, or "still broken on main" — that
  rule, and its precedents, belong to `fleet-orchestrator` gate class 1. Apply it; don't
  re-derive it here.
- Where the file names a test, a URL, a table, or a commit — check the named artifact exists.

State any divergence out loud in the first line of your reply ("STATE.md says X; git says Y").
Silently trusting a stale file is how a session re-does finished work or builds on a fix that
was reverted.

## Writing the record

Keep it short enough to stay true. Every line earns its place by changing what the next
session would do.

**STATE.md** — objective (one sentence, the outcome not the activity); status per workstream
with the evidence behind it; blockers naming *who or what* unblocks them; next actions concrete
enough to start cold. Evidence meets `fleet-orchestrator` gate class 5's bar (name the artifact
observed; an errored check is an open item, never a pass) — that gate owns the standard, this
file only records what it produced.

**DECISIONS.md** — one row per real decision: what was chosen, why, and **what was rejected**.
The rejected alternative is the half people forget and the half that stops the next session
re-litigating a settled question. Record the authority too: who approved it, or that it is
still pending approval.

Convert relative dates to absolute (`2026-09-07`, not "yesterday"). Name files as paths.
Prefer a commit SHA to a description of a change.

Before writing, check which file and editing tools are actually available. If no supported write
tool is available, return the complete handoff as an inline draft, clearly say it was not
persisted, and do not attempt an unavailable tool or claim a file was created.

## Boundaries

- **Do not** copy credentials, tokens, cookies, raw private conversation logs, or personal data
  into a state file. It is a working document that gets shared and committed.
- **Do not** let the handoff become the deliverable — write it *after* the work, in minutes,
  not as a substitute for finishing.
- **Update, don't append forever.** Replace stale status in place; a state file that only grows
  becomes an archive nobody reads. History already lives in git.
- **Lessons belong to `incident-miner`**, which gathers evidence and stops for approval before
  writing `docs/LESSONS.md`. This skill owns STATE and DECISIONS; hand a hard-won bug lesson
  there rather than duplicating it here.
- **A plan for a change that hasn't happened yet is `change-plan`**, not a handoff. This skill
  records what *is*; that one proposes what *should* be.
