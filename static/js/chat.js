// ConvoAI chat: streaming answers, Markdown + citations, sources sheet, history, feedback.
import { csrfToken } from './app.js';
import { Recorder, micSupported, speak, stopSpeaking, ttsSupported, localVoice } from './voice.js';

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const state = {
  conversationId: Number($('chat-layout').dataset.conversation) || null,
  collectionId: null,
  controller: null,            // AbortController while an answer streams
  conversations: [],
  messages: new Map(),         // bot message id → {content, sources, question}
  micAvailable: false,         // local Whisper reachable + browser can record
  canSpeak: false,             // a read-aloud voice installed on this computer
};

// ------------------------------------------------------------------ Markdown (safe)
window.marked.use({
  gfm: true,
  breaks: true,
  renderer: {
    html(token) { return esc(token.text); },                       // never render raw HTML from the model
    image(token) { return esc(token.text || ''); },
    link(token) {
      const text = this.parser.parseInline(token.tokens);
      return /^(https?:|mailto:)/i.test(token.href)
        ? `<a href="${esc(token.href)}" target="_blank" rel="noopener noreferrer">${text}</a>` : text;
    },
  },
});

function renderMarkdown(text) {
  const html = window.marked.parse(text || '');
  // [1] → clickable citation chip (outside code blocks)
  return html.replace(/(<code[\s\S]*?<\/code>)|\[(\d{1,2})\]/g, (m, code, n) =>
    code || `<button type="button" class="cite" data-n="${n}" aria-label="Source ${n}">${n}</button>`);
}

// ------------------------------------------------------------------ helpers
function toast(message, ms = 3500) {
  const t = $('toast');
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, ms);
}

async function api(url, options = {}) {
  const res = await fetch(url, { ...options, headers: { 'X-CSRFToken': csrfToken(), 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || res.statusText);
  return body;
}

const scroller = $('chat-scroll');
const nearBottom = () => scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 120;
function scrollToBottom(force = false) {
  if (force || nearBottom()) scroller.scrollTop = scroller.scrollHeight;
}
scroller.addEventListener('scroll', () => { $('jump-latest').hidden = nearBottom(); });
$('jump-latest').addEventListener('click', () => scrollToBottom(true));

function setHero(visible) {
  $('hero').hidden = !visible;
  $('thread').hidden = visible;
}

function setTitle(title) {
  $('chat-title').textContent = title || 'Chat';
  document.title = `${title || 'Chat'} · ConvoAI`;
}

// ------------------------------------------------------------------ sources
function groupSources(sources) {
  const groups = new Map();
  for (const s of sources) {
    const key = sourceLabel(s);  // title · page · section (saved messages have no precomputed label)
    if (!groups.has(key)) groups.set(key, { label: key, title: s.title, page: s.page, heading: s.heading, all: [], citedNs: [] });
    const g = groups.get(key);
    g.all.push(s.n);
    if (s.cited) g.citedNs.push(s.n);
  }
  // a chip shows (and opens at) the numbers the answer actually cites
  return [...groups.values()].map((g) => ({ ...g, cited: g.citedNs.length > 0, ns: g.citedNs.length ? g.citedNs : g.all }));
}

function sourceLabel(s) {
  return s.label || [s.title, s.page ? `p.${s.page}` : null, s.heading && s.heading !== s.title ? s.heading : null].filter(Boolean).join(' · ');
}

const STOP = new Set('what which when where does have from that this with your about there their will would could should into much many tell need please'.split(' '));
function highlight(text, question) {
  let html = esc(text);
  const words = [...new Set((question || '').toLowerCase().match(/[a-z0-9]{4,}/g) || [])].filter((w) => !STOP.has(w));
  for (const w of words.slice(0, 8)) {
    html = html.replace(new RegExp(`\\b(${w}\\w*)`, 'gi'), '<mark>$1</mark>');
  }
  return html;
}

function openSources(messageId, focusN) {
  const msg = state.messages.get(messageId);
  if (!msg) return;
  const ordered = [...msg.sources].sort((a, b) => (b.cited - a.cited) || (a.n - b.n));
  $('source-body').innerHTML = ordered.map((s) => `
    <article class="source-card${s.cited ? ' cited' : ''}" id="src-${messageId}-${s.n}">
      <div class="source-head">
        <span class="cite static">${s.n}</span>
        <div class="grow">
          <div class="source-title">${esc(s.title)}</div>
          <div class="muted source-loc">${esc([s.page ? `Page ${s.page}` : null, s.heading && s.heading !== s.title ? s.heading : null].filter(Boolean).join(' · ') || 'Document')}</div>
        </div>
        <span class="badge ${s.cited ? 'ok' : ''}" title="Retrieval score">${s.cited ? 'Cited' : 'Retrieved'}</span>
      </div>
      <div class="source-text">${highlight(s.text, msg.question)}</div>
    </article>`).join('');
  $('source-sheet').hidden = false;
  document.body.classList.add('sheet-open');
  const target = focusN && $(`src-${messageId}-${focusN}`);
  if (target) {
    target.scrollIntoView({ block: 'start', behavior: 'smooth' });
    target.classList.add('flash-focus');
    setTimeout(() => target.classList.remove('flash-focus'), 1200);
  } else {
    $('source-body').scrollTop = 0;
  }
}
function closeSources() {
  $('source-sheet').hidden = true;
  document.body.classList.remove('sheet-open');
}
$('close-sources').addEventListener('click', closeSources);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('source-sheet').hidden) closeSources(); });

// ------------------------------------------------------------------ message rendering
const ROUTES = {
  intent: ['bolt', 'Quick reply'],
  rag: ['description', 'From documents'],
  fallback: ['search_off', 'Not found in documents'],
};

function userBubble(text) {
  const el = document.createElement('div');
  el.className = 'msg user';
  el.innerHTML = `<div class="bubble">${esc(text)}</div>`;
  return el;
}

function botBubble() {
  const el = document.createElement('div');
  el.className = 'msg bot';
  el.innerHTML = `
    <div class="avatar-bot"><md-icon>forum</md-icon></div>
    <div class="bot-body">
      <div class="typing"><span class="dots"><i></i><i></i><i></i></span><span class="typing-text">Thinking…</span></div>
      <div class="content markdown"></div>
      <div class="source-chips"></div>
      <div class="msg-meta"></div>
    </div>`;
  return el;
}

function finishBot(el, msg) {
  el.dataset.id = msg.id;
  el.querySelector('.typing')?.remove();
  el.querySelector('.content').innerHTML = renderMarkdown(msg.content);

  const groups = msg.route === 'rag' ? groupSources(msg.sources || []) : [];
  const shown = groups.filter((g) => g.cited).length ? groups.filter((g) => g.cited) : groups.slice(0, 3);
  el.querySelector('.source-chips').innerHTML = shown.map((g) => `
    <button type="button" class="source-chip" data-n="${g.ns[0]}" title="${esc(g.label)}">
      <md-icon>${g.page ? 'picture_as_pdf' : 'article'}</md-icon>
      <span class="chip-title">${esc(g.title)}</span>
      ${g.page || (g.heading && g.heading !== g.title) ? `<span class="chip-loc">${esc(g.page ? `p.${g.page}` : g.heading)}</span>` : ''}
      <span class="chip-ns">${g.ns.map((n) => `<span class="cite static">${n}</span>`).join('')}</span>
    </button>`).join('') + (groups.length > shown.length ? `<button type="button" class="source-chip more" data-n="">+${groups.length - shown.length} more</button>` : '');

  const [icon, label] = ROUTES[msg.route] || ['chat', msg.route];
  const timings = msg.timings_ms ? Object.entries(msg.timings_ms).map(([k, v]) => `${k}: ${v} ms`).join('\n') : '';
  const detail = msg.route === 'intent' && msg.intent ? ` · ${esc(msg.intent)} ${Number(msg.confidence).toFixed(2)}` : '';
  el.querySelector('.msg-meta').innerHTML = `
    <span class="route-pill route-${esc(msg.route)}" title="${esc(timings)}"><md-icon>${icon}</md-icon>${label}${detail}</span>
    ${msg.latency_ms != null ? `<span class="muted latency">${(msg.latency_ms / 1000).toFixed(1)} s</span>` : ''}
    <span class="msg-actions">
      <md-icon-button data-act="speak" toggle aria-label="Read aloud" title="Read aloud" ${state.canSpeak ? '' : 'hidden'}>
        <md-icon>volume_up</md-icon><md-icon slot="selected">stop_circle</md-icon></md-icon-button>
      <md-icon-button data-act="copy" aria-label="Copy answer" title="Copy"><md-icon>content_copy</md-icon></md-icon-button>
      <md-icon-button data-act="up" toggle ${msg.feedback === 1 ? 'selected' : ''} aria-label="Good answer" title="Good answer">
        <md-icon>thumb_up</md-icon><md-icon slot="selected" class="filled">thumb_up</md-icon></md-icon-button>
      <md-icon-button data-act="down" toggle ${msg.feedback === -1 ? 'selected' : ''} aria-label="Bad answer" title="Bad answer">
        <md-icon>thumb_down</md-icon><md-icon slot="selected" class="filled">thumb_down</md-icon></md-icon-button>
    </span>`;
  state.messages.set(String(msg.id), { content: msg.content, sources: msg.sources || [], question: msg.question });
}

function renderThread(messages) {
  const thread = $('thread');
  thread.innerHTML = '';
  let lastQuestion = '';
  for (const m of messages) {
    if (m.role === 'user') {
      lastQuestion = m.content;
      thread.appendChild(userBubble(m.content));
    } else {
      const el = botBubble();
      thread.appendChild(el);
      finishBot(el, { ...m, question: lastQuestion });
    }
  }
  setHero(messages.length === 0);
  scrollToBottom(true);
}

// ------------------------------------------------------------------ thread interactions
$('thread').addEventListener('click', async (e) => {
  const bot = e.target.closest('.msg.bot');
  if (!bot || !bot.dataset.id) return;
  const id = bot.dataset.id;

  const cite = e.target.closest('.cite:not(.static), .source-chip');
  if (cite) { openSources(id, Number(cite.dataset.n) || null); return; }

  const btn = e.target.closest('[data-act="copy"]');
  if (!btn) return;
  const msg = state.messages.get(id);
  try {
    await navigator.clipboard.writeText((msg?.content || '').replace(/\s*\[\d{1,2}\]/g, ''));
    toast('Answer copied');
  } catch (_) { toast('Copy failed'); }
});

// ------------------------------------------------------------------ read aloud
function speakAnswer(id) {
  const bot = document.querySelector(`.msg.bot[data-id="${id}"]`);
  const btn = bot?.querySelector('[data-act="speak"]');
  const msg = state.messages.get(String(id));
  if (!msg || !state.canSpeak) return;
  document.querySelectorAll('[data-act="speak"]').forEach((b) => { b.selected = b === btn; });
  speak(String(id), msg.content, { onEnd: () => { if (btn) btn.selected = false; } });
}

function stopReading() {
  stopSpeaking();
  document.querySelectorAll('[data-act="speak"]').forEach((b) => { b.selected = false; });
}

$('thread').addEventListener('change', (e) => {
  const btn = e.target.closest('[data-act="speak"]');
  const bot = btn?.closest('.msg.bot');
  if (!btn || !bot?.dataset.id) return;
  if (btn.selected) speakAnswer(bot.dataset.id); else stopReading();
});

const AUTOSPEAK_KEY = 'convoai-autospeak';
$('autospeak').addEventListener('change', () => {
  try { localStorage.setItem(AUTOSPEAK_KEY, $('autospeak').selected ? '1' : '0'); } catch (_) { /* private mode */ }
  if (!$('autospeak').selected) stopReading();
  toast($('autospeak').selected ? 'Answers will be read aloud' : 'Read-aloud off (voice questions are still answered aloud)');
});

// feedback toggles fire `change` after their selected state flips
$('thread').addEventListener('change', async (e) => {
  const btn = e.target.closest('[data-act="up"], [data-act="down"]');
  const bot = btn?.closest('.msg.bot');
  if (!btn || !bot?.dataset.id) return;
  const id = bot.dataset.id;
  // the two toggles behave like a radio group that can be cleared
  const up = bot.querySelector('[data-act="up"]');
  const down = bot.querySelector('[data-act="down"]');
  const isUp = btn.dataset.act === 'up';
  const selected = btn.selected;
  (isUp ? down : up).selected = false;
  const rating = selected ? (isUp ? 1 : -1) : 0;
  try {
    await api(`/api/messages/${id}/feedback`, { method: 'POST', body: JSON.stringify({ rating }) });
    if (rating) toast(rating === 1 ? 'Thanks for the feedback!' : 'Thanks. This helps an admin improve the documents.');
  } catch (err) {
    btn.selected = !selected;
    toast(err.message);
  }
});

// ------------------------------------------------------------------ sending + streaming
const box = $('message');
const sendBtn = $('send');
const stopBtn = $('stop');

function autoGrow() {
  box.style.height = 'auto';
  box.style.height = `${Math.min(box.scrollHeight, 200)}px`;
  sendBtn.disabled = !box.value.trim() || !!state.controller;
}
box.addEventListener('input', autoGrow);
box.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); $('composer').requestSubmit(); }
});
$('composer').addEventListener('submit', (e) => { e.preventDefault(); send(box.value); });
document.querySelectorAll('[data-suggestion]').forEach((b) => b.addEventListener('click', () => send(b.dataset.suggestion)));
stopBtn.addEventListener('click', () => state.controller?.abort());

function setBusy(busy) {
  sendBtn.hidden = busy;
  stopBtn.hidden = !busy;
  $('mic').disabled = busy || !state.micAvailable;
  box.disabled = false;
  autoGrow();
}

async function send(raw, { viaVoice = false } = {}) {
  const text = raw.trim();
  if (!text || state.controller) return;
  stopReading();
  box.value = '';
  setHero(false);
  closeSources();
  $('thread').appendChild(userBubble(text));
  const el = botBubble();
  $('thread').appendChild(el);
  scrollToBottom(true);

  state.controller = new AbortController();
  setBusy(true);
  const contentEl = el.querySelector('.content');
  let answer = '';
  let frame = null;
  let finished = false;
  // Follow the answer only if the reader was at the bottom *before* this update
  // (checking afterwards fails when a big chunk, like the source chips, is added at once).
  const paint = () => {
    frame = null;
    const stick = nearBottom();
    contentEl.innerHTML = renderMarkdown(answer);
    if (stick) scrollToBottom(true);
  };

  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      signal: state.controller.signal,
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify({ message: text, conversation_id: state.conversationId, collection_id: state.collectionId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || res.statusText);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let cut;
      while ((cut = buffer.indexOf('\n\n')) >= 0) {
        const block = buffer.slice(0, cut);
        buffer = buffer.slice(cut + 2);
        const line = block.split('\n').find((l) => l.startsWith('data: '));
        if (!line) continue;
        const ev = JSON.parse(line.slice(6));
        if (ev.type === 'start') {
          if (state.conversationId !== ev.conversation_id) {
            state.conversationId = ev.conversation_id;
            history.replaceState({ id: ev.conversation_id }, '', `/c/${ev.conversation_id}`);
            setTitle(text.slice(0, 60));
          }
        } else if (ev.type === 'status') {
          const t = el.querySelector('.typing-text');
          if (t) t.textContent = ev.text;
        } else if (ev.type === 'token') {
          if (el.querySelector('.typing')) {
            const stick = nearBottom();
            el.querySelector('.typing').remove();
            if (stick) scrollToBottom(true);
          }
          answer += ev.text;
          if (!frame) frame = requestAnimationFrame(paint);
        } else if (ev.type === 'error') {
          toast(ev.error, 6000);
        } else if (ev.type === 'done') {
          if (frame) cancelAnimationFrame(frame);
          const stick = nearBottom();
          finishBot(el, { ...ev, id: ev.message_id, question: text });
          finished = true;
          // voice questions get spoken answers; typed ones only when read-aloud is switched on
          if (viaVoice || $('autospeak').selected) speakAnswer(ev.message_id);
          if (stick) scrollToBottom(true);
        }
      }
    }
    if (!finished) throw new Error('The connection closed before the answer finished.');
  } catch (err) {
    el.querySelector('.typing')?.remove();
    if (err.name === 'AbortError') {
      contentEl.innerHTML = renderMarkdown(answer) + '<p class="muted stopped">Stopped.</p>';
    } else {
      el.classList.add('error');
      contentEl.innerHTML = `<p>Sorry, something went wrong: ${esc(err.message)}</p>`;
      const retry = document.createElement('md-text-button');
      retry.innerHTML = '<md-icon slot="icon">refresh</md-icon>Try again';
      retry.addEventListener('click', () => { el.previousElementSibling?.remove(); el.remove(); send(text); });
      contentEl.appendChild(retry);
    }
  } finally {
    state.controller = null;
    setBusy(false);
    box.focus();
    loadHistory();
  }
}

// ------------------------------------------------------------------ collections
const chips = document.querySelectorAll('#collection-chips md-filter-chip');
function selectCollection(id) {
  state.collectionId = id ? Number(id) : null;
  chips.forEach((c) => { c.selected = (c.dataset.collection || '') === (id ? String(id) : ''); });
  const chip = [...chips].find((c) => c.selected);
  $('chat-subtitle').textContent = state.collectionId ? `Searching ${chip?.label || 'one collection'}` : 'Searching all your collections';
}
chips.forEach((chip) => chip.addEventListener('click', () => selectCollection(chip.dataset.collection)));

// ------------------------------------------------------------------ history
function dayGroup(iso) {
  const d = new Date(`${iso.replace(' ', 'T')}Z`);
  const start = new Date(); start.setHours(0, 0, 0, 0);
  const days = Math.floor((start - d) / 86400000) + 1;
  if (d >= start) return 'Today';
  if (days <= 1) return 'Yesterday';
  if (days <= 7) return 'Previous 7 days';
  if (days <= 30) return 'Previous 30 days';
  return 'Older';
}

function renderHistory() {
  const q = ($('history-search').value || '').toLowerCase();
  const list = state.conversations.filter((c) => !q || c.title.toLowerCase().includes(q));
  $('history-empty').hidden = state.conversations.length > 0;
  let html = '';
  let group = '';
  for (const c of list) {
    const g = dayGroup(c.updated_at);
    if (g !== group) { html += `<div class="history-group">${g}</div>`; group = g; }
    html += `
      <div class="history-item${c.id === state.conversationId ? ' active' : ''}" data-id="${c.id}">
        <a href="/c/${c.id}" class="history-link" title="${esc(c.title)}">${esc(c.title)}</a>
        <md-icon-button class="history-more" data-id="${c.id}" aria-label="More options for ${esc(c.title)}"><md-icon>more_vert</md-icon></md-icon-button>
      </div>`;
  }
  if (q && !list.length) html = '<div class="muted history-none">No chats match.</div>';
  $('history-list').innerHTML = html;
}

async function loadHistory() {
  try {
    state.conversations = (await api('/api/conversations')).conversations;
    renderHistory();
  } catch (_) { /* keep the old list */ }
}
$('history-search').addEventListener('input', renderHistory);

async function openConversation(id, push = true) {
  if (state.controller) state.controller.abort();
  try {
    const data = await api(`/api/conversations/${id}`);
    state.conversationId = id;
    state.messages.clear();
    setTitle(data.conversation.title);
    selectCollection(data.conversation.collection_id || '');
    renderThread(data.messages);
    if (push) history.pushState({ id }, '', `/c/${id}`);
    renderHistory();
    closeDrawer();
  } catch (err) {
    toast(err.message);
    newChat();
  }
}

function newChat(push = true) {
  if (state.controller) state.controller.abort();
  state.conversationId = null;
  state.messages.clear();
  $('thread').innerHTML = '';
  setHero(true);
  setTitle('Chat');
  closeSources();
  if (push) history.pushState({}, '', '/');
  renderHistory();
  closeDrawer();
  box.focus();
}
$('new-chat').addEventListener('click', () => newChat());
$('new-chat-top').addEventListener('click', () => newChat());

$('history-list').addEventListener('click', (e) => {
  const more = e.target.closest('.history-more');
  if (more) {
    e.preventDefault();
    const menu = $('conv-menu');
    menu.anchorElement = more;
    menu.dataset.id = more.dataset.id;
    menu.open = true;
    return;
  }
  const link = e.target.closest('.history-link');
  if (link) {
    e.preventDefault();
    openConversation(Number(link.closest('.history-item').dataset.id));
  }
});

window.addEventListener('popstate', () => {
  const m = location.pathname.match(/^\/c\/(\d+)/);
  if (m) openConversation(Number(m[1]), false); else newChat(false);
});

// rename / delete
$('conv-rename').addEventListener('click', () => {
  const id = Number($('conv-menu').dataset.id);
  const conv = state.conversations.find((c) => c.id === id);
  $('rename-input').value = conv?.title || '';
  $('rename-dialog').dataset.id = id;
  $('rename-dialog').show();
});
$('rename-save').addEventListener('click', async () => {
  const id = Number($('rename-dialog').dataset.id);
  const title = $('rename-input').value.trim();
  if (!title) return;
  try {
    await api(`/api/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) });
    $('rename-dialog').close();
    if (id === state.conversationId) setTitle(title);
    loadHistory();
  } catch (err) { toast(err.message); }
});
$('conv-delete').addEventListener('click', () => {
  const id = Number($('conv-menu').dataset.id);
  const conv = state.conversations.find((c) => c.id === id);
  $('delete-text').textContent = `“${conv?.title || 'This chat'}” and all its messages will be deleted. This can't be undone.`;
  $('delete-dialog').dataset.id = id;
  $('delete-dialog').show();
});
$('delete-cancel').addEventListener('click', () => $('delete-dialog').close());
$('delete-ok').addEventListener('click', async () => {
  const id = Number($('delete-dialog').dataset.id);
  try {
    await api(`/api/conversations/${id}`, { method: 'DELETE' });
    $('delete-dialog').close();
    if (id === state.conversationId) newChat();
    loadHistory();
    toast('Chat deleted');
  } catch (err) { toast(err.message); }
});

// mobile drawer
function closeDrawer() {
  $('history').classList.remove('open');
  $('history-scrim').hidden = true;
}
$('open-history').addEventListener('click', () => {
  $('history').classList.add('open');
  $('history-scrim').hidden = false;
});
$('history-scrim').addEventListener('click', closeDrawer);

// ------------------------------------------------------------------ voice input
const mic = $('mic');
let recording = null;

function fmtTime(ms) {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function setRecordingUI(mode) {               // false | 'recording' | 'transcribing'
  const composer = $('composer');
  composer.classList.toggle('recording', mode === 'recording');
  composer.classList.toggle('transcribing', mode === 'transcribing');
  $('rec-status').hidden = !mode;
  box.hidden = !!mode;
  $('rec-text').textContent = mode === 'transcribing' ? 'Transcribing on this computer…' : 'Listening… tap ■ when done, Esc to cancel';
  if (mode !== 'recording') { $('rec-level').style.width = '0%'; $('rec-time').textContent = mode ? '' : '0:00'; }
  mic.querySelector('md-icon').textContent = mode === 'recording' ? 'stop_circle' : 'mic';
  mic.setAttribute('aria-label', mode === 'recording' ? 'Stop recording and send' : 'Ask by voice');
  mic.disabled = mode === 'transcribing' || !!state.controller || !state.micAvailable;
  sendBtn.disabled = !!mode || !box.value.trim();
}

async function toggleMic() {
  if (recording) { recording.stop(); return; }
  if (state.controller) return;
  stopReading();
  const rec = new Recorder({
    onLevel: (level, ms) => {
      $('rec-level').style.width = `${Math.round(level * 100)}%`;
      $('rec-time').textContent = fmtTime(ms);
    },
  });
  recording = rec;
  setRecordingUI('recording');
  let blob;
  try {
    blob = await rec.start();
  } catch (err) {
    recording = null;
    setRecordingUI(false);
    toast(err.name === 'NotAllowedError' ? 'Microphone access is blocked. Allow it in the browser’s site settings and try again.'
      : err.name === 'NotFoundError' ? 'No microphone was found.' : `Microphone error: ${err.message}`, 6000);
    return;
  }
  recording = null;
  if (!blob) {
    setRecordingUI(false);
    if (rec.cancelReason === 'silence') toast("I didn't hear anything. Tap the mic and speak your question.");
    box.focus();
    return;
  }

  setRecordingUI('transcribing');
  try {
    const form = new FormData();
    form.append('audio', blob, `question.${blob.type.includes('ogg') ? 'ogg' : blob.type.includes('mp4') ? 'm4a' : 'webm'}`);
    const res = await fetch('/api/speech/transcribe', { method: 'POST', headers: { 'X-CSRFToken': csrfToken() }, body: form });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || res.statusText);
    setRecordingUI(false);
    send(body.text, { viaVoice: true });
  } catch (err) {
    setRecordingUI(false);
    toast(err.message, 5000);
  }
}

mic.addEventListener('click', toggleMic);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && recording) { e.preventDefault(); recording.cancel('user'); }
});

async function initVoice() {
  if (micSupported()) {
    try {
      const status = await api('/api/speech/status');
      state.micAvailable = status.available;
      mic.disabled = !status.available || !!state.controller;
      mic.title = status.available ? `Ask by voice (Whisper ${status.model}, on this computer)` : 'Voice input needs faster-whisper (pip install faster-whisper)';
    } catch (_) { mic.title = 'Voice input is unavailable'; }
  } else {
    mic.title = 'This browser cannot record audio';
  }
  if (ttsSupported() && await localVoice()) {
    state.canSpeak = true;
    $('autospeak').hidden = false;
    try { $('autospeak').selected = localStorage.getItem(AUTOSPEAK_KEY) === '1'; } catch (_) { /* ignore */ }
    document.querySelectorAll('[data-act="speak"]').forEach((b) => { b.hidden = false; });
  }
}

// ------------------------------------------------------------------ start
const hour = new Date().getHours();
$('greeting').textContent = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
selectCollection('');
loadHistory();
if (state.conversationId) openConversation(state.conversationId, false); else setHero(true);
autoGrow();
box.focus();
initVoice();
