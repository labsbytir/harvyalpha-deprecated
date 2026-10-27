"""Graph traversal and provenance query engine for Harvy Nodes."""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional, Set
from ontology.contracts import DEFAULT_ENVIRONMENT, build_scope_filter

DEFAULT_NODE_LIMIT = 50
MAX_NODE_LIMIT = 200


def query_scoped_graph(
    db: sqlite3.Connection,
    environment_id: Optional[str] = None,
    center_urn: Optional[str] = None,
    limit: int = DEFAULT_NODE_LIMIT,
) -> Dict[str, Any]:
    """Return nodes and links scoped to shared + current environment.

    Bounded to max limit to prevent client WebGL canvas crash.
    """
    bounded_limit = min(max(1, limit), MAX_NODE_LIMIT)
    link_scope, link_params = build_scope_filter(environment_id, "l.environment_id")

    links = []
    node_ids: Set[str] = set()

    if center_urn:
        node_ids.add(center_urn)
        # Fetch 1-hop and 2-hop edges connected to center
        sql = f"""
        SELECT l.id, l.source_id, l.target_id, l.link_type, l.confidence, l.evidence_observation_id
        FROM harvy_links l
        WHERE {link_scope} AND (l.source_id = ? OR l.target_id = ?)
        LIMIT ?
        """
        cursor = db.execute(sql, [*link_params, center_urn, center_urn, bounded_limit])
        for row in cursor.fetchall():
            lid, src, tgt, ltype, conf, evid = row
            links.append({
                "id": lid,
                "source": src,
                "target": tgt,
                "link_type": ltype,
                "confidence": conf,
                "evidence_id": evid,
            })
            node_ids.add(src)
            node_ids.add(tgt)
    else:
        # Fetch most active recent links in scope
        sql = f"""
        SELECT l.id, l.source_id, l.target_id, l.link_type, l.confidence, l.evidence_observation_id
        FROM harvy_links l
        WHERE {link_scope}
        ORDER BY l.created_at DESC
        LIMIT ?
        """
        cursor = db.execute(sql, [*link_params, bounded_limit])
        for row in cursor.fetchall():
            lid, src, tgt, ltype, conf, evid = row
            links.append({
                "id": lid,
                "source": src,
                "target": tgt,
                "link_type": ltype,
                "confidence": conf,
                "evidence_id": evid,
            })
            node_ids.add(src)
            node_ids.add(tgt)

    nodes = []
    if node_ids:
        placeholders = ",".join("?" for _ in node_ids)
        sql_nodes = f"""
        SELECT id, type_id, display_name, canonical_url
        FROM harvy_objects
        WHERE id IN ({placeholders})
        """
        cursor = db.execute(sql_nodes, list(node_ids))
        for row in cursor.fetchall():
            nid, tid, name, url = row
            nodes.append({
                "id": nid,
                "type": tid,
                "name": name,
                "url": url,
            })

    return {
        "nodes": nodes,
        "links": links,
        "environment": environment_id or DEFAULT_ENVIRONMENT,
        "total_nodes": len(nodes),
        "total_links": len(links),
    }


def get_object_provenance(
    db: sqlite3.Connection,
    object_urn: str,
    environment_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return canonical object details with observation history and evidence."""
    cursor = db.execute(
        "SELECT id, type_id, display_name, canonical_url, attributes_json, created_at, updated_at FROM harvy_objects WHERE id = ?",
        (object_urn,),
    )
    row = cursor.fetchone()
    if not row:
        return None

    oid, tid, name, url, attrs, created, updated = row
    obs_scope, obs_params = build_scope_filter(environment_id, "environment_id")

    obs_cursor = db.execute(
        f"""
        SELECT id, environment_id, source, job_id, r2_object_key, content_sha256, data_json, observed_at
        FROM harvy_observations
        WHERE object_id = ? AND {obs_scope}
        ORDER BY observed_at DESC
        """,
        [object_urn, *obs_params],
    )

    observations = [
        {
            "id": r[0],
            "environment_id": r[1],
            "source": r[2],
            "job_id": r[3],
            "r2_object_key": r[4],
            "content_sha256": r[5],
            "data": r[6],
            "observed_at": r[7],
        }
        for r in obs_cursor.fetchall()
    ]

    return {
        "object": {
            "id": oid,
            "type": tid,
            "display_name": name,
            "canonical_url": url,
            "attributes": attrs,
            "created_at": created,
            "updated_at": updated,
        },
        "observations": observations,
    }
