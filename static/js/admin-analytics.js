// Admin → Analytics dashboard.
import { api, toast } from './admin-common.js';
import { esc, onThemeChange, pct, rankedBars, rankedHeight, secs, stackedDaily, tableToggle } from './charts.js';

// Colour follows the entity: each route keeps its slot on every chart.
const ROUTES = [
  { key: 'rag', label: 'From documents', color: 's1', css: '--series-1' },
  { key: 'intent', label: 'Quick reply', color: 's2', css: '--series-2' },
  { key: 'fallback', label: 'Not found', color: 's3', css: '--series-3' },
];

let days = 30;
let data = null;
const charts = {};
const $ = (id) => document.getElementById(id);

function kpi(icon, label, value, sub = '') {
  return `<div class="card kpi"><div class="kpi-label"><md-icon>${icon}</md-icon>${label}</div>
    <div class="kpi-value">${value}</div>${sub ? `<div class="muted kpi-sub">${sub}</div>` : ''}</div>`;
}

function renderKpis(k, latency) {
  $('kpis').innerHTML = [
    kpi('chat', 'Questions asked', k.questions.toLocaleString(), `${k.conversations} chats · ${k.users} user${k.users === 1 ? '' : 's'}`),
    kpi('description', 'Answered from documents', pct(k.rag_rate), 'with cited sources'),
    kpi('search_off', 'Not found', pct(k.fallback_rate), 'possible content gaps'),
    kpi('timer', 'Typical document answer', secs(latency.rag.median_ms), latency.rag.p90_ms ? `90% within ${secs(latency.rag.p90_ms)}` : ''),
    kpi('thumb_up', 'Satisfaction', pct(k.satisfaction), `${k.thumbs_up} 👍 · ${k.thumbs_down} 👎`),
  ].join('');
}

function renderMix(routes) {
  const total = ROUTES.reduce((a, r) => a + routes[r.key], 0);
  const bar = $('segbar');
  if (!total) {
    bar.innerHTML = '<div class="muted chart-empty">No answers in this period.</div>';
    $('mix-legend').innerHTML = '';
    return;
  }
  bar.setAttribute('aria-label', ROUTES.map((r) => `${r.label} ${routes[r.key]}`).join(', '));
  bar.innerHTML = ROUTES.filter((r) => routes[r.key]).map((r) => {
    const share = routes[r.key] / total;
    // label inside only when it fits; otherwise it lives in the legend below
    const inside = share >= 0.12 ? `<span>${Math.round(share * 100)}%</span>` : '';
    return `<div class="seg" style="flex:${routes[r.key]}; background: var(${r.css})" title="${r.label}: ${routes[r.key]} (${Math.round(share * 100)}%)">${inside}</div>`;
  }).join('');
  $('mix-legend').innerHTML = ROUTES.map((r) => `
    <span class="legend-item"><span class="swatch" style="background: var(${r.css})"></span>${r.label}
      <strong>${routes[r.key]}</strong> <span class="muted">(${total ? Math.round((routes[r.key] / total) * 100) : 0}%)</span></span>`).join('');
}

function legend(el) {
  el.innerHTML = ROUTES.map((r) => `<span class="legend-item"><span class="swatch" style="background: var(${r.css})"></span>${r.label}</span>`).join('');
}

function ranked(id, cardId, items, unit, labelHeader) {
  charts[id]?.destroy();
  const canvas = $(id);
  const box = canvas.parentElement;
  box.style.height = `${rankedHeight(items.length || 1)}px`;
  if (!items.length) {
    canvas.hidden = true;
    box.querySelector('.chart-empty')?.remove();
    box.insertAdjacentHTML('beforeend', '<div class="muted chart-empty">No data in this period.</div>');
  } else {
    canvas.hidden = false;
    box.querySelector('.chart-empty')?.remove();
    charts[id] = rankedBars(canvas, items, { unit });
  }
  tableToggle($(cardId), [{ key: 'label', label: labelHeader }, { key: 'n', label: unit[0].toUpperCase() + unit.slice(1) }], items);
}

function renderCharts() {
  if (!data) return;
  charts.daily?.destroy();
  legend($('daily-legend'));
  charts.daily = stackedDaily($('chart-daily'), data.per_day, ROUTES);
  tableToggle($('card-daily'), [{ key: 'day', label: 'Day' }, ...ROUTES.map((r) => ({ key: r.key, label: r.label }))], data.per_day);
  ranked('chart-docs', 'card-docs', data.top_documents, 'answers', 'Document');
  ranked('chart-intents', 'card-intents', data.top_intents, 'replies', 'Intent');
  ranked('chart-collections', 'card-collections', data.by_collection, 'questions', 'Collection');
}

function fmtWhen(iso) {
  return new Date(`${iso.replace(' ', 'T')}Z`).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function renderTables() {
  $('latency-table').innerHTML = `<thead><tr><th>Route</th><th>Answers</th><th>Median</th><th>90th percentile</th></tr></thead><tbody>${
    ROUTES.map((r) => {
      const l = data.latency[r.key];
      return `<tr><td><span class="swatch" style="background: var(${r.css})"></span> ${r.label}</td><td>${l.n}</td><td>${secs(l.median_ms)}</td><td>${secs(l.p90_ms)}</td></tr>`;
    }).join('')}</tbody>`;

  $('gaps-table').innerHTML = data.unanswered.length
    ? `<thead><tr><th>Question</th><th>Times asked</th><th>Last asked</th></tr></thead><tbody>${
      data.unanswered.map((u) => `<tr><td>${esc(u.question)}</td><td>${u.times}</td><td class="muted">${fmtWhen(u.last_asked)}</td></tr>`).join('')}</tbody>`
    : '<tbody><tr><td class="muted">Every question in this period found an answer in the documents.</td></tr></tbody>';

  $('disliked-table').innerHTML = data.disliked.length
    ? `<thead><tr><th>Question</th><th>Answer</th><th>Comment</th><th>When</th></tr></thead><tbody>${
      data.disliked.map((d) => `<tr><td><a href="/c/${d.conversation_id}">${esc(d.question)}</a></td>
        <td class="clip">${esc(d.answer.replace(/\s*\[\d+\]/g, '').slice(0, 160))}${d.answer.length > 160 ? '…' : ''}</td>
        <td>${esc(d.comment || '—')}</td><td class="muted">${fmtWhen(d.created_at)}</td></tr>`).join('')}</tbody>`
    : '<tbody><tr><td class="muted">No answers have been marked 👎 in this period.</td></tr></tbody>';
}

async function load() {
  const dash = $('dash');
  dash.classList.add('loading');           // keep the previous render, dimmed (no skeleton flash)
  try {
    data = await api(`/api/analytics?days=${days}`);
    renderKpis(data.kpis, data.latency);
    renderMix(data.routes);
    renderCharts();
    renderTables();
    $('updated').textContent = `Updated ${new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`;
  } catch (err) {
    toast(`Couldn't load analytics: ${err.message}`, 5000);
  } finally {
    dash.classList.remove('loading');
  }
}

const chips = document.querySelectorAll('#range-chips md-filter-chip');
chips.forEach((chip) => chip.addEventListener('click', () => {
  chips.forEach((c) => { c.selected = c === chip; });
  days = Number(chip.dataset.days);
  load();
}));

onThemeChange(() => setTimeout(renderCharts, 30));  // let the new CSS tokens apply first
load();
