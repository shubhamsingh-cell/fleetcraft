# Evidence register

Observed on 2026-09-08. This integration is a **0.3.0 candidate**, not a stable release
or a demonstrated improvement over other agent systems. Popularity and permissive licenses
help select references; they do not establish quality.

| Check | Observed result | Limit |
|---|---|---|
| Standard-library test suite | 108 tests passed on macOS/Python 3.9.6 | Local fixtures, not production behavior |
| Source/plugin parity | Passed deterministic byte, mode and directory comparison | Re-run after every source change |
| Claude manifests | Marketplace and plugin strict validation passed | Schema validity alone is insufficient |
| Isolated clean install | Installed sparse 0.3.0 payload, doctor and package checks passed | Local marketplace fixture, not a public immutable release |
| Strict parser regression | Preserved pre-fix failures and candidate passes | Reconstructed immediate pre-fix source; not a v0.2 behavioral claim |
| GitHub workflow syntax | actionlint passed | Does not replace exact-commit CI |
| Credential preflight | Redacted gitleaks scan of publishable files passed | A point-in-time scan, not a security guarantee |
| Dependency advisory audit | OPEN: offline OSV npm database unavailable | No clean vulnerability verdict |
| Linux CI/public tag install | Observe exact commit/tag checks on GitHub | Prior main/PR runs do not certify this candidate |

## Live workflow smoke: mixed, behavioral gate OPEN

[Machine-readable summary](artifacts/live-smoke-summary-20260908.json) preserves run IDs,
case/prompt/package/trace hashes, individual verdicts and follow-up failures. Raw streams
remain private because they contain local runtime paths and session metadata. The public
summary is an author-reported result, not independently replayable proof or a signed
attestation. [The harness](evals/README.md) can produce fresh replayable bundles locally.

The first frozen batch ran 12 candidate and 12 Fleetcraft-absent baseline cases using
Claude Code 2.1.263, requested model `sonnet`, and observed model `claude-sonnet-5` where
trace validation succeeded. Each run used a fresh workspace/config, declared fixtures,
restricted tools and empty MCP configuration. Baseline CLI built-in skills remain available.
These are explicitly instructed skill-loading requests, not an automatic-routing benchmark.

- Candidate: 11/12 traces passed; 6/11 positive cases activated the expected skill, four
  did not, and one remained OPEN. The ordinary math negative correctly avoided activation.
- Candidate bounded quality checks: four PASS, three FAIL, five NOT_EVALUATED (including
  the invalid handoff trace). Debugging/performance exceeded 220 words; image analysis
  missed a required fact. Four routing-only cases do not grade answer quality.
- Baseline: 10/12 traces passed. Two were rejected for restricted-tool permission events.
  The full comparison correctly returns OPEN because not all evidence is valid. There is
  no supported aggregate quality-uplift conclusion.
- Visual/UI/fleet/image requests lacked a real design or code artifact. Several responses
  correctly requested that evidence instead of pretending to perform the workflow. Their
  failed activation expectations remain recorded; they are not proof of a product defect.
- The candidate handoff attempted unavailable `Write`. After adding an inline-draft
  fallback, the same-prompt follow-up passed trace and activation checks without that call.
- Follow-ups after word-budget guidance still exceeded 220 words: debug 258, performance
  242, handoff 235 (whitespace counts). All three failed quality checks; instructions are
  not a deterministic word-limit enforcement mechanism.
- One all-skills-disabled planning control also had a rejected permission-event trace and
  remains OPEN. It is separate from the primary baseline and establishes no comparison.

The three follow-ups used a changed package fingerprint and are reported separately from
the original batch. Earlier exploratory pilots used different prompts and are not folded
into these totals. No failed result was discarded or reclassified as an original pass.

## Adoption boundary

Use explicit skill invocation when selection matters, inspect actual tool results, and
keep independent verification for important work. Hooks are bounded controls, not a
sandbox or a guarantee that a model follows instructions. See [SECURITY.md](SECURITY.md)
and [COMPATIBILITY.md](COMPATIBILITY.md). Stable release readiness remains open until
representative artifact-backed, repeated behavioral checks justify it.
