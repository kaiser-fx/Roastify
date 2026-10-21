# AGENTS.md

Instructions for AI coding agents working on Roastify. Read this file first, then the docs listed below.

## Project in One Paragraph

Roastify is a Django web app (HTML, CSS, vanilla JS frontend) that takes a public Spotify playlist URL or a manual track list, computes real statistics in Python, and asks an AI model to write a humorous, personalized roast based on those statistics. The output is a responsive report with a headline, personality type, three entertainment scores, observations and a final verdict. It is a side hobby project aimed at fun, not seriousness.

## Read Before Working

1. `PRD.md`: what we are building and why
2. `ARCHITECTURE.md`: how it is structured
3. `RULES.md`: constraints you must follow
4. `PHASES.md`: build order and current phase
5. `MEMORY.md`: decisions, open questions, known limitations
6. `DESIGN.md`: exact look, tokens, layout and component specs
7. `reference/ui/`: working Django templates, stylesheet and script for every screen. This is the visual source of truth.

If these conflict, precedence is: RULES.md, then MEMORY.md decisions, then ARCHITECTURE.md, then PRD.md. For anything visual, DESIGN.md and `reference/ui/` win.

## Non Negotiables

- Stack is Django, HTML, CSS and vanilla JavaScript. Do not introduce React, Vue, Tailwind or similar.
- Facts come from deterministic code. The AI only writes language around supplied facts.
- Never invent playlist metadata. Missing fields stay missing.
- Secrets stay in environment variables and server side only.
- Only accept `open.spotify.com` playlist URLs and `spotify:playlist:` URIs. Never fetch arbitrary user URLs.
- Treat playlist titles, track names, CSV and pasted text as untrusted input. Treat AI output as untrusted too: validate it and render it with `textContent`.
- Jokes target playlist choices only. Never protected traits or sensitive personal characteristics.
- Do not store playlists or reports in the MVP.
- The UI must match `DESIGN.md` and `reference/ui/`. Copy those templates, CSS and JS into `apps/web/` and wire them up. Do not redesign, swap fonts or colors, or add a UI framework.
- No em dashes or double hyphens in docs, UI copy, comments or commit messages.

## How to Work

1. Check `PHASES.md` for the current phase. Do only that phase's tasks. Do not build future scope features early.
2. Prefer the smallest change that meets the exit criteria.
3. Put logic in service modules (`ingestion`, `analysis`, `roasting`), keep views thin.
4. Write tests with the code, especially for edge cases (empty playlist, duplicates, missing artists, malformed AI JSON, hostile input).
5. Mock Spotify and the LLM in tests. Never call real external APIs from tests.
6. Before Spotify work, read the current official docs: https://developer.spotify.com/documentation/web-api . Do not assume endpoint availability from memory.
7. Update `MEMORY.md` when you make a decision, verify a fact, or find a limitation.
8. Update the README when setup, env vars or limitations change.
9. If a requirement is ambiguous or you would need to break a rule, stop and ask instead of guessing.

## Code Conventions

- **Python:** PEP 8, type hints on service functions, small pure functions, dataclasses for `Track` and `Playlist`.
- **JavaScript:** ES modules, `const` and `let`, no globals, no inline handlers, `fetch` for API calls, send the CSRF token in a header.
- **CSS:** mobile first, CSS variables, meaningful class names, respect `prefers-reduced-motion`.
- **Comments:** explain why, not what.
- **Commits:** small and focused, imperative mood.

## Suggested Agent Roles

If using multiple agents or sessions, split work by area. Each agent stays in its lane and avoids editing files owned by another without coordination.

### Frontend Agent
- **Owns:** `apps/web/` templates, static CSS and JS. Starts from `reference/ui/` and keeps matching it.
- **Tasks:** landing page, results page, tone selector, loading and error states, responsive layout, accessibility.
- **Must not:** put business logic in templates or JS, use `innerHTML` with dynamic text.

### Ingestion Agent
- **Owns:** `apps/ingestion/`.
- **Tasks:** URL validator, Spotify adapter, normalizer, manual and CSV parsers, typed errors.
- **Must not:** scrape Spotify, skip the host allowlist, or fetch user supplied URLs.

### Analysis Agent
- **Owns:** `apps/analysis/`.
- **Tasks:** statistics, score formulas, edge case tests.
- **Must not:** add network calls, randomness or AI into this layer.

### Roasting Agent
- **Owns:** `apps/roasting/`.
- **Tasks:** prompts per intensity, sanitizer, LLM adapter, schema validation, fallback roast, prompt tests.
- **Must not:** let the model invent facts, skip validation, or pass raw untrusted strings into the prompt undelimited.

### API and Platform Agent
- **Owns:** `apps/api/`, `config/`, deployment files.
- **Tasks:** endpoints, error codes, rate limiting, caching, settings, deployment, README.
- **Must not:** commit secrets or loosen production security settings.

### Review Agent
- **Owns:** nothing, read only.
- **Tasks:** check changes against `RULES.md`, look for security issues (SSRF, XSS, prompt injection, CSRF), verify tests cover edge cases, confirm jokes cite real stats.

## Definition of Done for Any Task

- Meets the phase exit criteria it belongs to.
- Follows `RULES.md`.
- Has tests where logic was added or changed, and tests pass.
- Works at phone width and desktop width if it touches UI.
- Docs and `MEMORY.md` updated if needed.
- No secrets, no debug leftovers, no dead code.

## Quick Reference

- Intensities: `mild`, `savage`, `nuclear`
- Sources: `spotify`, `manual`
- Error codes: `INVALID_URL`, `PLAYLIST_PRIVATE`, `ACCESS_RESTRICTED`, `PLAYLIST_TOO_LARGE`, `EMPTY_PLAYLIST`, `RATE_LIMITED`, `AI_UNAVAILABLE`, `UPSTREAM_ERROR`
- AI output keys: `headline`, `personality`, `scores` (`artistObsession`, `mainCharacterEnergy`, `emotionalDamage`), `observations`, `roast`, `finalVerdict`
