import type { ConnectorQueueMessage } from "../../shared/contracts.ts";
import { PermanentConnectorError, processConnectorRequest } from "../../shared/queue.ts";

interface Env {
	V2_BUCKET: R2Bucket;
	V2_CONNECTOR_TOKEN: string;
	SPIDER_API_KEY: SecretsStoreSecret;
	WEBSHARE_PROXY_URL: SecretsStoreSecret;
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

// TODO(connector): restrict seeds to your court's host(s); keep https + no credentials.
function isSeed(value: string): boolean {
	try {
		const url = new URL(value);
		return url.protocol === "https:" && url.hostname === "records.example-court.gov" && !url.username && !url.password;
	} catch {
		return false;
	}
}

// TODO(connector): canonicalize /record/{id} URLs so reruns dedupe.
function canonicalUrl(value: string): string | null {
	try {
		const url = new URL(value);
		if (url.protocol !== "https:" || url.hostname !== "records.example-court.gov") return null;
		const match = url.pathname.match(/^\/record\/([a-z0-9]+)\/?$/i);
		return match ? `https://records.example-court.gov/record/${match[1].toLowerCase()}` : null;
	} catch {
		return null;
	}
}

function text(html: string): string {
	return html
		.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
		.replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
		.replace(/<br\s*\/?\s*>/gi, "\n")
		.replace(/<[^>]+>/g, " ")
		.replace(/\s+/g, " ")
		.trim();
}

async function sha256(value: string): Promise<string> {
	const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
	return [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function spiderHtml(url: string, env: Env): Promise<string> {
	const [apiKey, proxyUrl] = await Promise.all([env.SPIDER_API_KEY.get(), env.WEBSHARE_PROXY_URL.get()]);
	if (!apiKey || !proxyUrl) throw new PermanentConnectorError("Spider and proxy secrets are required");
	const response = await fetch("https://api.spider.cloud/unlimited/scrape", {
		method: "POST",
		headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
		body: JSON.stringify({
			url,
			return_format: "raw",
			return_json_data: false,
			return_page_links: false,
			metadata: true,
			cache: false,
			session: false,
			return_cookies: false,
			remote_proxy: proxyUrl,
		}),
	});
	if (!response.ok) {
		const ErrorType = response.status === 429 || response.status >= 500 ? Error : PermanentConnectorError;
		throw new ErrorType(`Spider returned HTTP ${response.status}`);
	}
	const pages = await response.json() as Array<{ status?: number; content?: string }>;
	// TODO(connector): Spider returns a page list; adjust if your plan shape differs.
	const html = pages.find((page) => page.status === 200 && page.content)?.content ?? "";
	if (!html) throw new PermanentConnectorError("Spider returned no usable page content");
	return html;
}

async function discover(request: Request, env: Env): Promise<Response> {
	let body: Record<string, unknown>;
	try { body = await request.json() as Record<string, unknown>; } catch { return json({ error: "valid JSON required" }, 400); }
	const runId = body.run_id;
	const environmentId = body.environment_id;
	const seeds = body.seeds;
	if (typeof runId !== "string" || !/^[0-9a-f-]{36}$/i.test(runId) || typeof environmentId !== "string") {
		return json({ error: "run_id and environment_id required" }, 400);
	}
	// TODO(connector): after extending shared/contracts.ts, switch to parseRunRequest.
	if (!Array.isArray(seeds) || seeds.length < 1 || seeds.length > 20 || !seeds.every((s) => typeof s === "string" && isSeed(s))) {
		return json({ error: "seeds[1..20] on the court host required" }, 400);
	}
	const urls = [...new Set((seeds as string[]).map((seed) => canonicalUrl(seed)).filter((url): url is string => Boolean(url)))];
	const items: ConnectorQueueMessage[] = urls.map((url) => ({
		connector: "legal-research",
		url,
		source_url: url,
		kind: "record",
		run_id: runId,
		environment_id: environmentId,
		item_id: "pending",
	} as ConnectorQueueMessage));
	return json({ items, discovered_count: items.length, total_available: items.length, truncated: false });
}

async function processRecord(item: ConnectorQueueMessage, env: Env): Promise<string> {
	// TODO(connector): validate against your canonical record URL shape.
	if (!canonicalUrl(item.url)) throw new PermanentConnectorError("Invalid record URL");
	const html = await spiderHtml(item.url, env);
	const plain = text(html).slice(0, 50_000);
	// TODO(connector): extract case number, court, parties, dates; mark complete only when required fields exist.
	const record = {
		schema_version: 1,
		source_url: item.url,
		collected_at: new Date().toISOString(),
		parser_version: "1.0.0",
		complete: false,
		limitations: ["Template stub: field extraction is not implemented."],
		provenance: { method: "spider_unlimited_scrape", proxy_requested: true },
		data: { raw_text: plain },
	};
	const serialized = JSON.stringify(record);
	const digest = await sha256(serialized);
	const path = `harvy-ql/raw/legal/court-records/example/${item.run_id}/${digest.slice(0, 16)}.json`;
	await env.V2_BUCKET.put(path, serialized, {
		httpMetadata: { contentType: "application/json" },
		customMetadata: { sha256: digest, run_id: item.run_id },
	});
	return path;
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		if (url.pathname === "/health" && request.method === "GET") return json({ status: "ok", connector: "legal-research" });
		if (url.pathname === "/v2/discover" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return discover(request, env);
		}
		if (url.pathname === "/v2/process" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return processConnectorRequest(request, "legal-research", (item) => processRecord(item, env));
		}
		return json({ error: "not found" }, 404);
	},
} satisfies ExportedHandler<Env>;
