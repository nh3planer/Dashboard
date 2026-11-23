"""KPI-Berechnung: Standard-KPIs und Management-KPIs."""
from datetime import datetime


def _num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _pct(x):
    return round(x * 100, 1)


def parse_date(s):
    try:
        return datetime.fromisoformat(s).date()
    except (TypeError, ValueError):
        return None


def days_delta(a, b):
    da, db = parse_date(a), parse_date(b)
    if not da or not db:
        return None
    return (da - db).days


def project_standard_kpis(p, milestones, resources, change_requests, quality, costs) -> dict:
    budget = _num(p["budget_soll"])
    ac = _num(p["cost_ist"])
    ev = _num(p["earned_value"])
    pv = _num(p["planned_value"])

    spi = round(ev / pv, 2) if pv else None
    cpi = round(ev / ac, 2) if ac else None
    fertigstellungsgrad_pct = _pct(ev / budget) if budget else None

    ms_total = len(milestones)
    ms_done = sum(1 for m in milestones if m["status"] == "erledigt")
    ms_on_time = sum(
        1 for m in milestones
        if m["status"] == "erledigt" and m["date_ist"] and days_delta(m["date_ist"], m["date_soll"]) is not None
        and days_delta(m["date_ist"], m["date_soll"]) <= 0
    )

    total_planned = sum(_num(r["planned_hours"]) for r in resources)
    total_actual = sum(_num(r["actual_hours"]) for r in resources)
    total_capacity = sum(_num(r["capacity_hours"]) for r in resources)
    overloads = sum(1 for r in resources if _num(r["actual_hours"]) > _num(r["capacity_hours"]))
    utilization_pct = _pct(total_actual / total_capacity) if total_capacity else None
    effort_deviation_pct = _pct((total_actual - total_planned) / total_planned) if total_planned else None

    cr_total = len(change_requests)
    cr_approved = sum(1 for c in change_requests if c["status"] == "genehmigt")
    defect_rate = round(sum(_num(q["defect_rate_pct"]) for q in quality) / len(quality), 2) if quality else 0.0
    rework_hours = sum(_num(q["rework_hours"]) for q in quality)
    open_critical = sum(_num(q["open_critical_issues"]) for q in quality)

    cost_soll = sum(_num(c["amount_soll"]) for c in costs)
    cost_ist = sum(_num(c["amount_ist"]) for c in costs)

    return {
        "spi": spi,
        "cpi": cpi,
        "fertigstellungsgrad_pct": fertigstellungsgrad_pct,
        "meilensteine_gesamt": ms_total,
        "meilensteine_erledigt": ms_done,
        "meilensteine_termingerecht_pct": _pct(ms_on_time / ms_total) if ms_total else None,
        "ressourcen_auslastung_pct": utilization_pct,
        "ressourcen_ueberlastungen": overloads,
        "aufwand_abweichung_pct": effort_deviation_pct,
        "change_requests_gesamt": cr_total,
        "change_requests_genehmigt": cr_approved,
        "qualitaet_fehlerquote_pct": defect_rate,
        "qualitaet_nacharbeitsstunden": rework_hours,
        "qualitaet_offene_kritische_issues": int(open_critical),
        "kosten_soll": round(cost_soll, 2),
        "kosten_ist": round(cost_ist, 2),
    }


def project_management_kpis(p, std_kpis) -> dict:
    budget = _num(p["budget_soll"])
    ac = _num(p["cost_ist"])
    ev = _num(p["earned_value"])
    business_value = _num(p["business_value"])
    cpi = std_kpis["cpi"] or 1.0

    est_completion_cost = ac / cpi if cpi else None
    overrun = round((est_completion_cost or 0) - budget, 2) if est_completion_cost else None
    cost_deviation_pct = _pct((ac - budget) / budget) if budget else None
    margin_ist_pct = round(p["margin_soll_pct"] - (cost_deviation_pct or 0), 1)
    roi_actual_pct = round((business_value - (est_completion_cost or ac)) / (est_completion_cost or ac) * 100, 1) \
        if (est_completion_cost or ac) else None

    return {
        "business_value": round(business_value, 2),
        "roi_erwartet_pct": p["roi_expected_pct"],
        "roi_ist_pct": roi_actual_pct,
        "budget_auslastung_pct": _pct(ac / budget) if budget else None,
        "gesamtkostenabweichung_eur": round(budget - ac, 2),
        "gesamtkostenabweichung_pct": cost_deviation_pct,
        "nachfinanzierungsbetarf_eur": overrun if overrun and overrun > 0 else 0.0,
        "deckungsbeitrag_soll_pct": p["margin_soll_pct"],
        "deckungsbeitrag_ist_pct": margin_ist_pct,
        "portfolio_status_ampel": p["health"],
        "kritischer_pfad_abweichung_tage": p["critical_path_deviation_days"],
        "nps_score": p["nps_score"],
    }


def portfolio_kpis(projects, per_project, risks) -> dict:
    total_budget = sum(_num(p["budget_soll"]) for p in projects)
    total_actual = sum(_num(p["cost_ist"]) for p in projects)
    total_business_value = sum(_num(p["business_value"]) for p in projects)
    rot = sum(1 for p in projects if p["health"] == "rot")
    gelb = sum(1 for p in projects if p["health"] == "gelb")
    gruen = sum(1 for p in projects if p["health"] == "gruen")
    escalations = [r for r in risks if r["escalation_needed"] and r["status"] != "geschlossen"]
    escalations.sort(key=lambda r: r["probability"] * r["impact"], reverse=True)
    deviations = [p["critical_path_deviation_days"] for p in projects]
    nps_values = [p["nps_score"] for p in projects if p["nps_score"] is not None]

    return {
        "projekte_gesamt": len(projects),
        "portfolio_ampel": {"gruen": gruen, "gelb": gelb, "rot": rot},
        "budget_gesamt_eur": round(total_budget, 2),
        "ist_kosten_gesamt_eur": round(total_actual, 2),
        "budget_auslastung_gesamt_pct": _pct(total_actual / total_budget) if total_budget else None,
        "gesamtkostenabweichung_eur": round(total_budget - total_actual, 2),
        "capital_at_risk_eur": round(sum(_num(p["budget_soll"]) for p in projects if p["health"] == "rot"), 2),
        "roi_portfolio_pct": round((total_business_value - total_actual) / total_actual * 100, 1) if total_actual else None,
        "kritische_pfad_abweichung_max_tage": max(deviations) if deviations else 0,
        "top_risiken": [dict(r) for r in escalations[:5]],
        "durchschnittlicher_nps": round(sum(nps_values) / len(nps_values), 1) if nps_values else None,
    }
