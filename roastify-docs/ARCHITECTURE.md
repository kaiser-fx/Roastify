# Roastify Architecture

## 1. Principles

- **Facts from code, jokes from AI.** All statistics are computed deterministically in Python. The AI only writes language around supplied facts.
- **Stateless by default.** No playlist or report is stored in the database in the MVP.
- **Server owns secrets.** API keys and tokens never reach the browser.
- **Untrusted input everywhere.** URLs, playlist titles, track names and AI output are all validated.
- **Graceful degradation.** Every failure path has a fallback (manual input, canned roast).

## 2. Stack

- **Backend:** Django (views, forms, services, caching, rate limiting)
- **Frontend:** Django templates, plain CSS, vanilla JS (fetch API, no framework)
- **AI:** Gemini API, called only through a thin adapter module so the provider can be swapped later
- **Spotify:** Spotify Web API through an adapter (subject to current access rules)
- **Cache and limits:** Django cache framework (local memory in dev, Redis in production), plus a rate limiting layer

## 3. High Level Flow

```
Browser
  |  POST playlist URL or manual tracks + intensity
  v
Django view (roast API)
  |  1. rate limit check
  |  2. input validation (URL host allowlist, size limits)
  v
Ingestion service
  |  Spotify adapter  OR  manual / CSV parser
  v
Normalizer  ->  Playlist (dataclass)
  v
Analysis engine (pure Python, deterministic)
  v
Prompt builder (sanitizes untrusted text)
  v
LLM adapter  ->  raw JSON
  v
Output validator (schema check, score clamping, fallback)
  v
JSON response  ->  Browser renders report
```

## 4. Suggested Project Layout

```
roastify/
  manage.py
  config/                  Django project (settings, urls, wsgi)
    settings/
      base.py
      dev.py
      prod.py
  apps/
    web/                   pages: landing, results, error states
      templates/web/
      static/web/css/
      static/web/js/
    ingestion/             getting tracks into the system
      spotify_client.py    Spotify adapter (token, fetch, pagination)
      url_validator.py     parse and validate playlist URLs
      manual_parser.py     pasted track list and CSV parsing
      normalizer.py        provider data -> Playlist
      errors.py            typed ingestion errors
    analysis/
      stats.py             deterministic statistics
      scoring.py           entertainment score formulas
      models.py            Track, Playlist dataclasses
    roasting/
      prompts.py           mild / savage / nuclear prompt templates
      llm_client.py        provider adapter
      schema.py            output schema and validation
      fallback.py          safe canned roast from stats
      sanitizer.py         cleans untrusted strings before prompting
    api/
      views.py             JSON endpoints
      throttling.py        rate limiting
  tests/
  docs/
  .env.example
  requirements.txt
  README.md
```

The `ingestion`, `analysis` and `roasting` apps should not import from `web`. Dependencies point inward: web and api call services, services never call views.

## 5. Components

### 5.1 URL Validator
- Accepts only `open.spotify.com` playlist URLs (and the `spotify:playlist:` URI form).
- Extracts the playlist ID with a strict regex.
- Rejects every other host, scheme or path. The server never fetches a user supplied URL directly; it only calls the Spotify API with the extracted ID.

### 5.2 Spotify Adapter
- Uses a supported auth flow chosen after reading the current docs (likely client credentials, if it permits the needed endpoints).
- Handles pagination, timeouts, retries with backoff and rate limit responses.
- Maps provider errors to typed errors: `PrivateOrMissing`, `AccessRestricted`, `TooLarge`, `UpstreamFailure`.
- If access is blocked, the API returns an error code that tells the frontend to show the manual fallback.

### 5.3 Manual and CSV Fallback
- Pasted text format: one track per line, `Title - Artist` (artists separated by commas).
- CSV upload with columns `title`, `artist`, optional `album`, `release_date`.
- Hard caps on file size and row count.

### 5.4 Analysis Engine
Pure functions, no network, no AI. Inputs: `Playlist`. Outputs: a `PlaylistStats` object containing only values supported by the data:
- track_count, unique_artist_count
- top_artists (name, count, share)
- top_artist_share, top3_share
- duplicate_tracks
- release_year_distribution (only if dates present)
- explicit_share (only if flags present)
- genre_distribution (only if present)

Fields absent from the provider stay `None` and are omitted from the prompt.

### 5.5 Scoring
Entertainment scores are derived from stats with documented formulas, for example:
- **Artist Obsession:** scaled from top artist share and unique artist ratio.
- **Main Character Energy:** scaled from playlist concentration and repetition.
- **Emotional Damage:** scaled from a mix of repetition and optional signals (such as year clustering).

Formulas live in `scoring.py` with docstrings and are shown in the UI as "for fun, not science." The AI may phrase scores but should be given the computed numbers rather than inventing them. Preferred design: code computes the scores and the model is told to use them as is.

### 5.6 Prompt Builder
- One system prompt, plus an intensity block (mild, savage, nuclear).
- User message contains only a structured JSON block of stats and a capped sample of track metadata.
- Playlist title and track names are wrapped in clearly delimited data sections and truncated. The prompt states that anything inside them is data, never instructions.
- Content rules in the system prompt: roast choices, not people; no protected traits; no sensitive personal assumptions.

### 5.7 LLM Adapter
- One function: `generate_roast(stats, sample_tracks, intensity) -> dict`.
- Calls the Gemini API with the official Google Gen AI Python SDK (confirm the current package name and usage in the Gemini docs before coding).
- Requests JSON output. Prefer Gemini's structured output option (JSON response type plus a response schema) if the chosen model supports it, and still validate server side.
- Sets a timeout, a max output token cap and a low retry count. Handles quota and rate limit errors (429) with backoff, then falls back.
- Model name and API key come from environment variables. Gemini model names and free tier limits change, so check the docs when picking a model.
- Gemini adapter lives in `llm_client.py`. No other module imports the SDK.

### 5.8 Output Validator
- Parses JSON, checks required keys and types.
- Clamps scores to 0 to 100, trims string lengths, limits observation count.
- Optionally cross checks that numbers mentioned in observations match stats (simple check on counts and percentages).
- On failure: one retry, then fall back to `fallback.py`, a template roast built straight from the stats.

## 6. HTTP Interface

- `GET /` landing page with URL input, tone selector and manual fallback tab
- `POST /api/roast/` JSON in, JSON out
  - Body: `{ "source": "spotify" | "manual", "url": "...", "tracks_text": "...", "intensity": "mild" | "savage" | "nuclear" }`
  - CSV upload as multipart on the same route or a sibling route
  - Success: `{ "playlist": {title, track_count}, "stats": {...}, "report": {...} }`
  - Failure: `{ "error": { "code": "...", "message": "...", "fallback": "manual" } }`
- `GET /results/` optional page that renders the report from client side state (no server storage)
- `GET /healthz` simple health check

Error codes: `INVALID_URL`, `PLAYLIST_PRIVATE`, `ACCESS_RESTRICTED`, `PLAYLIST_TOO_LARGE`, `EMPTY_PLAYLIST`, `RATE_LIMITED`, `AI_UNAVAILABLE`, `UPSTREAM_ERROR`.

## 7. Frontend

- Django templates with a base layout, partials for the report cards and error states.
- Vanilla JS modules:
  - `form.js`: validation, tab switch between URL and manual input, submit via `fetch`
  - `render.js`: builds report DOM from JSON, using `textContent` (never `innerHTML` with AI text) to prevent XSS
  - `ui.js`: loading state, error messages, tone selector
- CSS: mobile first, CSS variables for theming, no framework required.
- Accessibility: labelled inputs, focus states, readable contrast, reduced motion respect.
- Demo mode: example playlist JSON bundled so the UI can be built without API access.
- Visual direction: see PRD section 7.5. Fonts load from Google Fonts (a light serif plus a monospace). Define colors, fonts and spacing as CSS variables in one stylesheet so the theme is easy to tweak. Sleeves and shelf are built with CSS or inline SVG.

## 8. Security

- CSRF protection on the POST endpoint (token sent via header from JS).
- Host allowlist in the validator; no server side fetch of arbitrary URLs.
- Secrets in environment variables, loaded in settings, never in templates or JS.
- Input caps: URL length, pasted text size, CSV size, max tracks processed.
- Output escaping: all AI generated text inserted as text, not HTML.
- Prompt injection defense: delimiting, truncation, and strict output schema validation.
- Standard Django production settings: `DEBUG=False`, `ALLOWED_HOSTS`, secure cookies, HSTS.

## 9. Rate Limiting and Cost Control

- Per IP limit on the roast endpoint (for example a few requests per minute and a daily cap).
- Cache results for identical playlist and intensity for a short window to cut AI cost.
- Cap tracks sent to the model (stats for all, sample metadata for a subset).
- Cap output tokens.

## 10. Configuration (Environment Variables)

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `MAX_PLAYLIST_TRACKS`
- `RATE_LIMIT_PER_MINUTE`
- `CACHE_URL`

Provide `.env.example` with placeholders only.

## 11. Testing Strategy

- Unit tests: URL validator, normalizer, stats (empty playlist, duplicates, missing artists, huge playlists), scoring bounds, output validator with malformed JSON.
- Mocked integration tests: Spotify adapter and LLM adapter with recorded fake responses.
- Prompt regression checks: fixed sample playlists, assert that observations cite real numbers.
- Manual checklist: mobile layout, error states, fallback flow.

## 12. Deployment

- WSGI via gunicorn, static files via WhiteNoise.
- Single small service is enough for a hobby deployment (Render, Railway, Fly.io or similar).
- Redis optional, local memory cache acceptable for a single instance demo.

## 13. Open Questions

- Which Spotify auth flow and endpoints are currently allowed for reading public playlist tracks? Verify in the official docs before building the adapter.
- Which Gemini model gives the best humor per cost within free tier limits? Test a few and record the pick in MEMORY.md.
- Whether to render results server side or purely client side from the JSON response.
