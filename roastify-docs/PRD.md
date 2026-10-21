# Roastify PRD

**Tagline:** Your music taste. Your public execution.

## 1. Overview

Roastify is a fun web app that analyzes a user's music playlist and generates a personalized, humorous roast of their taste. The user pastes a public Spotify playlist link (or a manual track list), Roastify gathers the track data it can legitimately access, computes real statistics in code, and passes those facts to an AI model that writes the roast.

It is an entertainment product, not a serious music review tool.

## 2. Problem and Opportunity

People like teasing each other about music taste and sharing quiz-style results. Most playlist tools focus on organizing or recommending. Roastify focuses on entertainment.

The core challenge: jokes must feel specific to the actual playlist, not generic insults. Humor is therefore grounded in measurable playlist observations.

## 3. Goals

- Accept a supported public Spotify playlist URL.
- Retrieve and normalize available track metadata.
- Analyze playlist patterns with deterministic code.
- Generate humorous, personalized commentary with an AI model.
- Present results in a polished, responsive interface.
- Avoid requiring a music platform login for the initial experience wherever API access allows it.

## 4. Target Users

- Music fans who enjoy memes and internet humor.
- Friends who tease each other about playlists.
- Social media users who like shareable quizzes and cards.
- Developers and students who want a project combining APIs, data analysis, frontend design and generative AI.

## 5. Tech Stack (Mandatory)

- **Backend:** Django (Python)
- **Frontend:** HTML, CSS, vanilla JavaScript (Django templates, no frontend framework)
- Other supporting tools (HTTP client, AI SDK, cache, rate limiting) are allowed, but the four above are fixed.

## 6. Core User Journey

1. User opens the homepage.
2. User pastes a public Spotify playlist URL and picks a roast intensity.
3. Roastify validates the URL.
4. The server tries to retrieve playlist and track metadata through an approved API or permitted method.
5. Tracks are normalized into the internal data model.
6. The analysis layer computes real statistics.
7. The AI receives statistics and selected metadata and returns a structured roast.
8. The results page shows scores, observations, personality label and roast.
9. User can try another playlist.

If metadata cannot be retrieved, the app explains the limitation and offers a fallback: paste a track list or upload a simple CSV.

## 7. Features

### 7.1 Playlist URL Input
- Single input field for a playlist URL.
- Spotify URL validation with clear error messages.
- Loading state during retrieval.
- Helpful guidance when a playlist is private, unavailable, unsupported or too large.

### 7.2 Music Taste Analysis
Only compute statistics supported by the data actually retrieved:
- Number of tracks
- Number of unique artists
- Most repeated artists
- Artist concentration (share of tracks from top artists)
- Release year distribution (if release dates exist)
- Track and artist repetition, duplicate tracks
- Genre distribution (only if reliable genre data exists)
- Explicit/clean labels (if exposed)

Roastify never claims to know listening history, emotions or personality as fact. Everything is a joke or playful interpretation of the submitted playlist.

### 7.3 Roast Intensity
- **Mild:** friendly teasing.
- **Savage:** sharp, witty criticism.
- **Nuclear:** exaggerated, chaotic internet humor.

Humor targets playlist choices and listening patterns only. Never protected traits or sensitive personal characteristics.

### 7.4 Roast Report
- Headline roast
- Fictional music personality type
- A few evidence-based observations
- Main Character Syndrome score
- Artist Obsession score
- Emotional Damage score
- Most roastable playlist pattern
- Final verdict

Scores are entertainment labels. The UI states this clearly and explains the formulas or their playful nature.

### 7.5 UI Direction

The owner shared a reference screenshot (a minimal "how bad is your music taste" style landing page). Roastify should have the same feel: clean, calm, confident, with the joke carried by the copy and the artwork rather than by loud styling. The reference is for mood and layout only. Roastify must use its own copy, name, artwork and branding, and must not copy the reference's text, album art, logos or credits.

**Landing page layout (top to bottom, all centered):**
- Very light, near white background with a soft gradient and a faint light beam fading from the top center.
- Large headline in a light, elegant serif, two lines, generous line height. Roastify's own line, for example the tagline "Your music taste. Your public execution."
- One or two lines of monospace subtext under it explaining what the app does, in a friendly dry tone.
- A tiny uppercase accent label in a bright magenta (for example a version or tone hint).
- A single primary button: solid black, rounded corners, white serif text, soft drop shadow. The playlist URL input appears right after it is clicked, or sits directly above it as one clean field.
- Near the bottom, a row of playful record sleeves leaning on a wooden shelf, overlapping slightly, each with a short roast style title. Make these original: invented sleeve names and abstract or illustrated art built with CSS or SVG, not real album covers and not copies of the reference artwork.
- Small monospace footer text at the bottom left and bottom right (credit line, privacy and data note).

**Style tokens:**
- Display font: a light serif from Google Fonts such as Fraunces or Instrument Serif.
- Body and UI font: a monospace such as JetBrains Mono or IBM Plex Mono.
- Colors: off white background, near black text, black buttons, one hot magenta accent, warm light wood tone for the shelf, and a few saturated sleeve colors (teal, blue, hot pink, charcoal).
- Shapes: soft shadows, slightly rounded corners, lots of whitespace.
- Motion: gentle only (sleeves can slide up or tilt on hover). Respect reduced motion.

**Other screens follow the same system:**
- Tone selector (Mild, Savage, Nuclear) as simple pill toggles in the same black and white style.
- Loading state in the same monospace voice with rotating playful messages.
- Results page keeps the big serif headline for the roast headline, monospace for observations, and score meters in the magenta accent. A final verdict can be shown as a sleeve style card.
- Manual track list and CSV fallback sit in a clearly labeled secondary tab, styled the same way.

**Responsive:** on phones the shelf row shows fewer sleeves or becomes a horizontal scroll, and the headline scales down but stays two or three lines.

## 8. Spotify Support and Data Access

V1 supports Spotify only. A public playlist URL does not guarantee API access. Retrieval depends on the current Spotify Web API rules, app eligibility, scopes and endpoint availability. Check the official docs before implementing: https://developer.spotify.com/documentation/web-api

Use only supported APIs and comply with Spotify's terms. If retrieval fails, show the limitation and offer the manual track list or CSV fallback.

## 9. Data Model

```ts
type Track = {
  title: string;
  artists: string[];
  album?: string;
  releaseDate?: string;
  genres?: string[];
  durationMs?: number;
  explicit?: boolean;
  sourceUrl?: string;
};

type Playlist = {
  title?: string;
  source: "spotify" | "manual";
  sourceUrl?: string;
  tracks: Track[];
};
```

Optional fields stay absent when the provider does not supply them. Never invent metadata. In Django this is implemented as plain Python dataclasses (not DB models), since playlists are not stored.

## 10. AI Output Contract

The model returns JSON which the server validates before display:

```json
{
  "headline": "Your shuffle button needs a lawyer",
  "personality": "The Dedicated Fan Club President",
  "scores": {
    "artistObsession": 82,
    "mainCharacterEnergy": 71,
    "emotionalDamage": 64
  },
  "observations": ["..."],
  "roast": "...",
  "finalVerdict": "..."
}
```

Example grounded stat: 48 tracks, 13 unique artists, 15 tracks from the top artist (31.25%). Example roast: "Fifteen tracks from the same artist? This is less a playlist and more an unpaid internship in the fan club."

## 11. MVP Scope

1. Polished landing page with one playlist URL input.
2. Spotify URL validation.
3. One working, permitted retrieval method (subject to current API access).
4. Manual track list fallback (and CSV upload).
5. Basic stats: track count, unique artists, top artists, repetition.
6. Three roast intensity levels.
7. AI generated report based on those stats.
8. Responsive results page.
9. Clear errors, loading states and basic rate limiting.

## 12. Future Scope (Not in MVP)

- Shareable roast cards (downloadable image)
- Playlist comparisons
- Friend versus friend battles
- Defend your taste mode
- Saved reports for signed-in users with privacy controls
- More humor styles and languages
- Additional music platforms if access and licensing permit

## 13. Privacy, Security, Reliability

- Never ask for Spotify passwords.
- Keep API secrets server side only.
- Request user authorization only when a feature truly needs it.
- Do not store playlist contents or reports unless necessary and disclosed.
- Allow only supported provider hosts to prevent SSRF and malicious URLs.
- Cap playlist size, request frequency and AI token usage.
- Treat playlist titles, track names and metadata as untrusted input in prompts (prompt injection risk).
- Give understandable errors when a provider blocks access or returns incomplete data.
- Follow platform API terms, branding rules and privacy requirements.

## 14. Success Metrics

- Percentage of users who successfully generate a report
- Average time from submission to result
- Percentage who analyze a second playlist
- Playlist retrieval success and failure rates
- AI cost per report
- Feedback on whether the roast felt specific and funny

Collect analytics only when appropriate, disclose tracking, and avoid retaining sensitive data.

## 15. Definition of Done

- User can submit a supported URL or use the manual fallback.
- Invalid and inaccessible playlists give helpful messages.
- Statistics are accurate for the tracks received.
- The AI roast references those statistics and does not invent facts.
- Report renders correctly on desktop and mobile.
- Secrets stay server side and basic request limits are active.
- README explains setup, environment variables, known limitations and API requirements.

## 16. Summary

Roastify is an AI-powered Spotify playlist roaster. Its differentiator is the combination of real playlist analysis and personalized humor. V1 is Spotify only, built on Django with HTML, CSS and JS.
