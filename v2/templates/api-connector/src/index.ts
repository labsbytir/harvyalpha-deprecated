import type { ConnectorQueueMessage } from "../../shared/contracts.ts";
import { PermanentConnectorError, processConnectorRequest, type WorkItemOutput } from "../../shared/queue.ts";

interface Env {
	V2_BUCKET: R2Bucket;
	V2_CONNECTOR_TOKEN: string;
	// TODO(connector): rename to your provider key, e.g. SOURCE_API_KEY.
	SOURCE_API_KEY: SecretsStoreSecret;
}

// TODO(connector): replace with your source's query input.
interface SourceInput {
	from: string;
	to: string;
	limit?: number;
	max_pages?: number;
}

function json(body: unknown, status = 200): Response {
	return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

function authorized(request: Request, env: Env): boolean {
	const left = request.headers.get("Authorization") ?? "";
	const right = env.V2_CONNECTOR_TOKEN ? `Bearer ${env.V2_CONNECTOR_TOKEN}` : "";
	let mismatch = left.length ^ right.length;
	for (let i = 0; i < Math.max(left.length, right.length); i++) mismatch |= (left.charCodeAt(i) || 0) ^ (right.charCodeAt(i) || 0);
	return Boolean(right) && mismatch === 0;
}

// TODO(connector): validate input bounds, dates, enums; return null on invalid.
function parseInput(body: Record<string, unknown>): SourceInput | null {
	if (typeof body.from !== "string" || typeof body.to !== "string") return null;
	const limit = Number(body.limit ?? 100);
	const maxPages = Number(body.max_pages ?? 10);
	if (!Number.isInteger(limit) || limit < 1 || limit > 100) return null;
	if (!Number.isInteger(maxPages) || maxPages < 1 || maxPages > 25) return null;
	return { from: body.from, to: body.to, limit, max_pages: maxPages };
}

// TODO(connector): build a validated page URL; never embed the API key.
function buildPageUrl(input: SourceInput, offset: number): string {
	const url = new URL("https://api.example.gov/v2/search");
	url.searchParams.set("from", input.from);
	url.searchParams.set("to", input.to);
	url.searchParams.set("limit", String(input.limit ?? 100));
	url.searchParams.set("offset", String(offset));
	return url.toString();
}

// TODO(connector): allowlist host/path/params; reject api_key in URL.
function isPageUrl(value: string): boolean {
	try {
		const url = new URL(value);
		return url.protocol === "https:" && url.hostname === "api.example.gov" && !url.searchParams.has("api_key");
	} catch {
		return false;
	}
}

function redact(value: unknown): unknown {
	if (Array.isArray(value)) return value.map(redact);
	if (value && typeof value === "object") {
		return Object.fromEntries(Object.entries(value as Record<string, unknown>)
			.filter(([key]) => key.toLowerCase() !== "api_key")
			.map(([key, child]) => [key, redact(child)]));
	}
	if (typeof value === "string") return value.replace(/([?&]api_key=)[^&#\s]+/gi, "$1[redacted]");
	return value;
}

function getRows(page: unknown): Record<string, unknown>[] {
	if (!page || typeof page !== "object" || Array.isArray(page)) throw new PermanentConnectorError("Source returned an invalid JSON object");
	const rows = (page as Record<string, unknown>).results ?? (page as Record<string, unknown>).items;
	if (Array.isArray(rows)) return rows.filter((row): row is Record<string, unknown> => Boolean(row) && typeof row === "object");
	if (Number((page as Record<string, unknown>).total) === 0) return [];
	throw new PermanentConnectorError("Source response did not contain a record list");
}

async function sha256(value: string): Promise<string> {
	const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
	return [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function fetchPage(urlString: string, env: Env): Promise<Record<string, unknown>> {
	const apiKey = await env.SOURCE_API_KEY.get();
	if (!apiKey) throw new PermanentConnectorError("SOURCE_API_KEY is not configured");
	if (!isPageUrl(urlString)) throw new PermanentConnectorError("Page URL failed validation");
	// TODO(connector): set key transport per provider (query param vs header).
	const url = new URL(urlString);
	url.searchParams.set("api_key", apiKey);
	const response = await fetch(url, {
		headers: { Accept: "application/json", "User-Agent": "HarvyOpsAgent/1.0" },
		signal: AbortSignal.timeout(30_000),
	});
	if (!response.ok) {
		const ErrorType = response.status === 429 || response.status >= 500 ? Error : PermanentConnectorError;
		throw new ErrorType(`Source returned HTTP ${response.status}`);
	}
	try {
		return redact(await response.json()) as Record<string, unknown>;
	} catch (error) {
		if (error instanceof PermanentConnectorError) throw error;
		throw new PermanentConnectorError("Source returned malformed JSON");
	}
}

async function discover(request: Request, env: Env): Promise<Response> {
	let body: Record<string, unknown>;
	try { body = await request.json() as Record<string, unknown>; } catch { return json({ error: "valid JSON required" }, 400); }
	const runId = body.run_id;
	const environmentId = body.environment_id;
	if (typeof runId !== "string" || !/^[0-9a-f-]{36}$/i.test(runId) || typeof environmentId !== "string") {
		return json({ error: "run_id and environment_id required" }, 400);
	}
	const input = parseInput(body);
	if (!input) return json({ error: "invalid source query" }, 400);
	// TODO(connector): validate all source-specific fields here before discovery.
	const firstUrl = buildPageUrl(input, 0);
	const firstPage = await fetchPage(firstUrl, env);
	const rows = getRows(firstPage);
	const total = Number((firstPage.total as number) ?? rows.length);
	const limit = input.limit ?? 100;
	const pageCount = Math.min(input.max_pages ?? 10, Math.ceil(total / limit));
	const items: ConnectorQueueMessage[] = [];
	for (let offset = 0; offset < pageCount; offset++) {
		items.push({
			connector: "api-connector",
			url: buildPageUrl(input, offset),
			source_url: "https://api.example.gov/v2/search",
			kind: "api_page",
			run_id: runId,
			environment_id: environmentId,
			item_id: "pending",
		} as ConnectorQueueMessage);
	}
	const discovered = Math.min(total, pageCount * limit);
	return json({ items, discovered_count: discovered, total_available: total, truncated: discovered < total });
}

async function processPage(item: ConnectorQueueMessage, env: Env): Promise<WorkItemOutput> {
	if (!isPageUrl(item.url)) throw new PermanentConnectorError("Invalid queue item");
	const page = await fetchPage(item.url, env);
	const raw = JSON.stringify(page);
	const digest = await sha256(raw);
	// TODO(connector): change the R2 prefix to harvy-ql/raw/<family>/<connector>/<run_id>/.
	const rawPath = `harvy-ql/raw/government/example/${item.run_id}/pages/${digest.slice(0, 16)}.source.json`;
	await env.V2_BUCKET.put(rawPath, raw, {
		httpMetadata: { contentType: "application/json" },
		customMetadata: { sha256: digest, run_id: item.run_id },
	});
	const collectedAt = new Date().toISOString();
	let count = 0;
	for (const row of getRows(page)) {
		// TODO(connector): normalize the row; require a stable record id.
		const recordId = String((row as Record<string, unknown>).id ?? await sha256(JSON.stringify(row))).replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 150);
		const record = {
			schema_version: 1,
			record_id: recordId,
			source_url: item.url,
			collected_at: collectedAt,
			parser_version: "1.0.0",
			complete: Boolean((row as Record<string, unknown>).id),
			limitations: [] as string[],
			provenance: { method: "public_api_v2", raw_page_path: rawPath, api_key_redacted: true },
			data: row,
		};
		const serialized = JSON.stringify(record);
		const path = `harvy-ql/raw/government/example/${item.run_id}/records/${recordId}.json`;
		await env.V2_BUCKET.put(path, serialized, {
			httpMetadata: { contentType: "application/json" },
			customMetadata: { sha256: await sha256(serialized), run_id: item.run_id },
		});
		count++;
	}
	const manifest = {
		schema_version: 1, run_id: item.run_id, source_url: item.url,
		raw_page_path: rawPath, record_count: count, collected_at: collectedAt,
	};
	const manifestJson = JSON.stringify(manifest);
	const manifestPath = `harvy-ql/raw/government/example/${item.run_id}/page-manifests/${digest.slice(0, 16)}.json`;
	await env.V2_BUCKET.put(manifestPath, manifestJson, {
		httpMetadata: { contentType: "application/json" },
		customMetadata: { sha256: await sha256(manifestJson), run_id: item.run_id },
	});
	return { artifact_path: manifestPath, record_count: count };
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		if (url.pathname === "/health" && request.method === "GET") return json({ status: "ok", connector: "api-connector" });
		if (url.pathname === "/v2/discover" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return discover(request, env);
		}
		if (url.pathname === "/v2/process" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return processConnectorRequest(request, "api-connector", (item) => processPage(item, env));
		}
		return json({ error: "not found" }, 404);
	},
} satisfies ExportedHandler<Env>;
