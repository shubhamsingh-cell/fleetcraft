---
name: design-judge
description: >-
  Screenshot-first design judgment protocol for UI/page/deck/creative review. Load when
  judging whether a visual surface is ready to ship
  ("is this good enough", "does this look right", "review this design", "ship it?"),
  when choosing between design directions, or before any user-facing surface goes
  live. Runs a render→lens-panel→verdict loop with protocol vetoes for fabricated proof
  and design regressions. Invoke /fleetcraft:design-judge explicitly before shipping any visual
  surface if it hasn't fired on its own.
---

# design-judge — screenshot-first design review

> **v3 · 2026-08-04.** Hardening pass: added the Harness & verification traps section —
> static harnesses built from `outerHTML` drop IDL state and produce phantom vetoes,
> preview screenshots blank after any DOM mutation, CSS claims must be checked by
> computed style + real interaction (never your own stylesheet), and immutable-cached
> assets need an explicit cache-bust before a lens screenshots the "new" version.
>
> Prior **v2 · 2026-07-25.**
>
> Prior **v1 · 2026-07-15.**

This is a review protocol, not a substitute for a senior designer or a claim about any
model's taste. Historical examples in older revisions are author-reported anecdotes;
use the rendered artifact and an approved baseline as the evidence for the current call.
Any named incident, catalog summary, or live-site description below without a linked,
stored artifact is likewise an author-reported anecdote, not a current verified fact.

## Iron rules (before any judgment)

1. **Nothing is judged unrendered.** Render the artifact and screenshot it. Restart the preview
   after template edits, and bump the `?v=` cache-buster on every edited linked asset
   before judging — immutable-cached surfaces can otherwise show a stale result. Use the
   headless-render toolchain for decks (qlmanage/PIL/PyMuPDF). Judge the pixels, not
   the code.
2. **Mechanism before surface.** First
   question is never "is it pretty" — it's "is the underlying mechanism right?" A
   motif repeated 3+ times, or a component needing an exception every reuse, is a
   mechanism problem: kill it, don't polish it (plan-card motif → one Prediction
   Engine; navy band → invisible scaffold).
3. **Proof honesty is a protocol veto, not a score.** Testimonials, counters, logos, case
   studies: real artifact or explicit "illustrative" label — or the surface doesn't
   ship regardless of how good it looks.
4. **Regression is a protocol veto too.** On any previously-approved surface, judge
   against the last APPROVED render, not against nothing. A lens that finds an approved
   decision silently reverted vetoes regardless of score.
   (fleet-orchestrator gate class 3.)

## Harness & verification traps

Checks inside the render→lens→verdict loop, not a new philosophy — each has cost a
full judging round when skipped.

- **Static harness ≠ live page.** A harness rebuilt from `element.outerHTML` (the
  fallback when the real page won't screenshot) drops IDL state — `select.selected`,
  `checked`, `value`, `indeterminate`, scroll position never serialize as attributes,
  so a correctly-placeholdered dropdown falls through to its first enabled option in
  the harness alone. A lens VETO sourced from a static snapshot is a phantom defect
  until re-verified against the LIVE DOM (`javascript_tool` inspection) — precedent:
  a mechanism-lens veto on a dropdown that was actually fine, 2026-07-31. Also don't
  hand-abridge harness data (a truncated option list reads back as a product defect).
- **Screenshots go blank after DOM mutation.** Preview screenshots return an
  all-white frame after any JS mutation or resize; only a fresh `navigate` repaints.
  Never score a blank or post-mutation screenshot — sequence is navigate → mutate →
  inspect via JS → rebuild+navigate for pixels.
- **Verify by computed style and real interaction, never your own CSS.** A global
  reset can silently strip what your stylesheet promises — `buttons.css`'s
  11-`:not()` reset zeroed a new button class's border and clipped its focus ring
  while the authored rule read fine on paper. Assert `getComputedStyle`, not source
  text, and drive focus states with an actual Tab keypress (`.focus()` under-reports
  `:focus-visible`).
- **Stale-asset false-pass.** Immutable-cached static assets serve the OLD file to a
  lens screenshot unless the referring page's `?v=`/`?fresh=` is bumped first — same
  failure as iron rule 1's cache-buster clause, but it also fires mid-panel: a lens
  can screenshot a "fixed" surface that's still serving the pre-fix asset.
- **Context-light screenshot path.** When a lens needs only pixels, use an already
  installed, project-pinned `@playwright/cli` or an available browser tool. Do not fetch
  a package through bare `npx playwright-cli`; it can resolve a deprecated unscoped
  package. Anything needing computed style, IDL state, or a real Tab keypress still goes
  through an interactive browser path.

## The panel

For anything shipping to a real audience: use 3 parallel independent judges, each with a
DIFFERENT lens — never three clones. Dispatch every acceptance lens as the `verifier`
role; choose a capability-matched model/effort using the active harness. An executor may
provide an implementation self-check, but never the final panel verdict.

**mechanism is mandatory** on every panel, and **trust & proof is mandatory** on any
surface carrying proof elements — they are the only executors of iron rules 2 and 3,
and a panel without them cannot fire either veto. Pick the remaining lens(es) per
artifact:

- **mechanism** — is the structure right, or is polish hiding a wrong mechanism?
- **craft and coherence** — does the result demonstrate deliberate hierarchy, fit, and
  finish for its audience?
- **typography & craft** — scale hierarchy, spacing rhythm, alignment discipline; the
  details that separate designed from assembled.
- **brand-snap** — does every color/type/component choice trace to the brand system,
  or is it template default wearing a logo?
- **trust & proof** — does the page earn belief without fabricating it? (Runs rule 3.)
- **first-five-seconds** — what does a cold visitor understand, feel, and want to do?
- **expensive-feel** — does motion and the overall surface feel intentional and
  product-specific rather than sterile or template-default?

Each judge returns: score /10 against the anchored scale in
`../fleet-orchestrator/references/review-rubrics.md`, the ONE strongest
strength, the ONE change that would raise the score most, and any veto.

Each lens greps its section of `references/ai-slop-checklist.md` before scoring. The
checklist has 73 Markdown entries, 11 with overlap annotations; it covers tells such as
gradients, capsule badges, sparkle icons, em dashes, rule-of-three, mobile-reflow
failures, WCAG contrast formula, and fabricated-proof patterns. See that file for the
reproducible count, then judge
each hit against the surface's real intent — a named tell is a prompt to look closer, not
an automatic veto. The checklist informs the lenses; it does not replace the render→panel→
verdict loop or the two protocol vetoes.

## Verdict & loop

- **A judge that errored or timed out is an OPEN lens, never a passing one.** Re-run
  it, or report the verdict as INCOMPLETE naming the lens that never returned — "no
  vetoes raised" and "a lens did not complete" must never collapse into the same
  line. No panel may say Ship without a live mechanism verdict and, on any surface
  carrying proof, a live trust & proof verdict.
- **Ship:** median ≥8, zero vetoes.
- **Iterate:** median 6-7 — apply ONLY each judge's named top change, re-render,
  re-judge (same lenses, fresh context). Two iterations without breaking 8 = the
  mechanism is wrong; stop polishing (rule 2).
- **Kill/rebuild:** median ≤5, any mechanism-lens fail, or persistent veto.

Owner calibration: design-critical user; ask before pushing design changes to a
live surface; express your own brand system consistently on your own properties.

## Harvested anti-cliché catalog (taste-skill, 2026-08-24)

**Provenance:** `Leonxlnx/taste-skill` (MIT, © 2026 Leonxlnx), fetched 2026-08-24 from
`skills/taste-skill/SKILL.md` (core anti-slop skill, ~1200 lines) and
`skills/image-to-code-skill/SKILL.md` (image-first Codex variant, ~1200 lines). Checked against
`references/ai-slop-checklist.md` first — only tells NOT already covered are listed below.

**Duplicates skipped** (already in ai-slop-checklist.md): blue/purple "AI glow" gradient
(taste-skill's LILA RULE = checklist's Color&gradient #1); three-equal feature cards (checklist
Layout&spacing); capsule status badges with no real status (checklist Imagery&icons); em-dash as
a design tell (checklist Copy&microcopy #1 — taste-skill's own EM-DASH BAN is the stricter,
zero-tolerance version, no "sparingly" allowance); pill-shaped-everything (checklist
Color&gradient, overlaps taste-skill's Shape Consistency Lock).

**New named tells** (brand-snap / mechanism / expensive-feel lenses grep these):
- **Cards-in-cards-in-cards** (image-to-code-skill's ANTI-NESTED-BOX RULE) — "cards inside larger
  cards inside outer cards," giant rounded section containers wrapping bordered panels wrapping
  more bordered panels. Prefer open layouts, one primary framing move.
- **Centered-dark-hero cliché** — named directly in image-to-code-skill's default-tell list;
  taste-skill's ANTI-CENTER BIAS rule operationalizes it: avoid a centered hero/H1 over a dark
  mesh background once the surface wants any real design variance; force split-screen,
  left-aligned content/right asset, or asymmetric white space instead. Override: centered is fine
  for a manifesto/launch brief where the message IS the design.
- **Fake UI jargon pills** — image-to-code-skill's REDUCE MICRO-UI CLUTTER RULE: unnecessary
  pills, pseudo-system markers, fake control labels, decorative code-like tags, filler chips,
  "fake dashboard jargon" (named example: `"00 orchestration layer"`), filler
  operator/control-room labels that exist only to look complex. Broader than the checklist's
  capsule-badge item — also covers section-numbering eyebrows (`00 / INDEX`, `001 · Capabilities`),
  version footers on marketing pages (`v1.4.2`, `Build 0048`), and decorative status dots with no
  real semantic state (taste-skill §9.F).
- **Premium-consumer palette ban** ("cream+terracotta" family) — taste-skill §4.2: the AI default
  for cookware/wellness/artisan/luxury/DTC-home briefs is warm cream/beige backgrounds
  (`#f5f1ea`, `#faf7f1`, `#ece6db`...) + brass/clay/oxblood/ochre accents (`#b08947`, `#9a2436`,
  `#7d5621`...) + espresso near-black text. Banned as a default reach; rotate among Cold Luxury,
  Forest, Black-and-Tan, Cobalt+Cream, Terracotta+Slate, Olive+Brick+Paper, or monochrome+pop
  instead, and never ship the same family twice in a row.
- **Off-black / off-white discipline** — taste-skill §8.B/9.A: no pure `#000000` or `#ffffff`
  anywhere; use zinc-950/near-black warm-gray and off-white. Pure values read as flat/AI-default.
- **Hairline-as-decoration ban** — taste-skill §9.F: crosshair/hairline grid lines drawn only to
  make a page "feel designed," and `border-t`+`border-b` on every row of a long spec table/list
  (the single worst default for spec sheets), are both banned; hairlines earn their place only
  when they organize real content.
- **Eyebrow restraint (mechanical count)** — max 1 small-caps eyebrow label per 3 sections (hero
  counts as 1); the Pre-Flight check literally counts `uppercase tracking` instances and fails if
  count exceeds `ceil(sectionCount / 3)`.
- **No duplicate CTA intent** — two CTAs carrying the same intent anywhere on one page ("Get in
  touch" + "Let's talk" + "Contact us") is a fail; one label per intent, everywhere on the page.
- **Zigzag alternation cap** — max 2 consecutive left-image/right-text (or reverse) sections; a
  3rd in a row is a fail.
- **Split-header ban** — "left big headline + right small explainer paragraph" as a section header
  is banned by default; stack vertically instead unless the right column carries a real visual.
- **Marquee max-one-per-page** — more than one horizontal scrolling-text marquee on a page reads
  as lazy filler.
- **Serif discipline** — taste-skill flags serif as a recurring default for generic
  “creative brief” styling; `Fraunces` and `Instrument_Serif` are named examples. Treat
  this as an upstream author-reported heuristic, not a measured Fleetcraft result.

**Not found verbatim:** the brief's shorthand "near-black+acid-green" and "broadsheet/hairline-rule"
do not appear as named archetypes in either fetched file — closest real content is the off-black/
off-white discipline and the hairline-as-decoration ban above. "Acid green" as a named hover-state
color appears only in the separate `web-designer-plugin` repo's brutalist-agency example, not in
taste-skill. Used the real content rather than forcing a match; see report for detail.

**Proof-integrity positive reference:** unitedcarriers.com (author-captured 2026-08-24; re-check before reuse) stacks stat
counters, three named/titled testimonials, two full airline+shipping-line partner-logo walls, and
four dated case studies in one scroll — every element traceable to a real claim. This is the shape
a passing proof stack takes; contrast against iron rule 3's vetoed examples.
