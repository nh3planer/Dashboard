"""PDF-Report-Generierung mit ReportLab."""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DEFS = {
    "projekt_statusbericht": {
        "label": "Projekt-Statusbericht (KPIs & Termine)",
        "roles": ("geschaeftsfuehrer", "management", "projektleiter", "kunde"),
    },
    "kostenbericht": {
        "label": "Kostenbericht (Soll-/Ist-Kosten)",
        "roles": ("geschaeftsfuehrer", "management", "projektleiter"),
    },
    "terminbericht": {
        "label": "Terminbericht (Meilensteine)",
        "roles": ("geschaeftsfuehrer", "management", "projektleiter", "kunde"),
    },
    "management_report": {
        "label": "Management-Report (Portfolio & Risiko)",
        "roles": ("geschaeftsfuehrer", "management"),
    },
    "kundenbericht": {
        "label": "Kundenbericht (vereinfachter Status)",
        "roles": ("geschaeftsfuehrer", "management", "projektleiter", "kunde"),
    },
}

HEALTH_COLORS = {"gruen": colors.Color(0.2, 0.7, 0.3), "gelb": colors.Color(0.95, 0.75, 0.1), "rot": colors.Color(0.85, 0.25, 0.2)}

EUR = " EUR"


def _fmt(v, suffix=""):
    if v is None:
        return "–"
    if isinstance(v, str):
        return v + suffix
    if isinstance(v, float) and suffix == " %":
        return f"{v:.1f}".replace(".", ",") + suffix
    return f"{v:,}".replace(",", ".") + suffix


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="Small", fontName="Helvetica", fontSize=8, textColor=colors.grey))
    return s


def _table(data, widths=None, header=True):
    t = Table(data, colWidths=widths, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def _header_footer(doc, canvas, doc_title):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#1f3a5f"))
    canvas.rect(0, A4[1] - 1.4 * cm, A4[0], 1.4 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(1.6 * cm, A4[1] - 0.95 * cm, "Projekt-Dashboard")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - 1.6 * cm, A4[1] - 0.95 * cm, datetime.now().strftime("%d.%m.%Y %H:%M"))
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(colors.HexColor("#1f3a5f"))
    canvas.drawString(1.6 * cm, A4[1] - 2.3 * cm, doc_title)
    canvas.setStrokeColor(colors.HexColor("#1f3a5f"))
    canvas.line(1.6 * cm, 1.6 * cm, A4[0] - 1.6 * cm, 1.6 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(1.6 * cm, 1.1 * cm, "Automatisch generierter Report – Projektdashboard")
    canvas.restoreState()


def build_report(report_type: str, project, std, mgmt, portfolio, milestones, costs, risks, roles_label: str) -> bytes:
    styles = _styles()
    buffer = io.BytesIO()
    title = f"{DEFS[report_type]['label']}"
    if project:
        title += f" – {project['name']}"
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2.8 * cm, bottomMargin=2.2 * cm, title=title)
    story = [Spacer(1, 0.2 * cm)]

    if project:
        story.append(Paragraph(f"<b>Projekt:</b> {project['name']}  |  <b>Auftraggeber:</b> {project['client']}  "
                               f"|  <b>Status:</b> {project['status']}", styles["Normal"]))
        story.append(Paragraph(f"<b>Zeitraum:</b> {project['start_date']} – {project['planned_end_date']} (geplant)  "
                               f"|  <b>Ampelstatus:</b> {project['health'].upper()}", styles["Normal"]))
        story.append(Spacer(1, 0.4 * cm))

    if report_type in ("projekt_statusbericht", "kundenbericht", "terminbericht", "management_report"):
        kpi_rows = [
            ["KPI", "Wert", "Bewertung"],
            ["Fertigstellungsgrad", _fmt(std["fertigstellungsgrad_pct"], " %"), ""],
            ["SPI (Terminleistung)", _fmt(std["spi"]), "grün" if (std["spi"] or 0) >= 1 else "gelb"],
            ["Meilensteine termingerecht", _fmt(std["meilensteine_termingerecht_pct"], " %"), ""],
        ]
        if report_type != "kundenbericht":
            kpi_rows += [
                ["CPI (Kosteneffizienz)", _fmt(std["cpi"]), "grün" if (std["cpi"] or 0) >= 1 else "gelb"],
                ["Ressourcenauslastung", _fmt(std["ressourcen_auslastung_pct"], " %"), ""],
                ["Change Requests (offen/genehmigt)", f"{std['change_requests_gesamt']} / {std['change_requests_genehmigt']}", ""],
                ["Qualität: Fehlerquote", _fmt(std["qualitaet_fehlerquote_pct"], " %"),
                 "kritisch" if std["qualitaet_offene_kritische_issues"] > 2 else "ok"],
            ]
        story.append(Paragraph("<b>Standard-KPIs</b>", styles["Heading3"]))
        story.append(_table(kpi_rows, [7 * cm, 4 * cm, 4.5 * cm]))
        story.append(Spacer(1, 0.5 * cm))

        story.append(Paragraph("<b>Terminplan – Meilensteine (Soll/Ist)</b>", styles["Heading3"]))
        ms_rows = [["Meilenstein", "Soll", "Ist", "Status"]]
        for m in milestones:
            ms_rows.append([m["name"], m["date_soll"], m["date_ist"] or "–", m["status"]])
        story.append(_table(ms_rows, [6.5 * cm, 2.8 * cm, 2.8 * cm, 3.2 * cm]))
        story.append(Spacer(1, 0.5 * cm))

    if report_type in ("projekt_statusbericht", "kostenbericht", "management_report"):
        story.append(Paragraph("<b>Kosten – Soll/Ist je Position</b>", styles["Heading3"]))
        cost_rows = [["Kategorie", "Beschreibung", "Soll (EUR)", "Ist (EUR)", "Abweichung (EUR)"]]
        for c in costs:
            cost_rows.append([c["category"], c["description"], _fmt(c["amount_soll"]), _fmt(c["amount_ist"]),
                              _fmt(c["amount_soll"] - c["amount_ist"])])
        cost_rows.append(["Σ Gesamt", "", _fmt(std["kosten_soll"]), _fmt(std["kosten_ist"]),
                          _fmt(std["kosten_soll"] - std["kosten_ist"])])
        t = _table(cost_rows, [3 * cm, 4.5 * cm, 3.2 * cm, 3.2 * cm, 3.4 * cm])
        t.setStyle(TableStyle([("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dce6f1")),
                               ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
        story.append(t)
        story.append(Spacer(1, 0.5 * cm))

    if report_type == "management_report":
        story.append(Paragraph("<b>Management-KPIs (vertraulich)</b>", styles["Heading3"]))
        mgmt_rows = [["KPI", "Wert"]]
        for label, key, fmt in [
            ("ROI ist (%)", mgmt["roi_ist_pct"], " %"), ("Budgetauslastung (%)", mgmt["budget_auslastung_pct"], " %"),
            ("Gesamtkostenabweichung (EUR)", mgmt["gesamtkostenabweichung_eur"], EUR),
            ("Deckungsbeitrag ist (%)", mgmt["deckungsbeitrag_ist_pct"], " %"),
            ("Kritischer Pfad – Abweichung (Tage)", mgmt["kritischer_pfad_abweichung_tage"], ""),
            ("NPS Score", mgmt["nps_score"], ""),
        ]:
            mgmt_rows.append([label, _fmt(key, fmt)])
        story.append(_table(mgmt_rows, [9 * cm, 5 * cm]))
        story.append(Spacer(1, 0.5 * cm))

        if portfolio:
            story.append(Paragraph("<b>Portfolio-Übersicht</b>", styles["Heading3"]))
            pf_rows = [["Kennzahl", "Wert"]]
            for label, key, fmt in [
                ("Projekte gesamt", portfolio["projekte_gesamt"], ""),
                ("Ampel grün/gelb/rot", f"{portfolio['portfolio_ampel']['gruen']} / "
                                         f"{portfolio['portfolio_ampel']['gelb']} / {portfolio['portfolio_ampel']['rot']}", ""),
                ("Budget gesamt (EUR)", portfolio["budget_gesamt_eur"], EUR),
                ("Ist-Kosten gesamt (EUR)", portfolio["ist_kosten_gesamt_eur"], EUR),
                ("Gesamtkostenabweichung (EUR)", portfolio["gesamtkostenabweichung_eur"], EUR),
                ("Kapital in Gefahr (EUR, rote Projekte)", portfolio["capital_at_risk_eur"], EUR),
                ("Ø NPS", portfolio["durchschnittlicher_nps"], ""),
            ]:
                pf_rows.append([label, _fmt(key, fmt)])
            story.append(_table(pf_rows, [9 * cm, 5 * cm]))
            story.append(Spacer(1, 0.5 * cm))

        story.append(Paragraph("<b>Top-Risiken & Eskalationsbedarf</b>", styles["Heading3"]))
        r_rows = [["Risiko", "Wkt.", "Ausw.", "Score", "Eskalation"]]
        for r in risks:
            r_rows.append([r["title"], r["probability"], r["impact"], r["probability"] * r["impact"],
                           "JA" if r["escalation_needed"] else "nein"])
        story.append(_table(r_rows, [6.5 * cm, 1.5 * cm, 1.5 * cm, 1.7 * cm, 2.5 * cm]))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(f"Erstellt für Rolle: {roles_label} – automatische Generierung aus dem Projektdashboard, "
                           f"{datetime.now().strftime('%d.%m.%Y')}. Management-KPIs ausschließlich für berechtigte Rollen.",
                           styles["Small"]))

    doc.build(story, onFirstPage=lambda c, d: _header_footer(d, c, title),
              onLaterPages=lambda c, d: _header_footer(d, c, title))
    return buffer.getvalue()
