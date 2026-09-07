# Review rubrics — anchored scales for the two-verdict review & judge panels

Prose criteria drift across reviewers. These anchors make the review criteria
inspectable. Score against the anchors; never improvise a scale mid-review.

## Verdict 1 — SPEC COMPLIANCE (4-point anchored scale)

- **4 / exact:** every requirement in the brief maps to shipped behavior; deltas (if
  any) were flagged BEFORE building, not discovered in review.
- **3 / complete-with-noted-delta:** all requirements shipped; one immaterial,
  explicitly-reported deviation (e.g. a rename for convention consistency). PASS.
- **2 / near-miss:** does *approximately* what was asked — a requirement reinterpreted,
  weakened, or silently dropped. **FAIL — this is the exact grade "looks good" hides.**
- **1 / off-spec:** solves an adjacent problem. FAIL; the brief itself may need the
  brief-lint (Lever 2 §8).

**Pass line: ≥3.** Worked example (fail): brief said "country filter must combine with
seniority"; implementation shipped both filters working *separately* — each demo'd fine,
the combination 500'd. That's a 2: every piece "works," the requirement doesn't.

## Verdict 2 — BUILD QUALITY (4-point anchored scale)

- **4 / clean:** tests non-vacuous (regression tests shown failing on pre-fix code),
  conventions matched, no new debt, validation actually run with output shown.
- **3 / acceptable:** minor debt explicitly declared (a TODO with an owner), everything
  else clean. PASS.
- **2 / unproven:** "tests pass" without showing which tests exercise the change, or a
  regression test never shown failing pre-fix. **FAIL.** Worked example: f0fd921
  (2026-07-15) — the regression test passed on the parent commit; it certified an
  unlocked door. Caught only because the reviewer demanded the failing run.
- **1 / degrading:** breaks conventions, adds untested paths, or removes existing
  coverage. FAIL.

**Pass line: ≥3, and NO vacuous test at any score.**

## Judge-panel scoring (design/strategy artifacts, N-lens panels)

Each lens scores 1-10 with two hard anchors so 7s mean something:
- **6 = shippable-but-forgettable:** competent, nothing broken, nothing memorable.
- **8 = expensive-feel:** a stranger would assume a serious team built it.
- Scores of 9-10 require the judge to name the ONE element that earns it.

Panel rules: lenses must be *different* (mechanism, craft, trust — not three clones);
majority carries; any single lens can VETO on a gate violation (class 7 fabricated
proof, class 3 design regression) regardless of average score — vetoes are why the
panel exists.

## Register check (for written artifacts)

Before shipping any document/message, one line: who is the furthest reader? In-room
operator → terse. Outside the room (exec, client, team channel) → answer-first MBB
structure. Mixed → write for the furthest reader. (From fable-judgment §3.)
