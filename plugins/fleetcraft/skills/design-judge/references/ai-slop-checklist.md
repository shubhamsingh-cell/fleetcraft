# AI-slop checklist — named tells the lens panel greps for

A catalog of specific, testable AI-design clichés the design-judge lenses cite instead of
re-deriving from taste each pass. **This is checklist content, not a replacement mechanism** —
the render→panel→verdict loop and the two protocol vetoes (iron rules 2 & 3) still govern. A tell
appearing here is a *prompt* for the lens to look closer, not an automatic veto; judge each
against the surface's actual intent (a monospace heading is a tell on a fintech page, a
correct choice on a developer-tools page).

**Provenance:** original rule harvest: `miqdadbadjuber/anti-slop` (MIT, © 2026 Miqdad
Badjuber), full revision `cd9aeb191dfe8a13980ded004b91959cf62bf15c` (tag `v3.1.1`),
read read-only on 2026-08-20. Later revalidation: full revision
`f686dac1494a46ec22bbeba38e04e1ce80908078` (tag `v3.2.1`), verified 2026-08-30.
The current Fleetcraft document contains 73 Markdown checklist entries, including 11
`[overlap]` annotations. These are observable document counts, not a completeness or
novelty claim about the upstream source. Its meta-framework (tiers/dials/install wizard)
was excluded because Fleetcraft uses a separate review protocol. Attribute the source if
any of this ships externally.

To recount in a source checkout, run:

```bash
awk '/^[-*] /{n++} /^[-*].*\[overlap/{o++} END{printf "checklist_bullets=%d overlap_annotations=%d\\n", n, o}' plugins/fleetcraft/skills/design-judge/references/ai-slop-checklist.md
```

To recount from the installed plugin/package root, run:

```bash
awk '/^[-*] /{n++} /^[-*].*\[overlap/{o++} END{printf "checklist_bullets=%d overlap_annotations=%d\\n", n, o}' skills/design-judge/references/ai-slop-checklist.md
```

Which lens owns which section: **brand-snap** → Color/Gradient, Imagery/Icons, Typography;
**typography & craft** → Typography, Layout/Spacing; **mechanism** → Layout mobile-reflow,
dead-control checks; **trust & proof** → Proof/Trust (runs iron rule 3); **first-five-seconds**
& **humanizer** → Copy/Microcopy; **expensive-feel** → Motion + the "sterile default" tell.

---

## Color & gradient  (lens: brand-snap)

- Blue→purple / blue→cyan / purple→pink gradient as the primary treatment, or a full-page
  colored glow, with no brand/hierarchy reason — **the single most-cited AI tell.**
- One accent color on buttons + icons + badges + links + lines + backgrounds + glows at once —
  the accent stops reading as an accent. Cap: one deliberate accent.
- Backdrop-blur/glassmorphism on navbar + cards + modals + sidebar simultaneously. Dose cap: 1–2 elements.
- Every element pill-shaped (buttons, inputs, cards, badges, modals) — no radius variation as hierarchy.
- Every component carries a large drop shadow — the whole page "floats," no elevation hierarchy.
- Glow on cards + buttons + icons + badges + backgrounds at once. Cap: 1–2 focus accents.
- Grid-squares / blueprint-lines / graph-paper background with no product-identity reason.
- Dark mode forced by default with no rationale, OR a light/dark toggle where one mode breaks styles.
- 5–7+ distinct colors on one screen with no system; cap 2–3 core + 1 accent (neutrals uncounted).
- **Sterile default:** flat white, thin-grey borders, no texture, zero identity — under-direction,
  the opposite failure from ornament-slop but equally a tell. (expensive-feel also flags this.)

### Contrast (measure, never eyeball — lens: typography & craft / accessibility)
- Body/label text below WCAG AA: normal < 4.5:1; large text < 3:1 only when it is at
  least approximately 24 CSS px normal weight or 18.5 CSS px bold (WCAG's 18 pt / 14 pt
  definition). Measure across the *whole* area the text crosses, at the worst spot, not
  the brightest.
- White/light text over a photo/gradient contrast-checked only at the lightest point.
- Any "looks like it passes AA" claim with no computed ratio (e.g. #555 on black = 2.82:1, a common false pass).
- Non-text UI (borders, focus rings, chart segments, status dots) under 3:1 vs background.
- Status/success/error by color alone, no icon/label pairing (fails color-blind + forced-colors).

## Typography  (lens: brand-snap / typography & craft)

- Large monospace headings for "terminal" aesthetic with no brand-character reason.
- Uppercase labels with extreme letter-spacing ("HOW IT WORKS") as a default, not a choice.
- Typeface is the model's reflexive default (Inter used unreasoned) — Inter isn't banned, an
  *unreasoned* pick is.
- Fixed-px font sizes identical desktop↔mobile (check computed font-size both widths; want `clamp()`).
- Text clipped or horizontally scrolling at 200% browser zoom.

## Layout & spacing  (lens: typography & craft; mobile items → mechanism)

- The template landing order (hero → subtitle → 2 CTAs → screenshot → feature grid →
  testimonials → FAQ → CTA → footer) with no content reason for each section.
- Feature/pricing/stat cards identical in size, height, icon, padding across the whole set — no hierarchy.
- One literal spacing value everywhere — no scale, no rhythm.
- "How It Works" forced to exactly 3 round-icon steps regardless of the real process.
- Middle pricing tier auto-highlighted "Most Popular" with no business reason.
- Rote 4-column Product/Company/Resources/Legal footer with half-empty columns.
- Dashboard defaults to sidebar + top bar + 4 stat cards + chart + table regardless of the decision the screen supports.
- **Mobile (mechanism-lens, zero-tolerance on horizontal scroll):** desktop layout merely
  shrunk (no reflow); breakpoints pinned to device widths not content; desktop padding/hero
  heights carried to mobile (empty deserts); `100vh` on mobile (use `dvh`); multi-column grids
  not collapsing ≤480px; **any** horizontal scroll at narrow width; `overflow:hidden` clipping
  text; tap targets < 44×44px or packed with no gap; hover-only reveals with no tap equivalent;
  desktop nav kept as a row; bare unlabeled hamburger; fixed nav covering content/forms; focused
  input hidden behind the mobile keyboard.

## Motion  (lens: expensive-feel)

- Elements that pulse/bounce/float in an endless loop with no user trigger and no UX purpose.
- Fade-Up + Fade-In + Float + Scale + Bounce on everything at once — template motion, not
  choreography to one focal element.
- Motion intensity mismatched to the surface's claimed register (a "calm" page auto-animating,
  a "cinematic" page inert). Lens question: *does the amount of motion match what this surface claims to be?*

## Imagery & icons  (lens: brand-snap)

- Generic-AI glyph set: sparkle, star, magic wand, lightning, diamond, cube, robot, "AI orb" —
  check relevance to the specific feature.
- Emoji as literal feature/section icons (🚀 ✅ 🔥 📈) in headings/bullets.
- Decorative → / ↗ arrows on nearly every button rather than the one action a direction cue helps.
- Capsule badges "AI Powered / Beta / New / Secure / Fast" with no real status — especially the
  full combo pill + thin border + glow + dot + uppercase.
- Generic stock illustration (Undraw, Storyset, 3D blob characters) with no product connection.
- Invented logo/avatar/profile photo generated with no brief or placeholder label.
- Skeleton/placeholder blocks used AS the hero "product screenshot" instead of a real shot or honest label.

## Copy & microcopy  (lens: first-five-seconds / humanizer)

> Before flagging prose, use any available voice-and-false-positives reference that documents
> what NOT to flag (polish, lone em dashes, formal vocabulary,
> curly quotes) and the human-signal markers that mean leave it alone. Tells cluster; isolated
> hits are noise.

- Em dash (`—`) anywhere in shipped UI copy — hardest-banned tell; also spaced ` — ` and ` -- `.
- Generic CTAs: "Get Started / Learn More / Try Now / Explore / Discover" naming no product-specific action.
- AI buzzwords: AI-Powered, Next-Generation, Revolutionary, Seamless, Cutting-Edge, Intelligent,
  Ultimate, Powerful, Effortless, unlock, elevate, empower, delve, robust, game-changer, journey.
- Grandiosity: "the future of X", "a pivotal moment", "a testament to", "ushering in a new era."
- Weasel attribution: "Experts say", "industry observers", "leading analysts believe."
- Chatbot artifacts: "I hope this helps!", "Let me know if…", "Would you like me to expand?"
- Fake-candid openers: "Honestly?", "Let's be honest", "Here's the thing", "Real talk."
- Meta-narration: "Let's dive in", "Here's what you need to know", "In this article we'll explore."
- Sentence-internal ALL-CAPS for manufactured urgency.
- Actorless passive where an actor existed ("the pricing page has been updated" vs "we updated…").
- Abstraction given a human verb ("the data tells us", "the dashboard understands").
- Forced rule-of-three — every list padded to three.
- Negative-parallelism: "It's not just X, it's Y" / "Not only X but also Y" / clipped "no guessing, no waste."
- Aphorism formula: "X is the language of Y", "X is not a tool but a mirror."
- Staccato-drama runs ("No templates. No defaults. No safety.") — one is fine, a run is the tell.
- Synonym-cycling for one claim ("fast/quick/speedy") instead of repeating the clearest word.
- False range: "from onboarding to scale", "from first click to final invoice."
- Filler: "in order to", "due to the fact that", "at this point in time", "it is important to note."
- Stacked hedging: "could potentially possibly", "may perhaps."
- Mechanically bolded key terms throughout body copy — emphasis everywhere = emphasis nowhere.
- Quotation marks as default hedge around ordinary words.
- Inline-header list items where the bold header just restates the following sentence.
- Decorative emoji leading headings/bullets that add no information.
- Template FAQ ("Is my data secure?", "Can I cancel anytime?") with no evidence these are real questions.
- Navbar links pointing to pages/sections that don't exist in the build. `[overlap → mechanism]`

## Proof & trust  (lens: trust & proof — runs iron rule 3; every item here is veto-eligible)

- Stat counters with no citable source: "10K+ Users", "99.9% Uptime", "500M Requests". `[overlap]`
- Testimonials with AI avatars, invented names/titles, or fictional quotes. `[overlap]`
- Fabricated compliance/perf claims: "SOC 2", "ISO 27001", "Enterprise-grade", "300% faster". `[overlap]`
- Any realistically-styled fabricated content (invented features, ghost links, fictional team) vs a labeled placeholder. `[overlap]`
- Dashboard stat row with invented numbers and a green "+12% this week" delta with no series behind it. `[overlap]`
- Filler activity feed ("Sarah Chen updated a document, 2h ago") faking busyness. `[overlap]`
- Form/table cells filled with plausible-fake data (John Doe / johndoe@example.com) vs empty + honest label. `[overlap]`
- Empty/loading/error states present in name only ("No data available", no cause/next action). `[overlap → mechanism]`
- Dead interactive controls — every button/dropdown/form has real behavior or is visibly "Coming soon." `[overlap → mechanism]`
- Visual clone of a named product (Linear/Vercel/Stripe/Notion) with no request to — an originality/trust issue. `[overlap → brand-snap]`

---

**Integration note:** fold the relevant section into each lens's prompt as "grep for these named
tells, then judge against the surface's real intent." Do NOT adopt anti-slop's PASS/FAIL tiering,
dials, or its `CLAUDE.md`-editing install wizard (that section was excluded at harvest as
agent-directed config mutation). The checklist informs judgment; it does not replace the loop.
