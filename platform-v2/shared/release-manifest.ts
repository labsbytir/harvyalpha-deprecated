export interface DatasetReleaseManifest {
	schema_version: 1;
	dataset: string;
	release: string;
	environment_id: string;
	visibility: "public" | "private";
	created_at: string;
	record_count: number;
	files: Array<{
		path: string;
		sha256: string;
		bytes: number;
		content_type: "application/zip";
	}>;
}

export function parseDatasetRelease(value: unknown): Omit<DatasetReleaseManifest, "schema_version" | "created_at"> | null {
	if (!value || typeof value !== "object" || Array.isArray(value)) return null;
	const manifest = value as Record<string, unknown>;
	if (typeof manifest.dataset !== "string" || !/^[a-z0-9][a-z0-9_-]{0,63}$/.test(manifest.dataset)) return null;
	if (typeof manifest.release !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(manifest.release)) return null;
	if (typeof manifest.environment_id !== "string" || !/^[A-Za-z0-9._:-]{1,100}$/.test(manifest.environment_id)) return null;
	if (manifest.visibility !== "public" && manifest.visibility !== "private") return null;
	if (!Number.isInteger(manifest.record_count) || (manifest.record_count as number) < 0) return null;
	if (!Array.isArray(manifest.files) || manifest.files.length < 1 || manifest.files.length > 100) return null;
	const prefix = `harvy-ql/processed/bulk-datasets/${manifest.dataset}/${manifest.release}/`;
	const files: DatasetReleaseManifest["files"] = [];
	for (const value of manifest.files) {
		if (!value || typeof value !== "object" || Array.isArray(value)) return null;
		const file = value as Record<string, unknown>;
		if (typeof file.path !== "string" || !file.path.startsWith(prefix) || !file.path.endsWith(".zip") || file.path.includes("..")) return null;
		if (typeof file.sha256 !== "string" || !/^[a-f0-9]{64}$/i.test(file.sha256)) return null;
		if (!Number.isSafeInteger(file.bytes) || (file.bytes as number) < 1) return null;
		files.push({ path: file.path, sha256: file.sha256.toLowerCase(), bytes: file.bytes as number, content_type: "application/zip" });
	}
	files.sort((a, b) => a.path.localeCompare(b.path));
	return {
		dataset: manifest.dataset,
		release: manifest.release,
		environment_id: manifest.environment_id,
		visibility: manifest.visibility,
		record_count: manifest.record_count as number,
		files,
	};
}
