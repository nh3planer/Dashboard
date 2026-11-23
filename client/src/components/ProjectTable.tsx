import type { Project } from '../api/types';
import { STATUS_CLASS, STATUS_LABEL, formatDate, formatEUR } from '../utils';

export function ProjectTable({
  projects,
  selectedId,
  onSelect,
}: {
  projects: Project[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  return (
    <table className="project-table">
      <thead>
        <tr>
          <th>Projekt</th>
          <th>Status</th>
          <th>Fortschritt (Ist / Soll)</th>
          <th>Termin Soll / Ist</th>
          <th>Kosten Ist / Soll</th>
          <th>Meilensteine</th>
        </tr>
      </thead>
      <tbody>
        {projects.map((p) => {
          const costDelta = p.cost_ist_total - p.cost_soll_total;
          return (
            <tr
              key={p.id}
              className={p.id === selectedId ? 'selected' : ''}
              onClick={() => onSelect(p.id)}
            >
              <td>
                <div className="project-name">{p.name}</div>
                <div className="project-sub">{p.customer || p.description}</div>
              </td>
              <td>
                <span className={`badge ${STATUS_CLASS[p.status]}`}>{STATUS_LABEL[p.status]}</span>
              </td>
              <td className="progress-cell">
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${p.progress}%` }} />
                </div>
                <span className="progress-text">{p.progress}%</span>
              </td>
              <td>
                {formatDate(p.start_soll)} – {formatDate(p.end_soll)}
                {p.end_ist && <div className="project-sub">Ende Ist: {formatDate(p.end_ist)}</div>}
              </td>
              <td>
                <div>{formatEUR(p.cost_ist_total)}</div>
                <div className={`project-sub ${costDelta > 0 ? 'text-red' : 'text-green'}`}>
                  {costDelta > 0 ? '+' : ''}
                  {formatEUR(costDelta)} vs. Soll
                </div>
              </td>
              <td>
                {p.milestone_done}/{p.milestone_count} fertig
                {p.milestone_delayed > 0 && (
                  <span className="text-red"> · {p.milestone_delayed} verspätet</span>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
