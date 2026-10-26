import {
	isTruthSocialHandle,
	truthSocialProfileUrl,
	type ConnectorQueueMessage,
	type DiscoveredItem,
	type TruthSocialArtifact,
	type TruthSocialPost,
} from "../../shared/contracts.ts";
import { consumeWorkItem, PermanentConnectorError } from "../../shared/queue.ts";
import { publishWorkItemEvent, type K2Producer } from "../../shared/events.ts";

interface Env {
	V2_DB: D1Database;
	V2_BUCKET: R2Bucket;
	SPIDER_API_KEY: string;
	WEBSHARE_PROXY_URL: string;
	V2_CONNECTOR_TOKEN: string;
	V2_EVENTS: K2Producer;
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
	const expected = env.V2_CONNECTOR_TOKEN ?? "";
	const supplied = request.headers.get("Authorization") ?? "";
	let mismatch = expected.length ^ supplied.length;
	for (let i = 0; i < Math.max(expected.length, supplied.length); i++) mismatch |= (expected.charCodeAt(i) || 0) ^ (supplied.charCodeAt(i) || 0);
	return Boolean(expected) && mismatch === 0;
}

function collectObjects(value: unknown, output: Record<string, unknown>[] = [], seen = new Set<object>()): Record<string, unknown>[] {
	if (!value || typeof value !== "object" || seen.has(value)) return output;
	seen.add(value);
	if (Array.isArray(value)) {
		for (const item of value) collectObjects(item, output, seen);
	} else {
		const record = value as Record<string, unknown>;
		output.push(record);
		for (const child of Object.values(record)) collectObjects(child, output, seen);
	}
	return output;
}

function jsonFromContent(content: unknown): unknown[] {
	if (typeof content !== "string") return [];
	const pre = content.match(/<pre\b[^>]*>([\s\S]*?)<\/pre>/i)?.[1] ?? content;
	const candidate = pre.trim();
	try {
		return [JSON.parse(candidate) as unknown];
	} catch {
		return [];
	}
}

function pageObjects(pages: SpiderPage[]): Record<string, unknown>[] {
	const values: unknown[] = [];
	for (const page of pages) {
		values.push(page.json_data, ...jsonFromContent(page.content));
	}
	return collectObjects(values);
}

async function spider(url: string, env: Env): Promise<SpiderPage[]> {
	if (!env.SPIDER_API_KEY || !env.WEBSHARE_PROXY_URL) throw new PermanentConnectorError("Spider and proxy secrets are required");
	const response = await fetch("https://api.spider.cloud/unlimited/scrape", {
		method: "POST",
		headers: { Authorization: `Bearer ${env.SPIDER_API_KEY}`, "Content-Type": "application/json" },
		body: JSON.stringify({
			url,
			return_format: "raw",
			return_json_data: true,
			return_page_links: true,
			metadata: true,
			cache: false,
			session: false,
			return_cookies: false,
			remote_proxy: env.WEBSHARE_PROXY_URL,
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

function goodPages(pages: SpiderPage[]): SpiderPage[] {
	return pages.filter((page) => page.status === 200 && !page.error);
}

export function extractAccount(pages: SpiderPage[], requestedHandle: string): Record<string, unknown> {
	const handle = requestedHandle.replace(/^@/, "").toLowerCase();
	const account = pageObjects(goodPages(pages)).find((node) => {
		const accountName = String(node.acct ?? node.username ?? "").replace(/^@/, "").split("@")[0].toLowerCase();
		return accountName === handle && node.id !== undefined && node.id !== null;
	});
	if (!account) throw new PermanentConnectorError("Truth Social account was not found in the public lookup response");
	return account;
}

export function extractTruthSocialPosts(pages: SpiderPage[], profileUrl: string, maxPosts: number): TruthSocialPost[] {
	const expectedUrl = profileUrl.replace(/\/$/, "").toLowerCase();
	const posts = new Map<string, TruthSocialPost>();
	for (const node of pageObjects(goodPages(pages))) {
		const account = node.account;
		if (!account || typeof account !== "object" || !node.id || typeof node.content !== "string") continue;
		const authorUrl = (account as Record<string, unknown>).url;
		if (typeof authorUrl !== "string" || authorUrl.replace(/\/$/, "").toLowerCase() !== expectedUrl) continue;
		const id = String(node.id);
		posts.set(id, {
			id,
			url: typeof node.url === "string" ? node.url : `${profileUrl}/posts/${encodeURIComponent(id)}`,
			text_html: node.content,
			timestamp: typeof node.created_at === "string" ? node.created_at : null,
			like_count: typeof node.favourites_count === "number" ? node.favourites_count : null,
			repost_count: typeof node.reblogs_count === "number" ? node.reblogs_count : null,
			reply_count: typeof node.replies_count === "number" ? node.replies_count : null,
			ownership_verified: true,
			platform: "truthsocial",
			source: profileUrl,
		});
		if (posts.size >= maxPosts) break;
	}
	return [...posts.values()];
}

function publicProfile(account: Record<string, unknown>, url: string, posts: TruthSocialPost[]): Record<string, unknown> {
	const profileFields = ["username", "acct", "display_name", "note", "url", "avatar", "header", "followers_count", "following_count", "statuses_count", "created_at"];
	const profile: Record<string, unknown> = { platform: "truthsocial", kind: "profile", url };
	for (const field of profileFields) if (account[field] !== undefined) profile[field] = account[field];
	return {
		...profile,
		title: account.display_name ?? "",
		description: account.note ?? "",
		posts,
		bio_links: [],
		status: 200,
		complete: false,
		login_wall_detected: false,
		availability: posts.length ? "public_records" : "unverified_shell",
		limitation: "Public timeline capture only; no logged-in cookies, follower lists, or classified bio links are collected.",
	};
}

async function discover(request: Request): Promise<Response> {
	let body: Record<string, unknown>;
	try { body = await request.json() as Record<string, unknown>; } catch { return json({ error: "valid JSON required" }, 400); }
	const handles = body.handles;
	const maxPosts = body.max_posts ?? 25;
	if (!Array.isArray(handles) || handles.length < 1 || handles.length > 20 || !handles.every((handle) => typeof handle === "string" && isTruthSocialHandle(handle))) {
		return json({ error: "handles must contain 1-20 valid Truth Social handles" }, 400);
	}
	if (!Number.isInteger(maxPosts) || (maxPosts as number) < 1 || (maxPosts as number) > 40) return json({ error: "max_posts must be 1-40" }, 400);
	if (typeof body.run_id !== "string" || typeof body.environment_id !== "string") return json({ error: "run_id and environment_id required" }, 400);
	const uniqueHandles = [...new Set((handles as string[]).map((handle) => handle.replace(/^@/, "").toLowerCase()))];
	const items: DiscoveredItem[] = uniqueHandles.map((handle) => {
		const url = truthSocialProfileUrl(handle)!;
		return {
			connector: "truthsocial",
			url,
			source_url: url,
			kind: "profile",
			run_id: body.run_id as string,
			environment_id: body.environment_id as string,
			options: { max_posts: maxPosts as number },
		};
	});
	return json({ items, result_count: items.length });
}

async function fetchAndStoreProfile(item: ConnectorQueueMessage, env: Env): Promise<string> {
	const handle = item.url.match(/^https:\/\/truthsocial\.com\/@([A-Za-z0-9_.-]+)$/i)?.[1];
	if (item.kind !== "profile" || item.connector !== "truthsocial" || !handle || truthSocialProfileUrl(handle) !== item.url) {
		throw new PermanentConnectorError("Invalid Truth Social profile work item");
	}
	const maxPosts = item.options?.max_posts ?? 25;
	if (!Number.isInteger(maxPosts) || maxPosts < 1 || maxPosts > 40) throw new PermanentConnectorError("Invalid public timeline limit");
	const lookupUrl = `https://truthsocial.com/api/v1/accounts/lookup?acct=${encodeURIComponent(handle)}`;
	const lookupPages = await spider(lookupUrl, env);
	if (!goodPages(lookupPages).length) throw new Error("Truth Social account lookup returned no successful page");
	const account = extractAccount(lookupPages, handle);
	const accountId = String(account.id);
	const statusesUrl = `https://truthsocial.com/api/v1/accounts/${encodeURIComponent(accountId)}/statuses?limit=${maxPosts}`;
	const statusPages = await spider(statusesUrl, env);
	if (!goodPages(statusPages).length) throw new Error("Truth Social timeline returned no successful page");
	const posts = extractTruthSocialPosts(statusPages, item.url, maxPosts);
	const artifact: TruthSocialArtifact = {
		schema_version: 1,
		connector: "truthsocial",
		record_id: accountId,
		source_url: item.url,
		collected_at: new Date().toISOString(),
		parser_version: "1.0.0",
		complete: false,
		limitations: ["Public timeline capture only; no logged-in cookies, follower lists, or classified bio links are collected."],
		provenance: { method: "spider_unlimited_scrape", proxy_requested: true },
		data: {
			platform: "truthsocial",
			handle: `@${handle}`,
			url: item.url,
			account_id: accountId,
			profile: publicProfile(account, item.url, posts),
			posts,
		},
	};
	const serialized = JSON.stringify({ ...artifact, raw: { account_lookup: lookupPages, statuses: statusPages } });
	const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(serialized));
	const digest = [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
	const key = `harvy-ql/raw/social/truthsocial/${new Date().toISOString().slice(0, 10)}/${item.run_id}/${accountId}.json`;
	await env.V2_BUCKET.put(key, serialized, {
		httpMetadata: { contentType: "application/json" },
		customMetadata: { sha256: digest, connector: "truthsocial", schema_version: "1" },
	});
	return key;
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		if (url.pathname === "/health" && request.method === "GET") return json({ status: "ok", connector: "truthsocial", capability_gate: "requires_verified_spider_unlimited_access" });
		if (url.pathname === "/v2/discover" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return discover(request);
		}
		return json({ error: "not found" }, 404);
	},
	queue(batch: MessageBatch<ConnectorQueueMessage>, env: Env, ctx: ExecutionContext): void {
		ctx.waitUntil(Promise.all(batch.messages.map((message) => consumeWorkItem(
			message,
			env.V2_DB,
			"truthsocial",
			(item) => fetchAndStoreProfile(item, env),
			(type, item, payload) => publishWorkItemEvent(env.V2_EVENTS, type, item, payload),
		))));
	},
} satisfies ExportedHandler<Env, ConnectorQueueMessage>;
