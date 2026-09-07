---
name: image-to-code
description: "Implement a supplied visual reference as an accessible interface and compare a rendered result at the reference viewport; not for inventing a new design from an absent reference."
---

# Image to Code

Treat a supplied screenshot, mockup, or visual reference as the source of truth. Inspect it before implementation.

## Read the reference

- Record **observed** structure, type hierarchy, spacing, palette, controls, and supplied assets.
- Label unprovided assets, inferred breakpoints, hidden interactions, and unseen behavior **inferred**. A single reference does not establish another viewport or behavior.
- A still cannot establish motion. Request a video, frame sequence, or explicit motion decision before implementing animation.

## Implement and compare

- Reuse the project’s existing components, styles, and authorized assets where they match the reference. Do not add decorative controls, claims, imagery, text, logos, or other protected material beyond what was supplied or authorized.
- Preserve semantic structure, keyboard access, focus visibility, contrast, real-content behavior, and responsive reflow.
- Render with intended fonts and assets at the exact reference viewport. Compare visible features in order: structure, spacing, type, then decorative detail. Iterate on observed differences.
- Report unresolved differences and every inferred asset, behavior, or responsive constraint.

Generate original imagery only when explicitly requested or when an essential asset cannot be reconstructed safely from authorized material.

Provenance: independently authored portable synthesis informed by MIT-licensed screenshot-to-interface guidance; it does not reproduce upstream templates or automation behavior.
