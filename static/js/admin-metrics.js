// Admin → Model metrics: intent classifier report + retrieval evaluation.
import { api, toast } from './admin-common.js';
import { esc, onThemeChange, rateLines, stripPlot, tableToggle } from './charts.js';

const $ = (id) => document.getElementById(id);
const f3 = (v) => (v === null || v === undefined ? '—' : Number(v).toFixed(3));
const when = (iso) => (iso ? new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '');

let metrics = null;
let cmSet = 'cv';
const charts = {};

// --------------------------------------------------------------------------- intent classifier
function bestRun() {
  return metrics.intent.runs.find((r) => r.algorithm === metrics.intent.best);
}

function renderCompare() {
  const rows = metrics.intent.runs;
  const best = (key, sub) => Math.max(...rows.map((r) => (r[sub] ? r[sub][key] : -1)));
  const cell = (r, sub, key) => {
    const v = r[sub] ? r[sub][key] : null;
    return `<td class="${v !== null && v === best(key, sub) ? 'metric-good' : ''}">${f3(v)}</td>`;
  };
  $('compare-table').innerHTML = `
    <thead><tr><th>Model</th><th>Tuned setting</th><th>CV accuracy</th><th>CV precision</th><th>CV recall</th><th>CV F1</th><th>Test accuracy</th><th>Test F1</th></tr></thead>
    <tbody>${rows.map((r) => `<tr>
      <td>${esc(r.name)}${r.algorithm === metrics.intent.best ? ' <span class="badge ok">Active</span>' : ''}</td>
      <td class="mono">${esc(Object.entries(r.params).map(([k, v]) => `${k}=${v}`).join(', '))}</td>
      ${cell(r, 'cv', 'accuracy')}${cell(r, 'cv', 'precision')}${cell(r, 'cv', 'recall')}${cell(r, 'cv', 'f1')}
      ${cell(r, 'test', 'accuracy')}${cell(r, 'test', 'f1')}</tr>`).join('')}</tbody>`;
  const r = bestRun();
  $('intent-trained').textContent = `${r.n_samples} patterns · ${r.n_intents} intents · trained ${when(metrics.intent.trained_at)}`;
}

const SWEEP = [
  { key: 'routing_accuracy', label: 'Routed correctly', color: 's1', css: '--series-1' },
  { key: 'wrong_canned_reply', label: 'Wrong quick reply', color: 's2', css: '--series-2' },
  { key: 'small_talk_to_rag', label: 'Small talk sent to documents', color: 's3', css: '--series-3' },
];

function renderSweep() {
  const run = bestRun();
  const sweep = run.details.threshold_sweep || [];
  charts.sweep?.destroy();
  $('sweep-legend').innerHTML = SWEEP.map((s) => `<span class="legend-item"><span class="swatch" style="background: var(${s.css})"></span>${s.label}</span>`).join('');
  if (!sweep.length) return;
  const current = metrics.thresholds.intent;
  charts.sweep = rateLines($('chart-sweep'), sweep.map((r) => r.threshold),
    SWEEP.map((s) => ({ ...s, values: sweep.map((r) => r[s.key]) })),
    { marker: current, markerLabel: `In use: ${current}` });
  const at = sweep.reduce((a, b) => (Math.abs(b.threshold - current) < Math.abs(a.threshold - current) ? b : a));
  $('sweep-note').textContent = `At ${current}: ${(at.routing_accuracy * 100).toFixed(0)}% of held-out messages are routed correctly, `
    + `${(at.wrong_canned_reply * 100).toFixed(0)}% get the wrong quick reply and ${(at.small_talk_to_rag * 100).toFixed(0)}% of small talk goes to the documents. `
    + `Training picks the threshold with the lowest cost, counting a wrong quick reply twice.`;
  tableToggle($('card-sweep'), [{ key: 'threshold', label: 'Threshold' },
    ...SWEEP.map((s) => ({ key: s.key, label: s.label, format: (v) => `${(v * 100).toFixed(1)}%` }))], sweep);
}

function renderF1() {
  const per = bestRun().details.cv.per_class;
  const rows = Object.entries(per).map(([tag, m]) => ({ tag, ...m })).sort((a, b) => a['f1-score'] - b['f1-score']);
  $('f1-table').innerHTML = `<thead><tr><th>Intent</th><th>F1</th><th>Precision</th><th>Recall</th><th>Examples</th></tr></thead><tbody>${
    rows.map((r) => `<tr><td class="mono">${esc(r.tag)}</td>
      <td><span class="inline-bar" style="width:${Math.round(r['f1-score'] * 80)}px"></span>${f3(r['f1-score'])}</td>
      <td>${f3(r.precision)}</td><td>${f3(r.recall)}</td><td>${r.support}</td></tr>`).join('')}</tbody>`;
}

function renderHeatmap() {
  const details = bestRun().details[cmSet];
  if (!details) {
    $('heatmap').innerHTML = '<tbody><tr><td class="muted">No held-out results.</td></tr></tbody>';
    return;
  }
  const { labels, confusion_matrix: cm } = details;
  const max = Math.max(...cm.flat(), 1);
  $('cm-max').textContent = max;
  $('heatmap').innerHTML = `<thead><tr><th></th>${labels.map((l) => `<th scope="col"><div>${esc(l)}</div></th>`).join('')}</tr></thead>
    <tbody>${cm.map((row, i) => `<tr><th scope="row">${esc(labels[i])}</th>${row.map((v, j) => {
      const share = v / max;
      const cls = [v === 0 ? 'zero' : '', share > 0.55 ? 'hot' : '', i === j ? 'diag' : ''].join(' ').trim();
      const title = `${labels[i]} → predicted ${labels[j]}: ${v}`;
      return `<td class="${cls}" style="--v:${Math.round(Math.sqrt(share) * 100)}%" title="${esc(title)}">${v}</td>`;
    }).join('')}</tr>`).join('')}</tbody>`;
}

function renderErrors() {
  const errors = bestRun().details.test_errors || [];
  $('errors-table').innerHTML = errors.length
    ? `<thead><tr><th>Test phrasing</th><th>Expected</th><th>Predicted</th><th>Confidence</th><th>Effect at ${metrics.thresholds.intent}</th></tr></thead><tbody>${
      errors.map((e) => {
        const wrongReply = e.predicted !== 'doc_query' && e.confidence >= metrics.thresholds.intent;
        return `<tr><td>${esc(e.text)}</td><td class="mono">${esc(e.expected)}</td><td class="mono">${esc(e.predicted)}</td>
          <td>${f3(e.confidence)}</td><td>${wrongReply ? '<span class="badge warn">Wrong quick reply</span>' : '<span class="badge">Sent to documents</span>'}</td></tr>`;
      }).join('')}</tbody>`
    : '<tbody><tr><td class="muted">No mistakes on the held-out set.</td></tr></tbody>';
}

// --------------------------------------------------------------------------- retrieval
const GATE = [
  { key: 'answerable', label: 'Answerable', color: 's1', css: '--series-1' },
  { key: 'out_of_scope', label: 'Off-topic', color: 's2', css: '--series-2' },
];

function renderRag() {
  const rag = metrics.rag;
  $('rag-missing').hidden = !!rag;
  $('rag-section').hidden = !rag;
  if (!rag) return;
  $('rag-evaluated').textContent = `${rag.n_questions} answerable + ${rag.n_out_of_scope} off-topic questions · ${rag.embed_model}${rag.evaluated_at ? ` · ${when(rag.evaluated_at)}` : ''}`;

  const k = rag.k;
  const modes = [['vector', 'Vector (meaning)'], ['keyword', 'Keyword (BM25)'], ['hybrid', 'Hybrid (used)']];
  const best = (key) => Math.max(...modes.map(([m]) => rag.metrics[m][key]));
  $('rag-table').innerHTML = `<thead><tr><th>Mode</th><th>Hit@1</th><th>Hit@${k}</th><th>MRR@${k}</th></tr></thead><tbody>${
    modes.map(([m, label]) => `<tr><td>${label}</td>${['hit@1', `hit@${k}`, `mrr@${k}`].map((key) =>
      `<td class="${rag.metrics[m][key] === best(key) ? 'metric-good' : ''}">${f3(rag.metrics[m][key])}</td>`).join('')}</tr>`).join('')}</tbody>`;

  charts.gate?.destroy();
  $('gate-legend').innerHTML = GATE.map((g) => `<span class="legend-item"><span class="swatch" style="background: var(${g.css})"></span>${g.label}</span>`).join('');
  const threshold = metrics.thresholds.relevance;
  const g = rag.gate;
  $('chart-gate').parentElement.querySelector('.chart-empty')?.remove();
  if (rag.scores) {
    charts.gate = stripPlot($('chart-gate'), GATE.map((x) => ({ ...x, points: rag.scores[x.key] })),
      { threshold, thresholdLabel: `In use: ${threshold}` });
    const rows = [...rag.scores.answerable.map((s) => ({ ...s, group: 'Answerable' })),
      ...rag.scores.out_of_scope.map((s) => ({ ...s, group: 'Off-topic' }))];
    tableToggle($('card-gate'), [{ key: 'group', label: 'Set' }, { key: 'q', label: 'Question' },
      { key: 'score', label: 'Best similarity', format: (v) => v.toFixed(3) },
      { key: 'score', label: 'Result', format: (v, r) => ((v >= threshold) === (r.group === 'Answerable') ? 'Correct' : 'Wrong side') }], rows);
  } else {
    $('chart-gate').parentElement.insertAdjacentHTML('beforeend', '<div class="muted chart-empty">Re-run the evaluation to plot every question.</div>');
  }
  $('gate-note').textContent = `Answerable: ${g.answerable.min}–${g.answerable.max} (median ${g.answerable.median}). `
    + `Off-topic: ${g.out_of_scope.min}–${g.out_of_scope.max} (median ${g.out_of_scope.median}). `
    + `The evaluation recommends ${g.threshold} (gate accuracy ${(g.gate_accuracy * 100).toFixed(0)}%). Apply it in Settings → Relevance threshold.`;

  $('misses-table').innerHTML = rag.misses.length
    ? `<thead><tr><th>Question</th><th>Expected document</th><th>What came back</th></tr></thead><tbody>${
      rag.misses.map((m) => `<tr><td>${esc(m.q)}</td><td>${esc(m.expected)}</td><td class="muted">${esc(m.got.join('; '))}</td></tr>`).join('')}</tbody>`
    : '<tbody><tr><td class="muted">Every question found its passage.</td></tr></tbody>';
}

// --------------------------------------------------------------------------- load + events
function renderAll() {
  const hasIntent = !!metrics.intent;
  $('intent-missing').hidden = hasIntent;
  $('intent-section').hidden = !hasIntent;
  $('intent-dirty').hidden = !metrics.intents_dirty;
  if (hasIntent) {
    renderCompare(); renderSweep(); renderF1(); renderHeatmap(); renderErrors();
  }
  renderRag();
}

async function load() {
  metrics = await api('/api/metrics');
  renderAll();
}

document.querySelectorAll('#cm-chips md-filter-chip').forEach((chip, _, all) => chip.addEventListener('click', () => {
  all.forEach((c) => { c.selected = c === chip; });
  cmSet = chip.dataset.set;
  renderHeatmap();
}));

$('run-rag').addEventListener('click', async () => {
  $('run-rag').disabled = true;
  $('rag-progress').hidden = false;
  try {
    metrics.rag = await api('/api/metrics/rag/evaluate', { method: 'POST' });
    renderRag();
    toast('Retrieval evaluation finished');
  } catch (err) {
    toast(err.message, 6000);
  } finally {
    $('run-rag').disabled = false;
    $('rag-progress').hidden = true;
  }
});

onThemeChange(() => setTimeout(() => { if (metrics) { if (metrics.intent) renderSweep(); renderRag(); } }, 30));
load().catch((err) => toast(err.message, 5000));
