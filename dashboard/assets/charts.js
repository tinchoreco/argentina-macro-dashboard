/* ---------------------------------------------------------------------------
   charts.js — Chart.js rendering for the dashboard.
   Uses CSS variables read at runtime so theming stays in one place.
--------------------------------------------------------------------------- */

/* ---- Theme helpers ------------------------------------------------------- */

function cssVar(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

function chartTheme() {
  return {
    bone: cssVar("--bone"),
    boneDim: cssVar("--bone-dim"),
    boneDimmer: cssVar("--bone-dimmer"),
    accent: cssVar("--accent"),
    accentSoft: cssVar("--accent-soft"),
    gold: cssVar("--gold"),
    divider: cssVar("--divider"),
    gridLine: cssVar("--grid-line"),
    fontBody: cssVar("--font-body"),
    fontMono: cssVar("--font-mono"),
    series: [
      cssVar("--series-1"),
      cssVar("--series-2"),
      cssVar("--series-3"),
      cssVar("--series-4"),
      cssVar("--series-5"),
      cssVar("--series-6"),
      cssVar("--series-7"),
      cssVar("--series-8"),
    ],
  };
}

/**
 * Apply global Chart.js defaults that match our aesthetic.
 * Called once before the first chart is created.
 */
function applyChartDefaults() {
  const t = chartTheme();
  Chart.defaults.color = t.boneDim;
  Chart.defaults.borderColor = t.divider;
  Chart.defaults.font.family = t.fontBody;
  Chart.defaults.font.size = 12;

  Chart.defaults.plugins.tooltip = {
    ...Chart.defaults.plugins.tooltip,
    backgroundColor: "#0d0b09",
    titleColor: t.bone,
    bodyColor: t.bone,
    borderColor: t.accent,
    borderWidth: 1,
    padding: 12,
    cornerRadius: 2,
    displayColors: true,
    boxPadding: 4,
    titleFont: { family: t.fontMono, size: 11, weight: "500" },
    bodyFont: { family: t.fontMono, size: 12 },
  };
}

/* ---- Variations chart (bars + YoY line) ---------------------------------- */

let _variationsChart = null;

function renderVariationsChart(data) {
  applyChartDefaults();
  const key = getSelectedSeriesKey() || data.series[0].key;
  _variationsChart = buildVariationsChart(data, key);
}

function updateVariationsChart(data, key) {
  if (_variationsChart) {
    _variationsChart.destroy();
  }
  _variationsChart = buildVariationsChart(data, key);
}

function buildVariationsChart(data, seriesKey) {
  const series = data.series.find((s) => s.key === seriesKey);
  if (!series) return null;

  const t = chartTheme();
  // Take last 36 observations for readability on mobile.
  const N = 36;
  const momTail = series.mom_pct.slice(-N);
  const yoyTail = series.yoy_pct.slice(-N);

  const labels = momTail.map((row) => row[0]);
  const momValues = momTail.map((row) => row[1]);
  const yoyValues = yoyTail.map((row) => row[1]);

  const ctx = document.getElementById("chart-variations").getContext("2d");

  return new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          type: "bar",
          label: "Mensual",
          data: momValues,
          backgroundColor: t.accent,
          borderColor: t.accent,
          borderWidth: 0,
          yAxisID: "yMom",
          order: 2,
          maxBarThickness: 22,
        },
        {
          type: "line",
          label: "Interanual",
          data: yoyValues,
          borderColor: t.gold,
          backgroundColor: "transparent",
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: t.gold,
          pointHoverBorderColor: t.bone,
          tension: 0.25,
          yAxisID: "yYoy",
          order: 1,
          spanGaps: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          position: "top",
          align: "end",
          labels: {
            usePointStyle: true,
            pointStyle: "rect",
            padding: 16,
            font: {
              family: t.fontMono,
              size: 11,
            },
            color: t.bone,
          },
        },
        tooltip: {
          callbacks: {
            title: (items) => formatMonthYear(items[0].label),
            label: (ctx) => {
              const v = ctx.parsed.y;
              if (v === null || v === undefined) return `${ctx.dataset.label}: —`;
              const sign = v > 0 ? "+" : "";
              return `${ctx.dataset.label}: ${sign}${v.toFixed(1)}%`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false, drawBorder: false },
          ticks: {
            color: t.boneDimmer,
            font: { family: t.fontMono, size: 10 },
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 8,
            callback: function (val, idx) {
              const iso = this.getLabelForValue(val);
              return formatMonthYear(iso);
            },
          },
        },
        yMom: {
          position: "left",
          grid: { color: t.gridLine, drawBorder: false },
          ticks: {
            color: t.boneDim,
            font: { family: t.fontMono, size: 10 },
            callback: (v) => `${v}%`,
          },
          title: {
            display: true,
            text: "Variación mensual",
            color: t.boneDimmer,
            font: { family: t.fontMono, size: 10, weight: "400" },
          },
        },
        yYoy: {
          position: "right",
          grid: { display: false, drawBorder: false },
          ticks: {
            color: t.gold,
            font: { family: t.fontMono, size: 10 },
            callback: (v) => `${v}%`,
          },
          title: {
            display: true,
            text: "Interanual",
            color: t.gold,
            font: { family: t.fontMono, size: 10, weight: "400" },
          },
        },
      },
    },
  });
}

/* ---- Levels chart (multi-line, index values) ---------------------------- */

let _levelsChart = null;

function renderLevelsChart(data) {
  applyChartDefaults();
  const t = chartTheme();

  const ctx = document.getElementById("chart-levels").getContext("2d");

  // Use all dates from the first series as the x-axis (assume alignment).
  const allDates = data.series[0].observations.map((o) => o[0]);

  const datasets = data.series.map((series, idx) => {
    const valueByDate = new Map(series.observations);
    return {
      label: series.label,
      data: allDates.map((d) => valueByDate.get(d) ?? null),
      borderColor: t.series[idx % t.series.length],
      backgroundColor: "transparent",
      borderWidth: series.key === "nivel_general" ? 2.5 : 1.5,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.2,
      spanGaps: true,
    };
  });

  if (_levelsChart) _levelsChart.destroy();
  _levelsChart = new Chart(ctx, {
    type: "line",
    data: { labels: allDates, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "bottom",
          align: "start",
          labels: {
            usePointStyle: true,
            pointStyle: "line",
            padding: 14,
            font: { family: t.fontMono, size: 10 },
            color: t.bone,
            boxWidth: 20,
          },
        },
        tooltip: {
          callbacks: {
            title: (items) => formatMonthYear(items[0].label),
            label: (ctx) => {
              const v = ctx.parsed.y;
              if (v === null || v === undefined) return `${ctx.dataset.label}: —`;
              return `${ctx.dataset.label}: ${v.toLocaleString("es-AR", {
                maximumFractionDigits: 1,
              })}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false, drawBorder: false },
          ticks: {
            color: t.boneDimmer,
            font: { family: t.fontMono, size: 10 },
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 10,
            callback: function (val) {
              const iso = this.getLabelForValue(val);
              return formatMonthYear(iso);
            },
          },
        },
        y: {
          grid: { color: t.gridLine, drawBorder: false },
          ticks: {
            color: t.boneDim,
            font: { family: t.fontMono, size: 10 },
            callback: (v) =>
              v.toLocaleString("es-AR", { maximumFractionDigits: 0 }),
          },
          title: {
            display: true,
            text: "Índice (base Dic-2016 = 100)",
            color: t.boneDimmer,
            font: { family: t.fontMono, size: 10, weight: "400" },
          },
        },
      },
    },
  });
}
