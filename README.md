# Roastify

**Your music taste. Your public execution.**

Roastify is an AI-powered Spotify playlist roaster. Paste a public playlist link (or paste your tracks manually / upload a CSV), pick a roast intensity, and get a personalized, data-backed roast of your music taste.

## Features

- **Spotify & Manual Ingestion:** Paste public `open.spotify.com` playlist URLs, paste raw tracks (`Title - Artist`), or upload a CSV.
- **Graceful Fallback:** If Spotify API access is restricted, the app seamlessly redirects to manual and CSV input with pre-filled helpful alerts.
- **Deterministic Statistics:** Pure, tested statistical engine computing track counts, artist diversity, top artist shares, top 3 dominance, duplicate songs, and release year distributions.
- **Entertainment Scores:** Three transparent formulas clamped between 0 and 100:
  - *Artist Obsession*
  - *Main Character Energy*
  - *Emotional Damage*
- **Grounded AI Roasting:** Powered by the Gemini API (`gemini-2.0-flash` or `gemini-3.0-flash`) using structured JSON outputs. Every observation is strictly grounded in real numbers.
- **Three Roast Intensities:** Mild, Savage (default), and Nuclear.
- **Offline / Quota Fallback:** If the Gemini API is unreachable or unconfigured, Roastify automatically falls back to an offline template generator that crafts hilarious roasts directly from your playlist numbers.
- **Performance & Security:** Per-IP rate limiting, 30-minute result caching for identical playlists and tones, WhiteNoise static file compression, strict prompt injection defenses, and zero server-side storage of user playlists.

## Setup

### Prerequisites

- Python 3.12 or later
- pip

### Installation

1. Clone the repository and navigate to the project directory.

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv

   # Windows (PowerShell)
   venv\Scripts\Activate.ps1

   # Windows (Command Prompt)
   venv\Scripts\activate.bat

   # macOS and Linux
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create your `.env` file from `.env.example`:

   ```bash
   cp .env.example .env
   ```

5. Run automated tests to verify the setup:

   ```bash
   python manage.py test
   ```

6. Start the local development server:

   ```bash
   python manage.py runserver
   ```

7. Open `http://localhost:8000/` in your browser.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Dev fallback | Secret key for Django cryptographic signing. Required in production. |
| `DJANGO_DEBUG` | `True` | Set to `False` in production. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames. |
| `SPOTIFY_CLIENT_ID` | `""` | Spotify Web API client ID. |
| `SPOTIFY_CLIENT_SECRET` | `""` | Spotify Web API client secret. |
| `GEMINI_API_KEY` | `""` | Google Gemini API key. If omitted, uses grounded offline template roasts. |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name (e.g. `gemini-2.0-flash`, `gemini-3.0-flash`). |
| `MAX_PLAYLIST_TRACKS` | `200` | Maximum tracks ingested and processed. |
| `RATE_LIMIT_PER_MINUTE` | `10` | Allowed requests per minute per IP address. |
| `CACHE_URL` | `""` | Cache backend URL. Defaults to local memory cache. |

## Production Deployment

Roastify is configured for zero-friction deployment to platforms such as Render, Railway, Fly.io, or Heroku:

1. **Static Files:** WhiteNoise is pre-configured with manifest compression. Collect assets before starting:
   ```bash
   python manage.py collectstatic --noinput
   ```

2. **WSGI Server:** Gunicorn is included in `requirements.txt` and specified in `Procfile`:
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```

3. **Production Security Check:** Verify settings with Django's deployment check:
   ```bash
   python manage.py check --deploy --settings=config.settings.prod
   ```

## Project Structure

```
Roastify/
  manage.py
  Procfile                 Production web process definition
  requirements.txt         Pinned production dependencies
  config/                  Django project configuration
    settings/
      base.py              Base configuration, WhiteNoise, Cache
      dev.py               Development overrides
      prod.py              Production security headers and SSL
    urls.py                Root routing (/api/, /healthz, /)
    wsgi.py                WSGI entrypoint
  apps/
    web/                   Web frontend (templates, CSS, ES modules)
      templates/web/       landing.html, results.html, fallback.html, base.html
      static/web/          style.css, ui.js, form.js, render.js
    ingestion/             URL validator, Spotify adapter, manual & CSV parsers
    analysis/              Pure deterministic stats engine and scoring formulas
    roasting/              Gemini LLM client, prompt builder, schema validator, fallback
    api/                   REST endpoints (/api/roast/, /healthz) and rate limiting
```

## Known Limitations

- **Spotify API Restrictions:** Newly registered server-to-server apps on Spotify's Client Credentials flow are restricted from reading playlist track endpoints. Roastify detects this automatically and routes the user to the manual/CSV fallback.
- **Privacy & Storage:** In accordance with user privacy rules, Roastify does not persist playlist titles, track lists, or generated reports in any database. Reports exist solely in client-side memory for the active browser session.

## License

This is an independent hobby project. It is not affiliated with, endorsed by, or sponsored by Spotify.
