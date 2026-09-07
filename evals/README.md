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
