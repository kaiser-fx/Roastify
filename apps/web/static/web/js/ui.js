// Tone pill behavior and UI initialization.
// Plain ES module, no globals, no inline handlers.

import { initForms } from './form.js';
import { initResultsPage } from './render.js';

const toneGroups = document.querySelectorAll('[data-tone-group]');

toneGroups.forEach((group) => {
  const form = group.closest('form');
  const hiddenField = form ? form.querySelector('input[name="intensity"]') : null;

  group.addEventListener('click', (event) => {
    const pill = event.target.closest('[data-tone]');
    if (!pill) {
      return;
    }

    group.querySelectorAll('[data-tone]').forEach((other) => {
      const isSelected = other === pill;
      other.classList.toggle('is-selected', isSelected);
      other.setAttribute('aria-pressed', String(isSelected));
    });

    if (hiddenField) {
      hiddenField.value = pill.dataset.tone;
    }
  });
});

// Initialize form handling for landing and fallback pages.
initForms();

// Hydrate results page from client-side state if available.
initResultsPage();
