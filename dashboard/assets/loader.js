/* ---------------------------------------------------------------------------
   loader.js — Fetch the snapshot JSON and expose formatting helpers.
--------------------------------------------------------------------------- */

/**
 * Load the IPC snapshot JSON from the given path.
 * Validates the basic shape of the response.
 */
async function loadIpcSnapshot(path) {
  let resp;
  try {
    resp = await fetch(path, { cache: "no-store" });
  } catch (networkErr) {
    // Common cause: opening index.html via file:// (no fetch support for local files).
    throw new Error(
      "No se pudo acceder al archivo de datos. Serví el dashboard con un servidor (ej: python -m http.server) en vez de abrirlo directo desde el explorador de archivos."
    );
  }
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status} al cargar ${path}`);
  }
  const data = await resp.json();

  if (!data || !Array.isArray(data.series)) {
    throw new Error("El snapshot no tiene la estructura esperada");
  }
  if (data.series.length === 0) {
    throw new Error(
      "El snapshot no contiene series. Revisá los IDs en catalog.yaml."
    );
  }
  return data;
}

/* ---- Formatting helpers -------------------------------------------------- */

const MONTHS_ES = [
  "ene",
  "feb",
  "mar",
  "abr",
  "may",
  "jun",
  "jul",
  "ago",
  "sep",
  "oct",
  "nov",
  "dic",
];

/**
 * Format an ISO date (YYYY-MM-DD) as "mar 2025".
 */
function formatMonthYear(isoDate) {
  if (!isoDate) return "—";
  const [yyyy, mm] = isoDate.split("-");
  const monthIdx = parseInt(mm, 10) - 1;
  return `${MONTHS_ES[monthIdx]} ${yyyy}`;
}

/**
 * Format a percentage with sign and one decimal place.
 */
function formatPct(value, { withSign = true, decimals = 1 } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const formatted = value.toLocaleString("es-AR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  if (!withSign) return `${formatted}%`;
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatted}%`;
}

/**
 * Format an index value (large number, thousand separators).
 */
function formatIndex(value, { decimals = 1 } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("es-AR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format a timestamp like "2026-04-20T12:34:56Z" into something human.
 */
function formatSnapshotTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("es-AR", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

/**
 * Set the status message area. Type can be "", "error".
 */
function setStatus(message, type = "") {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = message || "";
  el.className = type === "error" ? "status status--error" : "status";
}

/* ---- Headline rendering -------------------------------------------------- */

function renderHeadline(data) {
  // Headline uses "nivel_general" by convention; fall back to first series.
  const headlineSeries =
    data.series.find((s) => s.key === "nivel_general") || data.series[0];
  const s = headlineSeries.summary;

  document.getElementById("source-label").textContent =
    data.source || "INDEC";

  document.getElementById("headline-mom").textContent = formatPct(s.last_mom);
  document.getElementById("headline-mom-period").textContent = formatMonthYear(
    s.last_date
  );

  document.getElementById("headline-yoy").textContent = formatPct(s.last_yoy);

  document.getElementById("headline-level").textContent = formatIndex(
    s.last_value
  );
  document.getElementById("headline-level-period").textContent =
    formatMonthYear(s.last_date);

  // Note text — adjust based on what's in the data.
  const note = document.getElementById("headline-note");
  if (data.name && data.name.includes("DEV DATA")) {
    note.textContent =
      "Datos de desarrollo provenientes de un fixture. No usar para análisis real.";
  } else {
    note.textContent = `Dato más reciente: ${formatMonthYear(
      s.last_date
    )}. ${data.description || ""}`.trim();
  }
}

/* ---- Series picker (pills) ---------------------------------------------- */

let _selectedSeriesKey = null;

function renderVariationsPicker(data) {
  const container = document.getElementById("variations-picker");
  container.innerHTML = "";

  data.series.forEach((series, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "series-pill";
    btn.textContent = series.label;
    btn.dataset.key = series.key;
    if (idx === 0) {
      btn.classList.add("series-pill--active");
      _selectedSeriesKey = series.key;
    }
    btn.addEventListener("click", () => {
      _selectedSeriesKey = series.key;
      container
        .querySelectorAll(".series-pill")
        .forEach((p) => p.classList.remove("series-pill--active"));
      btn.classList.add("series-pill--active");
      // charts.js reads this global key and updates
      updateVariationsChart(data, series.key);
    });
    container.appendChild(btn);
  });
}

function getSelectedSeriesKey() {
  return _selectedSeriesKey;
}

/* ---- Breakdown table ----------------------------------------------------- */

const CATEGORY_LABELS = {
  agregado: "General",
  clasificacion: "Clasificación",
  division: "División",
};

function renderBreakdownTable(data) {
  const tbody = document.getElementById("series-tbody");
  tbody.innerHTML = "";

  data.series.forEach((series) => {
    const s = series.summary;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="label-main">${escapeHtml(series.label)}</span></td>
      <td><span class="tag">${
        CATEGORY_LABELS[series.category] || series.category || "—"
      }</span></td>
      <td class="num">${formatIndex(s.last_value)}</td>
      <td class="num ${s.last_mom > 0 ? "pos" : "neg"}">${formatPct(
      s.last_mom
    )}</td>
      <td class="num ${s.last_yoy > 0 ? "pos" : "neg"}">${formatPct(
      s.last_yoy
    )}</td>
      <td>${formatMonthYear(s.last_date)}</td>
    `;
    tbody.appendChild(tr);
  });
}

/* ---- Snapshot metadata in footer ----------------------------------------- */

function renderSnapshotMeta(data) {
  const el = document.getElementById("snapshot-time");
  if (el) el.textContent = formatSnapshotTime(data.generated_at);
}

/* ---- Security helper ----------------------------------------------------- */

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
