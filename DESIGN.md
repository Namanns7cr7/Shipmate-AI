---
name: ShipMate AI
description: Mission-control console for deployment-readiness — dark radar/compass command center.
colors:
  bg: "#070c18"
  bg-2: "#060b16"
  panel: "#0d1528"
  panel-solid: "#0c1426"
  line: "#ffffff12"
  line-2: "#ffffff1f"
  ink: "#f3f6fc"
  ink-2: "#aeb9cf"
  ink-3: "#6f7d97"
  ink-4: "#495368"
  blue: "#3b82f6"
  blue-2: "#60a5fa"
  cyan: "#22d3ee"
  purple: "#8b5cf6"
  emerald: "#10b981"
  amber: "#f59e0b"
  orange: "#f97316"
  red: "#ef4444"
typography:
  display:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "clamp(2.25rem, 5vw, 3.5rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.18em"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  sm: "12px"
  md: "18px"
  pill: "999px"
spacing:
  xs: "6px"
  sm: "12px"
  md: "18px"
  lg: "32px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "0 18px"
    height: "44px"
  button-secondary:
    backgroundColor: "#ffffff06"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "0 18px"
    height: "44px"
  button-light:
    backgroundColor: "#ffffff"
    textColor: "#0a1326"
    rounded: "{rounded.sm}"
    padding: "0 18px"
    height: "44px"
  card:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "18px"
  pill:
    backgroundColor: "#ffffff08"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  input:
    backgroundColor: "#ffffff06"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0 14px"
    height: "42px"
---

# Design System: ShipMate AI

## 1. Overview

**Creative North Star: "The Mission Control Console"**

ShipMate is a dark instrument panel read in the minutes before launch. Its job is one calm, exact verdict — *is this safe to ship?* — surrounded by the readouts that justify it. The whole surface behaves like a console: a deep near-black field (`#070c18`) carrying a faint radar grid, translucent glass panels floating above it, and color used strictly as **signal** — emerald for clear, amber for caution, red for blocked. Nothing glows for decoration; light means something is happening or something needs attention.

Depth is a real, always-on system here, not an afterthought. Panels are `backdrop-filter: blur(14px)` glass that sit visibly above the radar grid (the **Layered Glass** model), and state — hover, focus, an actively-running agent — lifts them further with a blue glow. The compass/radar identity (sweep, concentric rings, aurora blobs) is the throughline, and the five agents speak a fixed color language (RepoLens emerald, PlanForge purple, GuardRail amber, TestPilot cyan, Ship Report blue) that must never be reassigned.

This system explicitly rejects the **generic SaaS template**: no hero-metric block (big gradient number + small label + supporting stats), no endless identical icon-heading-text card grids, no tiny tracked uppercase eyebrow stamped over every section, no `01 / 02 / 03` section scaffolding. The verdict and the real per-agent data are the product; they carry the page, not stock marketing scaffolding.

**Key Characteristics:**
- Deep navy command-center field with a faint radar grid, never flat black or pure gray.
- Layered translucent glass panels (`blur(14px)`) that float above the backdrop.
- Color is signal: emerald/amber/red encode readiness; agent hues are a fixed system.
- Compass / radar / sweep motif as the single coherent identity.
- Inter for UI, JetBrains Mono for scores, IDs, and telemetry-style readouts.

## 2. Colors

A dark, low-chroma navy substrate where saturated accents are reserved for meaning — readiness verdicts and the five agent identities.

### Primary
- **Command Blue** (#3b82f6): The system's primary action and identity color. Primary buttons, active nav state, focus rings, the Ship Report agent, and every "in progress / selected" glow. Its lighter sibling **Sky Blue** (#60a5fa) carries hover borders and active icons.

### Secondary
- **Radar Cyan** (#22d3ee): Live / running state. The radar sweep sector, the TestPilot agent, and the `status-running` pulse. Reads as "actively scanning".
- **Signal Purple** (#8b5cf6): The PlanForge agent and the secondary half of identity gradients (borders, hero ink). Never used for severity.

### Tertiary (verdict severity ramp)
- **Ready Emerald** (#10b981): Pass / ready / complete. RepoLens agent, `status-complete`, the high end of the score ramp (≥80).
- **Caution Amber** (#f59e0b): Needs-fixes / medium risk. GuardRail agent, the mid score band (≥40).
- **Alert Orange** (#f97316): Elevated warning between amber and red.
- **Blocked Red** (#ef4444): Fail / blocked / error. `status-error`, destructive actions, the low score band.

### Neutral
- **Void** (#070c18): The page background — a near-black navy, the radar field. **Deep Void** (#060b16) anchors gradients and the sidebar foot.
- **Panel Glass** (rgba(13,21,40,0.72)): The translucent surface of every card, floated over the grid with `blur(14px)`. **Panel Solid** (#0c1426) for surfaces that can't be translucent.
- **Ink** (#f3f6fc): Primary text. **Ink-2** (#aeb9cf) secondary, **Ink-3** (#6f7d97) muted, **Ink-4** (#495368) faint/disabled and table headers.
- **Hairline** (rgba(255,255,255,0.07)) default borders; **Hairline-2** (rgba(255,255,255,0.12)) on hover/emphasis.

### Named Rules
**The Signal Rule.** Saturated color is reserved for meaning — a verdict, a severity, or an agent identity. Chrome, structure, and body text live in the navy-to-ink neutral ramp. A panel that glows blue is doing something; a chip that's amber means caution. Never spend an accent on decoration.

**The Fixed-Agent Rule.** The five agents own their hues permanently: RepoLens = emerald, PlanForge = purple, GuardRail = amber, TestPilot = cyan, Ship Report = blue. These are never reassigned, swapped, or borrowed for unrelated UI.

**The Verdict Ramp Rule.** Score-to-color is fixed and used everywhere identically: ≥80 emerald, ≥60 blue, ≥40 amber, else red. Severity is never encoded by color alone — it always carries a text label (Ready / Needs Fixes / Blocked) and/or icon.

## 3. Typography

**Display / Body Font:** Inter (with system-ui, -apple-system fallback)
**Label/Mono Font:** JetBrains Mono (with ui-monospace fallback)

**Character:** One technical sans (Inter) carries the entire UI across weights — 400 for prose up to 700 for labels — paired on a contrast axis with JetBrains Mono for anything that reads as machine output: scores, repo IDs, timestamps, the live activity log. The mono is the "telemetry" voice; it makes data feel measured and exact.

### Hierarchy
- **Display** (700, clamp(2.25rem, 5vw, 3.5rem), 1.05, -0.02em): Hero headlines and the deployment-readiness verdict. Tight tracking, `text-wrap: balance`.
- **Headline** (650, 1.5rem, 1.2): Card and section titles within the app shell.
- **Title** (600, 1rem, 1.4): Sub-section heads, agent names, table-row primaries.
- **Body** (400, 0.875rem, 1.6): Default prose and descriptions. Cap measure at 65–75ch.
- **Label** (700, 11px, 0.18em, UPPERCASE): The `.eyebrow` and `.pill` micro-labels. A deliberate, sparing accent — not a per-section stamp.
- **Mono** (500, 0.8125rem, 1.5): Scores, IDs, telemetry, the activity log. The instrument readout voice.

### Named Rules
**The Telemetry-Mono Rule.** Any value that is a machine reading — a score, a commit SHA, a timestamp, a percentage, a log line — is set in JetBrains Mono. Prose and labels stay in Inter. The font *is* the signal that "this is data".

**The One-Sans Rule.** Inter does all UI typography across weights. Never introduce a second sans-serif; contrast comes from weight and from the mono pairing, not from a near-identical second family.

## 4. Elevation

Depth is an **always-on layered-glass system**, then amplified by state. At rest, panels are translucent glass (`background: rgba(13,21,40,0.72)` + `backdrop-filter: blur(14px)`) that visibly float above the radar grid — the layering is part of the resting composition, not a hover surprise. State then lifts the panel further: hover and active-agent states raise it `translateY(-3px)` and add the blue glow. Drop shadows are deep and diffuse to suit the dark field, never tight 2014-era dark shadows.

### Shadow Vocabulary
- **Ambient Lift** (`box-shadow: 0 24px 60px -24px rgba(0,0,0,0.7)`): The resting shadow that separates a floated panel from the void.
- **Signal Glow** (`box-shadow: 0 0 0 1px rgba(59,130,246,0.12), 0 24px 70px -30px rgba(37,99,235,0.45)`): The blue hover/active glow on `.card-hover` — depth *plus* meaning ("this is live / focused").
- **Focus Ring** (`box-shadow: 0 0 0 4px rgba(59,130,246,0.10)`): Inputs and secondary buttons on focus.

### Named Rules
**The Floating-Glass Rule.** Panels are translucent and blurred so the radar grid reads through them; they float above the field at rest. If a panel looks like a solid opaque box pasted on flat black, the blur is missing or the background is wrong.

**The Glow-Is-State Rule.** The blue glow is reserved for state — hover, focus, or an actively running agent. A panel that glows is alive; a panel at rest only carries its ambient lift. Never apply the signal glow as permanent decoration.

## 5. Components

### Buttons
- **Shape:** Gently curved (12px radius; `--radius-sm`), 44px tall, 650 weight.
- **Primary:** Blue gradient (`#2563eb → #1d4ed8 → #0e7490`) on white text with an inset top highlight and a blue drop-glow. The default ship/analyze action.
- **Light:** Solid white on dark ink (#0a1326) — for CTAs sitting on dark or busy backgrounds.
- **Secondary / Ghost:** Translucent white fill or transparent with a hairline border; on hover the border shifts to sky-blue and a soft 4px blue ring appears.
- **Danger:** Translucent red fill + red border, for destructive actions only.
- **Hover / Focus:** Lift `translateY(-2px)` + deepened glow; `:active` settles to `translateY(1px)`. Disabled drops to 0.4 opacity, no transform.

### Chips & Pills
- **Pill:** Fully rounded (999px), 11px/700 uppercase-ish micro-label, hairline border on a faint translucent fill.
- **Chip:** 8px radius, 11px/600, slightly tighter — for inline tags.
- **Tone modifiers:** `.tone-{blue|cyan|purple|emerald|amber|orange|red|slate}` each set a matched text + 32%-alpha border + 10%-alpha fill of one hue. This is how severity and agent identity appear inline.

### Cards / Containers
- **Corner Style:** 18px radius (`--radius`), tightening to 14px on mobile.
- **Background:** Panel Glass (rgba(13,21,40,0.72)) with `blur(14px)`.
- **Shadow Strategy:** Floating-Glass at rest; `.card-hover` adds Signal Glow + lift (see Elevation).
- **Border:** 1px Hairline at rest → sky-blue at 28% alpha on hover. The `.glow-border` variant paints a blue→purple→cyan gradient hairline via mask-composite.
- **Internal Padding:** 18–24px.

### Inputs / Fields
- **Style:** 42px tall, 11px radius, faint translucent fill, hairline border. Placeholder uses Ink-4.
- **Focus:** Border shifts to sky-blue (55% alpha) with a 4px blue glow ring. No default outline.

### Navigation
- **Style:** 248px sidebar. Nav items are 13.5px/550, Ink-3 at rest, lifting to Ink + faint fill on hover.
- **Active:** White text on a blue-tinted gradient fill (`rgba(37,99,235,0.28) → 0.06`) with a blue border, inset top highlight, and the icon recolored to Sky Blue.
- **Disabled:** Ink-4, no hover response.

### Signature Components
- **Score Ring:** Animated SVG ring with a count-up number, colored by the Verdict Ramp and wearing a blue drop-shadow glow. The single most important readout — the verdict made visible.
- **Radar Backdrop:** Aurora blobs + concentric compass rings + a rotating cyan conic-gradient sweep. The identity texture behind hero and analysis surfaces.
- **Live Activity Log:** Mono, timestamped, terminal-style stream of pipeline events with status dots (`.dot` + `.dot-pulse` ping).
- **Progress Track:** 6px rounded track; a running agent with no concrete % uses the `bar-indeterminate` slide so it reads as *working*, never *stuck*.

## 6. Do's and Don'ts

### Do:
- **Do** lead every surface with the verdict — the score ring and Ready/Needs-Fixes/Blocked call — and let supporting detail recede until asked for.
- **Do** keep saturated color as signal: verdict severity (≥80 emerald / ≥60 blue / ≥40 amber / else red) and the fixed agent hues, nothing decorative.
- **Do** float panels as translucent `blur(14px)` glass above the radar grid; reserve the blue glow for hover, focus, and actively-running agents.
- **Do** set every machine value (scores, IDs, timestamps, log lines) in JetBrains Mono; keep prose and labels in Inter.
- **Do** pair every color-coded severity with a text label and/or icon, and honor `prefers-reduced-motion` for the sweep, count-up, and agent transitions.

### Don't:
- **Don't** build the **generic SaaS template**: no hero-metric block (big gradient number + small label + stats row), no endless identical icon-heading-text card grids, no Stripe/Linear/Vercel-clone scaffolding.
- **Don't** stamp a tiny uppercase tracked **eyebrow over every section**, and don't add `01 / 02 / 03` numbered section markers as scaffolding. The 11px label is a sparing accent, not a per-section reflex.
- **Don't** use `background-clip: text` gradient text for meaning, or `border-left/right > 1px` colored side-stripes on cards, alerts, or list items. (Legacy `.neon-text` / `.gradient-ink` exist only for the landing hero phrase — don't spread them into product UI.)
- **Don't** reassign the agent colors (RepoLens emerald, PlanForge purple, GuardRail amber, TestPilot cyan, Ship Report blue) or invent a one-off visual language per screen.
- **Don't** drop muted Ink-3/Ink-4 text onto tinted panels where it falls below 4.5:1, and never let a running agent show an empty static bar that reads as "stuck" — use the indeterminate slide.
