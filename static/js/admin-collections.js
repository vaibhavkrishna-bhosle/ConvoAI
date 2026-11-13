// Admin → Collections: create, edit (name, description, icon, colour), delete.
import { $, api, confirmDialog, esc, showError, toast } from './admin-common.js';

let data = { collections: [], icons: [], colors: [] };
let editing = null;          // collection being edited, or null for new
let picked = { icon: 'folder', color: '#006A6A' };

function render() {
  $('collection-grid').innerHTML = data.collections.map((c) => `
    <article class="card collection-card" data-id="${c.id}">
      <div class="collection-head">
        <div class="icon-tile" style="background: color-mix(in srgb, ${esc(c.color)} 22%, var(--md-sys-color-surface)); color: ${esc(c.color)}">
          <md-icon>${esc(c.icon)}</md-icon></div>
        <div class="grow">
          <h2>${esc(c.name)}</h2>
          <div class="muted">${c.doc_count} document${c.doc_count === 1 ? '' : 's'}</div>
        </div>
        <md-icon-button data-act="edit" aria-label="Edit ${esc(c.name)}"><md-icon>edit</md-icon></md-icon-button>
        <md-icon-button data-act="delete" aria-label="Delete ${esc(c.name)}"><md-icon>delete</md-icon></md-icon-button>
      </div>
      <p class="muted collection-desc">${esc(c.description) || '<em>No description</em>'}</p>
      <a class="collection-link" href="/admin/documents">Manage documents <md-icon>arrow_forward</md-icon></a>
    </article>`).join('');
}

async function load() {
  data = await api('/api/collections');
  render();
}

function renderPickers() {
  $('c-icons').innerHTML = data.icons.map((i) => `
    <button type="button" class="pick-icon${i === picked.icon ? ' selected' : ''}" data-icon="${i}" role="radio"
      aria-checked="${i === picked.icon}" aria-label="${i.replace(/_/g, ' ')}"><md-icon>${i}</md-icon></button>`).join('');
  $('c-colors').innerHTML = data.colors.map((c) => `
    <button type="button" class="pick-color${c.toUpperCase() === picked.color.toUpperCase() ? ' selected' : ''}" data-color="${c}"
      role="radio" aria-checked="${c.toUpperCase() === picked.color.toUpperCase()}" aria-label="Colour ${c}" style="--swatch:${c}"></button>`).join('');
}

function openDialog(collection) {
  editing = collection;
  picked = { icon: collection?.icon || 'folder', color: collection?.color || data.colors[0] };
  $('collection-dialog-title').textContent = collection ? `Edit ${collection.name}` : 'New collection';
  $('c-name').value = collection?.name || '';
  $('c-description').value = collection?.description || '';
  showError('c-error', '');
  renderPickers();
  $('collection-dialog').show();
}

$('c-icons').addEventListener('click', (e) => {
  const b = e.target.closest('[data-icon]');
  if (b) { picked.icon = b.dataset.icon; renderPickers(); }
});
$('c-colors').addEventListener('click', (e) => {
  const b = e.target.closest('[data-color]');
  if (b) { picked.color = b.dataset.color; renderPickers(); }
});

$('c-save').addEventListener('click', async () => {
  const body = JSON.stringify({ name: $('c-name').value, description: $('c-description').value, ...picked });
  try {
    if (editing) await api(`/api/collections/${editing.id}`, { method: 'PATCH', body });
    else await api('/api/collections', { method: 'POST', body });
    $('collection-dialog').close();
    toast(editing ? 'Collection updated' : 'Collection created');
    load();
  } catch (err) {
    showError('c-error', err.message);
  }
});

$('new-collection').addEventListener('click', () => openDialog(null));

$('collection-grid').addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-act]');
  if (!btn) return;
  const c = data.collections.find((x) => x.id === Number(btn.closest('[data-id]').dataset.id));
  if (btn.dataset.act === 'edit') { openDialog(c); return; }
  const text = c.doc_count
    ? `“${c.name}” has ${c.doc_count} document${c.doc_count === 1 ? '' : 's'}. Deleting the collection also deletes them, their indexed chunks and the uploaded files. This can't be undone.`
    : `“${c.name}” is empty. Delete it?`;
  if (!await confirmDialog('Delete collection?', text, c.doc_count ? `Delete with ${c.doc_count} document${c.doc_count === 1 ? '' : 's'}` : 'Delete')) return;
  try {
    const r = await api(`/api/collections/${c.id}${c.doc_count ? '?force=1' : ''}`, { method: 'DELETE' });
    toast(`Deleted ${c.name}${r.documents_deleted ? ` and ${r.documents_deleted} document(s)` : ''}`);
    load();
  } catch (err) {
    toast(err.message, 5000);
  }
});

load();
