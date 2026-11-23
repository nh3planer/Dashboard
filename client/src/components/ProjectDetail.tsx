import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Project } from '../api/types';
import { STATUS_CLASS, STATUS_LABEL, formatDate, formatEUR, milestoneDelta } from '../utils';

export function ProjectDetail({
  project,
  onToggleMilestone,
}: {
  project: Project;
  onToggleMilestone: (id: number, done: boolean) => void;
}) {
  const costData = (project.costs ?? []).map((c) => ({
    month: c.month,
    soll: c.cost_soll,
    ist: c.cost_ist,
  }));
  let cumSoll = 0;
  let cumIst = 0;
  const cumData = (project.costs ?? []).map((c) => {
    cumSoll += c.cost_soll;
    cumIst += c.cost_ist;
    return { month: c.month, soll: cumSoll, ist: cumIst };
  });
  const costDelta = project.cost_ist_total - project.cost_soll_total;

  return (
    <section className="detail">
      <header className="detail-header">
        <div>
          <h2>{project.name}</h2>
          <p className="project-sub">{project.description}</p>
        </div>
        <span className={`badge ${STATUS_CLASS[project.status]}`}>{STATUS_LABEL[project.status]}</span>
      </header>

      <div className="detail-grid">
        <div className="card">
          <h3>Projektdaten</h3>
          <dl className="props">
            <dt>Auftraggeber</dt>
            <dd>{project.customer}</dd>
            <dt>Verantwortlich</dt>
            <dd>{project.responsible}</dd>
            <dt>Start (Soll)</dt>
            <dd>{formatDate(project.start_soll)}</dd>
            <dt>Ende Soll</dt>
            <dd>{formatDate(project.end_soll)}</dd>
            <dt>Ende Ist</dt>
            <dd>{formatDate(project.end_ist)}</dd>
            <dt>Fortschritt</dt>
            <dd>{project.progress}%</dd>
            <dt>Budget (Soll)</dt>
            <dd>{formatEUR(project.budget_soll)}</dd>
            <dt>Kosten Ist</dt>
            <dd className={costDelta > 0 ? 'text-red' : 'text-green'}>
              {formatEUR(project.cost_ist_total)} ({costDelta > 0 ? '+' : ''}
              {formatEUR(costDelta)})
            </dd>
          </dl>
        </div>

        <div className="card">
          <h3>Terminplan – Meilensteine (Soll / Ist)</h3>
          <ul className="milestones">
            {(project.milestones ?? []).map((m) => {
              const delta = milestoneDelta(m);
              return (
                <li key={m.id} className={`milestone status-${m.status}`}>
                  <label className="milestone-check">
                    <input
                      type="checkbox"
                      checked={m.status === 'done'}
                      onChange={(e) => onToggleMilestone(m.id, e.target.checked)}
                    />
                    <span>
                      <strong>{m.name}</strong>
                      <span className="project-sub">
                        Soll: {formatDate(m.date_soll)}
                        {m.status === 'done' && ` · Ist: ${formatDate(m.date_ist)}`} · {delta.label}
                      </span>
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="card card-wide">
          <h3>Kosten je Periode (Soll / Ist)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={costData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
              <Tooltip formatter={(v) => formatEUR(Number(v))} />
              <Legend />
              <Bar dataKey="soll" name="Soll" fill="#4c7dd0" radius={[3, 3, 0, 0]} />
              <Bar dataKey="ist" name="Ist" fill="#2fb37f" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card card-wide">
          <h3>Kostenverlauf kumuliert (Soll / Ist)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={cumData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
              <Tooltip formatter={(v) => formatEUR(Number(v))} />
              <Legend />
              <Line type="monotone" dataKey="soll" name="Soll (kumuliert)" stroke="#4c7dd0" strokeWidth={2} />
              <Line type="monotone" dataKey="ist" name="Ist (kumuliert)" stroke="#e07b39" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
