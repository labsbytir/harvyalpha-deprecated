import { makeWorkItemId, type ConnectorId, type ConnectorQueueMessage } from "./contracts.ts";

export class PermanentConnectorError extends Error {}

export interface WorkItemOutput {
	artifact_path: string;
	record_count?: number;
}

export async function consumeWorkItem(
	message: Message<ConnectorQueueMessage>,
	db: D1Database,
	connector: ConnectorId,
	process: (item: ConnectorQueueMessage) => Promise<string | WorkItemOutput>,
	publish?: (eventType: string, item: ConnectorQueueMessage, payload: Record<string, unknown>) => Promise<void>,
): Promise<void> {
	const item = message.body;
	if (!item || item.connector !== connector || !item.item_id || !item.run_id || !item.environment_id ||
		item.item_id !== await makeWorkItemId(item.connector, item.environment_id, item.run_id, item.url)) {
		message.ack();
		return;
	}
	const now = Date.now();
	const claim = await db.prepare(`
		UPDATE platform_v2_work_items
		SET status = 'processing', attempts = attempts + 1, lease_until = ?, updated_at = ?
		WHERE id = ? AND environment_id = ?
		  AND (status = 'queued' OR (status = 'processing' AND lease_until < ?))
		RETURNING attempts
	`).bind(now + 120_000, now, item.item_id, item.environment_id, now).first<{ attempts: number }>();
	if (!claim) {
		const state = await db.prepare("SELECT status FROM platform_v2_work_items WHERE id = ? AND environment_id = ?")
			.bind(item.item_id, item.environment_id).first<{ status: string }>();
		if (!state || state.status === "complete" || state.status === "failed") message.ack();
		else message.retry({ delaySeconds: 30 });
		return;
	}

	try {
		const output = await process(item);
		const artifactPath = typeof output === "string" ? output : output.artifact_path;
		const completedEvent = item.kind === "record" ? "record.completed" : item.kind === "profile" ? "profile.completed" : "work_item.completed";
		await publish?.(completedEvent, item, {
			item_id: item.item_id,
			artifact_path: artifactPath,
			kind: item.kind,
			...(typeof output === "string" || output.record_count === undefined ? {} : { record_count: output.record_count }),
		});
		await db.prepare(`
			UPDATE platform_v2_work_items
			SET status = 'complete', artifact_path = ?, lease_until = 0, last_error = NULL, updated_at = ?
			WHERE id = ? AND environment_id = ?
		`).bind(artifactPath, Date.now(), item.item_id, item.environment_id).run();
		await finalizeRun(db, item.run_id);
		message.ack();
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message.slice(0, 300) : "connector processing failed";
		if (claim.attempts >= 8 || error instanceof PermanentConnectorError) {
			await publish?.("work_item.failed", item, { item_id: item.item_id, kind: item.kind, failure: "processing_failed" });
			await db.prepare("UPDATE platform_v2_work_items SET status = 'failed', lease_until = 0, last_error = ?, updated_at = ? WHERE id = ?")
				.bind(errorMessage, Date.now(), item.item_id).run();
			await finalizeRun(db, item.run_id);
			message.ack();
			return;
		}
		await db.prepare("UPDATE platform_v2_work_items SET status = 'queued', lease_until = 0, last_error = ?, updated_at = ? WHERE id = ?")
			.bind(errorMessage, Date.now(), item.item_id).run();
		message.retry({ delaySeconds: Math.min(300, 5 * (2 ** (claim.attempts - 1))) });
	}
}

async function finalizeRun(db: D1Database, runId: string): Promise<void> {
	await db.prepare(`
		UPDATE platform_v2_runs
		SET status = CASE
			WHEN EXISTS (SELECT 1 FROM platform_v2_work_items WHERE run_id = ? AND status = 'failed') THEN 'failed'
			ELSE 'complete'
		END, updated_at = ?
		WHERE id = ? AND status IN ('running', 'dispatched')
		  AND NOT EXISTS (SELECT 1 FROM platform_v2_work_items WHERE run_id = ? AND status IN ('queued', 'processing'))
	`).bind(runId, Date.now(), runId, runId).run();
}
