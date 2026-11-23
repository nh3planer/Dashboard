/* Projekt-Dashboard Frontend */
const API = "/api";
let token = sessionStorage.getItem("pd_token") || "";
let currentUser = null;
let projectsCache = [];
let charts = {};

const fmtEUR = v => v == null ? "–" : new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(v);
const fmtPct = v => v == null ? "–" : v.toLocaleString("de-DE", { maximumFractionDigits: 1 }) + " %";
const fmtNum = v => v == null ? "–" : String(v).replace(".", ",");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const ROLE_LABELS = { geschaeftsfuehrer: "Geschäftsführer", management: "Management", projektleiter: "Projektleiter", kunde: "Kunde/Bauherr" };

async function api(path, opts = {}) {
  const res = await fetch(API + path, { ...opts, headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}), ...(opts.headers || {}) } });
  if (res.status === 401) { logoutLocal(); throw new Error("Nicht angemeldet"); }
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || ("HTTP " + res.status)); }
  return res.json();
}

/* ===================== LOGIN ===================== */
document.getElementById("login-form").addEventListener("submit", async e => {
  e.preventDefault();
  const err = document.getElementById("login-error");
  err.classList.add("hidden");
  try {
    const r = await fetch(API + "/login", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: login_user.value, password: login_pass.value }) });
    if (!r.ok) throw 0;
    const data = await r.json();
    token = data.token; currentUser = data.user;
    sessionStorage.setItem("pd_token", token);
    sessionStorage.setItem("pd_user", JSON.stringify(currentUser));
    bootApp();
  } catch { err.textContent = "Anmeldung fehlgeschlagen – Benutzername oder Passwort prüfen."; err.classList.remove("hidden"); }
});

function logoutLocal() { token = ""; currentUser = null; sessionStorage.clear(); location.reload(); }
document.getElementById("logout-btn").addEventListener("click", async () => { try { await api("/logout", { method: "POST" }); } catch {} logoutLocal(); });

function demoLogin(name) {
  document.getElementById("login-user").value = name;
  document.getElementById("login-pass").value = "demo123";
  document.getElementById("login-form").dispatchEvent(new Event("submit", { cancelable: true }));
}

/* ===================== NAVIGATION ===================== */
document.querySelectorAll(".nav-btn").forEach(btn => btn.addEventListener("click", () => showView(btn.dataset.view)));
function showView(name) {
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.view === name));
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === "view-" + name));
  if (name === "dashboard") loadDashboard();
  if (name === "management") loadManagement();
  if (name === "projects") loadProjects();
  if (name === "reports") loadReports();
  if (name === "users") loadUsers();
}

function bootApp() {
  document.getElementById("login-view").classList.add("hidden");
  document.getElementById("app-view").classList.remove("hidden");
  document.getElementById("user-name").textContent = currentUser.full_name;
  document.getElementById("user-role").textContent = ROLE_LABELS[currentUser.role];
  const isGF = currentUser.role === "geschaeftsfuehrer";
  const isMgmt = ["geschaeftsfuehrer", "management"].includes(currentUser.role);
  document.getElementById("nav-management").classList.toggle("hidden", !isMgmt);
  document.getElementById("nav-users").classList.toggle("hidden", !isGF);
  showView("dashboard");
}

/* ===================== DASHBOARD (Standard-KPIs) ===================== */
function kpiCard(label, value, sub, cls = "") {
  return `<div class="kpi-card ${cls}"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${value}</div><div class="kpi-sub">${sub || ""}</div></div>`;
}

async function loadDashboard() {
  const k = await api("/kpis");
  const cards = document.getElementById("kpi-standard-cards");
  const list = k.standard || [];
  const p0 = list[0];
  if (!p0) { cards.innerHTML = "<p>Kein Projekt für Ihre Rolle sichtbar.</p>"; return; }
  const isKunde = currentUser.role === "kunde";

  let html = "";
  if (isKunde) {
    const p = list[0];
    html = kpiCard("Fertigstellungsgrad", fmtPct(p.fertigstellungsgrad_pct), "", "good")
      + kpiCard("Meilensteine termingerecht", fmtPct(p.meilensteine_termingerecht_pct), `${p.meilensteine_erledigt} / ${p.meilensteine_gesamt} erledigt`)
      + kpiCard("Projektstatus", p.health ? `<span class="pill ${p.health}">${p.health}</span>` : "–", p.project_name);
  } else {
    const avg = (f, d = 1) => { const v = list.map(x => x[f]).filter(x => x != null); return v.length ? (v.reduce((a, b) => a + b, 0) / v.length) : null; };
    const spiAvg = avg("spi"), cpiAvg = avg("cpi");
    html = kpiCard("Ø SPI (Terminleistung)", fmtNum(spiAvg?.toFixed(2)), "EV / PV – &lt; 1 = Verzögerung", (spiAvg ?? 1) >= 1 ? "good" : "bad")
      + kpiCard("Ø CPI (Kosteneffizienz)", fmtNum(cpiAvg?.toFixed(2)), "EV / AC – &lt; 1 = Kostenüberschreitung", (cpiAvg ?? 1) >= 1 ? "good" : "bad")
      + kpiCard("Ø Fertigstellungsgrad", fmtPct(avg("fertigstellungsgrad_pct")), `${list.length} Projekt(e) im Zugriff`)
      + kpiCard("Ø Meilenstein-Erreichung", fmtPct(avg("meilensteine_termingerecht_pct")), "termingerecht erledigt")
      + kpiCard("Ø Ressourcenauslastung", fmtPct(avg("ressourcen_auslastung_pct")), `Überlastete Teams gesamt: ${list.reduce((a, b) => a + (b.ressourcen_ueberlastungen || 0), 0)}`)
      + kpiCard("Change Requests", `${list.reduce((a, b) => a + (b.change_requests_gesamt || 0), 0)} gesamt`, `${list.reduce((a, b) => a + (b.change_requests_genehmigt || 0), 0)} genehmigt`)
      + kpiCard("Ø Qualitäts-Fehlerquote", fmtPct(avg("qualitaet_fehlerquote_pct")), `Kritische offene Issues: ${list.reduce((a, b) => a + (b.qualitaet_offene_kritische_issues || 0), 0)}`, list.reduce((a, b) => a + (b.qualitaet_offene_kritische_issues || 0), 0) > 2 ? "bad" : "good");
  }
  cards.innerHTML = html;

  if (!isKunde) {
    drawChart("chart-costs", "bar", {
      labels: list.map(x => x.project_name),
      datasets: [
        { label: "Kosten Soll (EUR)", data: list.map(x => x.kosten_soll), backgroundColor: "#9fc2e8" },
        { label: "Kosten Ist (EUR)", data: list.map(x => x.kosten_ist), backgroundColor: "#2f6fb2" },
      ]
    });
    drawChart("chart-progress", "bar", {
      labels: list.map(x => x.project_name),
      datasets: [{ label: "Fertigstellungsgrad (%)", data: list.map(x => x.fertigstellungsgrad_pct), backgroundColor: "#23a55a" }]
    }, { indexAxis: "y" });

    document.getElementById("kpi-standard-table").innerHTML =
      `<table class="data"><tr><th>Projekt</th><th>Ampel</th><th>SPI</th><th>CPI</th><th>Fertigstellung</th><th>Meilensteine</th><th>Auslastung</th><th>CRs</th><th>Fehlerquote</th></tr>` +
      list.map(p => `<tr><td>${esc(p.project_name)}</td><td><span class="pill ${p.health}">${p.health}</span></td>
        <td>${p.spi == null ? "–" : fmtNum(p.spi.toFixed(2))}</td><td>${p.cpi == null ? "–" : fmtNum(p.cpi.toFixed(2))}</td>
        <td>${fmtPct(p.fertigstellungsgrad_pct)}</td><td>${p.meilensteine_erledigt}/${p.meilensteine_gesamt} (${fmtPct(p.meilensteine_termingerecht_pct)})</td>
        <td>${fmtPct(p.ressourcen_auslastung_pct)}</td><td>${p.change_requests_gesamt} (${p.change_requests_genehmigt})</td>
        <td>${fmtPct(p.qualitaet_fehlerquote_pct)}</td></tr>`).join("") + `</table>`;
  }
}

/* ===================== MANAGEMENT ===================== */
async function loadManagement() {
  const [k, pf] = await Promise.all([api("/kpis"), api("/portfolio")]);
  const mgmt = k.management || [];
  document.getElementById("kpi-management-cards").innerHTML =
    kpiCard("ROI Portfolio", fmtPct(pf.roi_portfolio_pct), "Nutzenrealisierung")
    + kpiCard("Budget gesamt", fmtEUR(pf.budget_gesamt_eur), "Ist: " + fmtEUR(pf.ist_kosten_gesamt_eur) + " (" + fmtPct(pf.budget_auslastung_gesamt_pct) + ")")
    + kpiCard("Gesamtkostenabweichung", fmtEUR(pf.gesamtkostenabweichung_eur), "Budget – Ist")
    + kpiCard("Kapital in Gefahr", fmtEUR(pf.capital_at_risk_eur), "Projekte mit Ampel rot", pf.capital_at_risk_eur > 0 ? "bad" : "good")
    + kpiCard("Portfolio-Ampel", `🟢 ${pf.portfolio_ampel.gruen} · 🟡 ${pf.portfolio_ampel.gelb} · 🔴 ${pf.portfolio_ampel.rot}`, "kritische Pfad-Abw. max: " + pf.kritische_pfad_abweichung_max_tage + " Tage")
    + kpiCard("Ø NPS (Kundenzufriedenheit)", fmtNum(pf.durchschnittlicher_nps), "Stakeholder-/Kundenzufriedenheit");

  drawChart("chart-mgmt", "bar", {
    labels: mgmt.map(m => m.project_name),
    datasets: [
      { label: "Budgetauslastung (%)", data: mgmt.map(m => m.budget_auslastung_pct), backgroundColor: "#2f6fb2" },
      { label: "ROI ist (%)", data: mgmt.map(m => m.roi_ist_pct), backgroundColor: "#23a55a" },
      { label: "Krit. Pfad-Abweichung (Tage)", data: mgmt.map(m => m.kritischer_pfad_abweichung_tage), backgroundColor: "#d64541" },
    ]
  });

  document.getElementById("mgmt-risks").innerHTML = pf.top_risiken.length ?
    `<table class="data"><tr><th>Risiko</th><th>Projekt</th><th>Wkt.</th><th>Ausw.</th><th>Score</th></tr>` +
    pf.top_risiken.map(r => `<tr><td>${esc(r.title)}</td><td>${esc(r.project_name)}</td><td>${r.probability}</td><td>${r.impact}</td><td><b>${r.probability * r.impact}</b></td></tr>`).join("") + "</table>"
    : "<p>Keine eskalationswürdigen Risiken.</p>";

  document.getElementById("kpi-management-table").innerHTML =
    `<h3>Management-KPIs je Projekt</h3><table class="data">
     <tr><th>Projekt</th><th>ROI ist</th><th>Budgetauslastung</th><th>Kostenabweichung</th><th>Deckungsbeitrag ist</th><th>Nachfinanzierung</th><th>Pfad-Abw. (Tage)</th><th>NPS</th></tr>` +
    mgmt.map(m => `<tr><td>${esc(m.project_name)}</td><td>${fmtPct(m.roi_ist_pct)}</td><td>${fmtPct(m.budget_auslastung_pct)}</td>
      <td>${fmtEUR(m.gesamtkostenabweichung_eur)}</td><td>${fmtPct(m.deckungsbeitrag_ist_pct)}</td><td>${fmtEUR(m.nachfinanzierungsbetarf_eur)}</td>
      <td>${m.kritischer_pfad_abweichung_tage}</td><td>${m.nps_score ?? "–"}</td></tr>`).join("") + "</table>";
}

/* ===================== PROJEKTE ===================== */
document.getElementById("project-select").addEventListener("change", loadProjectDetail);

async function loadProjects() {
  projectsCache = await api("/projects");
  const sel = document.getElementById("project-select");
  sel.innerHTML = projectsCache.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join("");
  if (projectsCache.length) loadProjectDetail();
  else document.getElementById("project-detail").innerHTML = "<p>Kein Projekt sichtbar.</p>";
}

async function loadProjectDetail() {
  const pid = document.getElementById("project-select").value;
  if (!pid) return;
  const d = await api(`/projects/${pid}`);
  const p = d.project, s = d.kpi_standard, m = d.kpi_management;
  const editable = currentUser.role !== "kunde";

  let html = `<div class="card"><h3>${esc(p.name)} <span class="pill ${p.health}">${p.health}</span></h3>
    <p class="hint">${esc(p.description)}</p>
    <p><b>Auftraggeber:</b> ${esc(p.client)} &nbsp;|&nbsp; <b>Projektleiter:</b> ${esc(d.project_manager || "–")}
       &nbsp;|&nbsp; <b>Zeitraum:</b> ${p.start_date} → ${p.planned_end_date} (Soll)</p></div>`;

  html += `<div class="kpi-grid" style="margin:1rem 0">` +
    kpiCard("SPI", s.spi == null ? "–" : fmtNum(s.spi.toFixed(2)), "Terminleistung", (s.spi ?? 1) >= 1 ? "good" : "bad") +
    kpiCard("CPI", s.cpi == null ? "–" : fmtNum(s.cpi.toFixed(2)), "Kosteneffizienz", (s.cpi ?? 1) >= 1 ? "good" : "bad") +
    kpiCard("Fertigstellungsgrad", fmtPct(s.fertigstellungsgrad_pct), "")

  if (m) {
    html += kpiCard("ROI ist (vertraulich)", fmtPct(m.roi_ist_pct), "", "warn")
      + kpiCard("Deckungsbeitrag ist", fmtPct(m.deckungsbeitrag_ist_pct), "vertraulich", "warn");
  }
  html += `</div>`;

  html += `<h3>Terminplan – Meilensteine Soll/Ist</h3><table class="data">
    <tr><th>Meilenstein</th><th>Termin Soll</th><th>Termin Ist</th><th>Abweichung</th><th>Status</th></tr>` +
    d.milestones.map(ms => {
      const dev = ms.date_ist ? (new Date(ms.date_ist) - new Date(ms.date_soll)) / 86400000 : null;
      return `<tr><td>${esc(ms.name)}</td><td>${ms.date_soll}</td><td>${ms.date_ist || "–"}</td>
        <td>${dev == null ? "–" : (dev > 0 ? "+" : "") + dev + " Tage"}</td>
        <td><span class="pill ${ms.status}">${ms.status}</span></td></tr>`;
    }).join("") + `</table>`;

  if (editable && d.costs.length) {
    html += `<h3>Kosten – Soll/Ist</h3><table class="data">
      <tr><th>Kategorie</th><th>Position</th><th>Datum</th><th>Soll (EUR)</th><th>Ist (EUR)</th><th>Abweichung (EUR)</th></tr>` +
      d.costs.map(c => `<tr><td>${esc(c.category)}</td><td>${esc(c.description)}</td><td>${c.date}</td>
        <td>${fmtEUR(c.amount_soll)}</td><td>${fmtEUR(c.amount_ist)}</td><td style="color:${c.amount_soll - c.amount_ist < 0 ? '#d64541' : '#23a55a'}">${fmtEUR(c.amount_soll - c.amount_ist)}</td></tr>`).join("") +
      `<tr class="total"><td>Σ</td><td></td><td></td><td>${fmtEUR(s.kosten_soll)}</td><td>${fmtEUR(s.kosten_ist)}</td><td>${fmtEUR(s.kosten_soll - s.kosten_ist)}</td></tr></table>`;
  }

  if (editable && d.change_requests.length) {
    html += `<h3>Scope &amp; Änderungen (Change Requests)</h3><table class="data">
      <tr><th>Änderung</th><th>Datum</th><th>Status</th></tr>` +
      d.change_requests.map(c => `<tr><td>${esc(c.title)}</td><td>${c.date}</td><td><span class="pill ${c.status}">${c.status}</span></td></tr>`).join("") + `</table>`;
  }

  if (editable && d.resources.length) {
    html += `<h3>Ressourcenauslastung &amp; Aufwand</h3><table class="data">
      <tr><th>Team</th><th>Bereich</th><th>Geplante Std.</th><th>Tatsächl. Std.</th><th>Kapazität Std.</th><th>Auslastung</th></tr>` +
      d.resources.map(r => {
        const u = r.capacity_hours ? (r.actual_hours / r.capacity_hours * 100) : 0;
        return `<tr><td>${esc(r.name)}</td><td>${esc(r.area)}</td><td>${fmtNum(r.planned_hours)}</td><td>${fmtNum(r.actual_hours)}</td><td>${fmtNum(r.capacity_hours)}</td>
          <td>${fmtPct(u)} ${u > 100 ? "⚠️ <b>Überlastung</b>" : ""}</td></tr>`;
      }).join("") + `</table>`;
  }

  if (editable && d.quality.length) {
    html += `<h3>Qualitätskennzahlen</h3><table class="data">
      <tr><th>Bereich</th><th>Fehlerquote</th><th>Nacharbeitsstunden</th><th>Kritische offene Issues</th></tr>` +
      d.quality.map(q => `<tr><td>${esc(q.label)}</td><td>${fmtPct(q.defect_rate_pct)}</td><td>${fmtNum(q.rework_hours)}</td><td>${q.open_critical_issues}</td></tr>`).join("") + `</table>`;
  }

  document.getElementById("project-detail").innerHTML = html;
}

/* ===================== BERICHTE (PDF) ===================== */
async function loadReports() {
  const [types, projects] = await Promise.all([api("/report-types"), api("/projects")]);
  const sel = document.getElementById("report-select");
  sel.innerHTML = types.map(t => `<option value="${t.id}" ${t.allowed ? "" : "disabled"}>${t.allowed ? "" : "🔒 "}${esc(t.label)}${t.allowed ? "" : " – keine Berechtigung"}</option>`).join("");
  document.getElementById("report-project").innerHTML = projects.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join("");
}

document.getElementById("report-download").addEventListener("click", () => {
  const type = document.getElementById("report-select").value;
  const pid = document.getElementById("report-project").value;
  const note = document.getElementById("report-note");
  if (!type) { note.textContent = "Kein Bericht ausgewählt."; return; }
  fetch(`${API}/reports/${type}/${pid}`, { headers: { Authorization: "Bearer " + token } })
    .then(async r => { if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Download fehlgeschlagen"); return r.blob(); })
    .then(blob => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${type}_bericht.pdf`;
      a.click();
      note.textContent = "✓ PDF wurde generiert und heruntergeladen.";
    })
    .catch(e => { note.textContent = "Fehler: " + e.message; });
});

/* ===================== BENUTZERVERWALTUNG ===================== */
async function loadUsers() {
  const users = await api("/users");
  document.getElementById("users-table").innerHTML = `<table class="data">
    <tr><th>ID</th><th>Benutzername</th><th>Name</th><th>Rolle</th><th>Status</th><th>Aktion</th></tr>` +
    users.map(u => `<tr><td>${u.id}</td><td>${esc(u.username)}</td><td>${esc(u.full_name)}</td>
      <td>${ROLE_LABELS[u.role] || u.role}</td><td>${u.active ? "aktiv" : "deaktiviert"}</td>
      <td>${u.active && u.id !== currentUser.id ? `<button class="btn small" onclick="deactivateUser(${u.id})">Deaktivieren</button>` : ""}</td></tr>`).join("") + `</table>`;
}

async function deactivateUser(id) {
  try { await api(`/users/${id}`, { method: "DELETE" }); loadUsers(); }
  catch (e) { alert(e.message); }
}

document.getElementById("nu-create").addEventListener("click", async () => {
  const msg = document.getElementById("nu-msg");
  try {
    await api("/users", { method: "POST", body: JSON.stringify({
      username: nu_username.value.trim(), password: nu_password.value, full_name: nu_fullname.value.trim(), role: nu_role.value }) });
    msg.textContent = "✓ Benutzer angelegt."; nu_username.value = nu_password.value = nu_fullname.value = "";
    loadUsers();
  } catch (e) { msg.textContent = "Fehler: " + e.message; }
});

/* ===================== CHART HELPER ===================== */
function drawChart(canvasId, type, data, options = {}) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (charts[canvasId]) charts[canvasId].destroy();
  charts[canvasId] = new Chart(ctx, { type, data, options: { responsive: true, ...options } });
}

/* ===================== INIT ===================== */
(async () => {
  if (token) {
    try { currentUser = JSON.parse(sessionStorage.getItem("pd_user")); await api("/me"); bootApp(); return; } catch {}
  }
  document.getElementById("login-view").classList.remove("hidden");
})();
