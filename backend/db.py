"""SQLite-Datenbank: Schema, Verbindung und Seed-Daten."""
import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.environ.get("DASHBOARD_DB", os.path.join(os.path.dirname(__file__), "..", "data", "dashboard.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('geschaeftsfuehrer','management','projektleiter','kunde')),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    client TEXT NOT NULL,
    client_user_id INTEGER,
    project_manager_id INTEGER,
    status TEXT NOT NULL DEFAULT 'laufend',
    health TEXT NOT NULL DEFAULT 'gelb',
    start_date TEXT NOT NULL,
    planned_end_date TEXT NOT NULL,
    actual_end_date TEXT,
    budget_soll REAL NOT NULL,
    cost_ist REAL NOT NULL,
    earned_value REAL NOT NULL,
    planned_value REAL NOT NULL,
    margin_soll_pct REAL NOT NULL DEFAULT 0,
    roi_expected_pct REAL NOT NULL DEFAULT 0,
    business_value REAL NOT NULL DEFAULT 0,
    nps_score INTEGER,
    critical_path_deviation_days INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    date_soll TEXT NOT NULL,
    date_ist TEXT,
    status TEXT NOT NULL DEFAULT 'offen' CHECK (status IN ('offen','erledigt','verspaetet'))
);

CREATE TABLE IF NOT EXISTS costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    amount_soll REAL NOT NULL,
    amount_ist REAL NOT NULL,
    date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    probability INTEGER NOT NULL CHECK (probability BETWEEN 1 AND 5),
    impact INTEGER NOT NULL CHECK (impact BETWEEN 1 AND 5),
    escalation_needed INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'offen'
);

CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    area TEXT NOT NULL,
    planned_hours REAL NOT NULL,
    actual_hours REAL NOT NULL,
    capacity_hours REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS change_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'offen'
);

CREATE TABLE IF NOT EXISTS quality_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    defect_rate_pct REAL NOT NULL,
    rework_hours REAL NOT NULL,
    open_critical_issues INTEGER NOT NULL
);
"""


def get_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db_and_seed():
    conn = get_db()
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed(conn)
    conn.commit()
    conn.close()


def hash_password(password: str, salt: str) -> str:
    import hashlib
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()


def make_user(conn, username, password, full_name, role):
    salt = os.urandom(16).hex()
    conn.execute(
        "INSERT INTO users (username, password_hash, salt, full_name, role, active, created_at) VALUES (?,?,?,?,?,1,?)",
        (username, hash_password(password, salt), salt, full_name, role, datetime.utcnow().isoformat()),
    )


def seed(conn):
    make_user(conn, "chef", "demo123", "Anna Chefin", "geschaeftsfuehrer")
    make_user(conn, "mgmt", "demo123", "Marco Manager", "management")
    make_user(conn, "pl", "demo123", "Paula Leiterin", "projektleiter")
    make_user(conn, "pl2", "demo123", "Peter Planer", "projektleiter")
    make_user(conn, "kunde", "demo123", "Klaus Bauherr", "kunde")

    users = {r["username"]: r["id"] for r in conn.execute("SELECT id, username FROM users")}
    today = datetime.utcnow().date()

    projects = [
        ("Neubau Bürogebäude Ost", "Bauherr Ost GmbH", "kunde", "chef", "pl",
         "laufend", "gelb", (today - timedelta(days=120)).isoformat(), (today + timedelta(days=90)).isoformat(), None,
         2_500_000, 1_450_000, 1_250_000, 1_300_000, 12.0, 18.0, 3_200_000, 42, 6,
         "Neubau eines Bürogebäudes mit Tiefgarage, 4 Etagen."),
        ("Sanierung Schulzentrum West", "Stadt Musterstadt", None, "mgmt", "pl2",
         "laufend", "gruen", (today - timedelta(days=60)).isoformat(), (today + timedelta(days=150)).isoformat(), None,
         1_800_000, 620_000, 680_000, 700_000, 10.0, 15.0, 2_100_000, 55, 0,
         "Generalsanierung des Schulzentrums, 3 Bauabschnitte."),
        ("Erweiterung Logistikzentrum", "Logistik AG Nord", "kunde", "chef", "pl",
         "laufend", "rot", (today - timedelta(days=200)).isoformat(), (today + timedelta(days=30)).isoformat(), None,
         3_900_000, 3_450_000, 3_100_000, 3_600_000, 8.0, 10.0, 4_600_000, 18, 14,
         "Hallerweiterung und Automation der Fördertechnik."),
    ]
    for p in projects:
        conn.execute(
            """INSERT INTO projects (name, client, client_user_id, project_manager_id, status, health,
               start_date, planned_end_date, actual_end_date, budget_soll, cost_ist, earned_value,
               planned_value, margin_soll_pct, roi_expected_pct, business_value, nps_score,
               critical_path_deviation_days, description)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (p[0], p[1], users.get(p[2]), users[p[4]], p[5], p[6], p[7], p[8], p[9], p[10], p[11],
             p[12], p[13], p[14], p[15], p[16], p[17], p[18], p[19]),
        )

    pids = [r["id"] for r in conn.execute("SELECT id FROM projects ORDER BY id")]

    milestones = [
        (pids[0], "Rohbau fertig", (today - timedelta(days=40)).isoformat(), (today - timedelta(days=35)).isoformat(), "erledigt"),
        (pids[0], "Dachabdichtung", (today - timedelta(days=10)).isoformat(), (today - timedelta(days=3)).isoformat(), "erledigt"),
        (pids[0], "Fassade geschlossen", (today + timedelta(days=25)).isoformat(), None, "offen"),
        (pids[0], "Ausbau Fenster", (today + timedelta(days=60)).isoformat(), None, "offen"),
        (pids[1], "BA1 abgeschlossen", (today - timedelta(days=20)).isoformat(), (today - timedelta(days=22)).isoformat(), "erledigt"),
        (pids[1], "BA2 gestartet", (today + timedelta(days=10)).isoformat(), None, "offen"),
        (pids[1], "Dach saniert", (today + timedelta(days=70)).isoformat(), None, "offen"),
        (pids[2], "Fundamente", (today - timedelta(days=120)).isoformat(), (today - timedelta(days=100)).isoformat(), "erledigt"),
        (pids[2], "Stahltragwerk", (today - timedelta(days=20)).isoformat(), (today - timedelta(days=5)).isoformat(), "erledigt"),
        (pids[2], "Fördertechnik montiert", (today + timedelta(days=15)).isoformat(), None, "verspaetet"),
        (pids[2], "Inbetriebnahme", (today + timedelta(days=28)).isoformat(), None, "offen"),
    ]
    for m in milestones:
        conn.execute("INSERT INTO milestones (project_id, name, date_soll, date_ist, status) VALUES (?,?,?,?,?)", m)

    costs = [
        (pids[0], "Rohbau", "Stahlbetonarbeiten", 800_000, 780_000, (today - timedelta(days=40)).isoformat()),
        (pids[0], "Fassade", "Fassadenarbeiten", 500_000, 320_000, (today - timedelta(days=5)).isoformat()),
        (pids[0], "Haustechnik", "HLK-Installation", 700_000, 350_000, (today - timedelta(days=2)).isoformat()),
        (pids[0], "Ausbau", "Innenausbau", 500_000, 0, (today + timedelta(days=1)).isoformat()),
        (pids[1], "BA1", "Abbrucharbeiten", 300_000, 290_000, (today - timedelta(days=30)).isoformat()),
        (pids[1], "BA1", "Elektro", 250_000, 260_000, (today - timedelta(days=15)).isoformat()),
        (pids[1], "BA2", "Dach", 400_000, 70_000, (today - timedelta(days=3)).isoformat()),
        (pids[2], "Rohbau", "Fundamente", 900_000, 950_000, (today - timedelta(days=100)).isoformat()),
        (pids[2], "Tragwerk", "Stahlbau", 1_200_000, 1_350_000, (today - timedelta(days=5)).isoformat()),
        (pids[2], "Automation", "Fördertechnik", 1_100_000, 1_150_000, (today - timedelta(days=2)).isoformat()),
    ]
    costs = [c[:6] for c in costs]
    for c in costs:
        conn.execute("INSERT INTO costs (project_id, category, description, amount_soll, amount_ist, date) VALUES (?,?,?,?,?,?)", c)

    risks = [
        (pids[0], "Lieferverzug Fensteranfertigungen", 3, 4, 1, "offen"),
        (pids[0], "Witterungsrisiko Fassade", 2, 2, 0, "offen"),
        (pids[1], "Kapazitätsengpass Handwerker", 2, 3, 0, "offen"),
        (pids[2], "Nicht verfügbare Spezialkräne", 4, 5, 1, "offen"),
        (pids[2], "Preissteigerung Stahl", 3, 4, 1, "offen"),
    ]
    for r in risks:
        conn.execute("INSERT INTO risks (project_id, title, probability, impact, escalation_needed, status) VALUES (?,?,?,?,?,?)", r)

    resources = [
        (pids[0], "Team Rohbau", "Rohbau", 1_600, 1_450, 1_800),
        (pids[0], "Team Ausbau", "Ausbau", 2_000, 900, 1_600),
        (pids[1], "Team BA1", "Renovierung", 1_200, 1_250, 1_300),
        (pids[1], "Team Dach", "Dach", 800, 120, 600),
        (pids[2], "Team Stahl", "Stahlbau", 2_400, 2_550, 2_000),
        (pids[2], "Team Automation", "Automation", 1_800, 1_200, 1_400),
    ]
    for r in resources:
        conn.execute("INSERT INTO resources (project_id, name, area, planned_hours, actual_hours, capacity_hours) VALUES (?,?,?,?,?,?)", r)

    crs = [
        (pids[0], "Zusätzliche Carport-Anlage", (today - timedelta(days=30)).isoformat(), "genehmigt"),
        (pids[0], "Farbwechsel Fassade", (today - timedelta(days=10)).isoformat(), "offen"),
        (pids[1], "Zusätzliche Brandschutztüren", (today - timedelta(days=20)).isoformat(), "genehmigt"),
        (pids[2], "Erweiterung Palettenplätze", (today - timedelta(days=45)).isoformat(), "abgelehnt"),
        (pids[2], "Neuer Leitstand", (today - timedelta(days=12)).isoformat(), "offen"),
    ]
    for c in crs:
        conn.execute("INSERT INTO change_requests (project_id, title, date, status) VALUES (?,?,?,?)", c)

    quality = [
        (pids[0], "Rohbau", 1.2, 40, 1),
        (pids[0], "Fassade", 0.8, 15, 0),
        (pids[1], "BA1", 0.5, 8, 0),
        (pids[2], "Stahlbau", 3.4, 120, 4),
        (pids[2], "Automation", 2.1, 60, 2),
    ]
    for q in quality:
        conn.execute("INSERT INTO quality_metrics (project_id, label, defect_rate_pct, rework_hours, open_critical_issues) VALUES (?,?,?,?,?)", q)
