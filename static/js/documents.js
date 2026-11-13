// Admin → Documents: upload, add URL, live status, chunk viewer, delete, test retrieval.
import { csrfToken } from './app.js';

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const TYPE_ICON = { pdf: 'picture_as_pdf', docx: 'description', txt: 'article', md: 'notes', url: 'language' };
const STATUS = {
  queued: ['Queued', 'badge'],
  processing: ['Processing', 'badge warn'],
  ready: ['Ready', 'badge ok'],
  failed: ['Failed', 'badge err'],
};

let filter = '';
let pollTimer = null;
let lastDocs = [];

function toast(message, ms = 3500) {
  const t = $('toast');
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { t.hidden = true; }, ms);
}

async function api(url, options = {}) {
  const headers = { 'X-CSRFToken': csrfToken(), ...(options.headers || {}) };
  const res = await fetch(url, { ...options, headers });
  let body = {};
  try { body = await res.json(); } catch (_) { /* empty */ }
  if (!res.ok && res.status !== 400) throw new Error(body.error || res.statusText);
  return { ok: res.ok, status: res.status, body };
}

function fmtSize(bytes) {
  if (!bytes) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0; let n = bytes;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso.replace(' ', 'T') + (iso.endsWith('Z') || iso.includes('+') ? '' : 'Z'));
  return d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function statusCell(d) {
  const [label, cls] = STATUS[d.status] || [d.status, 'badge'];
  if (d.status === 'processing' || d.status === 'queued') {
    return `<span class="${cls}">${label}${d.status === 'processing' ? ` · ${d.progress}%` : ''}</span>
            <md-linear-progress value="${(d.progress || 0) / 100}" ${d.status === 'queued' ? 'indeterminate' : ''} class="row-progress"></md-linear-progress>`;
  }
  if (d.status === 'failed') {
    return `<span class="${cls}" title="${esc(d.error)}">${label}</span><div class="row-error">${esc(d.error)}</div>`;
  }
  return `<span class="${cls}">${label}</span>`;
}

function render(docs) {
  $('empty').hidden = docs.length > 0;
  $('doc-rows').innerHTML = docs.map((d) => `
    <tr data-id="${d.id}">
      <td>
        <div class="doc-cell">
          <span class="icon-tile small"><md-icon>${TYPE_ICON[d.source_type] || 'draft'}</md-icon></span>
          <div class="grow">
            <div class="doc-title">${esc(d.title)}</div>
            <div class="muted doc-meta">${d.source_type.toUpperCase()}${d.page_count ? ` · ${d.page_count} pages` : ''}${d.url ? ` · <a href="${esc(d.url)}" target="_blank" rel="noopener noreferrer">${esc(new URL(d.url).hostname)}</a>` : ''}</div>
          </div>
        </div>
      </td>
      <td><span class="coll-pill" style="--c:${esc(d.collection_color)}"><md-icon>${esc(d.collection_icon)}</md-icon>${esc(d.collection_name)}</span></td>
      <td class="status-cell">${statusCell(d)}</td>
      <td>${d.status === 'ready' ? d.chunk_count : '—'}</td>
      <td>${fmtSize(d.size_bytes)}</td>
      <td class="muted">${fmtDate(d.uploaded_at)}</td>
      <td class="row-actions">
        <md-icon-button data-act="edit" ${['queued', 'processing'].includes(d.status) ? 'disabled' : ''} title="Rename or move" aria-label="Rename or move"><md-icon>drive_file_rename_outline</md-icon></md-icon-button>
        <md-icon-button data-act="chunks" ${d.status !== 'ready' ? 'disabled' : ''} title="View chunks" aria-label="View chunks"><md-icon>view_agenda</md-icon></md-icon-button>
        <md-icon-button data-act="reindex" ${['queued', 'processing'].includes(d.status) ? 'disabled' : ''} title="Re-index" aria-label="Re-index"><md-icon>refresh</md-icon></md-icon-button>
        <md-icon-button data-act="delete" ${d.status === 'processing' ? 'disabled' : ''} title="Delete" aria-label="Delete"><md-icon>delete</md-icon></md-icon-button>
      </td>
    </tr>`).join('');
}

async function refresh() {
  clearTimeout(pollTimer);
  try {
    const { body } = await api(`/api/documents${filter ? `?collection_id=${filter}` : ''}`);
    lastDocs = body.documents;
    render(body.documents);
    if (body.busy) pollTimer = setTimeout(refresh, 1500);
  } catch (err) {
    toast(`Could not load documents: ${err.message}`);
  }
}

// ---------------------------------------------------------------- upload
async function upload(files) {
  if (!files.length) return;
  const form = new FormData();
  form.append('collection_id', $('upload-collection').value);
  [...files].forEach((f) => form.append('files', f));
  $('upload-status').textContent = `Uploading ${files.length} file${files.length > 1 ? 's' : ''}…`;
  try {
    const { body } = await api('/api/documents', { method: 'POST', body: form });
    const parts = [];
    if (body.created?.length) parts.push(`${body.created.length} added`);
    (body.skipped || []).forEach((s) => parts.push(`${s.file}: ${s.reason}`));
    $('upload-status').textContent = parts.join(' · ') || body.error || '';
    refresh();
  } catch (err) {
    $('upload-status').textContent = `Upload failed: ${err.message}`;
  }
  $('file-input').value = '';
}

const dz = $('dropzone');
$('file-input').addEventListener('change', (e) => upload(e.target.files));
dz.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('file-input').click(); } });
['dragenter', 'dragover'].forEach((t) => dz.addEventListener(t, (e) => { e.preventDefault(); dz.classList.add('over'); }));
['dragleave', 'drop'].forEach((t) => dz.addEventListener(t, (e) => { e.preventDefault(); dz.classList.remove('over'); }));
dz.addEventListener('drop', (e) => upload(e.dataTransfer.files));

// ---------------------------------------------------------------- add URL
$('open-url').addEventListener('click', () => { $('url-error').hidden = true; $('url-dialog').show(); });
$('url-submit').addEventListener('click', async () => {
  const url = $('url-input').value.trim();
  if (!url) { $('url-input').reportValidity(); return; }
  try {
    const { ok, body } = await api('/api/documents/url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, collection_id: $('url-collection').value }),
    });
    if (!ok) throw new Error(body.error);
    $('url-dialog').close();
    $('url-input').value = '';
    toast('Page added. Fetching and indexing…');
    refresh();
  } catch (err) {
    $('url-error').textContent = err.message;
    $('url-error').hidden = false;
  }
});

// ---------------------------------------------------------------- row actions
function confirmDialog(title, text, okLabel = 'Delete') {
  return new Promise((resolve) => {
    $('confirm-title').textContent = title;
    $('confirm-text').textContent = text;
    $('confirm-ok').textContent = okLabel;
    const dlg = $('confirm-dialog');
    const done = (v) => { dlg.close(); resolve(v); };
    $('confirm-ok').onclick = () => done(true);
    $('confirm-cancel').onclick = () => done(false);
    dlg.show();
  });
}

async function showChunks(id) {
  const { body } = await api(`/api/documents/${id}/chunks`);
  $('chunks-title').textContent = `${body.document.title} · ${body.chunks.length} chunks`;
  $('chunks-body').innerHTML = body.chunks.map((c) => `
    <article class="chunk">
      <div class="chunk-meta mono">#${c.index}${c.page ? ` · p.${c.page}` : ''}${c.heading ? ` · ${esc(c.heading)}` : ''} · ${c.chars} chars</div>
      <div class="chunk-text">${esc(c.text)}</div>
    </article>`).join('');
  $('chunks-dialog').show();
}
$('chunks-close').addEventListener('click', () => $('chunks-dialog').close());

$('doc-rows').addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-act]');
  if (!btn || btn.disabled) return;
  const row = btn.closest('tr');
  const id = row.dataset.id;
  const title = row.querySelector('.doc-title').textContent;
  try {
    if (btn.dataset.act === 'edit') {
      const doc = lastDocs.find((d) => String(d.id) === String(id));
      $('edit-title').value = doc.title;
      $('edit-collection').value = String(doc.collection_id);
      $('edit-error').hidden = true;
      $('edit-dialog').dataset.id = id;
      $('edit-dialog').show();
      return;
    }
    if (btn.dataset.act === 'chunks') await showChunks(id);
    if (btn.dataset.act === 'reindex') {
      await api(`/api/documents/${id}/reindex`, { method: 'POST' });
      toast(`Re-indexing “${title}”…`);
      refresh();
    }
    if (btn.dataset.act === 'delete') {
      if (!await confirmDialog('Delete document?', `“${title}” and its indexed chunks will be removed. The original file is deleted too. This can't be undone.`)) return;
      await api(`/api/documents/${id}`, { method: 'DELETE' });
      toast(`Deleted “${title}”`);
      refresh();
    }
  } catch (err) {
    toast(err.message);
  }
});

$('edit-save').addEventListener('click', async () => {
  const id = $('edit-dialog').dataset.id;
  try {
    const { ok, body } = await api(`/api/documents/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: $('edit-title').value, collection_id: $('edit-collection').value }),
    });
    if (!ok) throw new Error(body.error);
    $('edit-dialog').close();
    toast('Document updated');
    refresh();
  } catch (err) {
    $('edit-error').textContent = err.message;
    $('edit-error').hidden = false;
  }
});

// ---------------------------------------------------------------- filter chips
const chips = document.querySelectorAll('#filter-chips md-filter-chip');
chips.forEach((chip) => chip.addEventListener('click', () => {
  chips.forEach((c) => { c.selected = c === chip; });
  filter = chip.dataset.collection;
  refresh();
}));

// ---------------------------------------------------------------- test retrieval
const sq = $('search-q');
sq.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('search-form').requestSubmit(); } });
$('search-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = sq.value.trim();
  if (!q) return;
  const params = new URLSearchParams({ q, k: 3 });
  if (filter) params.set('collection_id', filter);
  try {
    const { body } = await api(`/api/documents/search?${params}`);
    const list = (hits) => hits.length ? hits.map((h) => `
      <div class="hit">
        <div class="hit-head"><span class="mono">${h.score.toFixed(3)}</span> ${esc(h.title)}${h.page ? ` · p.${h.page}` : ''}${h.heading ? ` · ${esc(h.heading)}` : ''}</div>
        <div class="hit-text">${esc(h.text.slice(0, 260))}${h.text.length > 260 ? '…' : ''}</div>
      </div>`).join('') : '<div class="muted">No matches.</div>';
    $('vector-hits').innerHTML = list(body.vector);
    $('keyword-hits').innerHTML = list(body.keyword);
    $('search-results').hidden = false;
  } catch (err) {
    toast(err.message);
  }
});

refresh();
