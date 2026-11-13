// Shared chart helpers (Chart.js 4, loaded as window.Chart).
// Rules followed: thin marks with 4px rounded ends, hairline recessive grid, one y-axis,
// colour by entity (fixed slots), tooltips on every mark, and a table-view twin for every chart.

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function palette() {
  return {
    s1: css('--series-1'), s2: css('--series-2'), s3: css('--series-3'),
    surface: css('--chart-surface'), grid: css('--chart-grid'), axis: css('--chart-axis'),
    text: css('--chart-text'), ink: css('--md-sys-color-on-surface'),
    tooltipBg: css('--md-sys-color-inverse-surface'), tooltipInk: css('--md-sys-color-inverse-on-surface'),
  };
}

function baseOptions(p) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 250 },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: p.tooltipBg, titleColor: p.tooltipInk, bodyColor: p.tooltipInk,
        padding: 10, cornerRadius: 8, boxPadding: 4, usePointStyle: true,
        titleFont: { family: 'Inter, system-ui, sans-serif', weight: '600' },
        bodyFont: { family: 'Inter, system-ui, sans-serif' },
      },
    },
    font: { family: 'Inter, system-ui, sans-serif' },
  };
}

function axis(p, extra = {}) {
  return {
    grid: { color: p.grid, drawTicks: false, lineWidth: 1 },
    border: { color: p.axis, width: 1 },
    ticks: { color: p.text, font: { size: 12, family: 'Inter, system-ui, sans-serif' }, padding: 8 },
    ...extra,
  };
}

/** Horizontal ranked bars, one series (slot 1). */
export function rankedBars(canvas, items, { unit = '' } = {}) {
  const p = palette();
  return new window.Chart(canvas, {
    type: 'bar',
    data: {
      labels: items.map((i) => i.label),
      datasets: [{ data: items.map((i) => i.n), backgroundColor: p.s1, borderRadius: 4, borderSkipped: 'start',
        barThickness: 14, maxBarThickness: 14 }],
    },
    options: {
      ...baseOptions(p),
      indexAxis: 'y',
      scales: {
        x: axis(p, { beginAtZero: true, ticks: { ...axis(p).ticks, precision: 0 } }),
        y: axis(p, { grid: { display: false }, ticks: { ...axis(p).ticks, autoSkip: false,
          // Chart.js caps the label column, so shorten long names to fit the chart's width
          // (the full name is in the tooltip and the table view).
          callback(v) {
            const l = this.getLabelForValue(v);
            const max = Math.max(10, Math.min(30, Math.floor(this.chart.width / 18)));
            return l.length > max ? `${l.slice(0, max - 1)}…` : l;
          } } }),
      },
      plugins: { ...baseOptions(p).plugins,
        tooltip: { ...baseOptions(p).plugins.tooltip, displayColors: false,
          callbacks: { title: (items) => items[0].label, label: (ctx) => `${ctx.parsed.x} ${unit}`.trim() } } },
    },
  });
}

/** Height for a ranked-bar canvas so every row fits (plot + axis band). */
export const rankedHeight = (n) => Math.max(120, n * 30 + 40);

/** Stacked daily bars; series = [{key, label, color}]. The topmost non-zero segment gets the rounded end. */
export function stackedDaily(canvas, rows, series) {
  const p = palette();
  const topIndex = rows.map((r) => {
    let top = -1;
    series.forEach((s, i) => { if (r[s.key] > 0) top = i; });
    return top;
  });
  const fmt = (d) => new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  return new window.Chart(canvas, {
    type: 'bar',
    data: {
      labels: rows.map((r) => fmt(r.day)),
      datasets: series.map((s, si) => ({
        label: s.label,
        data: rows.map((r) => r[s.key]),
        backgroundColor: p[s.color],
        borderColor: p.surface,
        borderWidth: { top: 2 },          // 2px surface gap between stacked segments
        borderSkipped: 'start',
        borderRadius: (ctx) => (topIndex[ctx.dataIndex] === si ? { topLeft: 4, topRight: 4 } : 0),
        maxBarThickness: 28,
      })),
    },
    options: {
      ...baseOptions(p),
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: axis(p, { stacked: true, grid: { display: false }, ticks: { ...axis(p).ticks, maxRotation: 0, autoSkipPadding: 12 } }),
        y: axis(p, { stacked: true, beginAtZero: true, ticks: { ...axis(p).ticks, precision: 0 } }),
      },
      plugins: { ...baseOptions(p).plugins,
        tooltip: { ...baseOptions(p).plugins.tooltip,
          callbacks: { footer: (items) => `Total: ${items.reduce((a, i) => a + i.parsed.y, 0)}` } } },
    },
  });
}

/** Line chart on one 0–1 axis with an optional vertical marker (e.g. the chosen threshold). */
export function rateLines(canvas, xValues, series, { marker = null, markerLabel = '' } = {}) {
  const p = palette();
  const markerPlugin = {
    id: 'marker',
    afterDatasetsDraw(chart) {
      if (marker === null) return;
      const { ctx, chartArea: a, scales: { x } } = chart;
      const px = x.getPixelForValue(marker);
      ctx.save();
      ctx.strokeStyle = p.ink; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
      ctx.fillStyle = p.ink; ctx.font = '600 12px Inter, system-ui, sans-serif';
      ctx.textAlign = px > (a.left + a.right) / 2 ? 'right' : 'left';
      ctx.fillText(markerLabel, px + (ctx.textAlign === 'left' ? 6 : -6), a.top + 12);
      ctx.restore();
    },
  };
  return new window.Chart(canvas, {
    type: 'line',
    data: {
      datasets: series.map((s) => ({
        label: s.label, data: xValues.map((x, i) => ({ x, y: s.values[i] })),
        borderColor: p[s.color], backgroundColor: p[s.color], borderWidth: 2, tension: 0.25,
        pointRadius: 0, pointHoverRadius: 5, pointHoverBorderColor: p.surface, pointHoverBorderWidth: 2,
      })),
    },
    options: {
      ...baseOptions(p),
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: axis(p, { type: 'linear', min: Math.min(...xValues), max: Math.max(...xValues), grid: { display: false },
          title: { display: true, text: 'Confidence threshold', color: p.text } }),
        y: axis(p, { min: 0, max: 1, ticks: { ...axis(p).ticks, callback: (v) => `${Math.round(v * 100)}%` } }),
      },
      plugins: { ...baseOptions(p).plugins,
        tooltip: { ...baseOptions(p).plugins.tooltip,
          callbacks: { title: (items) => `Threshold ${items[0].parsed.x.toFixed(2)}`,
            label: (ctx) => ` ${ctx.dataset.label}: ${(ctx.parsed.y * 100).toFixed(1)}%` } } },
    },
    plugins: [markerPlugin],
  });
}

/** Strip plot: one row per group, each point a question; vertical threshold line. */
export function stripPlot(canvas, groups, { threshold, thresholdLabel }) {
  const p = palette();
  const rows = groups.map((g) => g.label);
  const marker = {
    id: 'threshold',
    afterDatasetsDraw(chart) {
      const { ctx, chartArea: a, scales: { x } } = chart;
      const px = x.getPixelForValue(threshold);
      ctx.save();
      ctx.strokeStyle = p.ink; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
      ctx.fillStyle = p.ink; ctx.font = '600 12px Inter, system-ui, sans-serif'; ctx.textAlign = 'left';
      ctx.fillText(thresholdLabel, px + 6, a.top + 12);
      ctx.restore();
    },
  };
  // deterministic jitter so overlapping dots stay visible
  const jitter = (i) => ((i * 37) % 11) / 11 * 0.5 - 0.25;
  return new window.Chart(canvas, {
    type: 'scatter',
    data: {
      datasets: groups.map((g, gi) => ({
        label: g.label,
        data: g.points.map((pt, i) => ({ x: pt.score, y: gi + jitter(i), q: pt.q })),
        backgroundColor: p[g.color], borderColor: p.surface, borderWidth: 2, pointRadius: 5, pointHoverRadius: 7,
        pointHitRadius: 8,
      })),
    },
    options: {
      ...baseOptions(p),
      scales: {
        x: axis(p, { title: { display: true, text: 'Best similarity to any document chunk', color: p.text } }),
        y: axis(p, { min: -0.6, max: rows.length - 0.4, grid: { display: false },
          ticks: { ...axis(p).ticks, stepSize: 1, callback: (v) => rows[v] ?? '' } }),
      },
      plugins: { ...baseOptions(p).plugins,
        tooltip: { ...baseOptions(p).plugins.tooltip,
          callbacks: { label: (ctx) => ` ${ctx.raw.q} (${ctx.parsed.x.toFixed(3)})` } } },
    },
    plugins: [marker],
  });
}

/** Wire a card's "Table" toggle: shows a generated <table> instead of the chart (and back). */
export function tableToggle(card, columns, rows) {
  const btn = card.querySelector('[data-table-toggle]');
  const chartBox = card.querySelector('.chart-box');
  let tableBox = card.querySelector('.table-box');
  if (!tableBox) {
    tableBox = document.createElement('div');
    tableBox.className = 'table-box table-wrap';
    tableBox.hidden = true;
    chartBox.after(tableBox);
  }
  tableBox.innerHTML = rows.length ? `<table class="data-table compact"><thead><tr>${columns.map((c) => `<th>${esc(c.label)}</th>`).join('')}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${columns.map((c) => `<td>${esc(c.format ? c.format(r[c.key], r) : r[c.key])}</td>`).join('')}</tr>`).join('')}</tbody></table>`
    : '<div class="muted chart-empty">No data yet.</div>';
  if (btn && !btn.dataset.wired) {
    btn.dataset.wired = '1';
    btn.addEventListener('change', () => { tableBox.hidden = !btn.selected; chartBox.hidden = btn.selected; });
  }
}

/** Call `redraw` whenever light/dark changes (toggle or OS setting). */
export function onThemeChange(redraw) {
  new MutationObserver(redraw).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', redraw);
}

export const pct = (v, digits = 0) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(digits)}%`);
export const secs = (ms) => (ms === null || ms === undefined ? '—' : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);
