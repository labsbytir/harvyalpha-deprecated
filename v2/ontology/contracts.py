"""Canonical ontology contracts, identifiers, and environment scoping for Harvy."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_ENVIRONMENT = "shared"


def normalize_identifier(raw: str) -> str:
    """Normalize identifier by stripping leading '@', trimming, and lowercasing."""
    return raw.strip().lstrip("@").lower()


def make_object_urn(type_id: str, source: str, native_id: str) -> str:
    """Generate canonical URN for a shared ontology object.

    Format: urn:harvy:<type_id>:<source>:<normalized_id>
    """
    clean_type = type_id.strip().lower()
    clean_source = source.strip().lower()
    clean_id = normalize_identifier(native_id)
    return f"urn:harvy:{clean_type}:{clean_source}:{clean_id}"


def make_observation_id(source: str, object_id: str, content_sha256: str, observed_at: int) -> str:
    """Generate deterministic observation ID based on source, object, content, and time."""
    seed = f"{source}:{object_id}:{content_sha256}:{observed_at}".encode("utf-8")
    return f"obs_{hashlib.sha256(seed).hexdigest()[:24]}"


def make_link_id(source_id: str, link_type: str, target_id: str, environment_id: str = DEFAULT_ENVIRONMENT) -> str:
    """Generate deterministic link ID scoped by environment."""
    env = (environment_id or DEFAULT_ENVIRONMENT).strip().lower()
    seed = f"{env}:{source_id}:{link_type.strip().lower()}:{target_id}".encode("utf-8")
    return f"lnk_{hashlib.sha256(seed).hexdigest()[:24]}"


def build_scope_filter(
    environment_id: Optional[str] = None,
    column_name: str = "environment_id",
) -> Tuple[str, List[str]]:
    """Build parameterized SQL predicate enforcing environment scoping.

    Always includes 'shared'. If tenant environment provided, includes it.
    Never allows arbitrary SQL injection.
    """
    env = (environment_id or "").strip()
    if not env or env.lower() == DEFAULT_ENVIRONMENT:
        return f"{column_name} = ?", [DEFAULT_ENVIRONMENT]
    return f"{column_name} IN (?, ?)", [DEFAULT_ENVIRONMENT, env]


def make_profile_object(
    platform: str,
    handle: str,
    display_name: Optional[str] = None,
    canonical_url: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    now: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a canonical profile object dict."""
    ts = now if now is not None else int(time.time())
    urn = make_object_urn("profile", platform, handle)
    name = display_name or f"@{normalize_identifier(handle)}"
    return {
        "id": urn,
        "type_id": "profile",
        "display_name": name,
        "canonical_url": canonical_url or f"https://{platform}.com/{normalize_identifier(handle)}",
        "attributes_json": json.dumps(attributes or {}, sort_keys=True),
        "created_at": ts,
        "updated_at": ts,
    }


def make_observation_record(
    object_id: str,
    source: str,
    payload: Dict[str, Any],
    r2_object_key: Optional[str] = None,
    job_id: Optional[str] = None,
    environment_id: str = DEFAULT_ENVIRONMENT,
    observed_at: Optional[int] = None,
    now: Optional[int] = None,
) -> Dict[str, Any]:
    """Create an append-only observation record dict."""
    ts_now = now if now is not None else int(time.time())
    ts_obs = observed_at if observed_at is not None else ts_now
    raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    content_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    obs_id = make_observation_id(source, object_id, content_sha256, ts_obs)
    env = (environment_id or DEFAULT_ENVIRONMENT).strip()

    return {
        "id": obs_id,
        "object_id": object_id,
        "environment_id": env,
        "source": source,
        "job_id": job_id,
        "r2_object_key": r2_object_key,
        "content_sha256": content_sha256,
        "data_json": json.dumps(payload, sort_keys=True),
        "observed_at": ts_obs,
        "created_at": ts_now,
    }


def make_link_record(
    source_id: str,
    target_id: str,
    link_type: str,
    evidence_observation_id: Optional[str] = None,
    environment_id: str = DEFAULT_ENVIRONMENT,
    confidence: float = 1.0,
    properties: Optional[Dict[str, Any]] = None,
    now: Optional[int] = None,
) -> Dict[str, Any]:
    """Create an evidence-backed directed link record dict."""
    ts = now if now is not None else int(time.time())
    env = (environment_id or DEFAULT_ENVIRONMENT).strip()
    link_id = make_link_id(source_id, link_type, target_id, env)

    return {
        "id": link_id,
        "environment_id": env,
        "source_id": source_id,
        "target_id": target_id,
        "link_type": link_type,
        "confidence": confidence,
        "evidence_observation_id": evidence_observation_id,
        "properties_json": json.dumps(properties or {}, sort_keys=True),
        "created_at": ts,
    }


def make_basin_observation_event(obs: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an ontology observation record into a Basin pipeline stream event."""
    data = obs.get("data_json")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            pass

    return {
        "event_id": f"basin_obs_{obs['id']}",
        "job_id": obs.get("job_id") or "ontology_sync",
        "kind": "ontology_observation",
        "source": obs.get("source", "unknown"),
        "target": obs["object_id"],
        "artifact_path": obs.get("r2_object_key") or "",
        "collected_at": obs.get("created_at") or int(time.time()),
        "file_sha256": obs.get("content_sha256", ""),
        "chunk_index": 0,
        "chunk_count": 1,
        "payload": {
            "observation_id": obs["id"],
            "environment_id": obs.get("environment_id", DEFAULT_ENVIRONMENT),
            "data": data or {},
            "observed_at": obs.get("observed_at"),
        },
    }


def make_basin_link_event(link: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an ontology link record into a Basin pipeline stream event."""
    props = link.get("properties_json")
    if isinstance(props, str):
        try:
            props = json.loads(props)
        except Exception:
            pass

    return {
        "event_id": f"basin_lnk_{link['id']}",
        "job_id": "ontology_sync",
        "kind": "ontology_link",
        "source": link["source_id"],
        "target": link["target_id"],
        "artifact_path": "",
        "collected_at": link.get("created_at") or int(time.time()),
        "file_sha256": hashlib.sha256(link["id"].encode("utf-8")).hexdigest(),
        "chunk_index": 0,
        "chunk_count": 1,
        "payload": {
            "link_id": link["id"],
            "link_type": link["link_type"],
            "environment_id": link.get("environment_id", DEFAULT_ENVIRONMENT),
            "confidence": link.get("confidence", 1.0),
            "evidence_observation_id": link.get("evidence_observation_id"),
            "properties": props or {},
        },
    }

