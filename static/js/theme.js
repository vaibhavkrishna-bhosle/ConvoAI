// Light / dark / system theme toggle.
// The initial theme is applied by an inline script in <head> (no flash);
// this module wires the toggle buttons and persists the choice.

const ORDER = ['system', 'light', 'dark'];
const ICONS = { system: 'brightness_auto', light: 'light_mode', dark: 'dark_mode' };
const LABELS = { system: 'Theme: system', light: 'Theme: light', dark: 'Theme: dark' };

function currentTheme() {
  return document.documentElement.dataset.themePref || 'system';
}

function apply(theme) {
  const root = document.documentElement;
  root.dataset.themePref = theme;
  if (theme === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', theme);
  try { localStorage.setItem('convoai-theme', theme); } catch (_) { /* storage unavailable */ }
  document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
    const icon = btn.querySelector('md-icon');
    if (icon) icon.textContent = ICONS[theme];
    btn.setAttribute('aria-label', LABELS[theme]);
    btn.title = LABELS[theme];
  });
}

async function persist(theme) {
  if (document.body.dataset.auth !== '1') return;
  const token = document.querySelector('meta[name="csrf-token"]')?.content;
  try {
    await fetch('/api/me/theme', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
      body: JSON.stringify({ theme }),
    });
  } catch (_) { /* offline: localStorage still has it */ }
}

apply(currentTheme());

document.addEventListener('click', (event) => {
  const btn = event.target.closest('[data-theme-toggle]');
  if (!btn) return;
  const next = ORDER[(ORDER.indexOf(currentTheme()) + 1) % ORDER.length];
  apply(next);
  persist(next);
});
