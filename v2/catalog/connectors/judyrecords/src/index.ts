import {
	canonicalRecordUrl,
	extractSpiderUrls,
	isJudySeed,
	type DiscoveredItem,
	type JudyRecord,
	type ConnectorQueueMessage,
} from "../../../../shared/contracts.ts";
import { consumeWorkItem, PermanentConnectorError } from "../../../../shared/queue.ts";
import { publishWorkItemEvent, type K2Producer } from "../../../../shared/events.ts";

interface Env {
	V2_DB: D1Database;
	V2_BUCKET: R2Bucket;
	SPIDER_API_KEY: string;
	WEBSHARE_PROXY_URL: string;
	V2_CONNECTOR_TOKEN: string;
	V2_EVENTS: K2Producer;
}

function json(body: unknown, status = 200): Response {
	return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

function authorizedConnector(request: Request, env: Env): boolean {
	const expected = env.V2_CONNECTOR_TOKEN ?? "";
	const supplied = request.headers.get("Authorization") ?? "";
	let mismatch = expected.length ^ supplied.length;
	for (let i = 0; i < Math.max(expected.length, supplied.length); i++) mismatch |= (expected.charCodeAt(i) || 0) ^ (supplied.charCodeAt(i) || 0);
	return Boolean(expected) && mismatch === 0;
}

function text(html: string): string {
	return html
		.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
		.replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
		.replace(/<br\s*\/?\s*>/gi, "\n")
		.replace(/<[^>]+>/g, " ")
		.replace(/&nbsp;|&#160;/gi, " ")
		.replace(/&amp;/gi, "&")
		.replace(/&quot;/gi, '"')
		.replace(/&#39;|&apos;/gi, "'")
		.replace(/&lt;/gi, "<")
		.replace(/&gt;/gi, ">")
		.replace(/\s+/g, " ")
		.trim();
}

function capitalize(value: string): string {
	return value ? value[0].toUpperCase() + value.slice(1) : value;
}

function htmlSection(html: string, className: string): string {
	const heading = new RegExp(`<h2\\b[^>]*class=["'][^"']*\\b${className}\\b[^"']*["'][^>]*>[\\s\\S]*?<\\/h2>`, "i");
	const match = heading.exec(html);
	if (!match) return "";
	const rest = html.slice(match.index + match[0].length);
	return rest.match(/^\s*<p\b[^>]*>[\s\S]*?<\/p>/i)?.[0] ?? "";
}

export function parseJudyRecord(html: string, recordUrl: string, proxyRequested: boolean): JudyRecord {
	const recordId = new URL(recordUrl).pathname.split("/").filter(Boolean).at(-1) ?? "unknown";
	const article = html.match(/<article\b[^>]*class=["'][^"']*\brecord\b[^"']*\bpage\b[^"']*["'][^>]*>([\s\S]*?)<\/article>/i)?.[1] ?? html;
	const content = article.match(/<div\b[^>]*id=["']oscn-content["'][^>]*>([\s\S]*?)<\/div>/i)?.[1] ?? article;
	const plain = text(content);
	const headingHtml = content.match(/<h2\b[^>]*class=["'][^"']*\bstyletop\b[^"']*["'][^>]*>([\s\S]*?)<\/h2>/i)?.[1] ?? "";
	const heading = text(headingHtml);
	const partiesHtml = htmlSection(content, "party");
	const parties = partiesHtml.replace(/<br\s*\/?\s*>/gi, "\n").replace(/<[^>]+>/g, "").split(/\r?\n/)
		.map((line) => line.trim().match(/^(.+?),\s*(Plaintiff|Defendant|Arresting Agency)\s*$/i))
		.filter((match): match is RegExpMatchArray => Boolean(match))
		.map((match) => ({ name: match[1].trim(), role: match[2].toLowerCase().replace(/\s+/g, "_") }));
	const numberMatch = plain.match(/\bNo\.\s*([A-Za-z]{1,5}-\d{4}-\d+[A-Za-z0-9-]*)/i);
	const typeMatch = plain.match(/\bNo\.\s*[A-Za-z0-9-]+\s*\(([^)]+)\)/i);
	const dateMatch = plain.match(/\bFiled:\s*(\d{1,2}\/\d{1,2}\/\d{4})/i);
	const courtMatch = heading.match(/District Court in and for\s+([A-Za-z ]+?\s+County)\s*,\s*([A-Za-z ]+)$/i);
	const title = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] ?? "";
	const closed = /\bClosed:\s*\d{1,2}\/\d{1,2}\/\d{4}/i.test(plain);
	const data = {
		title: text(title),
		case_number: numberMatch?.[1] ?? "",
		court: courtMatch ? `${capitalize(courtMatch[1].trim())}, ${courtMatch[2].trim()} District Court` : "",
		file_date: dateMatch?.[1] ?? "",
		case_type: typeMatch?.[1].trim() ?? "",
		case_status: closed ? "Closed" : "",
		parties,
		raw_text: plain.slice(0, 4000),
	};
	return {
		schema_version: 1,
		connector: "judyrecords",
		record_id: recordId,
		source_url: recordUrl,
		collected_at: new Date().toISOString(),
		parser_version: "1.0.0",
		complete: Boolean(data.case_number && data.case_type),
		limitations: data.case_number ? [] : ["No OSCN case number extracted"],
		provenance: { method: "spider_unlimited_scrape", proxy_requested: proxyRequested },
		data,
	};
}

async function spider(endpoint: "scrape" | "links" | "crawl", payload: Record<string, unknown>, env: Env): Promise<unknown> {
	if (!env.SPIDER_API_KEY || !env.WEBSHARE_PROXY_URL) throw new Error("Spider and proxy secrets are required");
	const response = await fetch(`https://api.spider.cloud/unlimited/${endpoint}`, {
		method: "POST",
		headers: { Authorization: `Bearer ${env.SPIDER_API_KEY}`, "Content-Type": "application/json" },
		body: JSON.stringify({ ...payload, remote_proxy: env.WEBSHARE_PROXY_URL }),
	});
	if (!response.ok) {
		const ErrorType = response.status === 429 || response.status >= 500 ? Error : PermanentConnectorError;
		throw new ErrorType(`Spider returned HTTP ${response.status}`);
	}
	return response.json();
}

function pageHtml(value: unknown): string | null {
	if (Array.isArray(value)) {
		for (const item of value) {
			const found = pageHtml(item);
			if (found) return found;
		}
	} else if (value && typeof value === "object") {
		const item = value as Record<string, unknown>;
		for (const key of ["content", "html", "raw"])
			if (typeof item[key] === "string" && /<html|<article|oscn-content/i.test(item[key] as string)) return item[key] as string;
		for (const child of Object.values(item)) {
			const found = pageHtml(child);
			if (found) return found;
		}
	}
	return null;
}

async function discover(request: Request, env: Env): Promise<Response> {
	let body: Record<string, unknown>;
	try { body = await request.json() as Record<string, unknown>; } catch { return json({ error: "valid JSON required" }, 400); }
	const seeds = body.seeds;
	const mode = body.mode ?? "links";
	const limit = body.limit ?? 50;
	if (!Array.isArray(seeds) || seeds.length < 1 || seeds.length > 20 || !seeds.every((seed) => typeof seed === "string" && isJudySeed(seed))) {
		return json({ error: "seeds must contain 1-20 JudyRecords HTTPS URLs" }, 400);
	}
	if ((mode !== "links" && mode !== "crawl") || !Number.isInteger(limit) || (limit as number) < 1 || (limit as number) > 100) {
		return json({ error: "invalid discovery mode or limit" }, 400);
	}
	if (typeof body.run_id !== "string" || typeof body.environment_id !== "string") return json({ error: "run_id and environment_id required" }, 400);
	const urls = new Map<string, string>();
	for (const seed of seeds as string[]) {
		const result = await spider(mode, mode === "links"
			? { url: seed, limit }
			: { url: seed, limit, depth: 1, request: "http" }, env);
		for (const found of extractSpiderUrls(result)) {
			const recordUrl = canonicalRecordUrl(found);
			if (recordUrl && !urls.has(recordUrl)) urls.set(recordUrl, seed);
			if (urls.size >= (limit as number)) break;
		}
		if (urls.size >= (limit as number)) break;
	}
	const items: DiscoveredItem[] = [...urls].map(([url, source_url]) => ({
		connector: "judyrecords", url, source_url, kind: "record",
		run_id: body.run_id as string, environment_id: body.environment_id as string,
	}));
	return json({ items, result_count: items.length, mode });
}

async function fetchAndStoreRecord(item: ConnectorQueueMessage, env: Env): Promise<string> {
	if (item.kind !== "record" || !isJudySeed(item.source_url) || canonicalRecordUrl(item.url) !== item.url) {
		throw new PermanentConnectorError("Invalid JudyRecords work item");
	}
	const result = await spider("scrape", {
		url: item.url, request: "http", return_format: "raw", metadata: true, cache: false,
	}, env);
	const html = pageHtml(result);
	if (!html) throw new Error("Spider response did not contain record HTML");
	const record = parseJudyRecord(html, item.url, true);
	const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(record)));
	const digest = [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
	const key = `harvy-ql/raw/legal/judyrecords/${new Date().toISOString().slice(0, 10)}/${item.run_id}/${record.record_id}.json`;
	await env.V2_BUCKET.put(key, JSON.stringify(record), {
		httpMetadata: { contentType: "application/json" },
		customMetadata: { sha256: digest, connector: "judyrecords", schema_version: "1" },
	});
	return key;
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		if (url.pathname === "/health" && request.method === "GET") return json({ status: "ok", connector: "judyrecords" });
		if (url.pathname === "/v2/discover" && request.method === "POST") {
			if (!authorizedConnector(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return discover(request, env);
		}
		return json({ error: "not found" }, 404);
	},
	queue(batch: MessageBatch<ConnectorQueueMessage>, env: Env, ctx: ExecutionContext): void {
		ctx.waitUntil(Promise.all(batch.messages.map((message) => consumeWorkItem(
			message,
			env.V2_DB,
			"judyrecords",
			(item) => fetchAndStoreRecord(item, env),
			(type, item, payload) => publishWorkItemEvent(env.V2_EVENTS, type, item, payload),
		))));
	},
} satisfies ExportedHandler<Env, ConnectorQueueMessage>;
