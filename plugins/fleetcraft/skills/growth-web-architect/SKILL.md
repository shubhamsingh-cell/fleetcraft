---
name: growth-web-architect
description: Architect or audit acquisition pages for conversion, accessibility, responsive behavior, and proof integrity. Use for marketing pages, not product workflows or routine frontend maintenance.
---

Ported from Codex on 2026-08-13, v1.

# Growth web architect
For a quick request, return the smallest complete requested artifact. For a formal audit or build, apply the full responsive matrix, proof register, gates, and acceptance ledger; never pad findings.
Start with audience, conversion mechanism, and a proof register before surface polish. Veto fabricated testimonials, logos, metrics, or case studies. Deliver a responsive matrix, reduced-motion, keyboard and error states, accessibility/axe check when available, a measured performance budget, technical-search handoff, funnel metric, owner, and human-readable binary acceptance checks.

Audits are read-only. Only implementation requests may add project-local pinned dependencies. Inspect existing stack; refresh facts with native `gh`, the `/agent-reach` Claude skill, or primary docs and record ADOPT/REFERENCE/REJECT. Run the repository's own lint/checks for framework-specific implementation work (e.g. after editing multiple components), and route framework-specific work to the matching installed skill if one exists; route rendered final output to the `/design-judge` Claude skill. If a named capability is unavailable, do not auto-install/network: use a safe local fallback when present and mark that gate incomplete. Do not deploy without explicit confirmation.

## Redesign boundaries

Redesigning an existing page is not building a new one. Recover the current conversion mechanism and product truth first — what the page actually promises, what its primary action is, which claims are load-bearing — and preserve them unless the user authorized replacing the mechanism itself. A redesign that quietly changes what the product claims is a product change wearing a visual costume, and it ships without anyone approving the product change.

A deliberately chosen aesthetic outranks a generic anti-slop ban. `design-judge`'s ai-slop checklist exists to catch defaults nobody chose; it does not veto a direction the user picked on purpose. When a flagged pattern *is* the stated design direction, keep it and record why the choice is deliberate rather than sanding it off to satisfy a generic rule.

## Harvest 2026-08-24

**Sources:** `Leonxlnx/taste-skill` MIT (`skills/image-to-code-skill/SKILL.md`) and `MickeyAlton33/web-designer-plugin` MIT (`README.md` + `skills/web-designer/design-patterns.md`), both fetched 2026-08-24.

**(a) Image-first gate.** For high-stakes hero/landing sections, taste-skill's image-to-code mechanism: generate a reference design image (or one image per section, never one compressed multi-section board) first, deeply analyze it (headline, subhead, CTA, spacing, color, component structure), THEN implement — never start with freeform coding when the visual problem should be solved with a reference image first. Optional, not mandatory: reach for it when a section is high-stakes enough that getting the reference wrong is expensive to unwind in code. **Asset authorization is separate from design authorization:** reach for image generation only when that capability is actually available and the user asked for it, and never place third-party artwork on a shipping page without a license that covers the use. This is a different failure from the fabricated-proof veto above — an invented logo wall and an unlicensed photograph are both ship-blockers, but only the first one is vetoed by the proof rule.

**(b) Motion-effect vocabulary (Aceternity UI — named treatments to reproduce, not a library to install):** spotlight card (cursor-tracked radial highlight on a card border/surface), background beams (animated light-beam field behind hero content), 3D tilt card (perspective rotation tracking cursor position), parallax hero (multi-layer depth on scroll), sparkles (subtle particle field for emphasis, used sparingly). Build these with native CSS/JS or the project's existing motion library per the pattern's mechanism — do not add the Aceternity package as a dependency.

**(c) Named reference case — unitedcarriers.com:** mechanism-first B2B hero ("One operator. Every leg of the journey.") answers the buyer's real fear (who's accountable when a shipment crosses carriers) instead of naming a feature; alternating content/image module rhythm down the page; proof stacked in one scroll — stat counters, three named/titled testimonials, two full airline+shipping-line partner-logo walls, four dated case studies (verified 2026-08-24, see design-judge's harvested catalog for detail).

**(d) web-designer-plugin's 48-patterns-from-38-real-sites list** (`skills/web-designer/design-patterns.md`) — best concrete patterns, each with its source site:
- **Museum Frame Modal** (Michael Kors Collection) — leave a thin border of background visible around a "fullscreen" modal instead of true edge-to-edge, reads as framed and deliberate.
- **Directional Underline** (Chiara Luzzana) — nav-link underline enters from the hover side, exits the opposite side on unhover, rather than a static fade.
- **Text-Slide Button** (April Ford) — button label slides up and out on hover, replaced by a duplicate label sliding in from below.
- **Two-Tone Split Heading** (Superlist) — bold claim in full-contrast color, supporting detail in muted gray, within the same headline.
- **Infinite Logo Ticker with Fade Masks** (Superlist) — seamless scrolling logo bar with a linear mask fading both edges to transparent, not a hard clip.
- **Torn Paper / Organic Edge Divider** (De La Calle) — an organic, non-geometric edge between two sections instead of a straight line.
- **Sharp-Corner Brutalist Cards** (De La Calle) — zero border-radius plus a visible stroke border for an editorial/zine feel, deliberately breaking a soft-radius system.
- **Giant Compressed Hero Text** (DONUTS) — display type treated as a graphic element (`clamp(5rem, 16vw, 15rem)`, tight negative letter-spacing, `line-height: 0.8`), not a normal heading.
- **Floating Overlapping Product Images** (DONUTS) — a product image breaks its section's boundary and overlaps into the section above/below for magazine-style depth.
- **Asymmetric Section Spacing** (Hardgraft) — 2:1 bottom-heavy padding ratio per section for a grounded, settled feel instead of symmetric top/bottom padding.
- **Viewport-Relative Spacing Scale** (Daylight) — a spacing scale defined in `vw` units so section rhythm breathes proportionally with viewport width instead of fixed rem steps.
- **Product Cards with Unique Backgrounds** (Magic Spoon, Snacklins) — each card in a product grid gets its own distinct background color/tint rather than a uniform card shell.
