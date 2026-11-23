import { useCallback, useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import {
  fetchProject,
  fetchProjects,
  fetchSummary,
  updateMilestone,
  updateProject,
} from './api/client';
import type { Project, Summary } from './api/types';
import { KpiCards } from './components/KpiCards';
import { ProjectTable } from './components/ProjectTable';
import { ProjectDetail } from './components/ProjectDetail';
import { formatEUR } from './utils';

export default function App() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (selectFirst = true) => {
    try {
      const [s, list] = await Promise.all([fetchSummary(), fetchProjects()]);
      setSummary(s);
      setProjects(list);
      if (selectFirst && list.length > 0 && !selected) {
        setSelected(await fetchProject(list[0].id));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unbekannter Fehler');
    }
  }, [selected]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectProject = async (id: number) => {
    setSelected(await fetchProject(id));
  };

  const toggleMilestone = async (id: number, done: boolean) => {
    if (!selected) return;
    await updateMilestone(id, {
      status: done ? 'done' : 'open',
      date_ist: done ? new Date().toISOString().slice(0, 10) : null,
    });
    setSelected(await fetchProject(selected.id));
    await load(false);
  };

  const bumpProgress = async (project: Project, delta: number) => {
    const progress = Math.min(100, Math.max(0, project.progress + delta));
    await updateProject(project.id, { progress });
    await load(false);
  };

  const statusData = projects.map((p) => ({
    name: p.name.length > 18 ? `${p.name.slice(0, 17)}…` : p.name,
    soll: p.budget_soll,
    ist: p.cost_ist_total,
  }));

  return (
    <div className="app">
      <header className="header">
        <h1>Projekt-Dashboard</h1>
        <span className="header-sub">Soll-/Ist-Steuerung von Terminen und Kosten</span>
      </header>

      {error && <div className="error-banner">Fehler: {error}</div>}

      <KpiCards summary={summary} />

      <section className="card">
        <h2>Projektübersicht</h2>
        <ProjectTable
          projects={projects}
          selectedId={selected?.id ?? null}
          onSelect={selectProject}
        />
      </section>

      <section className="card">
        <h2>Budget vs. Ist-Kosten je Projekt</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={statusData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" />
            <YAxis tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
            <Tooltip formatter={(v) => formatEUR(Number(v))} />
            <Bar dataKey="soll" name="Budget Soll" fill="#4c7dd0" radius={[3, 3, 0, 0]} />
            <Bar dataKey="ist" name="Kosten Ist" fill="#e07b39" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </section>

      {selected && (
        <>
          <div className="detail-toolbar">
            <h2>Detail: {selected.name}</h2>
            <div className="toolbar-actions">
              <button onClick={() => bumpProgress(selected, -10)}>Fortschritt −10%</button>
              <button onClick={() => bumpProgress(selected, 10)}>Fortschritt +10%</button>
            </div>
          </div>
          <ProjectDetail project={selected} onToggleMilestone={toggleMilestone} />
        </>
      )}

      <footer className="footer">
        React + TypeScript · Express · SQLite (data/dashboard.db)
      </footer>
    </div>
  );
}
