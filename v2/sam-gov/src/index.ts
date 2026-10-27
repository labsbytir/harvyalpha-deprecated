import {
	buildSamGovPageUrl,
	isSamGovPageUrl,
	normalizeSamGovInput,
	type ConnectorQueueMessage,
	type SamGovInput,
} from "../../shared/contracts.ts";
import { PermanentConnectorError, processConnectorRequest, type WorkItemOutput } from "../../shared/queue.ts";

interface Env {
	V2_BUCKET: R2Bucket;
	V2_CONNECTOR_TOKEN: string;
	SAM_GOV_API_KEY: SecretsStoreSecret;
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

export function redactSamGovApiKey(value: unknown): unknown {
	if (Array.isArray(value)) return value.map(redactSamGovApiKey);
	if (value && typeof value === "object") {
		return Object.fromEntries(Object.entries(value as Record<string, unknown>)
			.filter(([key]) => key.toLowerCase() !== "api_key")
			.map(([key, child]) => [key, redactSamGovApiKey(child)]));
	}
	if (typeof value === "string") return value.replace(/([?&]api_key=)[^&#\s]+/gi, "$1[redacted]");
	return value;
}

function getRows(page: unknown): Record<string, unknown>[] {
	if (!page || typeof page !== "object" || Array.isArray(page)) throw new PermanentConnectorError("SAM.gov returned an invalid JSON object");
	const data = page as Record<string, unknown>;
	const rows = data.opportunitiesData ?? data.opportunities ?? data.results;
	if (Array.isArray(rows)) return rows.filter((row): row is Record<string, unknown> => Boolean(row) && typeof row === "object" && !Array.isArray(row));
	if (Number(data.totalRecords ?? data.total_records ?? 0) === 0) return [];
	throw new PermanentConnectorError("SAM.gov response did not contain an opportunity list");
}

function getTotal(page: unknown, rows: Record<string, unknown>[]): number {
	if (!page || typeof page !== "object" || Array.isArray(page)) return rows.length;
	const total = Number((page as Record<string, unknown>).totalRecords ?? (page as Record<string, unknown>).total_records);
	return Number.isSafeInteger(total) && total >= 0 ? total : rows.length;
}

async function fetchSamPage(urlString: string, env: Env): Promise<Record<string, unknown>> {
	const apiKey = await env.SAM_GOV_API_KEY.get();
	if (!apiKey) throw new PermanentConnectorError("SAM_GOV_API_KEY is not configured");
	if (!isSamGovPageUrl(urlString)) throw new PermanentConnectorError("SAM.gov page URL failed validation");
	const url = new URL(urlString);
	url.searchParams.set("api_key", apiKey);
	const response = await fetch(url, {
		headers: { Accept: "application/json", "User-Agent": "HarvyOpsAgent/1.0" },
		signal: AbortSignal.timeout(30_000),
	});
	if (!response.ok) {
		const ErrorType = response.status === 429 || response.status >= 500 ? Error : PermanentConnectorError;
		throw new ErrorType(`SAM.gov returned HTTP ${response.status}`);
	}
	try {
		return redactSamGovApiKey(await response.json()) as Record<string, unknown>;
	} catch (error) {
		if (error instanceof PermanentConnectorError) throw error;
		throw new PermanentConnectorError("SAM.gov returned malformed JSON");
	}
}

async function sha256(value: string): Promise<string> {
	const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
	return [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function stringField(value: unknown): string | null {
	return typeof value === "string" && value.trim() ? value.trim() : null;
}

function safeLink(value: unknown): string | null {
	if (typeof value !== "string") return null;
	try {
		const url = new URL(value);
		return url.protocol === "https:" ? url.toString().replace(/([?&]api_key=)[^&#]+/gi, "$1[redacted]") : null;
	} catch {
		return null;
	}
}

export async function normalizeSamOpportunity(
	row: Record<string, unknown>,
	sourceUrl: string,
	collectedAt: string,
	rawPagePath: string,
): Promise<{ recordId: string; record: Record<string, unknown> }> {
	const data = row.data && typeof row.data === "object" ? row.data as Record<string, unknown> : {};
	const place = data.placeOfPerformance && typeof data.placeOfPerformance === "object" ? data.placeOfPerformance as Record<string, unknown> : {};
	const state = place.state && typeof place.state === "object" ? place.state as Record<string, unknown> : {};
	const city = place.city && typeof place.city === "object" ? place.city as Record<string, unknown> : {};
	const award = data.award && typeof data.award === "object" ? data.award as Record<string, unknown> : {};
	const noticeId = stringField(row.noticeId);
	const stableId = noticeId ?? await sha256(JSON.stringify(row));
	const recordId = stableId.replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 150);
	const links = Array.isArray(row.resourceLinks) ? row.resourceLinks.map(safeLink).filter((link): link is string => Boolean(link)) : [];
	const title = stringField(row.title);
	const record = {
		schema_version: 1,
		connector: "sam-gov",
		record_id: recordId,
		source_url: sourceUrl,
		collected_at: collectedAt,
		parser_version: "1.0.0",
		complete: Boolean(noticeId && title),
		limitations: ["The API returns the latest opportunity version; archived history is not included."],
		provenance: { method: "sam_gov_public_api_v2", raw_page_path: rawPagePath, api_key_redacted: true },
		data: {
			notice_id: noticeId,
			title,
			solicitation_number: stringField(row.solicitationNumber),
			posted_date: stringField(row.postedDate),
			response_deadline: stringField(row.responseDeadLine) ?? stringField(row.reponseDeadLine),
			type: stringField(row.type),
			base_type: stringField(row.baseType),
			archive_type: stringField(row.archiveType),
			archive_date: stringField(row.archiveDate),
			set_aside: stringField(row.setAside),
			set_aside_code: stringField(row.setAsideCode),
			naics_code: stringField(row.naicsCode),
			classification_code: stringField(row.classificationCode),
			active: stringField(row.active),
			agency_path: stringField(row.fullParentPathName),
			agency_code_path: stringField(row.fullParentPathCode),
			place_of_performance: {
				city: stringField(city.name),
				state_code: stringField(state.code),
				state_name: stringField(state.name),
				country_code: stringField((place.country as Record<string, unknown> | undefined)?.code),
				zip: stringField(place.zip),
			},
			award: {
				number: stringField(award.number),
				amount: typeof award.amount === "number" ? award.amount : null,
				date: stringField(award.date),
				awardee_name: stringField((award.awardee as Record<string, unknown> | undefined)?.name),
			},
			ui_link: safeLink(row.uiLink),
			description_url: safeLink(row.description),
			additional_info_url: safeLink(row.additionalInfoLink),
			resource_links: links,
		},
	};
	return { recordId, record };
}

async function storeRawPage(
	page: Record<string, unknown>,
	item: ConnectorQueueMessage,
	offset: number,
	env: Env,
): Promise<{ path: string; sha256: string; rows: Record<string, unknown>[]; total: number }> {
	const raw = JSON.stringify(page);
	const digest = await sha256(raw);
	const path = `harvy-ql/raw/government/sam-gov/${item.run_id}/pages/${offset}.source.json`;
	await env.V2_BUCKET.put(path, raw, {
		httpMetadata: { contentType: "application/json" },
		customMetadata: { sha256: digest, connector: "sam-gov", run_id: item.run_id },
	});
	const rows = getRows(page);
	return { path, sha256: digest, rows, total: getTotal(page, rows) };
}

async function discover(request: Request, env: Env): Promise<Response> {
	let body: Record<string, unknown>;
	try { body = await request.json() as Record<string, unknown>; } catch { return json({ error: "valid JSON required" }, 400); }
	const runId = body.run_id;
	const environmentId = body.environment_id;
	if (typeof runId !== "string" || !/^[0-9a-f-]{36}$/i.test(runId) || typeof environmentId !== "string") {
		return json({ error: "run_id and environment_id required" }, 400);
	}
	const input = normalizeSamGovInput(body);
	if (!input) return json({ error: "invalid SAM.gov query" }, 400);
	const firstPageUrl = buildSamGovPageUrl(input, 0);
	const firstPage = await fetchSamPage(firstPageUrl, env);
	const firstRows = getRows(firstPage);
	const total = getTotal(firstPage, firstRows);
	const limit = input.limit ?? 100;
	const pageCount = Math.min(input.max_pages ?? 10, Math.ceil(total / limit));
	const items: ConnectorQueueMessage[] = [];
	if (pageCount > 0) {
		const firstItem: ConnectorQueueMessage = {
			connector: "sam-gov",
			url: firstPageUrl,
			source_url: "https://api.sam.gov/opportunities/v2/search",
			kind: "api_page",
			run_id: runId,
			environment_id: environmentId,
			options: {},
			item_id: "pending",
		};
		const firstStored = await storeRawPage(firstPage, firstItem, 0, env);
		firstItem.options = { sam_gov_prefetched_path: firstStored.path };
		items.push(firstItem);
		for (let offset = 1; offset < pageCount; offset++) {
			items.push({
				connector: "sam-gov",
				url: buildSamGovPageUrl(input, offset),
				source_url: "https://api.sam.gov/opportunities/v2/search",
				kind: "api_page",
				run_id: runId,
				environment_id: environmentId,
				item_id: "pending",
			});
		}
	}
	const discoveredCount = Math.min(total, pageCount * limit);
	return json({ items, discovered_count: discoveredCount, total_available: total, truncated: discoveredCount < total });
}

async function processSamGovPage(item: ConnectorQueueMessage, env: Env): Promise<WorkItemOutput> {
	if (item.kind !== "api_page" || !isSamGovPageUrl(item.url)) throw new PermanentConnectorError("Invalid SAM.gov queue item");
	const offset = Number(new URL(item.url).searchParams.get("offset"));
	let page: Record<string, unknown>;
	let rawPagePath: string;
	if (item.options?.sam_gov_prefetched_path) {
		const expected = `harvy-ql/raw/government/sam-gov/${item.run_id}/pages/`;
		if (!item.options.sam_gov_prefetched_path.startsWith(expected) || !item.options.sam_gov_prefetched_path.endsWith(".source.json")) {
			throw new PermanentConnectorError("Invalid SAM.gov prefetched page reference");
		}
		rawPagePath = item.options.sam_gov_prefetched_path;
		const cached = await env.V2_BUCKET.get(rawPagePath);
		if (!cached) throw new PermanentConnectorError("SAM.gov prefetched page was not found");
		page = JSON.parse(await cached.text()) as Record<string, unknown>;
	} else {
		page = await fetchSamPage(item.url, env);
		rawPagePath = (await storeRawPage(page, item, offset, env)).path;
	}
	const rows = getRows(page);
	const recordEntries: Array<{ notice_id: string; artifact_path: string; sha256: string }> = [];
	const collectedAt = new Date().toISOString();
	for (const row of rows) {
		const normalized = await normalizeSamOpportunity(row, item.url, collectedAt, rawPagePath);
		const serialized = JSON.stringify(normalized.record);
		const digest = await sha256(serialized);
		const path = `harvy-ql/raw/government/sam-gov/${item.run_id}/notices/${normalized.recordId}.json`;
		await env.V2_BUCKET.put(path, serialized, {
			httpMetadata: { contentType: "application/json" },
			customMetadata: { sha256: digest, connector: "sam-gov", run_id: item.run_id },
		});
		recordEntries.push({ notice_id: normalized.recordId, artifact_path: path, sha256: digest });
	}
	const pageManifest = {
		schema_version: 1,
		connector: "sam-gov",
		run_id: item.run_id,
		page_offset: offset,
		source_url: item.url,
		raw_page_path: rawPagePath,
		total_records: getTotal(page, rows),
		record_count: recordEntries.length,
		records: recordEntries,
		collected_at: collectedAt,
	};
	const manifestPath = `harvy-ql/raw/government/sam-gov/${item.run_id}/page-manifests/${offset}.json`;
	const manifestJson = JSON.stringify(pageManifest);
	await env.V2_BUCKET.put(manifestPath, manifestJson, {
		httpMetadata: { contentType: "application/json" },
		customMetadata: { sha256: await sha256(manifestJson), connector: "sam-gov", run_id: item.run_id },
	});
	return { artifact_path: manifestPath, record_count: recordEntries.length };
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		if (url.pathname === "/health" && request.method === "GET") return json({ status: "ok", connector: "sam-gov", capability_gate: "requires_api_key_and_source_verification" });
		if (url.pathname === "/v2/discover" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return discover(request, env);
		}
		if (url.pathname === "/v2/process" && request.method === "POST") {
			if (!authorized(request, env)) return json({ error: "unauthorized" }, env.V2_CONNECTOR_TOKEN ? 401 : 503);
			return processConnectorRequest(request, "sam-gov", (item) => processSamGovPage(item, env));
		}
		return json({ error: "not found" }, 404);
	},
} satisfies ExportedHandler<Env>;
