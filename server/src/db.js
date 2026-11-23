import Database from 'better-sqlite3';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(__dirname, '../../data');
const DB_PATH = process.env.DASHBOARD_DB || path.join(DATA_DIR, 'dashboard.db');

fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });

export const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  customer TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('planned','active','at_risk','done')),
  start_soll TEXT NOT NULL,
  end_soll TEXT NOT NULL,
  end_ist TEXT,
  progress INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  budget_soll REAL NOT NULL DEFAULT 0,
  responsible TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS milestones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  date_soll TEXT NOT NULL,
  date_ist TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','done','delayed')),
  sequence INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cost_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  month TEXT NOT NULL,
  cost_soll REAL NOT NULL DEFAULT 0,
  cost_ist REAL NOT NULL DEFAULT 0,
  UNIQUE (project_id, month)
);
`);

function seedIfEmpty() {
  const count = db.prepare('SELECT COUNT(*) AS c FROM projects').get().c;
  if (count > 0) return;

  const today = new Date();
  const iso = (d) => d.toISOString().slice(0, 10);
  const shift = (months, days = 0) => {
    const d = new Date(today);
    d.setMonth(d.getMonth() + months);
    d.setDate(d.getDate() + days);
    return iso(d);
  };

  const insertProject = db.prepare(`
    INSERT INTO projects (name, description, customer, status, start_soll, end_soll, end_ist, progress, budget_soll, responsible)
    VALUES (@name, @description, @customer, @status, @start_soll, @end_soll, @end_ist, @progress, @budget_soll, @responsible)
  `);
  const insertMilestone = db.prepare(`
    INSERT INTO milestones (project_id, name, date_soll, date_ist, status, sequence)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  const insertCost = db.prepare(`
    INSERT INTO cost_entries (project_id, month, cost_soll, cost_ist) VALUES (?, ?, ?, ?)
  `);

  const projects = [
    {
      name: 'Neubau Werkshalle',
      description: 'Errichtung einer Produktionshalle inkl. Bürotrakt und Außenanlagen.',
      customer: 'Musterwerke GmbH',
      status: 'active',
      start_soll: shift(-8),
      end_soll: shift(4),
      end_ist: null,
      progress: 62,
      budget_soll: 2400000,
      responsible: 'A. Berger',
      milestones: [
        { name: 'Bauantrag genehmigt', date_soll: shift(-7), date_ist: shift(-7, 10), status: 'done' },
        { name: 'Rohbau fertiggestellt', date_soll: shift(-3), date_ist: shift(-3, 21), status: 'done' },
        { name: 'Dachabdichtung abgeschlossen', date_soll: shift(1), date_ist: null, status: 'open' },
        { name: 'Elektroinstallation abgenommen', date_soll: shift(3), date_ist: null, status: 'open' },
        { name: 'Schlüsselübergabe', date_soll: shift(4), date_ist: null, status: 'open' },
      ],
      costs: [
        { month: 'M-8', soll: 180000, ist: 175000 },
        { month: 'M-7', soll: 220000, ist: 231400 },
        { month: 'M-6', soll: 260000, ist: 254800 },
        { month: 'M-5', soll: 260000, ist: 268700 },
        { month: 'M-4', soll: 300000, ist: 295200 },
        { month: 'M-3', soll: 300000, ist: 316000 },
        { month: 'M-2', soll: 280000, ist: 247500 },
        { month: 'M-1', soll: 280000, ist: 261300 },
      ],
    },
    {
      name: 'ERP-Systemeinführung',
      description: 'Ablösung der Altsysteme durch eine moderne ERP-Lösung mit Schnittstellen zu Logistik und Finanzwesen.',
      customer: 'Intern / IT',
      status: 'at_risk',
      start_soll: shift(-5),
      end_soll: shift(2),
      end_ist: null,
      progress: 58,
      budget_soll: 850000,
      responsible: 'S. Krüger',
      milestones: [
        { name: 'Konzept freigegeben', date_soll: shift(-4), date_ist: shift(-4), status: 'done' },
        { name: 'Migration Stammdaten', date_soll: shift(-1), date_ist: shift(1, 7), status: 'delayed' },
        { name: 'Testphase abgeschlossen', date_soll: shift(1), date_ist: null, status: 'open' },
        { name: 'Go-Live', date_soll: shift(2), date_ist: null, status: 'open' },
      ],
      costs: [
        { month: 'M-5', soll: 60000, ist: 63500 },
        { month: 'M-4', soll: 90000, ist: 88200 },
        { month: 'M-3', soll: 110000, ist: 121800 },
        { month: 'M-2', soll: 110000, ist: 134000 },
        { month: 'M-1', soll: 120000, ist: 141500 },
      ],
    },
    {
      name: 'Modernisierung Kantine',
      description: 'Umbau und Neugestaltung der Betriebskantine, Energiesparmaßnahmen inkl. beleuchtung.',
      customer: 'Intern / Facility',
      status: 'done',
      start_soll: shift(-12),
      end_soll: shift(-2),
      end_ist: shift(-2, -12),
      progress: 100,
      budget_soll: 320000,
      responsible: 'M. Fischer',
      milestones: [
        { name: 'Planung abgeschlossen', date_soll: shift(-11), date_ist: shift(-11), status: 'done' },
        { name: 'Handwerkliche Arbeiten', date_soll: shift(-4), date_ist: shift(-4, 6), status: 'done' },
        { name: 'Abnahme', date_soll: shift(-2), date_ist: shift(-2, -12), status: 'done' },
      ],
      costs: [
        { month: 'M-12', soll: 40000, ist: 39800 },
        { month: 'M-10', soll: 80000, ist: 82100 },
        { month: 'M-8', soll: 100000, ist: 97800 },
        { month: 'M-6', soll: 70000, ist: 71500 },
        { month: 'M-4', soll: 30000, ist: 28400 },
      ],
    },
    {
      name: 'Produktlinie Alpha 2.0',
      description: 'Entwicklung der überarbeiteten Produktlinie inkl. Zulassung und Markteinführung.',
      customer: 'Vertrieb / Entwicklung',
      status: 'planned',
      start_soll: shift(1),
      end_soll: shift(10),
      end_ist: null,
      progress: 0,
      budget_soll: 1200000,
      responsible: 'T. Weber',
      milestones: [
        { name: 'Projektstart / Kickoff', date_soll: shift(1), date_ist: null, status: 'open' },
        { name: 'Prototypenbau', date_soll: shift(5), date_ist: null, status: 'open' },
        { name: 'Zulassung erteilt', date_soll: shift(8), date_ist: null, status: 'open' },
        { name: 'Markteinführung', date_soll: shift(10), date_ist: null, status: 'open' },
      ],
      costs: [
        { month: 'M+1', soll: 40000, ist: 0 },
        { month: 'M+3', soll: 90000, ist: 0 },
        { month: 'M+5', soll: 130000, ist: 0 },
        { month: 'M+7', soll: 150000, ist: 0 },
      ],
    },
  ];

  const tx = db.transaction(() => {
    for (const p of projects) {
      const { milestones, costs, ...project } = p;
      const res = insertProject.run(project);
      milestones.forEach((m, i) =>
        insertMilestone.run(res.lastInsertRowid, m.name, m.date_soll, m.date_ist, m.status, i)
      );
      costs.forEach((c) => insertCost.run(res.lastInsertRowid, c.month, c.soll, c.ist));
    }
  });
  tx();
  console.log('Demo-Daten in SQLite geladen.');
}

seedIfEmpty();
