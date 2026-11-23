"""Projekt-Dashboard – FastAPI-Backend."""
import os
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import kpi, reports
from backend.auth import ROLES, authenticate, create_token
from backend.db import create_user, get_db, init_db_and_seed, user_count
from backend.rbac import ROLE_MANAGEMENT_KPI, ROLE_STANDARD, ROLE_USER_ADMIN, current_user, require_roles

app = FastAPI(title="Projekt-Dashboard")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

SESSIONS = {}


@app.on_event("startup")
def startup():
    init_db_and_seed()


# ----------------------------- Models -----------------------------

class LoginData(BaseModel):
    username: str
    password: str


class UserData(BaseModel):
    username: str
    password: str
    full_name: str
    role: str


class ProjectData(BaseModel):
    name: str
    client: str
    client_user_id: int | None = None
    project_manager_id: int | None = None
    status: str = "laufend"
    health: str = "gelb"
    start_date: str
    planned_end_date: str
    budget_soll: float
    cost_ist: float = 0
    earned_value: float = 0
    planned_value: float = 0
    margin_soll_pct: float = 0
    roi_expected_pct: float = 0
    business_value: float = 0
    nps_score: int | None = None
    critical_path_deviation_days: int = 0
    description: str = ""


class MilestoneData(BaseModel):
    project_id: int
    name: str
    date_soll: str
    date_ist: str | None = None
    status: str = "offen"


class CostData(BaseModel):
    project_id: int
    category: str
    description: str = ""
    amount_soll: float
    amount_ist: float = 0
    date: str


# ----------------------------- Helpers -----------------------------

def visible_project_rows(conn, user) -> list:
    rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
    if user["role"] == "projektleiter":
        return [r for r in rows if r["project_manager_id"] == int(user["sub"])]
    if user["role"] == "kunde":
        return [r for r in rows if r["client_user_id"] == int(user["sub"])]
    return rows


def assert_project_access(conn, user, project_id) -> bool:
    return any(p["id"] == project_id for p in visible_project_rows(conn, user))


# ----------------------------- Ersteinrichtung (Setup) -----------------------------

class SetupData(BaseModel):
    username: str
    password: str
    full_name: str


@app.get("/api/setup-status")
def setup_status():
    conn = get_db()
    complete = user_count(conn) > 0
    conn.close()
    return {"setup_complete": complete}


@app.post("/api/setup")
def setup(data: SetupData):
    """Ersteinrichtung:Der allererste Benutzer wird als Administrator (Geschäftsführer) angelegt.
    Nur solange noch kein Benutzer existiert möglich."""
    conn = get_db()
    if user_count(conn) > 0:
        conn.close()
        raise HTTPException(409, "Die Ersteinrichtung wurde bereits abgeschlossen – bitte normal anmelden.")
    if not data.username.strip() or not data.password or len(data.password) < 4:
        conn.close()
        raise HTTPException(400, "Benutzername und Passwort (mindestens 4 Zeichen) sind erforderlich.")
    uid = create_user(conn, data.username.strip(), data.password, data.full_name.strip() or data.username.strip(),
                      "geschaeftsfuehrer")
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return {"token": create_token(user), "user": {"id": user["id"], "username": user["username"],
                                                   "full_name": user["full_name"], "role": user["role"]}}


# ----------------------------- Auth -----------------------------

@app.post("/api/login")
def login(data: LoginData):
    user = authenticate(data.username, data.password)
    if not user:
        raise HTTPException(401, "Benutzername oder Passwort falsch")
    token = create_token(user)
    SESSIONS[token] = user["id"]
    return {"token": token, "user": {"id": user["id"], "username": user["username"],
                                     "full_name": user["full_name"], "role": user["role"]}}


@app.get("/api/me")
def me(request: Request):
    return current_user(request)


@app.post("/api/logout")
def logout(request: Request):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    SESSIONS.pop(token, None)
    return {"ok": True}


# ----------------------------- KPIs -----------------------------

@app.get("/api/kpis")
def kpis(request: Request):
    user = current_user(request)
    conn = get_db()
    projects = visible_project_rows(conn, user)
    std_list, mgmt_list = [], []
    for p in projects:
        milestones = conn.execute("SELECT * FROM milestones WHERE project_id = ?", (p["id"],)).fetchall()
        resources = conn.execute("SELECT * FROM resources WHERE project_id = ?", (p["id"],)).fetchall()
        crs = conn.execute("SELECT * FROM change_requests WHERE project_id = ?", (p["id"],)).fetchall()
        quality = conn.execute("SELECT * FROM quality_metrics WHERE project_id = ?", (p["id"],)).fetchall()
        costs = conn.execute("SELECT * FROM costs WHERE project_id = ?", (p["id"],)).fetchall()
        std = kpi.project_standard_kpis(p, milestones, resources, crs, quality, costs)
        is_kunde = user["role"] == "kunde"
        std_public = {
            "project_id": p["id"], "project_name": p["name"], "health": p["health"],
            "fertigstellungsgrad_pct": std["fertigstellungsgrad_pct"],
            "meilensteine_termingerecht_pct": std["meilensteine_termingerecht_pct"],
            "meilensteine_gesamt": std["meilensteine_gesamt"],
            "meilensteine_erledigt": std["meilensteine_erledigt"],
        }
        if not is_kunde:
            std_public.update({k: v for k, v in std.items()
                               if k not in ("fertigstellungsgrad_pct", "meilensteine_termingerecht_pct")})
            std_public["planned_end_date"] = p["planned_end_date"]
            std_list.append(std_public)
        else:
            std_list.append(std_public)
        if user["role"] in ROLE_MANAGEMENT_KPI:
            mgmt_list.append({"project_id": p["id"], "project_name": p["name"],
                              **kpi.project_management_kpis(p, std)})
    result = {"standard": std_list, "management": mgmt_list if user["role"] in ROLE_MANAGEMENT_KPI else None}
    conn.close()
    return result


@app.get("/api/portfolio")
def portfolio(request: Request):
    user = require_roles(ROLE_MANAGEMENT_KPI)(request)
    conn = get_db()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    risks = conn.execute("SELECT r.*, p.name AS project_name FROM risks r JOIN projects p ON p.id = r.project_id "
                         "WHERE r.status != 'geschlossen'").fetchall()
    result = kpi.portfolio_kpis(projects, None, risks)
    result["top_risiken"] = [dict(r) for r in result["top_risiken"]]
    conn.close()
    return result


# ----------------------------- Projekte -----------------------------

@app.get("/api/projects")
def projects_list(request: Request):
    user = current_user(request)
    conn = get_db()
    rows = visible_project_rows(conn, user)
    result = []
    for p in rows:
        result.append({
            "id": p["id"], "name": p["name"], "client": p["client"], "status": p["status"],
            "health": p["health"], "start_date": p["start_date"], "planned_end_date": p["planned_end_date"],
            "project_manager": _manager_name(conn, p["project_manager_id"]),
            "budget_soll": p["budget_soll"] if user["role"] != "kunde" else None,
            "cost_ist": p["cost_ist"] if user["role"] != "kunde" else None,
            "management_fields_visible": user["role"] in ROLE_MANAGEMENT_KPI,
        })
    conn.close()
    return result


def _manager_name(conn, uid):
    if not uid:
        return None
    row = conn.execute("SELECT full_name FROM users WHERE id = ?", (uid,)).fetchone()
    return row["full_name"] if row else None


@app.get("/api/projects/{pid}")
def project_detail(pid: int, request: Request):
    user = current_user(request)
    conn = get_db()
    if not assert_project_access(conn, user, pid):
        raise HTTPException(403, "Keine Berechtigung für dieses Projekt")
    p = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if not p:
        raise HTTPException(404, "Projekt nicht gefunden")
    milestones = conn.execute("SELECT * FROM milestones WHERE project_id = ? ORDER BY date_soll", (pid,)).fetchall()
    resources = conn.execute("SELECT * FROM resources WHERE project_id = ?", (pid,)).fetchall()
    crs = conn.execute("SELECT * FROM change_requests WHERE project_id = ? ORDER BY date DESC", (pid,)).fetchall()
    quality = conn.execute("SELECT * FROM quality_metrics WHERE project_id = ?", (pid,)).fetchall()
    costs = conn.execute("SELECT * FROM costs WHERE project_id = ? ORDER BY date", (pid,)).fetchall()
    std = kpi.project_standard_kpis(p, milestones, resources, crs, quality, costs)
    is_kunde = user["role"] == "kunde"
    detail = {
        "project": dict(p),
        "project_manager": _manager_name(conn, p["project_manager_id"]),
        "milestones": [dict(m) for m in milestones],
        "resources": [] if is_kunde else [dict(r) for r in resources],
        "change_requests": [dict(c) for c in crs],
        "quality": [] if is_kunde else [dict(q) for q in quality],
        "costs": [] if is_kunde else [dict(c) for c in costs],
        "kpi_standard": std if not is_kunde else {k: v for k, v in std.items() if k in (
            "fertigstellungsgrad_pct", "meilensteine_termingerecht_pct", "meilensteine_gesamt", "meilensteine_erledigt")},
        "kpi_management": kpi.project_management_kpis(p, std) if user["role"] in ROLE_MANAGEMENT_KPI else None,
    }
    conn.close()
    return detail


@app.post("/api/projects")
def project_create(data: ProjectData, request: Request):
    require_roles(("geschaeftsfuehrer", "management", "projektleiter"))(request)
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO projects (name, client, client_user_id, project_manager_id, status, health, start_date,
           planned_end_date, budget_soll, cost_ist, earned_value, planned_value, margin_soll_pct,
           roi_expected_pct, business_value, nps_score, critical_path_deviation_days, description)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data.name, data.client, data.client_user_id, data.project_manager_id, data.status, data.health,
         data.start_date, data.planned_end_date, data.budget_soll, data.cost_ist, data.earned_value,
         data.planned_value, data.margin_soll_pct, data.roi_expected_pct, data.business_value,
         data.nps_score, data.critical_path_deviation_days, data.description))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}


@app.post("/api/projects/{pid}/milestones")
def milestone_create(pid: int, data: MilestoneData, request: Request):
    require_roles(("geschaeftsfuehrer", "management", "projektleiter"))(request)
    conn = get_db()
    conn.execute("INSERT INTO milestones (project_id, name, date_soll, date_ist, status) VALUES (?,?,?,?,?)",
                 (pid, data.name, data.date_soll, data.date_ist, data.status))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/projects/{pid}/costs")
def cost_create(pid: int, data: CostData, request: Request):
    require_roles(("geschaeftsfuehrer", "management", "projektleiter"))(request)
    conn = get_db()
    conn.execute("INSERT INTO costs (project_id, category, description, amount_soll, amount_ist, date) VALUES (?,?,?,?,?,?)",
                 (pid, data.category, data.description, data.amount_soll, data.amount_ist, data.date))
    conn.commit()
    conn.close()
    return {"ok": True}


# ----------------------------- Benutzerverwaltung -----------------------------

@app.get("/api/users")
def users_list(request: Request):
    require_roles(ROLE_USER_ADMIN)(request)
    conn = get_db()
    rows = conn.execute("SELECT id, username, full_name, role, active, created_at FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/users")
def user_create(data: UserData, request: Request):
    require_roles(ROLE_USER_ADMIN)(request)
    if data.role not in ROLES:
        raise HTTPException(400, "Unbekannte Rolle")
    if len(data.password) < 4:
        raise HTTPException(400, "Passwort muss mindestens 4 Zeichen haben")
    conn = get_db()
    if conn.execute("SELECT 1 FROM users WHERE username = ?", (data.username,)).fetchone():
        conn.close()
        raise HTTPException(400, "Benutzername existiert bereits")
    create_user(conn, data.username, data.password, data.full_name, data.role)
    conn.close()
    return {"ok": True}


class AssignData(BaseModel):
    project_manager_id: int | None = None
    client_user_id: int | None = None


@app.post("/api/projects/{pid}/assign")
def project_assign(pid: int, data: AssignData, request: Request):
    require_roles(ROLE_USER_ADMIN)(request)
    conn = get_db()
    if not conn.execute("SELECT 1 FROM projects WHERE id = ?", (pid,)).fetchone():
        conn.close()
        raise HTTPException(404, "Projekt nicht gefunden")
    if data.project_manager_id is not None:
        row = conn.execute("SELECT role FROM users WHERE id = ?", (data.project_manager_id,)).fetchone()
        if not row or row["role"] != "projektleiter":
            conn.close()
            raise HTTPException(400, "Projektleiter muss ein Benutzer mit Rolle 'Projektleiter' sein")
    if data.client_user_id is not None:
        row = conn.execute("SELECT role FROM users WHERE id = ?", (data.client_user_id,)).fetchone()
        if not row or row["role"] != "kunde":
            conn.close()
            raise HTTPException(400, "Bauherr muss ein Benutzer mit Rolle 'Kunde/Bauherr' sein")
    conn.execute("UPDATE projects SET project_manager_id = ?, client_user_id = ? WHERE id = ?",
                 (data.project_manager_id, data.client_user_id, pid))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/users/{uid}")
def user_delete(uid: int, request: Request):
    user = require_roles(ROLE_USER_ADMIN)(request)
    if uid == int(user["sub"]):
        raise HTTPException(400, "Eigener Benutzer kann nicht deaktiviert werden")
    conn = get_db()
    conn.execute("UPDATE users SET active = 0 WHERE id = ?", (uid,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ----------------------------- PDF-Reports -----------------------------

@app.get("/api/report-types")
def report_types(request: Request):
    user = current_user(request)
    return [{"id": rid, "label": d["label"], "allowed": user["role"] in d["roles"]}
            for rid, d in reports.DEFS.items()]


@app.get("/api/reports/{report_type}/{pid}")
def report_download(report_type: str, pid: int, request: Request):
    user = current_user(request)
    if report_type not in reports.DEFS:
        raise HTTPException(404, "Unbekannter Report-Typ")
    if user["role"] not in reports.DEFS[report_type]["roles"]:
        raise HTTPException(403, "Keine Berechtigung für diesen Report")
    conn = get_db()
    if not assert_project_access(conn, user, pid):
        conn.close()
        raise HTTPException(403, "Keine Berechtigung für dieses Projekt")
    p = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    milestones = conn.execute("SELECT * FROM milestones WHERE project_id = ? ORDER BY date_soll", (pid,)).fetchall()
    resources = conn.execute("SELECT * FROM resources WHERE project_id = ?", (pid,)).fetchall()
    crs = conn.execute("SELECT * FROM change_requests WHERE project_id = ?", (pid,)).fetchall()
    quality = conn.execute("SELECT * FROM quality_metrics WHERE project_id = ?", (pid,)).fetchall()
    costs = conn.execute("SELECT * FROM costs WHERE project_id = ? ORDER BY date", (pid,)).fetchall()
    risks = conn.execute("SELECT r.*, p.name AS project_name FROM risks r JOIN projects pr ON pr.id = r.project_id "
                         "JOIN projects p ON p.id = r.project_id WHERE r.project_id = ?", (pid,)).fetchall()
    std = kpi.project_standard_kpis(p, milestones, resources, crs, quality, costs)
    mgmt = kpi.project_management_kpis(p, std) if user["role"] in ROLE_MANAGEMENT_KPI else None
    portfolio = None
    if user["role"] in ROLE_MANAGEMENT_KPI:
        all_projects = conn.execute("SELECT * FROM projects").fetchall()
        all_risks = conn.execute("SELECT r.*, p.name AS project_name FROM risks r "
                                 "JOIN projects p ON p.id = r.project_id WHERE r.status != 'geschlossen'").fetchall()
        portfolio = kpi.portfolio_kpis(all_projects, None, all_risks)
    conn.close()

    pdf = reports.build_report(report_type, dict(p), std, mgmt, portfolio,
                               [dict(m) for m in milestones], [dict(c) for c in costs],
                               [dict(r) for r in risks], user["role"])
    filename = f"{report_type}_{p['name'].replace(' ', '_')}_{uuid.uuid4().hex[:6]}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


# ----------------------------- Static -----------------------------

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
