---
name: performance-diagnosis
description: "Diagnose and fix slow software with measurement, not guesswork — slow pages, slow API endpoints, slow SQL, N+1 queries, connection-pool exhaustion, cache design, Core Web Vitals regressions. Use when something is slow, when a latency or Core Web Vitals target is missed, when a query or endpoint regressed, or when planning a cache. Not for correctness bugs (use debugging-and-error-recovery) or for code cleanliness refactors (use simplify)."
---

# Performance diagnosis

Optimization without a baseline is decoration. Every rule below exists to stop a plausible
change from being kept on vibes.

## 1. Measure before touching anything

No performance work starts without a recorded baseline: the exact command or URL, the
conditions (cache cold/warm, dataset, concurrency), and the number. Write it down before the
first edit — a baseline reconstructed afterwards is a memory, not a measurement.

Take both kinds where they exist: **synthetic** (a repeatable local/CI run — Lighthouse, a
timed query, a load script) for reproducibility, and **field/RUM** (`web-vitals`, CrUX, p95
from real traffic) to confirm users actually feel it. Synthetic-only improvement is a claim
about your laptop.

Thresholds worth naming when the ask is vague: LCP ≤2.5s, INP ≤200ms, CLS ≤0.1. For backend
work, argue in **p95/p99**, never mean — the mean hides the experience people complain about.

## 2. Route by symptom, don't grep for something slow-looking

Pick the tree from what the user actually reports:

- **Slow first load** → payload and critical path: bundle size, render-blocking assets, image
  weight, server TTFB.
- **Sluggish interaction** → main-thread work, re-render storms, unbatched state, long tasks.
- **Fast page, slow data** → the request: N+1, unbounded fetch, missing index, pool contention.
- **Everything slowed at once** → shared resource, not code: connection pool, CPU/memory
  ceiling, a saturated upstream, a noisy neighbour.

## 3. Database work: read the plan, then decide

- Start with plain `EXPLAIN`; it does not execute the statement. `EXPLAIN (ANALYZE, BUFFERS)`
  executes it, so use it only for a known read-only statement after confirming scope, runtime
  budget, and authorization. The plan is evidence; "probably needs an index" is a guess.
- Read for: sequential scan on a large table, row estimates far off actual, an unexpected sort
  or hash spill, and time concentrated in one node rather than spread.
- **Composite index order**: equality columns first, then the range/sort column.
- **Know when an index will NOT help** and say so instead of adding one: the filter matches a
  large share of rows (low selectivity), a leading-wildcard `LIKE '%x'`, a function-wrapped or
  type-cast column that defeats the index, or a write-heavy table where the write cost exceeds
  the read win.
- **N+1**: fix with a join/`include`/batch load, not a faster per-row query. A 200× loop of 2ms
  queries is a 400ms problem that no index fixes. **Condition, not a blanket rule:** joining a
  *narrow* parent is right; joining a *wide* parent (JSONB/TEXT/BYTEA columns) multiplies those
  wide rows across every child and can cost more in bytes than the round trips saved — there,
  split it into two queries. Decide by row width, not by round-trip count.
- **Unbounded fetch**: paginate or cap. `findMany()` with no limit is a production incident
  waiting for the table to grow.
- **Connection-pool exhaustion** has a signature: every endpoint degrades together while the
  database itself looks idle (sessions mostly idle-in-transaction or waiting). The fix is
  sizing the pool against the database's real ceiling, shortening transactions, or putting a
  multiplexer in front (pgbouncer, RDS Proxy) — **not** raising `max` until the database dies.
  On serverless/autoscaling Postgres, more concurrency is frequently *slower*: measure it.
  (Precedent, a production CRM on the managed Postgres provider, 2026-07-31: fan-out
  concurrency 4 measured slower than 2.)

### Index tuning: measure the plan, don't build the index

Building an index to see if it helps is a migration you then have to undo. If the existing,
authorized database already exposes a hypothetical-index extension, use its documented
session-scoped workflow only after checking permissions and cleanup semantics. Compare plain
`EXPLAIN` estimated costs before and after; estimated cost is planning evidence, not runtime
proof. Do not install extensions as part of diagnosis. Build only an index whose measured runtime
and write/storage tradeoff justify it.

### Cost-shaped queries — on serverless Postgres, bytes are the bill

On the managed Postgres provider and similar, egress and compute-time dominate; milliseconds
are a proxy, not the invoice.

- **Rank by bytes, not time.** Order `pg_stat_statements` by `rows` and `rows/calls`, and
  cross-reference the schema for wide JSONB/TEXT/BYTEA columns. The slowest query and the most
  expensive query are frequently not the same query.
- Snapshot a representative observation window and compare deltas. Do not reset shared statistics
  during diagnosis: that changes other users' observability. Confirm extension and
  provider support from the actual environment before depending on either.

## 4. Caching is a correctness feature that happens to be fast

- Cache only what is expensive to produce and read far more often than it changes.
- **Every input that changes the response must be in the key** — tenant, user, locale, role,
  feature flag, currency. A missing key input is not a cache-hit-rate issue; it is a data leak
  that serves one user's content to another.
- Pick **one** invalidation strategy — TTL, event/tag-based, or versioned keys. Mixing two
  produces a system nobody can reason about at 2am.
- Guard the stampede: stale-while-revalidate or single-flight coalescing on a hot-key miss,
  or the first expiry becomes an outage.
- For balances, permissions, inventory, and failures, define the correctness and staleness
  requirements first. Cache only if its key, invalidation, and bounded stale behavior satisfy
  those requirements; otherwise keep the authoritative path.

## 5. Verify: keep or revert, and neutral is a revert

Re-measure under **identical conditions** to the baseline — same command, same cache state,
same dataset, same concurrency. A cold-vs-warm comparison measures the cache, not your change.

Change one thing at a time. If several must ship together, measure each in isolation first,
or you have shipped a bundle with an unknown active ingredient.

| Result vs. baseline | Action |
|---|---|
| Past the target, tests green | **Keep** |
| Within measurement noise | **Revert** |
| Worse | **Revert** |
| Improved but a test broke | **Revert**, then fix the correctness problem first |

**"Neutral" is a revert, not a keep.** An unmeasurable optimization is permanent complexity
bought with nothing — the most common way a codebase gets harder to change for no gain.

Log every attempt, *including the reverted ones*, in the PR description, or in the project's
existing state file if it has one. Do NOT create a fresh `PERF.md` beside an existing state
convention — `project-handoff` owns that rule (never a second state system). The
ledger's real value is stopping the next person re-trying an idea that was already measured
and rejected.

## 6. Rank findings by severity, not by discovery order

A profiling pass returns a pile of findings. Report them tiered, so the reader fixes the
right one first rather than the one you happened to find first:

- **Critical** — actively degrading production now, or a correctness/leak risk (missing cache
  key input, unbounded query on a growing table, pool exhaustion under normal load).
- **High** — a measured user-visible miss against a stated target (p95 over budget, LCP > 2.5s).
- **Medium** — measured waste with no current user impact; will bite at the next growth step.
- **Low** — theoretical or unmeasured. If it is unmeasured it cannot rank higher than Low,
  however obvious it looks.

*(Tiering convention adapted from `supabase/agent-skills`' Postgres performance categories,
MIT, reviewed 2026-09-07 — concept only, no text reused.)*

## 7. Guard the win

Put a budget on the metric users actually feel (p95, LCP, INP) in CI, plus field monitoring.
When either fires, restart from step 1 with a fresh baseline — do not keep patching against a
stale measurement.

## Rationalizations this skill exists to refuse

"It's obviously faster." "We'll measure it later." "It can't hurt." "Just add an index."
"The mean looks fine." Each of these is a decision to skip the step that would have shown the
change did nothing.

## Boundaries

Reproducing a failure before changing code, and proving a regression test fails pre-fix, are
`fleet-orchestrator`'s standing gates — they apply here too and are not restated. Correctness
bugs go to `debugging-and-error-recovery` — **arbitration for the genuine overlap:** an error or
timeout that appears ONLY under load starts here (a capacity symptom); an error with any other
trigger starts there. Structural "what calls this" questions are cheaper
through `graphify` than by re-reading files.

## Response shape

Honor an explicit user format or word limit before this skill's default detail. Reserve a small
margin, merge non-material sections, and count words with an available local means when a cap was
requested. Retain the baseline, measured finding, decision, and validation; do not expand a
response merely to repeat every diagnostic branch.

*Independently authored 2026-09-07, informed by `addyosmani/agent-skills` (MIT, © 2025 Addy
Osmani) at commit `469d00f4e67ff4a21eb6e6e467a086c9a1f1deb8`; no text reused.*
