import test from "node:test";
import assert from "node:assert/strict";
import { buildSamGovPageUrl, canonicalRecordUrl, extractSpiderUrls, isJudySeed, isSamGovPageUrl, parseRunRequest, truthSocialProfileUrl } from "../shared/contracts.ts";
import { parseJudyRecord } from "../catalog/connectors/judyrecords/src/index.ts";
import { extractAccount, extractTruthSocialPosts } from "../catalog/connectors/truthsocial/src/index.ts";
import { parseDatasetRelease } from "../shared/release-manifest.ts";
import { createPlatformV2Event, publishPlatformV2Event } from "../shared/events.ts";
import { normalizeSamOpportunity, redactSamGovApiKey } from "../catalog/connectors/sam-gov/src/index.ts";

test("run request validates explicit scope and bounded Judy seeds", () => {
	const valid = {
		connector: "judyrecords",
		environment_id: "shared",
		idempotency_key: "test-run-1",
		input: { seeds: ["https://www.judyrecords.com/search/"], mode: "links", limit: 10 },
	};
	assert.deepEqual(parseRunRequest(valid), valid);
	assert.equal(parseRunRequest({ ...valid, environment_id: undefined }), null);
	assert.equal(parseRunRequest({ ...valid, input: { seeds: ["https://example.com/"] } }), null);
	assert.equal(parseRunRequest({ ...valid, input: { seeds: ["https://judyrecords.com/"], limit: 101 } }), null);
});

test("Truth Social runs accept handles and enforce a public-timeline cap", () => {
	const valid = {
		connector: "truthsocial",
		environment_id: "shared",
		idempotency_key: "truthsocial-run-1",
		input: { handles: ["@Alice", "bob"], max_posts: 12 },
	};
	assert.deepEqual(parseRunRequest(valid), { ...valid, input: { handles: ["@Alice", "bob"], max_posts: 12 } });
	assert.equal(truthSocialProfileUrl("@Alice"), "https://truthsocial.com/@alice");
	assert.equal(parseRunRequest({ ...valid, input: { handles: ["../bad"] } }), null);
	assert.equal(parseRunRequest({ ...valid, input: { handles: ["alice"], max_posts: 41 } }), null);
});

test("Judy URL canonicalization excludes non-record paths and other hosts", () => {
	assert.equal(isJudySeed("https://www.judyrecords.com/record/abc123"), true);
	assert.equal(canonicalRecordUrl("https://judyrecords.com/record/ABC123?x=1"), "https://www.judyrecords.com/record/abc123");
	assert.equal(canonicalRecordUrl("https://www.judyrecords.com/search"), null);
	assert.equal(canonicalRecordUrl("https://example.com/record/abc123"), null);
});

test("Spider link responses are reduced to unique Judy URLs", () => {
	assert.deepEqual(extractSpiderUrls({ links: ["https://www.judyrecords.com/record/a1", "https://example.com/no", { url: "https://judyrecords.com/record/b2" }] }), [
		"https://www.judyrecords.com/record/a1",
		"https://judyrecords.com/record/b2",
	]);
});

test("OSCN record parser extracts stable fields and source provenance", () => {
	const html = `<article class="record page"><div id="oscn-content">
	<h2 class="styletop">In the District Court in and for Garfield County, Oklahoma</h2>
	<table class="caseStyle"><tr><td><strong>No. CM-2020-260 (Criminal Misdemeanor)</strong><br>Filed: 04/22/2020<br>Closed: 09/17/2020</td></tr></table>
	<h2 class="section party">Parties</h2><p>ANDY, Defendant<br>STATE OF OKLAHOMA, Plaintiff</p>
	</div></article>`;
	const record = parseJudyRecord(html, "https://www.judyrecords.com/record/0dkk2dkd6452", true);
	assert.equal(record.data.case_number, "CM-2020-260");
	assert.equal(record.data.court, "Garfield County, Oklahoma District Court");
	assert.equal(record.data.case_type, "Criminal Misdemeanor");
	assert.equal(record.data.case_status, "Closed");
	assert.deepEqual(record.data.parties, [
		{ name: "ANDY", role: "defendant" },
		{ name: "STATE OF OKLAHOMA", role: "plaintiff" },
	]);
	assert.equal(record.provenance.proxy_requested, true);
});

test("Truth Social parser emits only posts owned by the requested public account", () => {
	const profileUrl = "https://truthsocial.com/@alice";
	const pages = [{ status: 200, json_data: [
		{ id: "42", username: "alice", acct: "alice" },
		{ id: "p1", url: "https://truthsocial.com/@alice/posts/p1", content: "<p>Public post</p>", created_at: "2026-10-01T00:00:00Z", favourites_count: 3, account: { url: profileUrl } },
		{ id: "p2", content: "Other account", account: { url: "https://truthsocial.com/@other" } },
	] }];
	assert.equal(extractAccount(pages, "alice").id, "42");
	assert.deepEqual(extractTruthSocialPosts(pages, profileUrl, 10).map((post) => post.id), ["p1"]);
});

test("dataset release manifests reject paths outside their public release prefix", () => {
	const base = {
		dataset: "court-data",
		release: "2026-10-26",
		environment_id: "shared",
		visibility: "public",
		record_count: 10,
		files: [{
			path: "harvy-ql/processed/bulk-datasets/court-data/2026-10-26/part-0001.zip",
			sha256: "a".repeat(64),
			bytes: 2048,
		}],
	};
	assert.equal(parseDatasetRelease(base)?.files.length, 1);
	assert.equal(parseDatasetRelease({ ...base, files: [{ ...base.files[0], path: "harvy-ql/private/file.zip" }] }), null);
});

test("K2 lifecycle events use deterministic IDs and typed headers", async () => {
	const first = await createPlatformV2Event("work_item.completed", "judyrecords", "run-1", "shared", "item-1", { count: 1 });
	const retry = await createPlatformV2Event("work_item.completed", "judyrecords", "run-1", "shared", "item-1", { count: 1 });
	assert.equal(first.event_id, retry.event_id);
	let sent;
	await publishPlatformV2Event({ send: async (records) => { sent = records; return { success: true }; } }, first);
	assert.deepEqual(sent[0].headers, { platform: "v2", "event-type": "work_item.completed", connector: "judyrecords", event_id: first.event_id });
	assert.equal(JSON.parse(new TextDecoder().decode(sent[0].content)).event_id, first.event_id);
});

test("SAM.gov query requires a bounded date range and builds key-free page URLs", () => {
	const run = parseRunRequest({
		connector: "sam-gov",
		environment_id: "shared",
		idempotency_key: "sam-run-1",
		input: { postedFrom: "01/01/2026", postedTo: "03/31/2026", ptype: ["o"], limit: 100, max_pages: 3 },
	});
	assert.ok(run);
	assert.equal(run.input.postedFrom, "01/01/2026");
	const url = buildSamGovPageUrl(run.input, 2);
	assert.equal(isSamGovPageUrl(url), true);
	assert.equal(new URL(url).searchParams.get("offset"), "2");
	assert.equal(new URL(url).searchParams.has("api_key"), false);
	assert.equal(isSamGovPageUrl(`${url}&api_key=leak`), false);
	assert.equal(parseRunRequest({
		connector: "sam-gov", environment_id: "shared", idempotency_key: "sam-run-large",
		input: { postedFrom: "01/01/2026", postedTo: "03/31/2026", limit: 101 },
	}), null);
	assert.equal(parseRunRequest({
		connector: "sam-gov", environment_id: "shared", idempotency_key: "sam-run-2",
		input: { postedFrom: "01/01/2025", postedTo: "01/02/2026" },
	}), null);
});

test("SAM.gov normalizer omits contact PII and redacts API keys", async () => {
	const input = {
		noticeId: "notice-123",
		title: "Public notice",
		solicitationNumber: "RFP-123",
		responseDeadLine: "2026-12-01",
		pointOfContact: [{ fullname: "Public Employee", email: "person@example.gov" }],
		data: { placeOfPerformance: { state: { code: "DC", name: "District of Columbia" } } },
	};
	const normalized = await normalizeSamOpportunity(input, "https://api.sam.gov/opportunities/v2/search", "2026-10-26T00:00:00.000Z", "harvy-ql/raw/government/sam-gov/run/pages/0.source.json");
	assert.equal(normalized.record.data.notice_id, "notice-123");
	assert.equal(normalized.record.data.response_deadline, "2026-12-01");
	assert.equal(JSON.stringify(normalized.record).includes("person@example.gov"), false);
	const redacted = redactSamGovApiKey({ api_key: "secret-value", href: "https://api.sam.gov/?api_key=secret-value&offset=1" });
	assert.equal(JSON.stringify(redacted).includes("secret-value"), false);
});
