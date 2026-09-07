---
name: Rule proposal
about: Propose a new rule, or a change to an existing one
title: "[rule] "
labels: rule-proposal
assignees: ""
---

<!--
Read CONTRIBUTING.md's "The evidence bar" section before filling this in.
Every rule here exists because a specific, dated failure happened — "this
seems better" or "this is a well-known best practice" is not evidence and
this template won't get you past that bar without the field below filled
in for real.
-->

## What actually broke (required)

<!--
Concretely, not "this could cause confusion." What happened, what was the
observable consequence, and roughly when (even an approximate date is
fine — the date is what lets a future reader tell a fresh rule from a
load-bearing one). If you don't have a real failure to point to, this
proposal isn't ready yet — open a discussion instead, or come back once
it's happened.
-->

## The check that would have caught it

<!--
What rule, hook check, or validator check — if it had existed at the time
— would have prevented this, or caught it before it shipped? Be specific
enough that someone could implement it from this description.
-->

## Which skill/gate class it belongs in

<!--
Does this extend an existing skill (fleet-orchestrator, design-judge,
incident-miner, growth-web-architect, product-interface-craft, an agent
contract, or a hook), or does it need a new one? See CONTRIBUTING.md's
"Proposing a new skill vs. extending an existing one" for the bar — a new
skill needs its own trigger conditions and routing, not just a rule that
could be a paragraph in an existing file.
-->

## Sanitization check

<!-- Confirm: no employer, client, colleague, or product name appears anywhere in this issue (including any pasted logs/transcripts). Genericize before posting. -->

- [ ] I've re-read this issue for names and genericized anything specific.
