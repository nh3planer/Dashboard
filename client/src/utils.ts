import type { Project } from './api/types';

export function formatEUR(value: number): string {
  return value.toLocaleString('de-DE', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  });
}

export function formatDate(iso: string | null): string {
  if (!iso) return '–';
  return new Date(iso).toLocaleDateString('de-DE');
}

export const STATUS_LABEL: Record<Project['status'], string> = {
  planned: 'Geplant',
  active: 'Aktiv',
  at_risk: 'Kritisch',
  done: 'Abgeschlossen',
};

export const STATUS_CLASS: Record<Project['status'], string> = {
  planned: 'status-planned',
  active: 'status-active',
  at_risk: 'status-risk',
  done: 'status-done',
};

export function milestoneDelta(m: { date_soll: string; date_ist: string | null; status: string }): {
  days: number;
  label: string;
} {
  const today = new Date();
  if (m.status === 'done' && m.date_ist) {
    const days = Math.round((new Date(m.date_ist).getTime() - new Date(m.date_soll).getTime()) / 86400000);
    return { days, label: days === 0 ? 'planmäßig' : `${days > 0 ? '+' : ''}${days} T` };
  }
  const days = Math.round((new Date(m.date_soll).getTime() - today.getTime()) / 86400000);
  return { days, label: days >= 0 ? `in ${days} T` : `${-days} T überfällig` };
}
