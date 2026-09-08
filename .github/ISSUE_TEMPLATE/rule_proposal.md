---
name: Rule proposal
about: Propose a new rule, or a change to an existing one
title: "[rule] "
labels: rule-proposal
assignees: ""
---

<!--
Read CONTRIBUTING.md before filling this in. Ground a proposal in a concrete
failure, observed usability problem, reproducible preventive finding, or a
clearly labeled proposal. Do not invent dates or metrics to make a case.
-->

## Evidence or proposal basis (required)

<!--
State the concrete failure, observed usability problem, reproducible
preventive finding, or proposal. Describe the observable consequence or risk
and identify supporting artifacts when available. A date is useful context
when known, but do not fabricate one.
-->

## The check that would have caught it

<!--
What rule, hook check, or validator check — if it had existed at the time
— would have prevented this, or caught it before it shipped? Be specific
enough that someone could implement it from this description.
-->

## Existing surface and routing

<!--
Which existing skill, agent contract, hook, validator, or documentation
surface should own this? Extend the narrowest existing surface where possible.
If a new skill is needed, give its trigger conditions and routing.
-->

## Sensitive data and attribution check

<!-- Exclude credentials, private logs, proprietary bundles, and personal context. Keep public product names when they are necessary for accurate attribution; preserve applicable source revisions, licenses, and notices. -->

- [ ] I removed sensitive material and preserved any needed public attribution.
