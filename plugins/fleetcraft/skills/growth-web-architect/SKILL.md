---
name: growth-web-architect
description: "Architect or audit marketing/acquisition homepages and landing pages — conversion mechanism, responsive matrix, proof integrity (a protocol veto for fabricated testimonials/logos/metrics/case studies), reduced-motion and keyboard/error states, accessibility check, and technical-search handoff. Trigger on: \"build/redesign our homepage\", \"landing page for <campaign/launch>\", \"pricing page\", \"waitlist/signup page\", \"marketing site\", \"conversion page\", \"hero section\", \"campaign microsite\". Excludes ordinary product UI (dashboards, settings, in-app workflows — use product-interface-craft) and routine frontend maintenance. Audits are read-only; routes rendered output to the design-judge skill before shipping; deploys require explicit confirmation."
---

# Growth web architect
For a quick request, return the smallest complete requested artifact. For a formal audit or build, apply the full responsive matrix, proof register, gates, and acceptance ledger; never pad findings.
Start with audience, conversion mechanism, and a proof register before surface polish. Treat fabricated testimonials, logos, metrics, or case studies as a protocol veto. Deliver a responsive matrix, reduced-motion, keyboard and error states, accessibility/axe check when available, a measured performance budget, technical-search handoff, funnel metric, owner, and human-readable binary acceptance checks.

Treat approved specifications, copy, assets, conversion flows, and rendered approved surfaces as the baseline authority. A scoped refinement preserves the conversion mechanism and product truth. An authorized redesign may change the aesthetic only within its stated scope. Missing design documentation does not make an established page greenfield.

Preserve the page’s real conversion mechanism and information density; do not replace useful controls or evidence with decorative surface treatment. Audits are read-only. Only implementation requests may add pinned dependencies. Inspect the existing stack and record ADOPT/REFERENCE/REJECT. Send rendered final output to design-judge. Detect an optional capability before naming it; if unavailable, do not install or use a network fallback automatically, and mark that gate incomplete. Do not deploy without explicit confirmation.

For changed overlays or controls, verify clipping, focus entry and return, narrow viewports, zoom, and long or overflowing content whenever applicable.

## Harvest 2026-08-24

**Sources:** `Leonxlnx/taste-skill` and `MickeyAlton33/web-designer-plugin` (MIT), both fetched 2026-08-24.

**(a) Image-first gate.** For high-stakes hero/landing sections, taste-skill's image-to-code mechanism: generate a reference design image (or one image per section, never one compressed multi-section board) first, deeply analyze it (headline, subhead, CTA, spacing, color, component structure), THEN implement — never start with freeform coding when the visual problem should be solved with a reference image first. Optional, not mandatory: reach for it when a section is high-stakes enough that getting the reference wrong is expensive to unwind in code.

**(b) Motion choices.** Use motion only when it clarifies hierarchy, state, or a specific
brand direction. Implement the smallest accessible effect with native CSS/JS or the
project's existing motion library; respect reduced-motion preferences and do not add a
dependency merely for decoration.

**(c) Named reference case — unitedcarriers.com:** author-captured 2026-08-24 and subject to change; re-check the live page before reuse. Its mechanism-first B2B hero ("One operator. Every leg of the journey.") answers the buyer's real fear (who's accountable when a shipment crosses carriers) instead of naming a feature; alternating content/image module rhythm down the page; proof was stacked in one scroll at capture time — stat counters, named/titled testimonials, partner-logo walls, and dated case studies.

**(d) web-designer-plugin's 48-patterns-from-38-real-sites list** — best concrete patterns, each with its source site:
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
