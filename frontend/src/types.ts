export interface Location {
  id: string;
  name: string;
  kind: string;
  x: number;
  y: number;
}
export interface Road {
  id: string;
  name: string;
  a: string;
  b: string;
  minutes: number;
  status: string;
  valid_until: number;
  inspection_minutes: number;
  prior: number;
  prior_source: string;
}
export interface Delivery {
  id: string;
  destination: string;
  quantity: number;
  deadline: number;
  weight: number;
  status: string;
  delivered_at: number | null;
}
export interface Report {
  id: string;
  road: string;
  claim: string;
  source: string;
  authority: string;
  observed_at: number;
  received_at: number;
  text: string;
}
export interface Leg {
  road: string;
  start: string;
  end: string;
  minutes: number;
  request: string | null;
}
export interface Route {
  vehicle: string;
  depot: string;
  requests: string[];
  quantity: number;
  legs: Leg[];
  arrivals: Record<string, number>;
  utility: number;
  travel: number;
}
export interface Plan {
  id: string;
  revision: number;
  routes: Route[];
  utility: number;
  status: string;
  solver_seconds: number;
  unmet: { id: string; quantity: number; reason: string }[];
  limits: string;
}
export interface Vehicle {
  id: string;
  name: string;
  depot: string;
  location: string;
  capacity: number;
  available: boolean;
  loaded: number;
  assignment: string | null;
}
export interface Assignment {
  id: string;
  plan: string;
  route: Route;
  state: string;
  index: number;
  entered_at: number | null;
  exits_at: number | null;
}
export interface Decision {
  id: string;
  time: number;
  mode: string;
  summary: string;
  evidence: string[];
  calls: unknown[];
  plan: string | null;
}
export interface Event {
  id: string;
  seq: number;
  time: number;
  kind: string;
  summary: string;
  ids: string[];
}
export interface World {
  id: string;
  scenario: string;
  time: number;
  horizon: number;
  budget: number;
  revision: number;
  cycles: number;
  status: string;
  locations: Location[];
  roads: Road[];
  requests: Delivery[];
  depots: { id: string; stock: number }[];
  vehicles: Vehicle[];
  reports: Report[];
  assignments: Assignment[];
  decisions: Decision[];
  events: Event[];
  metrics: Record<string, number>;
  stock_available: Record<string, number>;
}
export interface Candidate {
  road: string;
  name: string;
  prior: number;
  prior_source: string;
  minutes: number;
  open_utility: number;
  closed_utility: number;
  expected_utility: number;
  gain: number;
  affected_requests: string[];
  evidence_ids: string[];
}
export interface Ranking {
  base_utility: number;
  candidates: Candidate[];
  recommendation: string;
  revision: number;
  limits: string;
}
export interface Snapshot {
  revision: number;
  time: number;
  state: World;
}
