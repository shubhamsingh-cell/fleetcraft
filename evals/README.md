# Fleetcraft evaluations

The default command only validates corpus structure:

```bash
python3 scripts/evaluate_skills.py
```

To run one isolated candidate case, use
`python3 scripts/evaluate_skills.py --live --mode candidate --case plan --output-dir artifacts/evals --model sonnet --budget 0.25 --timeout 90`.
Use `--mode baseline` for the primary no-plugin comparison and `--mode disabled-control` only
as sensitivity evidence because it also removes built-in skills. Raw streams remain local under
`artifacts/evals/`. Trace integrity, activation, and output quality are separate verdicts;
token or cost telemetry is overhead evidence, never quality proof.

Validate a completed record before using it:

```bash
python3 scripts/evaluate_skills.py --validate-record artifacts/evals/RUN/candidate/plan/record.json
```

This command returns zero only for replay integrity. Its output still shows trace, activation,
quality, and candidate acceptance; use `--compare` to evaluate paired acceptance.

Compare a scoped candidate/baseline pair only after both records validate:

```bash
python3 scripts/evaluate_skills.py --compare CANDIDATE_RECORD BASELINE_RECORD --scope plan
```

Without `--scope`, comparison requires a valid candidate and primary baseline record for every
declared corpus case. Comparison reports `pair_integrity: COMPARABLE` separately from
`candidate_acceptance`; it does not claim an uplift, quality win, or general behavior from a small
sample. Deterministic quality checks use declared fixture facts and bounded lexical rules;
they leave routing-only cases `NOT_EVALUATED` and cannot establish general reasoning or injection
resistance. No command invokes a provider unless `--live` is passed.

The current corpus is an **instructed workflow activation smoke**: each positive prompt asks the
runtime to use or load a relevant installed skill if available. It does not measure automatic
routing or comparative improvement. The earlier exploratory schema-1 records used different
prompts and kernel behavior, so they are retained as historical evidence only.

New run records use schema 2 and hash raw streams, stderr, case, prompt, fixtures, and the full
plugin tree. These hashes detect local changes but are not signatures or execution attestations;
a fully rewritten bundle has no trusted external anchor. Exploratory schema-1 records remain
immutable and are not replayed with this scorer.

## First-party runner (`claude plugin eval`, early access)

```bash
CLAUDE_CODE_WALNUT_SPIRE=1 claude plugin eval ./plugins/fleetcraft --ablation with-without --runs 3 --report evals/results/report.html --json evals/results/result.json
```

**Status — discovered and schema-valid, not yet a measurement.** A real single-case run on
2026-10-11 (Claude Code 2.1.263, host authenticated by interactive login) found and parsed the
case, then ended `partial: true`, `partialReason: "auth_failed"` with the sandboxed agent
reporting `Not logged in`: the runner uses a fresh config directory and does not inherit the
host login. **Always check `partial`/`partialReason` before reading a score** — that run still
printed `overallScore: 0.5`, because a `min: 0, max: 0` grader passes when no agent ran. How to
authenticate the sandbox is undocumented in the CLI's embedded reference and was not attempted
(it means giving the harness a credential and spending API money). See
`docs/SKILL_ACTIVATION.md`, "A run that measured nothing".

This gate is early-access and sits behind that environment variable; without it, `claude plugin
eval` refuses to run at all. `--ablation with-without` runs every case twice, with and without the
plugin, and reports the score delta. A `tool_used: Skill` grader with no `arm:` key is
**display-only** under that ablation: dropped from the baseline arm and reported as
`[with-only, not scored]` rather than counted in either arm's score. That is deliberate — adding
`arm:` would start scoring a check the no-plugin baseline can never pass and inflate the measured
uplift. `evals/plugin-eval/math/case.yaml` is the one documented exception: its `tool_used` grader
sets `arm: both` because that case's whole point is asserting the skill does **not** fire on
either arm.

The 12 cases under `evals/plugin-eval/<id>/case.yaml` are the same 12 cases as
`evals/skill-routing.json`, with each case's fixtures inlined directly into the prompt (the
runner's sandbox cwd carries no fixture files, so a case cannot reference a path) and
`allowed_tools` restricted to `[Skill]` so a run measures activation only, not what the model does
once a skill has loaded.

This runner is complementary to `scripts/evaluate_skills.py`, not a replacement: the Python
harness above validates corpus structure and (with `--live`) runs scoped, replay-verified live
comparisons outside the sandboxed CLI harness; `claude plugin eval` is the first-party sandboxed
ablation runner for the installed plugin itself. Use both.
