// Admin → Intents: list, search, create, edit, delete. Saving marks the model as needing a retrain.
import { $, api, confirmDialog, esc, showError, toast } from './admin-common.js';

const DOC_QUERY = 'doc_query';
let intents = [];
let editing = null;

function render() {
  const q = ($('intent-search').value || '').toLowerCase();
  const list = intents.filter((i) => !q || i.tag.includes(q) || i.description.toLowerCase().includes(q)
    || i.patterns.some((p) => p.toLowerCase().includes(q)));
  $('intent-count').textContent = intents.length;
  $('intent-rows').innerHTML = list.map((i) => `
    <tr data-id="${i.id}" class="${i.is_active ? '' : 'inactive'}" tabindex="0">
      <td class="mono">${esc(i.tag)}${i.is_active ? '' : ' <span class="badge">Off</span>'}</td>
      <td>${esc(i.description)}</td>
      <td>${i.patterns.length}</td>
      <td>${i.tag === DOC_QUERY ? '<span class="badge primary">→ RAG</span>' : i.responses.length}</td>
      <td class="muted">${i.patterns[0] ? `“${esc(i.patterns[0])}”` : ''}</td>
      <td class="row-actions"><md-icon-button aria-label="Edit ${esc(i.tag)}"><md-icon>edit</md-icon></md-icon-button></td>
    </tr>`).join('') || '<tr><td colspan="6" class="muted">No intents match.</td></tr>';
}

async function load() {
  const data = await api('/api/intents');
  intents = data.intents;
  $('dirty-banner').hidden = !data.dirty;
  render();
}

function openEditor(intent) {
  editing = intent;
  const isDocQuery = intent?.tag === DOC_QUERY;
  $('intent-dialog-title').textContent = intent ? `Edit ${intent.tag}` : 'New intent';
  $('i-tag').value = intent?.tag || '';
  $('i-tag').disabled = isDocQuery;
  $('i-active').selected = intent ? intent.is_active : true;
  $('i-active').disabled = isDocQuery;
  $('i-description').value = intent?.description || '';
  $('i-patterns').value = (intent?.patterns || []).join('\n');
  $('i-responses').value = (intent?.responses || []).join('\n');
  $('i-responses').disabled = isDocQuery;
  $('i-responses').supportingText = isDocQuery
    ? 'doc_query has no responses: matching questions are answered from the documents.'
    : 'One is picked at random. Placeholders: {name} {time} {date} {day} {collections}';
  $('i-delete').hidden = !intent || isDocQuery;
  showError('i-error', '');
  $('intent-dialog').show();
}

$('i-save').addEventListener('click', async () => {
  const body = JSON.stringify({
    tag: $('i-tag').value,
    description: $('i-description').value,
    is_active: $('i-active').selected,
    patterns: $('i-patterns').value,
    responses: $('i-responses').value,
  });
  try {
    if (editing) await api(`/api/intents/${editing.id}`, { method: 'PATCH', body });
    else await api('/api/intents', { method: 'POST', body });
    $('intent-dialog').close();
    toast('Saved. Retrain to apply it to the chat.');
    load();
  } catch (err) {
    showError('i-error', err.message);
  }
});

$('i-delete').addEventListener('click', async () => {
  const target = editing;
  $('intent-dialog').close();
  if (!await confirmDialog('Delete intent?', `“${target.tag}” and its ${target.patterns.length} patterns will be deleted. Retrain afterwards to update the model.`)) {
    $('intent-dialog').show();
    return;
  }
  try {
    await api(`/api/intents/${target.id}`, { method: 'DELETE' });
    toast(`Deleted ${target.tag}`);
    load();
  } catch (err) { toast(err.message, 5000); }
});

$('intent-rows').addEventListener('click', (e) => {
  const row = e.target.closest('tr[data-id]');
  if (row) openEditor(intents.find((i) => i.id === Number(row.dataset.id)));
});
$('intent-rows').addEventListener('keydown', (e) => {
  const row = e.target.closest('tr[data-id]');
  if (row && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); openEditor(intents.find((i) => i.id === Number(row.dataset.id))); }
});
$('intent-search').addEventListener('input', render);
$('new-intent').addEventListener('click', () => openEditor(null));

load();
