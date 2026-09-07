# Contributing

Thank you for improving Fleetcraft. Changes must make a claim more testable, safer, or
clearer; they should not add an unsupported capability claim.

## Before opening a change

1. Read `README.md`, `COMPATIBILITY.md`, `EVIDENCE.md`, and `THIRD_PARTY_NOTICES.md`.
2. Keep the smallest coherent change. Do not edit unrelated working-tree changes.
3. For a factual or vendor/version claim, cite a primary source and date.
4. For copied, adapted, or distilled third-party material, add its source revision,
   affected files, modification note, and applicable license notice.

## Validation expectations

- Hook, plugin, installer, or doctor changes need fixtures for normal, malformed, and
  no-match inputs plus a clean-install path.
- Bug fixes need a captured pre-fix reproduction and a regression test that fails on the
  parent revision where feasible.
- Visual guidance changes need a rendered example or must be labeled as a protocol rule,
  not empirical proof.
- Documentation links and internal paths must resolve.
- A final reviewer returns separate spec-compliance and build-quality verdicts.

## Boundaries

Do not add a dependency, external send, deployment, secret, package download, or automatic
workflow without explicit maintainer approval. Slash commands that can commit, push, deploy,
share, or send must use `disable-model-invocation: true` so they require direct user
invocation. Never add unverifiable testimonials, metrics, logos, or benchmark claims.
