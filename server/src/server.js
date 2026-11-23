import express from 'express';
import cors from 'cors';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { db } from './db.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

const projectAggregates = `
  SELECT p.*,
    COALESCE((SELECT SUM(cost_soll) FROM cost_entries c WHERE c.project_id = p.id), 0) AS cost_soll_total,
    COALESCE((SELECT SUM(cost_ist) FROM cost_entries c WHERE c.project_id = p.id), 0) AS cost_ist_total,
    (SELECT COUNT(*) FROM milestones m WHERE m.project_id = p.id) AS milestone_count,
    (SELECT COUNT(*) FROM milestones m WHERE m.project_id = p.id AND m.status = 'done') AS milestone_done,
    (SELECT COUNT(*) FROM milestones m WHERE m.project_id = p.id AND m.status = 'delayed') AS milestone_delayed
  FROM projects p
`;

app.get('/api/projects', (req, res) => {
  const rows = db.prepare(`${projectAggregates} ORDER BY p.name`).all();
  res.json((req.query.details === 'true')
    ? rows.map(withDetail)
    : rows);
});

app.get('/api/projects/:id', (req, res) => {
  const row = db.prepare(`${projectAggregates} WHERE p.id = ?`).get(req.params.id);
  if (!row) return res.status(404).json({ error: 'Projekt nicht gefunden' });
  res.json(withDetail(row));
});

function withDetail(p) {
  const milestones = db
    .prepare('SELECT * FROM milestones WHERE project_id = ? ORDER BY sequence, date_soll')
    .all(p.id);
  const costs = db
    .prepare('SELECT * FROM cost_entries WHERE project_id = ? ORDER BY id')
    .all(p.id);
  return { ...p, milestones, costs };
}

app.post('/api/projects', (req, res) => {
  const b = req.body ?? {};
  if (!b.name || !b.start_soll || !b.end_soll) {
    return res.status(400).json({ error: 'name, start_soll und end_soll sind erforderlich' });
  }
  const info = db.prepare(`
    INSERT INTO projects (name, description, customer, status, start_soll, end_soll, end_ist, progress, budget_soll, responsible)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    b.name, b.description ?? '', b.customer ?? '', b.status ?? 'planned',
    b.start_soll, b.end_soll, b.end_ist ?? null,
    b.progress ?? 0, b.budget_soll ?? 0, b.responsible ?? ''
  );
  res.status(201).json({ id: info.lastInsertRowid });
});

app.put('/api/projects/:id', (req, res) => {
  const b = req.body ?? {};
  const info = db.prepare(`
    UPDATE projects SET
      name = COALESCE(?, name),
      description = COALESCE(?, description),
      customer = COALESCE(?, customer),
      status = COALESCE(?, status),
      start_soll = COALESCE(?, start_soll),
      end_soll = COALESCE(?, end_soll),
      end_ist = COALESCE(?, end_ist),
      progress = COALESCE(?, progress),
      budget_soll = COALESCE(?, budget_soll),
      responsible = COALESCE(?, responsible)
    WHERE id = ?
  `).run(
    b.name ?? null, b.description ?? null, b.customer ?? null, b.status ?? null,
    b.start_soll ?? null, b.end_soll ?? null, b.end_ist ?? null,
    b.progress ?? null, b.budget_soll ?? null, b.responsible ?? null, req.params.id
  );
  if (info.changes === 0) return res.status(404).json({ error: 'Projekt nicht gefunden' });
  res.json({ ok: true });
});

app.post('/api/projects/:id/milestones', (req, res) => {
  const b = req.body ?? {};
  if (!b.name || !b.date_soll) return res.status(400).json({ error: 'name und date_soll sind erforderlich' });
  const info = db.prepare(`
    INSERT INTO milestones (project_id, name, date_soll, date_ist, status, sequence)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(req.params.id, b.name, b.date_soll, b.date_ist ?? null, b.status ?? 'open', b.sequence ?? 0);
  res.status(201).json({ id: info.lastInsertRowid });
});

app.put('/api/milestones/:id', (req, res) => {
  const b = req.body ?? {};
  const info = db.prepare(`
    UPDATE milestones SET
      name = COALESCE(?, name),
      date_soll = COALESCE(?, date_soll),
      date_ist = COALESCE(?, date_ist),
      status = COALESCE(?, status),
      sequence = COALESCE(?, sequence)
    WHERE id = ?
  `).run(b.name ?? null, b.date_soll ?? null, b.date_ist ?? null, b.status ?? null, b.sequence ?? null, req.params.id);
  if (info.changes === 0) return res.status(404).json({ error: 'Meilenstein nicht gefunden' });
  res.json({ ok: true });
});

app.put('/api/projects/:id/costs/:month', (req, res) => {
  const b = req.body ?? {};
  const info = db.prepare(`
    INSERT INTO cost_entries (project_id, month, cost_soll, cost_ist)
    VALUES (?, ?, ?, ?)
    ON CONFLICT (project_id, month)
    DO UPDATE SET cost_soll = excluded.cost_soll, cost_ist = excluded.cost_ist
  `).run(req.params.id, req.params.month, b.cost_soll ?? 0, b.cost_ist ?? 0);
  res.json({ ok: true, id: info.lastInsertRowid });
});

app.get('/api/summary', (req, res) => {
  const projects = db.prepare(`${projectAggregates}`).all();
  const today = new Date().toISOString().slice(0, 10);
  res.json({
    project_count: projects.length,
    active_count: projects.filter((p) => p.status === 'active').length,
    at_risk_count: projects.filter((p) => p.status === 'at_risk').length,
    done_count: projects.filter((p) => p.status === 'done').length,
    planned_count: projects.filter((p) => p.status === 'planned').length,
    budget_soll_total: projects.reduce((s, p) => s + p.budget_soll, 0),
    cost_ist_total: projects.reduce((s, p) => s + p.cost_ist_total, 0),
    cost_soll_total: projects.reduce((s, p) => s + p.cost_soll_total, 0),
    overdue_milestones: projects.reduce((s, p) => s + p.milestone_delayed, 0),
    upcoming_deadlines: projects.filter(
      (p) => p.status !== 'done' && p.end_soll >= today
    ).length,
  });
});

if (process.env.SERVE_CLIENT !== 'false') {
  const clientDist = path.resolve(__dirname, '../../client/dist');
  app.use(express.static(clientDist));
  app.get(/^(?!\/api).*/, (req, res) => res.sendFile(path.join(clientDist, 'index.html')));
}

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Interner Serverfehler' });
});

app.listen(PORT, '127.0.0.1', () => {
  console.log(`Dashboard-Server läuft auf http://127.0.0.1:${PORT}`);
});
