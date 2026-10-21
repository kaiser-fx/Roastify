// Form submission and fallback behavior for Roastify.
// Handles URL submission, manual track lists, CSV upload, and fallback transitions.

const LOADING_MESSAGES = [
  'Reading playlist...',
  'Counting how many times you hit repeat...',
  'Evaluating top artist obsession...',
  'Consulting the roast tribunal...',
  'Measuring emotional damage...',
  'Sharpening the final verdict...',
];

function startLoadingMessages(statusEl) {
  if (!statusEl) return null;
  let idx = 0;
  statusEl.textContent = LOADING_MESSAGES[0];
  const timer = setInterval(() => {
    idx = (idx + 1) % LOADING_MESSAGES.length;
    statusEl.textContent = LOADING_MESSAGES[idx];
  }, 1400);
  return timer;
}

function stopLoadingMessages(timer) {
  if (timer) {
    clearInterval(timer);
  }
}

function getCsrfToken(form) {
  const tokenInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
  if (tokenInput) {
    return tokenInput.value;
  }
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

export function initForms() {
  const roastForm = document.getElementById('roast-form');
  const manualForm = document.getElementById('manual-form');

  if (roastForm) {
    setupRoastForm(roastForm);
  }

  if (manualForm) {
    setupManualForm(manualForm);
  }
}

function setupRoastForm(form) {
  const urlInput = form.querySelector('#playlist-url');
  const statusEl = form.querySelector('#form-status');
  const submitBtn = form.querySelector('button[type="submit"]');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const rawUrl = urlInput ? urlInput.value.trim() : '';
    if (!rawUrl) {
      if (statusEl) {
        statusEl.textContent = 'Please enter a Spotify playlist link.';
      }
      if (urlInput) {
        urlInput.focus();
      }
      return;
    }

    const intensity = form.querySelector('input[name="intensity"]')?.value || 'savage';

    if (submitBtn) {
      submitBtn.disabled = true;
    }
    const loadingTimer = startLoadingMessages(statusEl);

    try {
      const response = await fetch('/api/roast/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(form),
        },
        body: JSON.stringify({
          source: 'spotify',
          url: rawUrl,
          intensity: intensity,
        }),
      });

      const data = await response.json();
      stopLoadingMessages(loadingTimer);

      if (!response.ok) {
        const error = data.error || {};
        if (error.fallback === 'manual') {
          // Switch to the manual fallback page with the error message.
          const fallbackUrl = `/fallback/?error=${encodeURIComponent(error.message || 'Spotify access was blocked.')}`;
          window.location.href = fallbackUrl;
          return;
        }

        if (statusEl) {
          statusEl.textContent = error.message || 'Could not read that playlist.';
        }
        return;
      }

      // Store report and navigate to results page
      if (data.report) {
        sessionStorage.setItem('roastify_session', JSON.stringify(data));
        window.location.href = '/results/';
      } else if (statusEl) {
        const trackCount = data.playlist?.track_count || 0;
        const title = data.playlist?.title || 'Playlist';
        statusEl.textContent = `Found ${trackCount} tracks for "${title}".`;
      }
    } catch (err) {
      stopLoadingMessages(loadingTimer);
      if (statusEl) {
        statusEl.textContent = 'Network error. Please try again.';
      }
    } finally {
      stopLoadingMessages(loadingTimer);
      if (submitBtn) {
        submitBtn.disabled = false;
      }
    }
  });
}

function setupManualForm(form) {
  const textarea = form.querySelector('#tracks');
  const fileInput = form.querySelector('#csv-file');
  const statusEl = form.querySelector('#form-status');
  const submitBtn = form.querySelector('button[type="submit"]');
  const fileLabel = form.querySelector('label[for="csv-file"]');

  if (fileInput && fileLabel) {
    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files[0]) {
        fileLabel.textContent = fileInput.files[0].name;
      } else {
        fileLabel.textContent = 'Upload a CSV';
      }
    });
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const tracksText = textarea ? textarea.value.trim() : '';
    const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;

    if (!tracksText && !hasFile) {
      if (statusEl) {
        statusEl.textContent = 'Paste at least one track or choose a CSV file.';
      }
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
    }
    const loadingTimer = startLoadingMessages(statusEl);

    const formData = new FormData(form);
    formData.set('source', 'manual');

    try {
      const response = await fetch('/api/roast/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(form),
        },
        body: formData,
      });

      const data = await response.json();
      stopLoadingMessages(loadingTimer);

      if (!response.ok) {
        const error = data.error || {};
        if (statusEl) {
          statusEl.textContent = error.message || 'Could not parse tracks.';
        }
        return;
      }

      // Store report and navigate to results page
      if (data.report) {
        sessionStorage.setItem('roastify_session', JSON.stringify(data));
        window.location.href = '/results/';
      } else if (statusEl) {
        const count = data.playlist?.track_count || 0;
        statusEl.textContent = `Loaded ${count} tracks successfully.`;
      }
    } catch (err) {
      stopLoadingMessages(loadingTimer);
      if (statusEl) {
        statusEl.textContent = 'Network error. Please try again.';
      }
    } finally {
      stopLoadingMessages(loadingTimer);
      if (submitBtn) {
        submitBtn.disabled = false;
      }
    }
  });
}
