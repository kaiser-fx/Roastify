// Render module for Roastify results page.
// Hydrates the report DOM from sessionStorage using textContent to prevent XSS.

export function initResultsPage() {
  const resultTitle = document.querySelector('.result-title');
  if (!resultTitle) {
    return; // Not on the results page
  }

  const storedData = sessionStorage.getItem('roastify_session');
  if (!storedData) {
    return; // Keep initial template demo content
  }

  try {
    const data = JSON.parse(storedData);
    const report = data.report;
    const stats = data.stats;

    if (!report) {
      return;
    }

    // Hydrate header
    const eyebrow = document.querySelector('.result-head .eyebrow');
    if (eyebrow && report.tone_label) {
      eyebrow.textContent = `Roast level: ${report.tone_label}`;
    }

    if (report.headline) {
      resultTitle.textContent = report.headline;
    }

    const personality = document.querySelector('.personality');
    if (personality && report.personality) {
      personality.textContent = report.personality;
    }

    const metaNote = document.querySelector('.meta-note');
    if (metaNote && report.meta_line) {
      metaNote.textContent = report.meta_line;
    }

    // Hydrate roast text
    const roastText = document.querySelector('.roast-text');
    if (roastText && report.roast) {
      roastText.textContent = report.roast;
    }

    // Hydrate stats panel if present
    if (stats) {
      const statItems = document.querySelectorAll('.stats-panel .stat-item');
      if (statItems.length >= 2) {
        statItems[0].querySelector('.stat-number').textContent = String(stats.track_count);
        statItems[1].querySelector('.stat-number').textContent = String(stats.unique_artist_count);
      }
      if (statItems.length >= 3 && stats.top_artists && stats.top_artists.length > 0) {
        const top = stats.top_artists[0];
        const pct = Math.round(stats.top_artist_share * 1000) / 10;
        statItems[2].querySelector('.stat-number').textContent = `${pct}%`;
        statItems[2].querySelector('.stat-name').textContent = `Top artist (${top.name})`;
      }
      if (statItems.length >= 4) {
        const top3Pct = Math.round(stats.top3_share * 1000) / 10;
        statItems[3].querySelector('.stat-number').textContent = `${top3Pct}%`;
      }
    }

    // Hydrate scores
    if (Array.isArray(report.scores) && report.scores.length === 3) {
      const scoreCards = document.querySelectorAll('.scores .score-card');
      report.scores.forEach((score, idx) => {
        if (scoreCards[idx]) {
          const valEl = scoreCards[idx].querySelector('.score-value');
          const meterFill = scoreCards[idx].querySelector('.meter-fill');
          const meter = scoreCards[idx].querySelector('.meter');

          if (valEl) {
            valEl.textContent = String(score.value);
          }
          if (meterFill) {
            meterFill.style.width = `${score.value}%`;
          }
          if (meter) {
            meter.setAttribute('aria-valuenow', String(score.value));
          }
        }
      });
    }

    // Hydrate observations list
    if (Array.isArray(report.observations)) {
      const obsList = document.querySelector('.observations');
      if (obsList) {
        obsList.innerHTML = ''; // Clear demo list
        report.observations.forEach((obsText) => {
          const li = document.createElement('li');
          li.textContent = obsText;
          obsList.appendChild(li);
        });
      }
    }

    // Hydrate final verdict
    const verdictText = document.querySelector('.verdict-text');
    if (verdictText && report.final_verdict) {
      verdictText.textContent = report.final_verdict;
    }
  } catch (err) {
    console.error('Error hydrating report:', err);
  }
}
