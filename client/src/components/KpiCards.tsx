import { formatEUR } from '../utils';
import type { Summary } from '../api/types';

export function KpiCards({ summary }: { summary: Summary | null }) {
  if (!summary) return null;
  const cards = [
    { label: 'Projekte gesamt', value: String(summary.project_count), hint: `${summary.active_count} aktiv · ${summary.planned_count} geplant` },
    { label: 'Projektbudget (Soll)', value: formatEUR(summary.budget_soll_total), hint: 'Summe aller Projektcodes' },
    {
      label: 'Kosten Ist / Soll',
      value: formatEUR(summary.cost_ist_total),
      hint: `Soll: ${formatEUR(summary.cost_soll_total)} · Abweichung ${formatEUR(summary.cost_ist_total - summary.cost_soll_total)}`,
      warn: summary.cost_ist_total > summary.cost_soll_total,
    },
    {
      label: 'Kritische Projekte',
      value: String(summary.at_risk_count),
      hint: `${summary.overdue_milestones} überfällige Meilensteine`,
      warn: summary.at_risk_count > 0 || summary.overdue_milestones > 0,
    },
  ];
  return (
    <section className="kpi-grid">
      {cards.map((c) => (
        <div key={c.label} className={`kpi-card${c.warn ? ' kpi-warn' : ''}`}>
          <div className="kpi-value">{c.value}</div>
          <div className="kpi-label">{c.label}</div>
          <div className="kpi-hint">{c.hint}</div>
        </div>
      ))}
    </section>
  );
}
