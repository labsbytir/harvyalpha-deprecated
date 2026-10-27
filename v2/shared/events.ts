import { PermanentConnectorError } from "./queue.ts";
import type { ConnectorQueueMessage } from "./contracts.ts";

export interface PlatformV2Event {
	event_id: string;
	platform: "v2";
	event_type: string;
	connector: string;
	run_id: string;
	environment_id: string;
	occurred_at: string;
	payload: Record<string, unknown>;
}

export interface K2Producer {
	send(records: Array<{ content: Uint8Array; headers?: Record<string, string> }>): Promise<{
		success: boolean;
		error?: { message: string; retryable: boolean };
	}>;
}

export async function createPlatformV2Event(
	eventType: string,
	connector: string,
	runId: string,
	environmentId: string,
	key: string,
	payload: Record<string, unknown>,
): Promise<PlatformV2Event> {
	const bytes = new TextEncoder().encode(`${eventType}\0${connector}\0${runId}\0${key}`);
	const hash = await crypto.subtle.digest("SHA-256", bytes);
	const eventId = [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
	return {
		event_id: eventId,
		platform: "v2",
		event_type: eventType,
		connector,
		run_id: runId,
		environment_id: environmentId,
		occurred_at: new Date().toISOString(),
		payload,
	};
}

export async function publishPlatformV2Event(binding: K2Producer, event: PlatformV2Event): Promise<void> {
	const content = new TextEncoder().encode(JSON.stringify(event));
	if (content.byteLength > 1_000_000) throw new PermanentConnectorError("K2 event exceeds the 1 MB record limit");
	const result = await binding.send([{
		content,
		headers: { platform: "v2", "event-type": event.event_type, connector: event.connector, event_id: event.event_id },
	}]);
	if (!result.success) {
		if (result.error?.retryable) throw new Error(`K2 temporarily unavailable: ${result.error.message}`);
		throw new PermanentConnectorError(`K2 rejected event: ${result.error?.message ?? "unknown error"}`);
	}
}

export async function publishWorkItemEvent(
	binding: K2Producer,
	eventType: string,
	item: ConnectorQueueMessage,
	payload: Record<string, unknown>,
): Promise<void> {
	const event = await createPlatformV2Event(eventType, item.connector, item.run_id, item.environment_id, item.item_id, payload);
	await publishPlatformV2Event(binding, event);
}
