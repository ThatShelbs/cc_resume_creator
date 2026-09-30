# Resume Taylor brand guide

<img src="../../webapp/frontend/public/favicon.svg" alt="Resume Taylor mark" width="96">

**Resume Taylor** is a pun on *tailor*: the app tailors your real history to each job,
and never makes anything up. The personality comes from sewing (dress forms, tape
measures, stitched seams), sparkle, and friendship-bracelet beads, all in a warm,
concert-evening palette.

## Palette

| Swatch | Name | Hex | Where it's used |
|---|---|---|---|
| ![](https://img.shields.io/badge/-%20%20%20%20-343C5B) | Midnight navy | `#343C5B` | Text, dark-mode surfaces, gradient start |
| ![](https://img.shields.io/badge/-%20%20%20%20-843745) | Burgundy | `#843745` | Primary (day), gradient end |
| ![](https://img.shields.io/badge/-%20%20%20%20-F8BDD5) | Pink | `#F8BDD5` | Primary (night), the *Taylor* wordmark, dress form |
| ![](https://img.shields.io/badge/-%20%20%20%20-D0B3D1) | Lilac | `#D0B3D1` | Accents (night), beads |
| ![](https://img.shields.io/badge/-%20%20%20%20-BDD6B9) | Sage | `#BDD6B9` | Success (night), beads |
| ![](https://img.shields.io/badge/-%20%20%20%20-F6CC8F) | Gold | `#F6CC8F` | Warning (night), sparkles, tape measure |
| ![](https://img.shields.io/badge/-%20%20%20%20-C2E8F6) | Sky | `#C2E8F6` | Info callouts, beads |
| ![](https://img.shields.io/badge/-%20%20%20%20-CEB499) | Tan | `#CEB499` | Dress-form stand, paper canvas |
| ![](https://img.shields.io/badge/-%20%20%20%20-D3CFC8) | Stone | `#D3CFC8` | Borders and inputs (day) |
| ![](https://img.shields.io/badge/-%20%20%20%20-7A7474) | Warm gray | `#7A7474` | Secondary text (darkened slightly for contrast) |

In code the raw colors are `--brand-*` CSS variables (`webapp/frontend/src/index.css`) and
Tailwind's `brand.*` colors. Components use the semantic tokens (`primary`, `success`,
`muted-foreground`, ...), which are tuned from the palette for readable contrast in each
theme. Prefer those over raw brand colors for anything that carries meaning.

## Type

- **Inter** for everything in the interface.
- **Fraunces italic** (`font-display`) only for the word *Taylor* in the wordmark and for
  occasional hero headings. Both fonts are bundled with the app (SIL Open Font License), so
  nothing loads from the internet.

## Logo

The mark is a tailor's dress form on a stand, with a gold tape measure at the neck, a strand
of palette beads at the waist, and a sequin sparkle, on a navy-to-burgundy tile.

- Source of truth: `webapp/frontend/public/favicon.svg`. Every raster is rendered from it by
  `python scripts/make_brand_assets.py` (desktop `.ico`, README banner, social preview).
- Keep it on its own tile; don't recolor, stretch, or add effects.

## Flourishes

- `BeadBracelet` and `Sequins` in `webapp/frontend/src/components/brand.tsx`.
- `.bg-brand-gradient`, `.stitch` (a dashed seam), and `.bead-rule` in `index.css`.
- Sewing words in progress steps ("Taking measurements", "Pressing the PDF"). Keep the
  detail line under each one plain and factual.
- Use flourishes in heroes, empty states, and moments of success. Never inside the resume
  itself: generated resumes, templates, and the resume preview stay neutral and ATS-safe.

## Naming and likeness guardrails

This is an independent, non-commercial, open-source project. To keep it that way, no code,
copy, or asset may use:

- any real person's name, likeness, silhouette, photo, or signature;
- song titles, album titles, lyrics, or lyric-adjacent puns;
- tour names or tour branding (including the word "Eras"), fan-community names, or any
  logo, font, or artwork belonging to someone else.

The nod stays in things nobody owns: a color palette, sparkle, friendship-bracelet beads,
and the *tailor* pun. When in doubt, pick a sewing reference instead.
