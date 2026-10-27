export type ConnectorId = "judyrecords" | "truthsocial" | "sam-gov";
export type DiscoveryMode = "links" | "crawl";

export interface JudyRecordsInput {
	seeds: string[];
	mode?: DiscoveryMode;
	limit?: number;
}

export interface TruthSocialInput {
	handles: string[];
	max_posts?: number;
}

export interface SamGovInput {
	postedFrom: string;
	postedTo: string;
	ptype?: string[];
	noticeid?: string;
	solnum?: string;
	title?: string;
	state?: string;
	zip?: string;
	organizationName?: string;
	typeOfSetAside?: string;
	ncode?: string;
	ccode?: string;
	rdlfrom?: string;
	rdlto?: string;
	limit?: number;
	max_pages?: number;
}

export interface RunRequest {
	connector: ConnectorId;
	environment_id: string;
	idempotency_key: string;
	input: JudyRecordsInput | TruthSocialInput | SamGovInput;
}

export interface DiscoveredItem {
	connector: ConnectorId;
	url: string;
	source_url: string;
	kind: "record" | "profile" | "api_page";
	run_id: string;
	environment_id: string;
	options?: { max_posts?: number; sam_gov_prefetched_path?: string };
}

export interface ConnectorQueueMessage extends DiscoveredItem {
	item_id: string;
}

export interface TruthSocialPost {
	id: string;
	url: string;
	text_html: string;
	timestamp: string | null;
	like_count: number | null;
	repost_count: number | null;
	reply_count: number | null;
	ownership_verified: true;
	platform: "truthsocial";
	source: string;
}

export interface TruthSocialArtifact {
	schema_version: 1;
	connector: "truthsocial";
	record_id: string;
	source_url: string;
	collected_at: string;
	parser_version: "1.0.0";
	complete: false;
	limitations: string[];
	provenance: { method: "spider_unlimited_scrape"; proxy_requested: true };
	data: {
		platform: "truthsocial";
		handle: string;
		url: string;
		account_id: string;
		profile: Record<string, unknown>;
		posts: TruthSocialPost[];
	};
}

export interface JudyRecord {
	schema_version: 1;
	connector: "judyrecords";
	record_id: string;
	source_url: string;
	collected_at: string;
	parser_version: "1.0.0";
	complete: boolean;
	limitations: string[];
	provenance: {
		method: "spider_unlimited_scrape";
		proxy_requested: boolean;
	};
	data: {
		title: string;
		case_number: string;
		court: string;
		file_date: string;
		case_type: string;
		case_status: string;
		parties: Array<{ name: string; role: string }>;
		raw_text: string;
	};
}

export const CONNECTORS = [
	{ id: "judyrecords", enabled: true, capabilities: ["discovery", "record_fetch"] },
	{ id: "truthsocial", enabled: false, capabilities: ["profile", "public_timeline"], blocked_by: "Spider Unlimited social-domain capability is not verified" },
	{ id: "courtlistener-pacer", enabled: false, capabilities: ["api", "dockets", "documents"] },
	{ id: "sam-gov", enabled: false, capabilities: ["api", "contract_opportunities"], blocked_by: "SAM_GOV_API_KEY and API capability verification are required" },
] as const;

function validSamDate(value: unknown): value is string {
	if (typeof value !== "string" || !/^\d{2}\/\d{2}\/\d{4}$/.test(value)) return false;
	const [month, day, year] = value.split("/").map(Number);
	const date = new Date(Date.UTC(year, month - 1, day));
	return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

function boundedSamText(value: unknown, max = 200): value is string {
	return typeof value === "string" && value.length > 0 && value.length <= max && !/[\u0000-\u001f]/.test(value);
}

function normalizeSamGovInput(value: Record<string, unknown>): SamGovInput | null {
	if (!validSamDate(value.postedFrom) || !validSamDate(value.postedTo)) return null;
	const [fromMonth, fromDay, fromYear] = value.postedFrom.split("/").map(Number);
	const [toMonth, toDay, toYear] = value.postedTo.split("/").map(Number);
	const from = Date.UTC(fromYear, fromMonth - 1, fromDay);
	const to = Date.UTC(toYear, toMonth - 1, toDay);
	const maxTo = new Date(from);
	maxTo.setUTCFullYear(maxTo.getUTCFullYear() + 1);
	if (to < from || to > maxTo.getTime()) return null;
	if (value.ptype !== undefined && (!Array.isArray(value.ptype) || value.ptype.length > 8 ||
		!value.ptype.every((code) => typeof code === "string" && ["u", "p", "a", "r", "s", "o", "g", "k", "i"].includes(code)))) return null;
	for (const [key, max] of [["noticeid", 100], ["solnum", 100], ["title", 200], ["organizationName", 200], ["typeOfSetAside", 50], ["rdlfrom", 10], ["rdlto", 10]] as const) {
		if (value[key] !== undefined && !boundedSamText(value[key], max)) return null;
	}
	if (value.state !== undefined && (typeof value.state !== "string" || !/^[A-Za-z]{2}$/.test(value.state))) return null;
	if (value.zip !== undefined && (typeof value.zip !== "string" || !/^\d{5}(?:-\d{4})?$/.test(value.zip))) return null;
	if (value.ncode !== undefined && (typeof value.ncode !== "string" || !/^\d{1,6}$/.test(value.ncode))) return null;
	if (value.ccode !== undefined && (typeof value.ccode !== "string" || !/^[A-Za-z0-9-]{1,10}$/.test(value.ccode))) return null;
	if (value.rdlfrom !== undefined && !validSamDate(value.rdlfrom)) return null;
	if (value.rdlto !== undefined && !validSamDate(value.rdlto)) return null;
	if (value.rdlfrom !== undefined && value.rdlto !== undefined) {
		const [fromMonth, fromDay, fromYear] = (value.rdlfrom as string).split("/").map(Number);
		const [toMonth, toDay, toYear] = (value.rdlto as string).split("/").map(Number);
		const from = Date.UTC(fromYear, fromMonth - 1, fromDay);
		const maxTo = new Date(from);
		maxTo.setUTCFullYear(maxTo.getUTCFullYear() + 1);
		if (Date.UTC(toYear, toMonth - 1, toDay) < from || Date.UTC(toYear, toMonth - 1, toDay) > maxTo.getTime()) return null;
	}
	const limit = value.limit ?? 100;
	const maxPages = value.max_pages ?? 10;
	// shortcut: cap API pages at 100, raise only after Worker subrequest/runtime budgets are measured.
	if (!Number.isInteger(limit) || (limit as number) < 1 || (limit as number) > 100) return null;
	if (!Number.isInteger(maxPages) || (maxPages as number) < 1 || (maxPages as number) > 25) return null;
	return {
		postedFrom: value.postedFrom,
		postedTo: value.postedTo,
		...(value.ptype ? { ptype: [...new Set(value.ptype as string[])] } : {}),
		...Object.fromEntries(["noticeid", "solnum", "title", "organizationName", "typeOfSetAside", "state", "zip", "ncode", "ccode", "rdlfrom", "rdlto"]
			.filter((key) => value[key] !== undefined).map((key) => [key, value[key]])),
		limit: limit as number,
		max_pages: maxPages as number,
	};
}

export function parseRunRequest(value: unknown): RunRequest | null {
	if (!value || typeof value !== "object" || Array.isArray(value)) return null;
	const input = value as Record<string, unknown>;
	if (input.connector !== "judyrecords" && input.connector !== "truthsocial" && input.connector !== "sam-gov") return null;
	if (typeof input.environment_id !== "string" || !/^[A-Za-z0-9._:-]{1,100}$/.test(input.environment_id)) return null;
	if (typeof input.idempotency_key !== "string" || !/^[A-Za-z0-9._:-]{1,160}$/.test(input.idempotency_key)) return null;
	if (!input.input || typeof input.input !== "object" || Array.isArray(input.input)) return null;
	const runInput = input.input as Record<string, unknown>;
	let normalizedInput: JudyRecordsInput | TruthSocialInput | SamGovInput;
	if (input.connector === "judyrecords") {
		if (!Array.isArray(runInput.seeds) || runInput.seeds.length < 1 || runInput.seeds.length > 20) return null;
		if (!runInput.seeds.every((seed) => typeof seed === "string" && isJudySeed(seed))) return null;
		if (runInput.mode !== undefined && runInput.mode !== "links" && runInput.mode !== "crawl") return null;
		if (runInput.limit !== undefined && (!Number.isInteger(runInput.limit) || (runInput.limit as number) < 1 || (runInput.limit as number) > 100)) return null;
		normalizedInput = {
			seeds: runInput.seeds as string[],
			mode: (runInput.mode as DiscoveryMode | undefined) ?? "links",
			limit: (runInput.limit as number | undefined) ?? 50,
		};
	} else if (input.connector === "truthsocial") {
		if (!Array.isArray(runInput.handles) || runInput.handles.length < 1 || runInput.handles.length > 20) return null;
		if (!runInput.handles.every((handle) => typeof handle === "string" && isTruthSocialHandle(handle))) return null;
		if (runInput.max_posts !== undefined && (!Number.isInteger(runInput.max_posts) || (runInput.max_posts as number) < 1 || (runInput.max_posts as number) > 40)) return null;
		normalizedInput = { handles: runInput.handles as string[], max_posts: (runInput.max_posts as number | undefined) ?? 25 };
	} else {
		const samGovInput = normalizeSamGovInput(runInput);
		if (!samGovInput) return null;
		normalizedInput = samGovInput;
	}
	return {
		connector: input.connector,
		environment_id: input.environment_id,
		idempotency_key: input.idempotency_key,
		input: normalizedInput,
	};
}

export function isTruthSocialHandle(value: string): boolean {
	return /^@?[A-Za-z0-9_.-]{1,100}$/.test(value) && !value.includes("..") && !value.startsWith(".") && !value.endsWith(".");
}

export function truthSocialProfileUrl(handle: string): string | null {
	if (!isTruthSocialHandle(handle)) return null;
	return `https://truthsocial.com/@${handle.replace(/^@/, "").toLowerCase()}`;
}

export function buildSamGovPageUrl(input: SamGovInput, pageOffset: number): string {
	const url = new URL("https://api.sam.gov/opportunities/v2/search");
	url.searchParams.set("postedFrom", input.postedFrom);
	url.searchParams.set("postedTo", input.postedTo);
	url.searchParams.set("limit", String(input.limit ?? 100));
	url.searchParams.set("offset", String(pageOffset));
	for (const type of input.ptype ?? []) url.searchParams.append("ptype", type);
	for (const key of ["noticeid", "solnum", "title", "state", "zip", "organizationName", "typeOfSetAside", "ncode", "ccode", "rdlfrom", "rdlto"] as const) {
		const value = input[key];
		if (value !== undefined) url.searchParams.set(key, value);
	}
	return url.toString();
}

export function isSamGovPageUrl(value: string): boolean {
	try {
		const url = new URL(value);
		const limit = Number(url.searchParams.get("limit"));
		const offset = Number(url.searchParams.get("offset"));
		const allowed = new Set(["postedFrom", "postedTo", "limit", "offset", "ptype", "noticeid", "solnum", "title", "state", "zip", "organizationName", "typeOfSetAside", "ncode", "ccode", "rdlfrom", "rdlto"]);
		return url.protocol === "https:" && url.hostname === "api.sam.gov" && url.pathname === "/opportunities/v2/search" &&
			[...url.searchParams.keys()].every((key) => allowed.has(key)) &&
			!url.searchParams.has("api_key") && validSamDate(url.searchParams.get("postedFrom")) && validSamDate(url.searchParams.get("postedTo")) &&
			Number.isSafeInteger(offset) && offset >= 0 && Number.isSafeInteger(limit) && limit >= 1 && limit <= 1000;
	} catch {
		return false;
	}
}

export function isJudySeed(value: string): boolean {
	try {
		const url = new URL(value);
		return url.protocol === "https:" && ["judyrecords.com", "www.judyrecords.com"].includes(url.hostname) && !url.username && !url.password;
	} catch {
		return false;
	}
}

export function canonicalRecordUrl(value: string): string | null {
	try {
		const url = new URL(value);
		if (url.protocol !== "https:" || !["judyrecords.com", "www.judyrecords.com"].includes(url.hostname)) return null;
		const match = url.pathname.match(/^\/record\/([a-z0-9]+)\/?$/i);
		return match ? `https://www.judyrecords.com/record/${match[1].toLowerCase()}` : null;
	} catch {
		return null;
	}
}

export function extractSpiderUrls(value: unknown, output = new Set<string>()): string[] {
	if (typeof value === "string") {
		for (const candidate of value.match(/https?:\/\/[^\s"'<>\\]+/g) ?? []) {
			try {
				const url = new URL(candidate.replace(/[),.;]+$/, ""));
				if (["judyrecords.com", "www.judyrecords.com"].includes(url.hostname)) output.add(url.href);
			} catch {
				// Ignore non-URL strings in Spider metadata.
			}
		}
	} else if (Array.isArray(value)) {
		for (const item of value) extractSpiderUrls(item, output);
	} else if (value && typeof value === "object") {
		for (const item of Object.values(value)) extractSpiderUrls(item, output);
	}
	return [...output];
}

export function makeWorkItemId(connector: string, environmentId: string, runId: string, url: string): Promise<string> {
	return crypto.subtle.digest("SHA-256", new TextEncoder().encode(`${connector}\0${environmentId}\0${runId}\0${url}`)).then((hash) =>
		[...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join(""),
	);
}
