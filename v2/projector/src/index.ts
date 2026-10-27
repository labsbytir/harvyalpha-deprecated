import type { PlatformV2Event } from "../../shared/events.ts";

interface AnalyticsDataset {
	writeDataPoint(point: { blobs: string[]; doubles: number[]; indexes: string[] }): void;
}

interface BasinStream {
	send(records: Array<Record<string, unknown>>): Promise<void>;
}

interface Env {
	V2_DB: D1Database;
	V2_CONFIG: KVNamespace;
	V2_BUCKET: R2Bucket;
	V2_BASIN_STREAM: BasinStream;
	V2_ANALYTICS: AnalyticsDataset;
	V2_PUBLIC_ANALYTICS: AnalyticsDataset;
	V2_K2_ENDPOINT: string;
	V2_K2_TOKEN: string;
}

interface K2Record {
	content: string;
	headers?: Record<string, string>;
}

interface K2Batch {
	batch_id: string | null;
	records: K2Record[];
}

const SUBSCRIPTIONS = ["basin", "analytics", "progress"] as const;

function response(body: unknown, status = 200): Response {
	return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

function decodeRecord(content: string): PlatformV2Event | null {
	try {
		const binary = atob(content);
		const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
		const value = JSON.parse(new TextDecoder().decode(bytes)) as Record<string, unknown>;
		if (value.platform !== "v2" || typeof value.event_id !== "string" || typeof value.event_type !== "string" ||
			typeof value.connector !== "string" || typeof value.run_id !== "string" || typeof value.environment_id !== "string" ||
			typeof value.occurred_at !== "string" || !Number.isFinite(Date.parse(value.occurred_at)) ||
			!value.payload || typeof value.payload !== "object" || Array.isArray(value.payload)) return null;
		return value as unknown as PlatformV2Event;
	} catch {
		return null;
	}
}

async function fetchK2(env: Env, path: string, body: Record<string, unknown>): Promise<Record<string, unknown>> {
	const result = await fetch(`${env.V2_K2_ENDPOINT.replace(/\/$/, "")}${path}`, {
		method: "POST",
		headers: { Authorization: `Bearer ${env.V2_K2_TOKEN}`, "Content-Type": "application/json" },
		body: JSON.stringify(body),
	});
	const value = await result.json() as Record<string, unknown>;
	if (!result.ok || value.success === false) throw new Error(`K2 request failed with HTTP ${result.status}`);
	return value;
}

async function projectBasin(env: Env, event: PlatformV2Event): Promise<void> {
	let value: unknown = event;
	const artifactPath = event.payload.artifact_path ?? event.payload.manifest_path;
	if (event.connector === "sam-gov" && event.event_type === "work_item.completed" && typeof artifactPath === "string" &&
		artifactPath.startsWith("harvy-ql/raw/government/sam-gov/") && artifactPath.includes("/page-manifests/")) {
		const object = await env.V2_BUCKET.get(artifactPath);
		if (!object) throw new Error("SAM.gov page manifest referenced by K2 event was not found");
		const manifest = JSON.parse(await object.text()) as { records?: Array<{ artifact_path?: string }> };
		if (!Array.isArray(manifest.records)) throw new Error("SAM.gov page manifest has no record list");
		for (let i = 0; i < manifest.records.length; i += 25) {
			const records = await Promise.all(manifest.records.slice(i, i + 25).map(async (entry) => {
				if (typeof entry.artifact_path !== "string" || !entry.artifact_path.startsWith("harvy-ql/raw/government/sam-gov/") || !entry.artifact_path.includes("/notices/")) {
					throw new Error("SAM.gov page manifest contains an invalid record path");
				}
				const record = await env.V2_BUCKET.get(entry.artifact_path);
				if (!record) throw new Error("SAM.gov normalized record was not found in R2");
				return { value: JSON.parse(await record.text()) as unknown };
			}));
			await env.V2_BASIN_STREAM.send(records);
		}
		return;
	}
	const connectorArtifact = typeof artifactPath === "string" &&
		((event.connector === "judyrecords" && artifactPath.startsWith("harvy-ql/raw/legal/judyrecords/")) ||
		(event.connector === "truthsocial" && artifactPath.startsWith("harvy-ql/raw/social/truthsocial/")) ||
		(event.connector === "sam-gov" && artifactPath.startsWith("harvy-ql/raw/government/sam-gov/")));
	const releaseManifest = event.event_type === "dataset.published" && event.connector === "bulk" && typeof artifactPath === "string" &&
		/^harvy-ql\/processed\/bulk-datasets\/[a-z0-9][a-z0-9_-]{0,63}\/[A-Za-z0-9][A-Za-z0-9._-]{0,63}\/manifest\.json$/.test(artifactPath);
	if (typeof artifactPath === "string" && artifactPath.endsWith(".json") && (connectorArtifact || releaseManifest)) {
		const object = await env.V2_BUCKET.get(artifactPath);
		if (!object) throw new Error("R2 artifact referenced by K2 event was not found");
		value = { ...event, artifact: JSON.parse(await object.text()) as unknown };
	}
	await env.V2_BASIN_STREAM.send([{ value }]);
}

function projectAnalytics(env: Env, event: PlatformV2Event): void {
	const count = Number(event.payload.record_count ?? event.payload.discovered_count ?? 1);
	const elapsed = Number(event.payload.duration_ms ?? 0);
	env.V2_ANALYTICS.writeDataPoint({
		blobs: [event.event_type, event.connector, event.environment_id, "v2"],
		doubles: [Number.isFinite(count) ? count : 1, Number.isFinite(elapsed) ? elapsed : 0],
		indexes: [event.event_id],
	});
}

async function projectPublicProgress(env: Env, event: PlatformV2Event): Promise<void> {
	if (event.environment_id !== "shared" || !["run.discovered", "record.completed", "profile.completed", "work_item.completed", "work_item.failed"].includes(event.event_type)) return;
	const itemCount = event.event_type === "run.discovered" ? Number(event.payload.discovered_count ?? 0) : Number(event.payload.record_count ?? 1);
	if (!Number.isSafeInteger(itemCount) || itemCount < 0) return;
	const inserted = await env.V2_DB.prepare(`
		INSERT OR IGNORE INTO platform_v2_progress_events
		(event_id, connector, event_type, environment_id, occurred_at, item_count)
		VALUES (?, ?, ?, 'shared', ?, ?)
	`).bind(event.event_id, event.connector, event.event_type, Math.floor(Date.parse(event.occurred_at) / 1000), itemCount).run();
	if (inserted.meta.changes > 0) {
		env.V2_PUBLIC_ANALYTICS.writeDataPoint({
			blobs: [event.connector, event.event_type, "shared"],
			doubles: [itemCount],
			indexes: [event.event_id],
		});
	}
}

async function ack(env: Env, subscription: string, batchId: string, workerId: string, action: "ack" | "nack"): Promise<void> {
	await fetchK2(env, `/subscriptions/${subscription}/batches/${batchId}/${action}`, { worker_id: workerId });
}

async function pollSubscription(env: Env, name: typeof SUBSCRIPTIONS[number]): Promise<void> {
	if (!env.V2_K2_TOKEN || !env.V2_K2_ENDPOINT) return;
	const subscription = await env.V2_CONFIG.get(`v2:k2:subscriptions:${name}`);
	if (!subscription) return;
	const workerId = `v2-projector-${name}-${crypto.randomUUID()}`;
	const response = await fetchK2(env, `/subscriptions/${encodeURIComponent(subscription)}/consume`, { worker_id: workerId, max_records: 100 });
	if (response.success !== true || !response.result || typeof response.result !== "object") throw new Error(`K2 ${name} consume failed`);
	const batch = response.result as K2Batch;
	if (!Array.isArray(batch.records) || !batch.records.length || !batch.batch_id) return;
	try {
		for (const record of batch.records) {
			const event = decodeRecord(record.content);
			if (!event) continue;
			if (name === "basin") await projectBasin(env, event);
			else if (name === "analytics") projectAnalytics(env, event);
			else await projectPublicProgress(env, event);
		}
		await ack(env, subscription, batch.batch_id, workerId, "ack");
	} catch (error) {
		await ack(env, subscription, batch.batch_id, workerId, "nack");
		throw error;
	}
}

async function recordBuildEvent(message: Message<unknown>, env: Env): Promise<void> {
	const event = message.body as Record<string, unknown> | null;
	const payload = event?.payload as Record<string, unknown> | undefined;
	const metadata = payload?.buildTriggerMetadata as Record<string, unknown> | undefined;
	const buildId = payload?.buildUuid;
	const eventType = event?.type;
	const workerName = (event?.source as Record<string, unknown> | undefined)?.workerName;
	if (typeof buildId !== "string" || typeof eventType !== "string" || typeof workerName !== "string") {
		message.ack();
		return;
	}
	const occurredAt = Date.parse(String(payload?.stoppedAt ?? payload?.runningAt ?? payload?.createdAt ?? ""));
	const createdAt = Date.parse(String(payload?.createdAt ?? ""));
	const duration = Number.isFinite(occurredAt) && Number.isFinite(createdAt) ? Math.max(0, occurredAt - createdAt) : 0;
	const stored = await env.V2_DB.prepare(`
		INSERT OR IGNORE INTO platform_v2_build_events
		(build_uuid, event_type, worker_name, status, branch, commit_hash, occurred_at, duration_ms)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`).bind(
		buildId,
		eventType,
		workerName,
		String(payload?.status ?? "unknown"),
		String(metadata?.branch ?? ""),
		String(metadata?.commitHash ?? ""),
		Math.floor((Number.isFinite(occurredAt) ? occurredAt : Date.now()) / 1000),
		duration,
	).run();
	if (stored.meta.changes > 0) {
		env.V2_ANALYTICS.writeDataPoint({
			blobs: ["deployment", workerName, eventType, String(payload?.status ?? "unknown")],
			doubles: [1, duration],
			indexes: [buildId],
		});
	}
	message.ack();
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		if (url.pathname === "/health" && request.method === "GET") return response({ status: "ok", worker: "v2-projector" });
		return response({ error: "not found" }, 404);
	},
	scheduled(_controller: ScheduledController, env: Env, ctx: ExecutionContext): void {
		ctx.waitUntil(Promise.all(SUBSCRIPTIONS.map(async (name) => {
			try { await pollSubscription(env, name); }
			catch (error) { console.error(`V2 ${name} projection failed`, error instanceof Error ? error.name : "unknown"); }
		})));
	},
	queue(batch: MessageBatch<unknown>, env: Env, ctx: ExecutionContext): void {
		ctx.waitUntil(Promise.all(batch.messages.map((message) => recordBuildEvent(message, env))));
	},
} satisfies ExportedHandler<Env>;
