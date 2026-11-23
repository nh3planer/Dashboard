export interface Project {
  id: number;
  name: string;
  description: string;
  customer: string;
  status: 'planned' | 'active' | 'at_risk' | 'done';
  start_soll: string;
  end_soll: string;
  end_ist: string | null;
  progress: number;
  budget_soll: number;
  responsible: string;
  cost_soll_total: number;
  cost_ist_total: number;
  milestone_count: number;
  milestone_done: number;
  milestone_delayed: number;
  milestones?: Milestone[];
  costs?: CostEntry[];
}

export interface Milestone {
  id: number;
  project_id: number;
  name: string;
  date_soll: string;
  date_ist: string | null;
  status: 'open' | 'done' | 'delayed';
  sequence: number;
}

export interface CostEntry {
  id: number;
  project_id: number;
  month: string;
  cost_soll: number;
  cost_ist: number;
}

export interface Summary {
  project_count: number;
  active_count: number;
  at_risk_count: number;
  done_count: number;
  planned_count: number;
  budget_soll_total: number;
  cost_ist_total: number;
  cost_soll_total: number;
  overdue_milestones: number;
  upcoming_deadlines: number;
}
