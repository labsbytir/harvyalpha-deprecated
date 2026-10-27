import { WorkflowEntrypoint, WorkerEntrypoint, type WorkflowEvent, type WorkflowStep } from "cloudflare:workers";
import {
	makeWorkItemId,
	parseRunRequest,
	type ConnectorId,
	type DiscoveredItem,
	type ConnectorQueueMessage,
	type RunRequest,
} from "../../shared/contracts.ts";
import { createPlatformV2Event, publishPlatformV2Event, publishWorkItemEvent, type K2Producer } from "../../shared/events.ts";
import { parseDatasetRelease } from "../../shared/release-manifest.ts";
import { consumeWorkItem, PermanentConnectorError, type WorkItemOutput } from "../../shared/queue.ts";
import connectorScopes from "../../catalog/connector-scopes.json";

interface Env {
	V2_DB: D1Database;
	V2_CONFIG: KVNamespace;
	V2_BUCKET: R2Bucket;
	V2_WORK_QUEUE: Queue<ConnectorQueueMessage>;
	V2_CONNECTORS: DispatchNamespace;
	V2_RUN_WORKFLOW: Workflow<RunWorkflowParams>;
	V2_SUPERVISOR_TOKEN: string;
	V2_CONNECTOR_TOKEN: string;
	V2_EVENTS: K2Producer;
	V2_ACCOUNT_ID: string;
	V2_ANALYTICS_READ_TOKEN: string;
}

interface PublicProgressExport {
	fetch(request: Request): Promise<Response>;
}

export interface RunWorkflowParams {
	run_id: string;
	connector: ConnectorId;
	environment_id: string;
	requested_by: string;
	input: RunRequest["input"];
}

function json(body: unknown, status = 200): Response {
	return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

function constantTimeEqual(left: string, right: string): boolean {
	let mismatch = left.length ^ right.length;
	const length = Math.max(left.length, right.length);
	for (let i = 0; i < length; i++) mismatch |= (left.charCodeAt(i) || 0) ^ (right.charCodeAt(i) || 0);
	return mismatch === 0;
}

function authorized(request: Request, env: Env): boolean {
	if (!env.V2_SUPERVISOR_TOKEN) return false;
	return constantTimeEqual(request.headers.get("Authorization") ?? "", `Bearer ${env.V2_SUPERVISOR_TOKEN}`);
}

interface ConnectorRegistration {
	id: string;
	enabled: number;
	capability_verified: number;
}

async function connectorRegistration(db: D1Database, id: string): Promise<ConnectorRegistration | null> {
	return db.prepare("SELECT id, enabled, capability_verified FROM platform_v2_connectors WHERE id = ?")
		.bind(id).first<ConnectorRegistration>();
}

async function processDispatchedItem(item: ConnectorQueueMessage, env: Env): Promise<WorkItemOutput> {
	if (!await connectorRegistration(env.V2_DB, item.connector)) throw new PermanentConnectorError("connector is not registered");
	const response = await env.V2_CONNECTORS.get(`harvy-${item.connector}`).fetch("https://connector/v2/process", {
		method: "POST",
		headers: { "Content-Type": "application/json", Authorization: `Bearer ${env.V2_CONNECTOR_TOKEN}` },
		body: JSON.stringify(item),
	});
	if (response.status === 400 || response.status === 422) throw new PermanentConnectorError("connector rejected work item");
	if (!response.ok) throw new Error(`connector processing returned HTTP ${response.status}`);
	const output = await response.json() as WorkItemOutput;
	if (!output || typeof output.artifact_path !== "string" || !output.artifact_path ||
		(output.record_count !== undefined && (!Number.isSafeInteger(output.record_count) || output.record_count < 0))) {
		throw new Error("connector returned an invalid artifact");
	}
	return output;
}

async function publishDatasetRelease(request: Request, env: Env): Promise<Response> {
	let body: unknown;
	try { body = await request.json(); } catch { return json({ error: "valid JSON required" }, 400); }
	const parsed = parseDatasetRelease(body);
	if (!parsed) return json({ error: "invalid dataset release manifest" }, 400);
	const prefix = `harvy-ql/processed/bulk-datasets/${parsed.dataset}/${parsed.release}/`;
	for (const file of parsed.files) {
		if (!file.path.startsWith(prefix)) return json({ error: "file path is outside this release" }, 400);
		const object = await env.V2_BUCKET.head(file.path);
		if (!object) return json({ error: "release file not found" }, 400);
		if (object.size !== file.bytes || object.customMetadata?.sha256?.toLowerCase() !== file.sha256) {
			return json({ error: "release file size or SHA-256 does not match R2 metadata" }, 409);
		}
	}
	const manifestPath = `${prefix}manifest.json`;
	const before = await env.V2_DB.prepare(`
		SELECT manifest_sha256, created_at, manifest_path FROM platform_v2_dataset_releases
		WHERE environment_id = ? AND dataset = ? AND release = ?
	`).bind(parsed.environment_id, parsed.dataset, parsed.release).first<{ manifest_sha256: string; created_at: number }>();
	if (before?.manifest_sha256 !== undefined && before.manifest_sha256 !== "pending" && !/^[a-f0-9]{64}$/.test(before.manifest_sha256)) {
		return json({ error: "release manifest state is invalid" }, 500);
	}
	await env.V2_DB.prepare(`
		INSERT OR IGNORE INTO platform_v2_dataset_releases
		(environment_id, dataset, release, visibility, record_count, manifest_path, manifest_sha256, created_at)
		VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
	`).bind(parsed.environment_id, parsed.dataset, parsed.release, parsed.visibility, parsed.record_count, manifestPath, Date.now()).run();
	const stored = await env.V2_DB.prepare(`
		SELECT manifest_sha256, created_at, manifest_path FROM platform_v2_dataset_releases
		WHERE environment_id = ? AND dataset = ? AND release = ?
	`).bind(parsed.environment_id, parsed.dataset, parsed.release).first<{ manifest_sha256: string; created_at: number; manifest_path: string }>();
	if (!stored || stored.manifest_path !== manifestPath) return json({ error: "release state unavailable" }, 503);
	if (stored.manifest_sha256 !== "pending" && !/^[a-f0-9]{64}$/.test(stored.manifest_sha256)) return json({ error: "release manifest state is invalid" }, 500);
	const manifest = { schema_version: 1 as const, ...parsed, created_at: new Date(stored.created_at).toISOString() };
	const manifestBytes = JSON.stringify(manifest);
	const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(manifestBytes));
	const manifestSha = [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
	if (stored.manifest_sha256 !== "pending" && stored.manifest_sha256 !== manifestSha) {
		return json({ error: "release is immutable and already exists with different content" }, 409);
	}
	await env.V2_DB.prepare(`
		UPDATE platform_v2_dataset_releases SET manifest_sha256 = ?
		WHERE environment_id = ? AND dataset = ? AND release = ? AND manifest_sha256 = 'pending'
	`).bind(manifestSha, parsed.environment_id, parsed.dataset, parsed.release).run();
	const finalized = await env.V2_DB.prepare(`
		SELECT manifest_sha256 FROM platform_v2_dataset_releases
		WHERE environment_id = ? AND dataset = ? AND release = ?
	`).bind(parsed.environment_id, parsed.dataset, parsed.release).first<{ manifest_sha256: string }>();
	if (finalized?.manifest_sha256 !== manifestSha) return json({ error: "release is immutable and already exists with different content" }, 409);
	const prior = await env.V2_BUCKET.head(manifestPath);
	if (prior && prior.customMetadata?.sha256 !== manifestSha) return json({ error: "existing release manifest hash does not match" }, 409);
	if (!prior) {
		await env.V2_BUCKET.put(manifestPath, manifestBytes, {
			httpMetadata: { contentType: "application/json" },
			customMetadata: { sha256: manifestSha, visibility: parsed.visibility },
		});
	}
	const event = await createPlatformV2Event("dataset.published", "bulk", `release:${parsed.dataset}:${parsed.release}`, parsed.environment_id,
		manifestSha, { dataset: parsed.dataset, release: parsed.release, record_count: parsed.record_count, manifest_path: manifestPath });
	await publishPlatformV2Event(env.V2_EVENTS, event);
	return json({ dataset: parsed.dataset, release: parsed.release, manifest_path: manifestPath, sha256: manifestSha }, before ? 200 : 201);
}

function cachedJson(body: unknown, tags: string): Response {
	return Response.json(body, {
		headers: {
			"Cache-Control": "public, max-age=300, stale-while-revalidate=300",
			"Cache-Tag": tags,
		},
	});
}

async function publicProgress(env: Env, days: number): Promise<Record<string, unknown>> {
	if (env.V2_ACCOUNT_ID && env.V2_ANALYTICS_READ_TOKEN) {
		try {
			const query = `SELECT blob1 AS connector, SUM(CASE WHEN blob2 = 'run.discovered' THEN _sample_interval * double1 ELSE 0 END) AS discovered, SUM(CASE WHEN blob2 IN ('record.completed', 'profile.completed', 'work_item.completed') THEN _sample_interval * double1 ELSE 0 END) AS completed, SUM(CASE WHEN blob2 = 'work_item.failed' THEN _sample_interval * double1 ELSE 0 END) AS failed FROM harvy_v2_public_progress WHERE timestamp >= NOW() - INTERVAL '${days}' DAY AND blob3 = 'shared' GROUP BY connector FORMAT JSON`;
			const result = await fetch(`https://api.cloudflare.com/client/v4/accounts/${encodeURIComponent(env.V2_ACCOUNT_ID)}/analytics_engine/sql`, {
				method: "POST",
				headers: { Authorization: `Bearer ${env.V2_ANALYTICS_READ_TOKEN}`, "Content-Type": "text/plain" },
				body: query,
			});
			if (!result.ok) throw new Error(`Analytics Engine query returned HTTP ${result.status}`);
			const data = await result.json() as { data?: Array<Record<string, unknown>> };
			if (!Array.isArray(data.data)) throw new Error("Analytics Engine returned an invalid aggregate result");
			return { period_days: days, source: "analytics_engine", approximate: true, connectors: data.data };
		} catch {
			// Use the exact D1 projection while the analytics query is unavailable.
		}
	}
	const rows = await env.V2_DB.prepare(`
		SELECT connector,
			SUM(CASE WHEN event_type = 'run.discovered' THEN item_count ELSE 0 END) AS discovered,
			SUM(CASE WHEN event_type IN ('record.completed', 'profile.completed', 'work_item.completed') THEN item_count ELSE 0 END) AS completed,
			SUM(CASE WHEN event_type = 'work_item.failed' THEN item_count ELSE 0 END) AS failed,
			MAX(occurred_at) AS last_event_at
		FROM platform_v2_progress_events
		WHERE environment_id = 'shared' AND occurred_at >= ?
		GROUP BY connector ORDER BY connector
	`).bind(Math.floor(Date.now() / 1000) - days * 86400).all();
	return { period_days: days, source: "d1", approximate: false, connectors: rows.results ?? [] };
}

export class PublicProgress extends WorkerEntrypoint<Env> {
	async fetch(request: Request): Promise<Response> {
		const url = new URL(request.url);
		if (request.method === "GET" && url.pathname === "/api/public/progress") {
			const days = Number(url.searchParams.get("days") ?? "7");
			if (![1, 7, 30].includes(days)) return json({ error: "days must be 1, 7, or 30" }, 400);
			return cachedJson(await publicProgress(this.env, days), "v2-progress");
		}
		const manifestMatch = url.pathname.match(/^\/api\/public\/datasets\/([a-z0-9][a-z0-9_-]{0,63})\/([A-Za-z0-9][A-Za-z0-9._-]{0,63})\/manifest$/);
		if (request.method === "GET" && manifestMatch) {
			const release = await this.env.V2_DB.prepare(`
				SELECT manifest_path FROM platform_v2_dataset_releases
				WHERE environment_id = 'shared' AND visibility = 'public' AND dataset = ? AND release = ?
			`).bind(manifestMatch[1], manifestMatch[2]).first<{ manifest_path: string }>();
			if (!release) return json({ error: "not found" }, 404);
			const object = await this.env.V2_BUCKET.get(release.manifest_path);
			if (!object) return json({ error: "not found" }, 404);
			return new Response(object.body, {
				headers: {
					"Content-Type": "application/json",
					"Cache-Control": "public, max-age=300, stale-while-revalidate=300",
					"Cache-Tag": `v2-dataset-${manifestMatch[1]}-${manifestMatch[2]}`,
				},
			});
		}
		return json({ error: "not found" }, 404);
	}
}

export class PlatformV2RunWorkflow extends WorkflowEntrypoint<Env, RunWorkflowParams> {
	async run(event: WorkflowEvent<RunWorkflowParams>, step: WorkflowStep) {
		const params = event.payload;
		await step.do("mark-run-running", async () => {
			await this.env.V2_DB.prepare(
				"UPDATE platform_v2_runs SET status = 'running', updated_at = ? WHERE id = ? AND status = 'queued'",
			).bind(Date.now(), params.run_id).run();
			return { run_id: params.run_id };
		});

		try {
			await step.do("publish-run-started", async () => {
				const event = await createPlatformV2Event("run.started", params.connector, params.run_id, params.environment_id, params.run_id, { run_id: params.run_id });
				await publishPlatformV2Event(this.env.V2_EVENTS, event);
				return { event_id: event.event_id };
			});
			const discovery = await step.do(
				"discover-record-urls",
				{ retries: { limit: 3, delay: "5 seconds", backoff: "exponential" }, timeout: "2 minutes" },
				async () => {
					const response = await this.env.V2_CONNECTORS.get(`harvy-${params.connector}`).fetch("https://connector/v2/discover", {
						method: "POST",
						headers: { "Content-Type": "application/json", Authorization: `Bearer ${this.env.V2_CONNECTOR_TOKEN}` },
						body: JSON.stringify({ ...params.input, run_id: params.run_id, environment_id: params.environment_id }),
					});
					if (!response.ok) throw new Error(`${params.connector} discovery returned HTTP ${response.status}`);
					const body = await response.json() as { items?: DiscoveredItem[]; discovered_count?: number; total_available?: number; truncated?: boolean };
					if (!Array.isArray(body.items) || body.items.length > 1000) throw new Error("Connector returned an invalid discovery result");
					if (body.items.some((item) => !item || item.connector !== params.connector || item.run_id !== params.run_id || item.environment_id !== params.environment_id ||
						typeof item.url !== "string" || typeof item.source_url !== "string" ||
						!item.url.startsWith("https://") || !item.source_url.startsWith("https://") ||
						!["record", "document", "profile", "api_page"].includes(item.kind))) {
						throw new Error("Connector returned work outside the requested run scope");
					}
					return {
						items: body.items,
						discovered_count: Number.isSafeInteger(body.discovered_count) && body.discovered_count! >= 0 ? body.discovered_count! : body.items.length,
						total_available: body.total_available,
						truncated: body.truncated === true,
					};
				},
			);
			await step.do("publish-discovery-result", async () => {
				const event = await createPlatformV2Event("run.discovered", params.connector, params.run_id, params.environment_id, params.run_id, {
					discovered_count: discovery.discovered_count,
					total_available: discovery.total_available,
					truncated: discovery.truncated,
				});
				await publishPlatformV2Event(this.env.V2_EVENTS, event);
				return { event_id: event.event_id };
			});

			const queued = await step.do(
				"persist-and-enqueue-items",
				{ retries: { limit: 3, delay: "5 seconds", backoff: "exponential" }, timeout: "5 minutes" },
				async () => {
					for (const item of discovery.items) {
						const itemId = await makeWorkItemId(item.connector, item.environment_id, params.run_id, item.url);
						const now = Date.now();
						await this.env.V2_DB.prepare(`
							INSERT INTO platform_v2_work_items
							(id, connector, environment_id, run_id, url, source_url, kind, status, created_at, updated_at)
							VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)
							ON CONFLICT(run_id, url) DO NOTHING
						`).bind(itemId, item.connector, item.environment_id, params.run_id, item.url, item.source_url, item.kind, now, now).run();
						await this.env.V2_WORK_QUEUE.send({ ...item, item_id: itemId });
					}
					return { discovered: discovery.items.length, enqueued: discovery.items.length };
				},
			);

			await step.do("finish-run", async () => {
				const wanted = queued.discovered === 0 ? "complete" : "dispatched";
				await this.env.V2_DB.prepare(
					"UPDATE platform_v2_runs SET status = ?, updated_at = ? WHERE id = ? AND status = 'running'",
				).bind(wanted, Date.now(), params.run_id).run();
				const current = await this.env.V2_DB.prepare("SELECT status FROM platform_v2_runs WHERE id = ?")
					.bind(params.run_id).first<{ status: string }>();
				const status = current?.status ?? wanted;
				const event = await createPlatformV2Event(`run.${status}`, params.connector, params.run_id, params.environment_id, params.run_id, queued);
				await publishPlatformV2Event(this.env.V2_EVENTS, event);
				return { run_id: params.run_id, status, ...queued };
			});
			const state = await this.env.V2_DB.prepare("SELECT status FROM platform_v2_runs WHERE id = ?")
				.bind(params.run_id).first<{ status: string }>();
			return { run_id: params.run_id, status: state?.status ?? "dispatched", ...queued };
		} catch (error) {
			await this.env.V2_DB.prepare(`
				UPDATE platform_v2_runs SET status = 'failed', error = ?, updated_at = ?
				WHERE id = ? AND status IN ('queued', 'running')
			`).bind(error instanceof Error ? error.message.slice(0, 300) : "workflow failed", Date.now(), params.run_id).run();
			try {
				const event = await createPlatformV2Event("run.failed", params.connector, params.run_id, params.environment_id, params.run_id, { failure: "workflow_failed" });
				await publishPlatformV2Event(this.env.V2_EVENTS, event);
			} catch {
				console.error("Platform v2 failure event could not be published", params.run_id);
			}
			throw error;
		}
	}
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		const url = new URL(request.url);
		if (request.method === "GET" && url.pathname.startsWith("/api/public/")) {
			const exports = ctx.exports as unknown as { PublicProgress: PublicProgressExport };
			return exports.PublicProgress.fetch(request);
		}
		if (url.pathname === "/health" && request.method === "GET") {
			try {
				await env.V2_DB.prepare("SELECT 1").first();
				return json({ status: "ok", platform: "v2" });
			} catch {
				return json({ status: "degraded", platform: "v2", checks: { d1: "unavailable" } }, 503);
			}
		}
		if (url.pathname === "/v2/connectors" && request.method === "GET") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_SUPERVISOR_TOKEN ? 401 : 503);
			const rows = await env.V2_DB.prepare("SELECT id, enabled, capability_verified FROM platform_v2_connectors ORDER BY id").all<ConnectorRegistration>();
			const connectors = await Promise.all((rows.results ?? []).map(async (connector) => ({
				...connector,
				config: await env.V2_CONFIG.get(`v2:connector:${connector.id}:config`, "json"),
			})));
			return json({ connectors });
		}
		const connectorMatch = url.pathname.match(/^\/v2\/connectors\/([a-z][a-z0-9-]{0,62})$/);
		if (connectorMatch && request.method === "PUT") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_SUPERVISOR_TOKEN ? 401 : 503);
			let body: unknown;
			try { body = await request.json(); } catch { return json({ error: "valid JSON required" }, 400); }
			if (!body || typeof body !== "object" || Array.isArray(body) ||
				typeof (body as Record<string, unknown>).enabled !== "boolean" ||
				typeof (body as Record<string, unknown>).capability_verified !== "boolean") return json({ error: "enabled and capability_verified booleans required" }, 400);
			const { enabled, capability_verified } = body as { enabled: boolean; capability_verified: boolean };
			if (enabled && !capability_verified) return json({ error: "capability must be verified before enabling" }, 409);
			if (enabled) {
				try {
					const health = await env.V2_CONNECTORS.get(`harvy-${connectorMatch[1]}`).fetch("https://connector/health");
					if (!health.ok || (await health.json() as { connector?: string }).connector !== connectorMatch[1]) return json({ error: "connector health identity mismatch" }, 409);
				} catch { return json({ error: "connector is not deployed or healthy" }, 409); }
			}
			const now = Date.now();
			await env.V2_DB.prepare(`INSERT INTO platform_v2_connectors (id, enabled, capability_verified, created_at, updated_at)
				VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET enabled = excluded.enabled,
				capability_verified = excluded.capability_verified, updated_at = excluded.updated_at`)
				.bind(connectorMatch[1], Number(enabled), Number(capability_verified), now, now).run();
			return json({ id: connectorMatch[1], enabled, capability_verified });
		}
		if (url.pathname === "/v2/source-catalog" && request.method === "GET") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_SUPERVISOR_TOKEN ? 401 : 503);
			return json(connectorScopes);
		}
		if (url.pathname === "/v2/releases" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_SUPERVISOR_TOKEN ? 401 : 503);
			return publishDatasetRelease(request, env);
		}
		if (url.pathname === "/v2/runs" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_SUPERVISOR_TOKEN ? 401 : 503);
			let payload: unknown;
			try { payload = await request.json(); } catch { return json({ error: "valid JSON required" }, 400); }
			const runRequest = parseRunRequest(payload);
			if (!runRequest) return json({ error: "invalid run request" }, 400);
			const connectorConfig = await env.V2_CONFIG.get(`v2:connector:${runRequest.connector}:config`, "json") as Record<string, unknown> | null;
			const registration = await connectorRegistration(env.V2_DB, runRequest.connector);
			if (!registration?.enabled || !registration.capability_verified || connectorConfig?.enabled === false) {
				return json({ error: "connector is disabled or its required capability is unverified" }, 409);
			}

			const existing = await env.V2_DB.prepare(`
				SELECT id, status, input_json FROM platform_v2_runs
				WHERE connector = ? AND environment_id = ? AND idempotency_key = ?
			`).bind(runRequest.connector, runRequest.environment_id, runRequest.idempotency_key).first<{ id: string; status: string; input_json: string }>();
			const inputJson = JSON.stringify(runRequest.input);
			if (existing) {
				if (existing.input_json !== inputJson) return json({ error: "idempotency key was already used with different input" }, 409);
				return json({ run_id: existing.id, status: existing.status, deduplicated: true }, 200);
			}

			const runId = crypto.randomUUID();
			const now = Date.now();
			const requestedBy = request.headers.get("X-Harvy-Actor")?.slice(0, 100) || "v2-api";
			try {
				await env.V2_DB.prepare(`
					INSERT INTO platform_v2_runs
					(id, connector, environment_id, requested_by, idempotency_key, input_json, status, created_at, updated_at)
					VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?)
				`).bind(runId, runRequest.connector, runRequest.environment_id, requestedBy, runRequest.idempotency_key,
					inputJson, now, now).run();
			} catch (error) {
				const raced = await env.V2_DB.prepare(`
					SELECT id, status, input_json FROM platform_v2_runs
					WHERE connector = ? AND environment_id = ? AND idempotency_key = ?
				`).bind(runRequest.connector, runRequest.environment_id, runRequest.idempotency_key).first<{ id: string; status: string; input_json: string }>();
				if (raced) {
					if (raced.input_json !== inputJson) return json({ error: "idempotency key was already used with different input" }, 409);
					return json({ run_id: raced.id, status: raced.status, deduplicated: true }, 200);
				}
				console.error("Platform v2 run insert failed", error instanceof Error ? error.name : "unknown");
				return json({ error: "could not create run" }, 503);
			}

			try {
				const workflow = await env.V2_RUN_WORKFLOW.create({
					id: runId,
					params: {
						run_id: runId,
						connector: runRequest.connector,
						environment_id: runRequest.environment_id,
						requested_by: requestedBy,
						input: runRequest.input,
					},
				});
				return json({ run_id: runId, workflow_id: workflow.id, status: "queued" }, 202);
			} catch (error) {
				await env.V2_DB.prepare("UPDATE platform_v2_runs SET status = 'failed', error = ?, updated_at = ? WHERE id = ?")
					.bind("workflow start failed", Date.now(), runId).run();
				console.error("Platform v2 workflow start failed", error instanceof Error ? error.name : "unknown");
				return json({ error: "workflow could not be started", run_id: runId }, 503);
			}
		}
		const runMatch = url.pathname.match(/^\/v2\/runs\/([0-9a-f-]{36})$/i);
		if (runMatch && request.method === "GET") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_SUPERVISOR_TOKEN ? 401 : 503);
			const run = await env.V2_DB.prepare(`
				SELECT id, connector, environment_id, status, error, created_at, updated_at
				FROM platform_v2_runs WHERE id = ?
			`).bind(runMatch[1]).first();
			return run ? json({ run }) : json({ error: "not found" }, 404);
		}
		return json({ error: "not found" }, 404);
	},
	queue(batch: MessageBatch<ConnectorQueueMessage>, env: Env, ctx: ExecutionContext): void {
		ctx.waitUntil(Promise.all(batch.messages.map((message) => consumeWorkItem(
			message, env.V2_DB, message.body?.connector,
			(item) => processDispatchedItem(item, env),
			(type, item, payload) => publishWorkItemEvent(env.V2_EVENTS, type, item, payload),
		))));
	},
} satisfies ExportedHandler<Env, ConnectorQueueMessage>;
