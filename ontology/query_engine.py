"""Allowlisted Query Catalog and compilation engine for Harvy Shared Ontology."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from ontology.contracts import build_scope_filter

CATALOG: Dict[str, Any] = {
    "metrics": {
        "objects.count": {
            "name": "Total Objects",
            "description": "Total number of canonical entities accessible in scope",
            "sql": "SELECT count(DISTINCT o.id) AS value FROM harvy_objects o JOIN harvy_observations obs ON o.id = obs.object_id WHERE {scope_clause}",
            "table_prefix": "obs",
            "type": "scalar",
        },
        "observations.count": {
            "name": "Total Observations",
            "description": "Count of observation events in scope",
            "sql": "SELECT count(*) AS value FROM harvy_observations obs WHERE {scope_clause}",
            "table_prefix": "obs",
            "type": "scalar",
        },
        "links.count": {
            "name": "Total Relationships",
            "description": "Count of active graph links in scope",
            "sql": "SELECT count(*) AS value FROM harvy_links lnk WHERE {scope_clause}",
            "table_prefix": "lnk",
            "type": "scalar",
        },
        "objects.by_type": {
            "name": "Objects by Type",
            "description": "Distribution of entities by type",
            "sql": "SELECT o.type_id AS dimension, count(DISTINCT o.id) AS value FROM harvy_objects o JOIN harvy_observations obs ON o.id = obs.object_id WHERE {scope_clause} GROUP BY o.type_id ORDER BY value DESC",
            "table_prefix": "obs",
            "type": "distribution",
        },
        "observations.by_source": {
            "name": "Observations by Source",
            "description": "Distribution of observations across platforms",
            "sql": "SELECT obs.source AS dimension, count(*) AS value FROM harvy_observations obs WHERE {scope_clause} GROUP BY obs.source ORDER BY value DESC",
            "table_prefix": "obs",
            "type": "distribution",
        },
        "observations.timeseries": {
            "name": "Daily Observation Activity",
            "description": "Observation volume per day over the last 30 days",
            "sql": "SELECT strftime('%Y-%m-%d', datetime(obs.observed_at, 'unixepoch')) AS dimension, count(*) AS value FROM harvy_observations obs WHERE {scope_clause} GROUP BY dimension ORDER BY dimension ASC LIMIT 30",
            "table_prefix": "obs",
            "type": "timeseries",
        },
        "links.by_type": {
            "name": "Links by Type",
            "description": "Distribution of relationship types",
            "sql": "SELECT lnk.link_type AS dimension, count(*) AS value FROM harvy_links lnk WHERE {scope_clause} GROUP BY lnk.link_type ORDER BY value DESC",
            "table_prefix": "lnk",
            "type": "distribution",
        },
    },
    "dimensions": ["type_id", "source", "link_type", "date"],
}


def get_query_catalog() -> Dict[str, Any]:
    """Return public catalog description without internal SQL templates."""
    return {
        "metrics": [
            {
                "id": k,
                "name": v["name"],
                "description": v["description"],
                "type": v["type"],
            }
            for k, v in CATALOG["metrics"].items()
        ],
        "dimensions": CATALOG["dimensions"],
    }


def compile_metric_query(
    metric_id: str,
    environment_id: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Any]]:
    """Compile an allowlisted metric query with strict environment scoping.

    Raises ValueError if metric_id is not in allowlisted catalog.
    """
    if metric_id not in CATALOG["metrics"]:
        raise ValueError(f"Invalid or disallowed metric: '{metric_id}'")

    spec = CATALOG["metrics"][metric_id]
    prefix = spec["table_prefix"]
    scope_clause, params = build_scope_filter(environment_id, f"{prefix}.environment_id")

    extra_clauses = []
    if filters and isinstance(filters, dict):
        if "source" in filters and isinstance(filters["source"], str) and prefix == "obs":
            extra_clauses.append("obs.source = ?")
            params.append(filters["source"])
        if "type_id" in filters and isinstance(filters["type_id"], str) and "o.type_id" in spec["sql"]:
            extra_clauses.append("o.type_id = ?")
            params.append(filters["type_id"])
        if "link_type" in filters and isinstance(filters["link_type"], str) and prefix == "lnk":
            extra_clauses.append("lnk.link_type = ?")
            params.append(filters["link_type"])
        if "since" in filters and isinstance(filters["since"], (int, float)) and prefix == "obs":
            extra_clauses.append("obs.observed_at >= ?")
            params.append(int(filters["since"]))

    full_scope = scope_clause
    if extra_clauses:
        full_scope = f"{scope_clause} AND {' AND '.join(extra_clauses)}"

    compiled_sql = spec["sql"].format(scope_clause=full_scope)
    return compiled_sql, params


def get_cube_meta() -> Dict[str, Any]:
    """Return Cube.js/Drizzle-Cube semantic metadata catalog."""
    return {
        "cubes": [
            {
                "name": "Observations",
                "title": "Observations",
                "measures": [
                    {
                        "name": "Observations.count",
                        "title": "Count",
                        "shortTitle": "Count",
                        "type": "number",
                        "aggType": "count",
                        "isVisible": True,
                    }
                ],
                "dimensions": [
                    {
                        "name": "Observations.source",
                        "title": "Source Network",
                        "type": "string",
                        "isVisible": True,
                    },
                    {
                        "name": "Observations.typeId",
                        "title": "Entity Type",
                        "type": "string",
                        "isVisible": True,
                    },
                    {
                        "name": "Observations.environmentId",
                        "title": "Environment",
                        "type": "string",
                        "isVisible": True,
                    },
                ],
                "timeDimensions": [
                    {
                        "name": "Observations.observedAt",
                        "title": "Observed At",
                        "type": "time",
                        "isVisible": True,
                    }
                ],
            },
            {
                "name": "Objects",
                "title": "Entities",
                "measures": [
                    {
                        "name": "Objects.count",
                        "title": "Count",
                        "shortTitle": "Count",
                        "type": "number",
                        "aggType": "count",
                        "isVisible": True,
                    }
                ],
                "dimensions": [
                    {
                        "name": "Objects.typeId",
                        "title": "Type",
                        "type": "string",
                        "isVisible": True,
                    }
                ],
            },
            {
                "name": "Links",
                "title": "Graph Relationships",
                "measures": [
                    {
                        "name": "Links.count",
                        "title": "Count",
                        "shortTitle": "Count",
                        "type": "number",
                        "aggType": "count",
                        "isVisible": True,
                    }
                ],
                "dimensions": [
                    {
                        "name": "Links.linkType",
                        "title": "Relationship Type",
                        "type": "string",
                        "isVisible": True,
                    }
                ],
            },
        ]
    }



def get_cube_meta() -> Dict[str, Any]:
    """Return Cube.js/Drizzle-Cube semantic metadata catalog."""
    return {
        "cubes": [
            {
                "name": "Observations",
                "title": "Observations",
                "measures": [
                    {
                        "name": "Observations.count",
                        "title": "Count",
                        "shortTitle": "Count",
                        "type": "number",
                        "aggType": "count",
                        "isVisible": True,
                    }
                ],
                "dimensions": [
                    {
                        "name": "Observations.source",
                        "title": "Source Network",
                        "type": "string",
                        "isVisible": True,
                    },
                    {
                        "name": "Observations.typeId",
                        "title": "Entity Type",
                        "type": "string",
                        "isVisible": True,
                    },
                    {
                        "name": "Observations.environmentId",
                        "title": "Environment",
                        "type": "string",
                        "isVisible": True,
                    },
                ],
                "timeDimensions": [
                    {
                        "name": "Observations.observedAt",
                        "title": "Observed At",
                        "type": "time",
                        "isVisible": True,
                    }
                ],
            },
            {
                "name": "Objects",
                "title": "Entities",
                "measures": [
                    {
                        "name": "Objects.count",
                        "title": "Count",
                        "shortTitle": "Count",
                        "type": "number",
                        "aggType": "count",
                        "isVisible": True,
                    }
                ],
                "dimensions": [
                    {
                        "name": "Objects.typeId",
                        "title": "Type",
                        "type": "string",
                        "isVisible": True,
                    }
                ],
            },
            {
                "name": "Links",
                "title": "Graph Relationships",
                "measures": [
                    {
                        "name": "Links.count",
                        "title": "Count",
                        "shortTitle": "Count",
                        "type": "number",
                        "aggType": "count",
                        "isVisible": True,
                    }
                ],
                "dimensions": [
                    {
                        "name": "Links.linkType",
                        "title": "Relationship Type",
                        "type": "string",
                        "isVisible": True,
                    }
                ],
            },
        ]
    }

