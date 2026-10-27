// Typed client for the V2 query API; its supervisor routes are not implemented yet.
// Requests carry only allowlisted metric ids and approved filter keys; all SQL
// compilation and environment scoping happen server-side.

export interface MetricDef {
  id: string;
  name: string;
  type?: string;
}

export interface Catalog {
  metrics: MetricDef[];
  dimensions: string[];
}

export interface QueryFilters {
  source?: string;
  type_id?: string;
  link_type?: string;
  since?: number;
}

export interface QuerySpec {
  metric: string;
  filters: QueryFilters;
}

export type Viz = "card" | "bar" | "line" | "table";

export interface WidgetSpec extends QuerySpec {
  title: string;
  viz: Viz;
  span?: 1 | 2 | 3;
}

export interface ResultRow {
  dimension?: string;
  value: number;
}

export interface ExecuteResponse {
  metric: string;
  environment: string;
  results: ResultRow[];
}

export interface DashboardRecord {
  id: string;
  title: string;
  description?: string;
  layout_json?: string | { widgets?: WidgetSpec[] };
  queries_json?: string | WidgetSpec[];
  created_at?: number;
  updated_at?: number;
}

export class ApiError extends Error {
  authRequired: boolean;

  constructor(message: string, authRequired = false) {
    super(message);
    this.name = "ApiError";
    this.authRequired = authRequired;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (res.status === 401) {
    throw new ApiError("Sign in to manage saved dashboards.", true);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError((data as { error?: string }).error || `Request failed (${res.status})`);
  }
  return data as T;
}

export function getCatalog(): Promise<Catalog> {
  return request<Catalog>("/api/v2/query/catalog");
}

export function executeQuery(spec: QuerySpec): Promise<ExecuteResponse> {
  return request<ExecuteResponse>("/api/v2/query/execute", {
    method: "POST",
    body: JSON.stringify(spec),
  });
}

export function listDashboards(): Promise<{ dashboards: DashboardRecord[] }> {
  return request<{ dashboards: DashboardRecord[] }>("/api/v2/dashboards");
}

export async function saveDashboard(
  title: string,
  layout: unknown,
  queries?: unknown,
  id?: string,
): Promise<{ id: string }> {
  const payload = {
    title,
    description: "Saved analytics dashboard.",
    layout,
    queries: queries || [],
  };
  return request<{ id: string }>(id ? `/api/v2/dashboards/${id}` : "/api/v2/dashboards", {
    method: id ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteDashboard(id: string): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/api/v2/dashboards/${id}`, { method: "DELETE" });
}

function parseJsonField<T>(value: unknown): T | null {
  if (typeof value === "string") {
    try {
      return JSON.parse(value) as T;
    } catch {
      return null;
    }
  }
  return (value as T) ?? null;
}

export function parseWidgets(record: DashboardRecord): WidgetSpec[] {
  const queries = parseJsonField<WidgetSpec[]>(record.queries_json);
  const layout = parseJsonField<{ widgets?: WidgetSpec[] }>(record.layout_json);
  const raw = (Array.isArray(queries) && queries.length ? queries : layout?.widgets) || [];
  return raw
    .filter((w) => w && typeof w.metric === "string")
    .map((w) => ({
      metric: w.metric,
      title: w.title || w.metric,
      viz: (["card", "bar", "line", "table"] as const).includes(w.viz as Viz) ? w.viz : "table",
      filters: w.filters && typeof w.filters === "object" ? w.filters : {},
      span: w.span === 2 || w.span === 3 ? w.span : 1,
    }));
}
