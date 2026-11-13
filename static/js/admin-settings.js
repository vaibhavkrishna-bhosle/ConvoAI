// Admin → Settings: form generated from the server's settings schema.
import { $, api, confirmDialog, esc, toast } from './admin-common.js';

const GROUP_ICONS = { Answering: 'smart_toy', Retrieval: 'travel_explore', Documents: 'description', Voice: 'mic' };
let state = null;            // last GET /api/settings
const changed = new Map();   // key → new value

function fieldHtml(spec, value, installed) {
  const def = state.defaults[spec.key];
  const support = `${spec.help}${def !== undefined && String(def) !== String(value) ? ` (Default: ${def})` : ''}`;
  const attrs = `data-key="${spec.key}" label="${esc(spec.label)}" supporting-text="${esc(support)}"`;
  if (spec.type === 'choice' || (spec.type === 'ollama_model' && installed)) {
    const options = spec.type === 'choice' ? spec.choices : [...new Set([...installed, value].filter(Boolean))];
    return `<md-outlined-select ${attrs}>${options.map((o) => `
      <md-select-option value="${esc(o)}" ${String(o) === String(value) ? 'selected' : ''}><div slot="headline">${esc(o)}</div></md-select-option>`).join('')}
      </md-outlined-select>`;
  }
  if (spec.type === 'ollama_model') return `<md-outlined-text-field ${attrs} value="${esc(value)}"></md-outlined-text-field>`;
  return `<md-outlined-text-field ${attrs} type="number" min="${spec.min}" max="${spec.max}" step="${spec.step}" value="${esc(value)}"></md-outlined-text-field>`;
}

function render() {
  const groups = {};
  state.schema.forEach((s) => { (groups[s.group] ||= []).push(s); });
  $('settings-groups').innerHTML = Object.entries(groups).map(([name, specs]) => `
    <section class="card settings-card">
      <h2><md-icon>${GROUP_ICONS[name] || 'tune'}</md-icon>${esc(name)}</h2>
      <div class="settings-fields">${specs.map((s) => fieldHtml(s, state.values[s.key], state.installed_models)).join('')}</div>
    </section>`).join('');
  $('ollama-banner').hidden = state.installed_models !== null;
  updateReindexBanner(false);
  // md-outlined-select created via innerHTML doesn't always draw its pre-selected option;
  // assigning the value after it upgrades makes it show (no change event is fired).
  document.querySelectorAll('#settings-groups md-outlined-select').forEach(async (sel) => {
    await customElements.whenDefined('md-outlined-select');
    await sel.updateComplete;
    sel.value = state.values[sel.dataset.key];
  });
}

function updateReindexBanner(justChanged) {
  const n = justChanged ? state.total_documents : state.stale_documents;
  $('reindex-banner').hidden = !n;
  $('reindex-text').textContent = justChanged
    ? `You changed a document setting. Re-index the ${n} document${n === 1 ? '' : 's'} to apply it to existing ones.`
    : `${n} document${n === 1 ? ' was' : 's were'} indexed with a different embedding model and won't be found until re-indexed.`;
}

async function load() {
  state = await api('/api/settings');
  changed.clear();
  $('save').disabled = true;
  render();
}

$('settings-groups').addEventListener('input', onEdit);
$('settings-groups').addEventListener('change', onEdit);
function onEdit(e) {
  const el = e.target.closest('[data-key]');
  if (!el) return;
  const key = el.dataset.key;
  if (String(el.value) === String(state.values[key])) changed.delete(key); else changed.set(key, el.value);
  el.error = false;
  $('save').disabled = changed.size === 0;
}

$('save').addEventListener('click', async () => {
  try {
    const r = await api('/api/settings', { method: 'PATCH', body: JSON.stringify(Object.fromEntries(changed)) });
    toast(`Saved ${r.saved.length} setting${r.saved.length === 1 ? '' : 's'}`);
    await load();
    if (r.needs_reindex) updateReindexBanner(true);
  } catch (err) {
    toast(err.message, 6000);
    // highlight the field the message names
    const spec = state.schema.find((s) => err.message.startsWith(s.label));
    const el = spec && document.querySelector(`[data-key="${spec.key}"]`);
    if (el) { el.error = true; el.errorText = err.message; el.focus?.(); }
  }
});

$('reset').addEventListener('click', async () => {
  if (!await confirmDialog('Reset settings?', 'All settings on this page go back to their defaults. Tuned thresholds are reset too (re-run training/evaluation to tune them again).', 'Reset', false)) return;
  const r = await api('/api/settings/reset', { method: 'POST' });
  toast(r.reset.length ? `Reset ${r.reset.length} setting(s)` : 'Already at defaults');
  await load();
  if (r.needs_reindex) updateReindexBanner(true);
});

$('reindex-all').addEventListener('click', async () => {
  const r = await api('/api/documents/reindex-all', { method: 'POST' });
  $('reindex-banner').hidden = true;
  toast(`Re-indexing ${r.queued} document${r.queued === 1 ? '' : 's'}. Follow progress on the Documents page.`, 5000);
});

window.addEventListener('beforeunload', (e) => { if (changed.size) { e.preventDefault(); e.returnValue = ''; } });

load();
