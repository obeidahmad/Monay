// The JSON the Python engine sends (monay/web/presenter.py). Money is a
// 2-decimal string; the UI only formats it, never does money math.

export type Money = string;

export interface ProfileRef { id: number; name: string }

export interface Viewing { key: string; label: string; closed: boolean; first_month: boolean }

export interface Income { name: string; amount: Money; kind: "manual" | "leftover" }

export interface Field {
  name: string;
  budget: Money;
  budget_pct: string | null;
  current: Money;
  paid: Money;
  left: Money;
  consumed: Money;
  cap: Money | null; // null = ∞
  pocket: string;
}

export type SectionKind = "tax" | "pre" | "post";

export interface Section {
  name: string;
  kind: SectionKind;
  alloc_kind: "pct" | "amount";
  percentage: string | null;
  amount: Money | null;
  share_label: string;
  position: number;
  accent: number; // 0–7 → --section-1..8
  routing: { kind: "income" | "self" | "section"; target: string | null };
  routing_label: string;
  available: Money;
  consumed: Money;
  rest: Money;
  budget_left: Money;
  carried_rest: Money;
  fields: Field[];
}

export interface Pocket {
  name: string;
  is_default: boolean;
  counter: Money;
  fields: { section: string; field: string; left: Money }[];
  rests: Money | null;
}

export interface Transaction {
  index: number;
  day: number;
  section: string;
  field: string;
  amount: Money;
  description: string;
}

export interface Transfer {
  day: number;
  from_section: string;
  from_field: string;
  to_section: string;
  to_field: string;
  amount: Money;
  note: string;
}

export interface Summary {
  total_income: Money;
  tax_total: Money;
  pre_total: Money;
  post_pool: Money;
  has_post: boolean;
  pct_total: string;
  balanced: boolean;
}

export interface MonthView {
  key: string;
  label: string;
  state: "open" | "closed";
  total_income: Money;
  fresh_income: Money;
  incomes: Income[];
  sections: Section[];
  pockets: Pocket[];
  transactions: Transaction[];
  transfers: Transfer[];
  summary: Summary;
  warnings: string[];
}

export interface HistoryRow {
  key: string;
  label: string;
  state: "open" | "closed";
  income: Money;
  spent: Money;
  leftovers: Money;
}

export interface AppState {
  profile: ProfileRef | null;
  profiles: ProfileRef[];
  viewing: Viewing | null;
  month: MonthView | null;
  history: HistoryRow[];
}

export interface ClosePreview {
  label: string;
  next_label: string;
  leftovers: Money;
  carries: { section: string; rest: Money }[];
}
