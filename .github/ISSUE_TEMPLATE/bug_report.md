---
name: Bug report
about: A hook or skill is misbehaving
title: "[bug] "
labels: bug
assignees: ""
---

## Which file

<!-- e.g. hooks/fleet-delegation-guard.py, or skills/design-judge/SKILL.md -->

## Claude Code version

<!-- claude --version, or the version shown in the app -->

## Installation channel and plugin version

<!-- e.g. marketplace install, local checkout, or manual installation; include
the installed Fleetcraft plugin version or commit when known. -->

## Relevant option modes

<!-- Include only settings that affect this report, such as delegation_mode
(audit or strict), routing_enforce, completion_gate, or evidence_batch. -->

## OS

<!-- e.g. macOS 15.x, Ubuntu 24.04 -->

## Observed and claimed artifact context

<!-- Link or identify the actual output, trace, screenshot, test result, or
other artifact you observed. State the specific documented behavior or claim
you expected it to support. Distinguish missing evidence from a failed claim. -->

## Hook stdin payload (if this is a hook bug)

<!--
If you can reproduce it, paste the JSON payload the hook received (redact
credentials, tokens, private file contents, customer data, and command text or
paths you do not want to share). Replace sensitive values with clear redaction
markers. If you do not have a payload, say so explicitly.
-->

## What happened

<!-- The actual behavior: what the hook/skill did, output produced, error raised, or silence where you expected a reminder/veto. -->

## What you expected

<!-- What should have happened instead, and why (which check/rule in the file leads you to expect that). -->

## Anything else

<!-- Optional: whether this reproduces reliably, whether it's new since a recent change, etc. -->
