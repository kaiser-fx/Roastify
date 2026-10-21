# Roastify Design

This file is the design source of truth for Roastify, together with the working reference code in `reference/ui/`. If you are an AI agent building the UI, do not reinterpret the look. Copy the reference templates, stylesheet and script, then wire them to real data.

## 1. What is in the reference kit

```
reference/ui/
  templates/web/
    base.html          page shell, fonts, stylesheet, script
    landing.html       hero, URL form, tone pills, record sleeves on a shelf
    results.html       headline, personality, roast, scores, observations, verdict
    fallback.html      error alert, paste tracks form, CSV upload
  static/web/
    css/style.css      the complete stylesheet with all tokens
    js/ui.js           tone pill behavior
  demo_report.json     example report data in the exact shape the results template expects
  screenshots/         (add) screenshots of each screen and the original inspiration image
```

Where the files go in the Django project:
- `reference/ui/templates/web/*` goes to `apps/web/templates/web/`
- `reference/ui/static/web/*` goes to `apps/web/static/web/`
- The templates use these URL names, so register them in the `web` app with `app_name = "web"`: `web:landing`, `web:results`, `web:fallback`.

## 2. Look and feel

Calm, minimal, confident. The joke lives in the copy and the sleeve artwork, not in loud styling. Everything is centered on a near white background. Lots of whitespace. Soft shadows. One hot magenta accent used sparingly.

The look was inspired by a minimal music taste roast site. Roastify copy, naming and artwork are original and must stay that way.

## 3. Design tokens

All tokens are CSS variables at the top of `style.css`.

Colors:
- Background: `#f6f6f4`
- Page gradient: `#fbfcff` at the top fading to `#f6f6f4` at 38% and `#f4f4f2` at the bottom, plus a soft pink glow in the top right corner (`rgba(255, 214, 235, 0.5)`)
- Beam: a faint blue white trapezoid fading downward from the top center (`rgba(130, 190, 255, 0.14)` to transparent)
- Ink (text): `#161616`
- Muted text: `#555555`
- Accent (magenta text): `#b8009f`
- Accent bright (meter gradient start): `#e000c8`
- Card: `#ffffff` with border `#e4e4e0`
- Field border: `#cfcfcf`
- Button: `#000000` with white text
- Lime (on dark and pink sleeves): `#d8f56a`
- Alert: background `#fff4f9`, border `#f0b3da`, text `#6b0057`
- Wood shelf: gradient from `#f2dcb2` to `#d6b583`

Fonts (Google Fonts):
- Display serif: Instrument Serif, weight 400, fallback Georgia
- Body and UI: JetBrains Mono, weights 400 and 500
- Sleeve titles: Space Grotesk, weight 700

Type sizes:
- Landing headline: `clamp(48px, 7.2vw, 96px)`, line height 1.02, letter spacing -0.01em, serif
- Results headline: `clamp(44px, 6.4vw, 84px)`, line height 1.02, serif
- Fallback headline: `clamp(40px, 5.6vw, 68px)`, line height 1.04, serif
- Personality label: serif italic 32px, accent color
- Lede: mono 17px, line height 1.7, max width 470px
- Body and roast text: mono 15px to 18px, line height 1.7 to 1.75
- Small labels and footer: mono 12px to 13px
- Eyebrow labels: mono 12px, uppercase, letter spacing 0.08em, accent color
- Score numbers: serif 52px
- Verdict text: serif 38px (30px on phones)
- Button text: serif 24px

Shape and depth:
- Primary button: height 52px, horizontal padding 34px, radius 12px, shadow `0 10px 24px rgba(0, 0, 0, 0.28)`
- URL input: height 52px, fully rounded pill, 1px border, 22px side padding
- Pills (tone, tabs, secondary buttons): height 44px, fully rounded, 1px ink border. Selected pill is filled ink with white text.
- Cards: radius 14px to 16px, 1px border, light shadow
- Verdict card: radius 6px, background `#161616`, big dim disc in the top right corner

## 4. Layout

- Landing: single centered column, max width 960px, top padding 88px, gap 22px between hero items. Order: headline, lede, eyebrow, form (URL field and button on one row, then tone pills), fallback link. Then the shelf, 56px below. Footer pinned to the bottom with the credit on the left and privacy note on the right.
- Results and fallback: compact top padding (36px). Results column max width 880px with 36px gaps. Fallback column max width 760px with 28px gaps.
- The three score cards sit in a wrapping row, each at least 220px wide.

## 5. Record sleeve shelf

Decorative only (`aria-hidden`). Five sleeves in a row, bottom aligned, overlapping by 22px, each 172px wide, slightly rotated, sitting on a 14px wooden board with a soft drop shadow.

Sleeves left to right (original names and art, never real albums):
1. Repeat Offender: blue gradient (`#6f93b4` to `#b9cbdc`), 200px tall, tilt -1.5deg, translucent disc top right, dark navy text, 27px title
2. Skip Button Graveyard: charcoal `#1d1d1f`, 172px tall, tilt 1deg, thin ring top right, light text, 23px title
3. Gym Bro Anthems: light gray `#dcdce0`, 150px tall, tilt -1deg, dark text, 23px title
4. 3 AM Regrets: teal to blue gradient (`#10a5a0` to `#1a4f9c`), 196px tall, tilt 1.5deg, translucent disc top left, white text, 27px title
5. Main Character Era: hot pink `#c4147f`, 186px tall, tilt -1deg, lime text, 28px title

Hover (only when reduced motion is not requested): sleeve lifts 8px. On phones the row scrolls sideways instead of shrinking.

## 6. Data shapes the templates expect

Results template context `report`:
- `headline` string
- `personality` string
- `tone_label` string (Mild, Savage or Nuclear)
- `meta_line` string (a factual line built from the stats)
- `scores` list of `{label, value}` with value 0 to 100
- `observations` list of strings, each backed by real stats
- `roast` string
- `final_verdict` string

See `reference/ui/demo_report.json` for a complete example. Phase 1 uses this file as the demo report so the screens work without any API.

Fallback template context: optional `error_message` string. If missing, the default Spotify blocked message shows.

Form fields: `url`, `tracks_text`, `csv_file`, `intensity` (mild, savage or nuclear). Real submission and the loading status text (`#form-status`) are wired in later phases. All AI generated text must be rendered as text, never as HTML.

## 7. Behavior

- Tone pills toggle one at a time, update `aria-pressed` and the hidden `intensity` field (`ui.js`).
- `#form-status` is a polite live region for loading messages and short errors.
- No other JavaScript is needed for the static screens.

## 8. Accessibility

- Real buttons, links, inputs and labels. The URL field has a visually hidden label.
- Text contrast of at least 4.5:1. The magenta text color `#b8009f` was chosen to pass on the light background.
- Focus outlines on inputs, buttons and pills.
- Score meters use `role="progressbar"` with value attributes.
- Decorative art (beam, sleeves, discs) is `aria-hidden`.
- Respect `prefers-reduced-motion`.

## 9. Do and do not

Do:
- Keep the page minimal and centered, with generous whitespace.
- Keep the copy dry and playful, grounded in the stats.
- Use the reference classes and structure as they are, and extend them in the same style.

Do not:
- Add a CSS or JS framework.
- Swap fonts, accent colors or the sleeve and shelf concept.
- Use real album covers, real artist names for sleeves, the inspiration site's text, logos or credits, or any copyrighted image.
- Add gradient heavy hero backgrounds, emoji or stock illustrations.
- Use `innerHTML` with dynamic text.
