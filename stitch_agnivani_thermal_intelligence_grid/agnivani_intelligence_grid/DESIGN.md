---
name: AGNIVANI Intelligence Grid
colors:
  surface: '#10131b'
  surface-dim: '#10131b'
  surface-bright: '#363941'
  surface-container-lowest: '#0b0e15'
  surface-container-low: '#181c23'
  surface-container: '#1c2027'
  surface-container-high: '#272a32'
  surface-container-highest: '#31353d'
  on-surface: '#e0e2ed'
  on-surface-variant: '#bbc9cd'
  inverse-surface: '#e0e2ed'
  inverse-on-surface: '#2d3038'
  outline: '#859397'
  outline-variant: '#3c494c'
  surface-tint: '#2fd9f4'
  primary: '#8aebff'
  on-primary: '#00363e'
  primary-container: '#22d3ee'
  on-primary-container: '#005763'
  inverse-primary: '#006877'
  secondary: '#c0c7d4'
  on-secondary: '#2a313b'
  secondary-container: '#404752'
  on-secondary-container: '#afb5c2'
  tertiary: '#ffd6a3'
  on-tertiary: '#462b00'
  tertiary-container: '#ffb13b'
  on-tertiary-container: '#6e4600'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#a2eeff'
  primary-fixed-dim: '#2fd9f4'
  on-primary-fixed: '#001f25'
  on-primary-fixed-variant: '#004e5a'
  secondary-fixed: '#dce3f0'
  secondary-fixed-dim: '#c0c7d4'
  on-secondary-fixed: '#151c25'
  on-secondary-fixed-variant: '#404752'
  tertiary-fixed: '#ffddb5'
  tertiary-fixed-dim: '#ffb957'
  on-tertiary-fixed: '#2a1800'
  on-tertiary-fixed-variant: '#643f00'
  background: '#10131b'
  on-background: '#e0e2ed'
  surface-variant: '#31353d'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.2'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 9px
  xs: 4.5px
  sm: 9px
  md: 18px
  lg: 27px
  xl: 36px
  gutter: 18px
  margin: 27px
---

## Brand & Style

The design system is engineered for high-stakes industrial monitoring and aerospace telemetry. It targets technical operators, fire safety engineers, and environmental analysts who require absolute clarity under pressure. The aesthetic is defined as a **Dark Aerospace Telemetry Console**: dense, authoritative, and strictly functional.

The visual narrative is built on the concept of a "Command HUD" (Heads-Up Display). It avoids decorative flourishes in favor of information density and technical precision. The style leverages **Minimalism** with a **Corporate/Modern** technical edge, utilizing hairline borders and monochromatic surfaces to ensure that thermal anomalies and data classes remain the undisputed focal point of the interface.

## Colors

The palette is anchored by a deep near-black navy (`#060910`), providing a high-contrast foundation for thermal data. Interactive elements are strictly reserved for the Cyan accent (`#22d3ee`), ensuring a clear distinction between "information" and "action."

### Data Classification
Functional colors are used for specific thermal classes:
- **Gas Flare:** Orange-Gold (`#ffa94d`)
- **Industrial Fire:** Intense Red (`#ff4d4d`)
- **Coal Seam:** Deep Amber (`#f59e0b`)
- **Vegetation:** Green (`#4ade80`)
- **Gas Leak:** Soft Violet (`#b197fc`)

Surface levels are established through varying shades of navy and slate, with borders using `#1b2735` to define panel boundaries without creating visual noise.

## Typography

This design system employs a dual-font strategy. **Inter** handles the primary UI hierarchy, providing a neutral and utilitarian sans-serif for readability. **JetBrains Mono** is utilized for all data-heavy contexts, telemetry readouts, and labels to evoke a technical terminal feel.

All numerical data must use **tabular figures** to ensure vertical alignment in monitoring tables and live-streaming coordinates. Headlines are kept tight and compact. Labels use uppercase monospaced type to distinguish metadata from content.

## Layout & Spacing

The layout is governed by a **9px dense grid**, deviating from the standard 8px system to achieve a specific "compact terminal" rhythm. 

- **Grid:** A 12-column fluid grid is used for dashboard layouts, while internal panel layouts rely on fixed 9px increments.
- **Density:** High information density is preferred. Components should minimize internal padding to maximize the amount of telemetry visible on a single screen.
- **Alignment:** Elements should align strictly to the grid edges. Use 1px hairlines to separate different functional zones of the console.

## Elevation & Depth

Depth in this design system is achieved through **Tonal Layers** rather than shadows. 

- **Level 0 (Base):** Background `#060910`.
- **Level 1 (Panels):** Surface `#0d141d` at 72% opacity, allowing map or data underlays to be faintly visible.
- **Level 2 (Popovers/Tooltips):** Surface `#1b2735` with no transparency.

**Borders & Glows:** 
Instead of shadows, use 1px solid borders (`#1b2735`). For critical status or active selections, a subtle radial glow using the primary Cyan or the Severity color may be applied behind the element to simulate a backlit hardware console.

## Shapes

The shape language is rigid and industrial. Consistent with the `Soft` setting, the default border radius is 0.25rem (4px). 

- **Container Panels:** Specifically overridden to **10px** radius to provide a distinct structural frame for the dense internal data.
- **Controls:** Buttons and input fields use a consistent 4px radius. 
- **Prohibited:** Do not use "pill" shapes or highly rounded "blobs." Every shape should feel like it was machined for a rack-mounted hardware interface.

## Components

### Buttons & Interaction
- **Primary:** Solid Cyan (`#22d3ee`) with `#060910` text. Sharp corners (4px).
- **Secondary:** Transparent background, 1px Cyan border.
- **Ghost:** No border, Cyan text. Use only for low-priority actions in utility bars.

### Input Fields
- **Styling:** Background `#060910`, 1px border `#1b2735`. On focus, the border transitions to Cyan with a subtle 2px outer glow.
- **Text:** Use JetBrains Mono for input text to reinforce the technical nature of data entry.

### Cards & Panels
- Panels must use the `#0d141d` 72% opacity background. 
- Header areas within panels should be separated by a 1px horizontal line and use a slightly lighter background (`#1b2735`) for the title bar.

### Data Chips & Status Indicators
- **Chips:** Small, rectangular indicators with 2px radius. The background is a 15% opacity tint of the Data Class color, with a 1px solid border of the full-strength color.
- **Indicators:** Use 8px square "LED" icons for status. Pulse animation is reserved for **CRITICAL** severity only.

### Telemetry Lists
- Use hairline dividers between items. 
- Column headers must be uppercase JetBrains Mono at 11px. 
- Zebra-striping is permitted using a 2% opacity increase on alternate rows for high-density tables.