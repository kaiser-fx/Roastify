# Roastify Phases

Build order for the MVP. Finish each phase's exit criteria before moving on. Stack throughout: Django, HTML, CSS, JS.

## Phase 0: Project Setup

**Goal:** a running Django skeleton.

- Create virtual environment, `requirements.txt`, `.env.example`, `.gitignore`.
- Start the Django project with the `config/` settings split (base, dev, prod).
- Create apps: `web`, `ingestion`, `analysis`, `roasting`, `api`.
- Add a base template, static file setup and a `/healthz` route.
- Start a README with setup steps.

**Exit criteria:** `python manage.py runserver` serves a blank styled page. Secrets load from environment variables.

## Phase 1: UI Prototype (No Real APIs)

**Goal:** the whole experience looks right using fake data.

- Landing page: tagline, URL input, tone selector (Mild, Savage, Nuclear), tab for manual track list and CSV.
- Results page: headline, personality, three score meters, observations, roast, final verdict, "try another playlist" button.
- Loading, error and empty states.
- Bundle example playlist and example report JSON so the UI works without any API.
- Start from the reference kit in `reference/ui/` and DESIGN.md: copy its templates, stylesheet and script into `apps/web/`, register the `web:landing`, `web:results` and `web:fallback` URL names, and feed the results page from `demo_report.json`. PRD section 7.5 explains the intent. Check mobile layout and spacing against DESIGN.md.
- Create the shelf and sleeve artwork with CSS or inline SVG so no copyrighted images are needed.
- Entertainment disclaimer and privacy note in the UI.

**Exit criteria:** the full flow can be clicked through on desktop and phone width using example data.

## Phase 2: Playlist Ingestion

**Goal:** real track data enters the system.

- Define `Track` and `Playlist` dataclasses.
- Spotify URL validator with host allowlist and ID extraction.
- Check current Spotify Web API docs and decide the auth flow and endpoints. Record the decision in MEMORY.md.
- Spotify adapter: token handling, pagination, timeouts, retries, typed errors.
- Normalizer from Spotify response to `Playlist`.
- Manual pasted list parser and CSV parser with size limits.
- Wire the `/api/roast/` endpoint to ingestion only (return normalized playlist as JSON for now).
- Fallback flow: if Spotify access fails, the UI switches to manual input with a helpful message.

**Exit criteria:** a valid public playlist (or manual list) returns a normalized `Playlist`. Invalid, private, restricted and oversized cases return clear errors.

## Phase 3: Analysis Engine

**Goal:** trustworthy statistics.

- Implement stats: track count, unique artists, top artists, top artist share, top 3 share, duplicates, optional year distribution, optional explicit share, optional genres.
- Implement scoring formulas with docstrings and 0 to 100 clamping.
- Unit tests for edge cases: empty playlist, one track, all same artist, missing artist names, duplicates, very large playlists.
- Show stats on the results page next to the roast.

**Exit criteria:** every number the UI shows is computed by tested code. Absent data produces absent stats, never fake values.

## Phase 4: AI Roasting

**Goal:** funny, grounded, safe output.

- Build the LLM adapter (provider and model from env vars, timeout, token cap).
- Write prompts for the three intensities with content rules baked in.
- Prompt builder with sanitizing and delimiting of untrusted strings.
- Output schema and validator: required keys, type checks, score clamping, length trimming.
- One retry on malformed output, then the stats based fallback roast.
- Test with a set of sample playlists: all repeated, all unique, tiny, huge, hostile text in titles (prompt injection attempts).
- Review jokes for being generic, repetitive or unsupported by the stats.

**Exit criteria:** every report cites real numbers from the stats. Malformed or failed AI calls still produce a usable report.

## Phase 5: Hardening and Polish

**Goal:** demo ready.

- Rate limiting per IP and result caching.
- Final error messages for every error code.
- Mobile layout pass, accessibility pass (labels, focus, contrast, reduced motion).
- Loading polish (rotating playful loading messages are fine).
- Production settings, WhiteNoise, gunicorn config, deployment to a hobby host.
- Complete the README: setup, environment variables, known limitations, API requirements.
- Final run through the Definition of Done in the PRD.

**Exit criteria:** all items in the PRD Definition of Done are checked.

## Later Enhancements (After MVP)

In rough priority order:

1. Shareable roast card export (downloadable image with branding, short roast, one or two scores).
2. Defend your taste mode.
3. Playlist comparison, then friend versus friend battles.
4. More humor styles and languages.
5. Saved reports with accounts and privacy controls.
6. Other music platforms, only if access and licensing allow.

## Progress Tracker

Update as work completes.

- [x] Phase 0: Project Setup
- [x] Phase 1: UI Prototype
- [x] Phase 2: Playlist Ingestion
- [x] Phase 3: Analysis Engine
- [x] Phase 4: AI Roasting
- [x] Phase 5: Hardening and Polish
