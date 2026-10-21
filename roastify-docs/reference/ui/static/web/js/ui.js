// Tone pill behavior. Plain ES module, no globals, no inline handlers.
// Form submission (fetch to /api/roast/) is wired in later phases; this file only
// keeps the pill buttons and the hidden "intensity" field in sync.

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
