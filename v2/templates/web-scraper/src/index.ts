import type { ConnectorQueueMessage } from "../../shared/contracts.ts";
import { PermanentConnectorError, processConnectorRequest } from "../../shared/queue.ts";

interface Env {
	V2_BUCKET: R2Bucket;
	V2_CONNECTOR_TOKEN: string;
	SPIDER_API_KEY: SecretsStoreSecret;
	WEBSHARE_PROXY_URL: SecretsStoreSecret;
}

interface SpiderPage {
	status?: number;
	error?: unknown;
	content?: string;
	json_data?: unknown;
	metadata?: Record<string, unknown>;
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

// TODO(connector): validate/normalize the source handle or profile slug.
function isHandle(value: string): boolean {
	return /^@?[A-Za-z0-9_.-]{1,100}$/.test(value) && !value.includes("..");
}

// TODO(connector): map a handle to its canonical public profile URL.
function profileUrl(handle: string): string | null {
	if (!isHandle(handle)) return null;
	return `https://example-social.com/@${handle.replace(/^@/, "").toLowerCase()}`;
}

async function spider(url: string, env: Env): Promise<SpiderPage[]> {
	const [apiKey, proxyUrl] = await Promise.all([env.SPIDER_API_KEY.get(), env.WEBSHARE_PROXY_URL.get()]);
	if (!apiKey || !proxyUrl) throw new PermanentConnectorError("Spider and proxy secrets are required");
	const response = await fetch("https://api.spider.cloud/unlimited/scrape", {
		method: "POST",
		headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
		body: JSON.stringify({
			url,
			return_format: "raw",
			return_json_data: true,
			return_page_links: true,
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
	const pages = await response.json() as unknown;
	if (!Array.isArray(pages)) throw new Error("Spider returned an invalid page list");
	return pages as SpiderPage[];
}

async function sha256(value: string): Promise<string> {
	const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
	return [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function discover(request: Request, env: Env): Promise<Response> {
	let body: Record<string, unknown>;
	try { body = await request.json() as Record<string, unknown>; } catch { return json({ error: "valid JSON required" }, 400); }
	const runId = body.run_id;
	const environmentId = body.environment_id;
	const handles = body.handles;
	if (typeof runId !== "string" || !/^[0-9a-f-]{36}$/i.test(runId) || typeof environmentId !== "string") {
		return json({ error: "run_id and environment_id required" }, 400);
	}
	// TODO(connector): after extending shared/contracts.ts, switch to parseRunRequest.
	if (!Array.isArray(handles) || handles.length < 1 || handles.length > 20 || !handles.every((h) => typeof h === "string" && isHandle(h))) {
		return json({ error: "handles[1..20] required" }, 400);
	}
	const items: ConnectorQueueMessage[] = (handles as string[])
		.map((handle) => profileUrl(handle))
		.filter((url): url is string => Boolean(url))
		.map((url) => ({
			connector: "web-scraper",
			url,
			source_url: url,
			kind: "profile",
			run_id: runId,
			environment_id: environmentId,
			item_id: "pending",
		} as ConnectorQueueMessage));
	return json({ items, discovered_count: items.length, total_available: items.length, truncated: false });
}

async function processProfile(item: ConnectorQueueMessage, env: Env): Promise<string> {
	const pages = await spider(item.url, env);
	const good = pages.filter((page) => page.status === 200 && !page.error);
	if (!good.length) throw new PermanentConnectorError("Spider returned no usable pages");
	// TODO(connector): parse profile + posts from SSR JSON / OG tags; cap posts (e.g. 25).
	const raw = JSON.stringify(good.map((page) => ({ content: (page.content ?? "").slice(0, 200_000), metadata: page.metadata ?? {} })));
	const digest = await sha256(raw);
	const rawPath = `harvy-ql/raw/social/example/${item.run_id}/profiles/${digest.slice(0, 16)}.source.json`;
	await env.V2_BUCKET.put(rawPath, raw, {
		httpMetadata: { contentType: "application/json" },
		customMetadata: { sha256: digest, run_id: item.run_id },
	});
	const record = {
		schema_version: 1,
		source_url: item.url,
		collected_at: new Date().toISOString(),
		parser_version: "1.0.0",
		complete: false,
		limitations: ["Template stub: post extraction is not implemented."],
		provenance: { method: "spider_unlimited_scrape", proxy_requested: true },
		data: { url: item.url, raw_path: rawPath },
	};
	const serialized = JSON.stringify(record);
	const artifactPath = `harvy-ql/raw/social/example/${item.run_id}/records/${digest.slice(0, 16)}.json`;
	await env.V2_BUCKET.put(artifactPath, serialized, {
		httpMetadata: { contentType: "application/json" },
		customMetadata: { sha256: await sha256(serialized), run_id: item.run_id },
	});
	return artifactPath;
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		if (url.pathname === "/health" && request.method === "GET") return json({ status: "ok", connector: "web-scraper" });
		if (url.pathname === "/v2/discover" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return discover(request, env);
		}
		if (url.pathname === "/v2/process" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return processConnectorRequest(request, "web-scraper", (item) => processProfile(item, env));
		}
		return json({ error: "not found" }, 404);
	},
} satisfies ExportedHandler<Env>;
