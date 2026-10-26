"""Versioned internal envelope for scraper jobs and results."""
import re
from urllib.parse import urlparse

VERSION = 1
PROTOCOL_V1 = 1
PROTOCOL_V2 = 2
SUPPORTED_PROTOCOLS = {PROTOCOL_V1, PROTOCOL_V2}

V1_OPERATIONS = {"profile", "posts", "followers", "following"}
V2_OPERATIONS = V1_OPERATIONS | {"research", "legal", "map", "username", "crawl", "search"}
ALL_OPERATIONS = V2_OPERATIONS

VALID_STATUSES = {"complete", "partial", "failed", "inconclusive"}


def network_for_url(url):
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if host in {"facebook.com", "instagram.com", "threads.com", "threads.net", "x.com", "twitter.com", "truthsocial.com"}:
        return {"facebook.com": "facebook", "instagram.com": "instagram", "threads.com": "threads",
                "threads.net": "threads", "x.com": "x", "twitter.com": "x", "truthsocial.com": "truthsocial"}[host]
    return host


def make_job(job_id, url, operation="profile", options=None, environment_id="shared", limits=None, source=None, protocol=VERSION):
    if not job_id or not isinstance(url, str):
        raise ValueError("Scrape job requires an id and URL")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Scrape targets must be credential-free HTTPS URLs")
    if protocol not in SUPPORTED_PROTOCOLS:
        raise ValueError("Unsupported scrape job protocol")
    if operation not in ALL_OPERATIONS:
        raise ValueError("Unsupported scrape operation")
    if options is not None and not isinstance(options, dict):
        raise ValueError("Scrape job options must be an object")
    if limits is not None and not isinstance(limits, dict):
        raise ValueError("Scrape job limits must be an object")
    if environment_id is not None and (not isinstance(environment_id, str) or not re.fullmatch(r"[\w.-]+", environment_id)):
        raise ValueError("Invalid environment_id")

    net = network_for_url(url)
    src = str(source) if source else net
    env = str(environment_id) if environment_id else "shared"

    return {
        "protocol": protocol,
        "job_id": str(job_id),
        "network": net,
        "source": src,
        "operation": operation,
        "target": url,
        "environment_id": env,
        "limits": dict(limits or {}),
        "options": dict(options or {}),
    }


def make_legal_job(job_id, query, sources, first_name="", last_name="", state="", environment_id="shared", limits=None, options=None, protocol=VERSION):
    from scrape.jobs import ARREST_STATE_SLUGS, RESEARCH_SOURCES

    if not isinstance(query, str) or len(query.strip()) < 2 or len(query) > 200:
        raise ValueError("Enter a search query between 2 and 200 characters")
    if (not isinstance(sources, list) or not sources
            or any(not isinstance(source, str) or source not in RESEARCH_SOURCES for source in sources)):
        raise ValueError("Select one or more supported legal sources")
    first, last = (first_name or "").strip(), (last_name or "").strip()
    if len(first) > 80 or len(last) > 80:
        raise ValueError("First and last names must be 80 characters or fewer")
    state_code = (state or "").strip().upper()
    if state_code and state_code not in ARREST_STATE_SLUGS:
        raise ValueError("Select a supported state")
    if "arrests_org" in sources and (not first or not last or not state_code):
        raise ValueError("Arrests.org requires first name, last name, and state")

    legal_options = dict(options or {})
    legal_options.update({
        "mode": "legal",
        "query": query.strip(),
        "first_name": first,
        "last_name": last,
        "state": state_code,
        "sources": list(dict.fromkeys(sources)),
    })
    legal_limits = dict(limits or {})
    if "max_records" not in legal_limits:
        legal_limits["max_records"] = 10

    # Default canonical legal endpoint target
    target_url = "https://harvy.internal/legal/search"
    return make_job(
        job_id=job_id,
        url=target_url,
        operation="legal",
        options=legal_options,
        environment_id=environment_id,
        limits=legal_limits,
        source="legal_search",
        protocol=protocol,
    )


def validate_job(message):
    if not isinstance(message, dict) or message.get("protocol") not in SUPPORTED_PROTOCOLS:
        raise ValueError("Unsupported scrape job protocol")
    proto = message.get("protocol")
    options = message.get("options", {})
    if not isinstance(options, dict):
        raise ValueError("Malformed scrape job envelope")

    # If it is a strict legacy v1 message without extended keys
    is_strict_v1 = (
        proto == PROTOCOL_V1
        and "environment_id" not in message
        and "limits" not in message
        and "source" not in message
    )
    if is_strict_v1:
        if message.get("operation") not in V1_OPERATIONS:
            raise ValueError("Unsupported scrape operation")
        expected = {
            "protocol": PROTOCOL_V1,
            "job_id": str(message.get("job_id")),
            "network": network_for_url(str(message.get("target"))),
            "operation": message.get("operation", "profile"),
            "target": str(message.get("target")),
            "options": dict(options),
        }
        if message.get("network") != expected["network"]:
            raise ValueError("Malformed scrape job envelope")
        return expected

    expected = make_job(
        message.get("job_id"),
        message.get("target"),
        message.get("operation", "profile"),
        options=options,
        environment_id=message.get("environment_id", "shared"),
        limits=message.get("limits"),
        source=message.get("source"),
        protocol=proto,
    )
    if message.get("network") != expected["network"]:
        raise ValueError("Malformed scrape job envelope")
    return expected


def make_result(job, status, records=None, error=None, completeness=None, provenance=None):
    if status not in VALID_STATUSES:
        raise ValueError("Unsupported scrape result status")
    proto = job.get("protocol", VERSION)
    net = job.get("network") or network_for_url(job.get("target", ""))
    src = job.get("source") or net
    env = job.get("environment_id", "shared")

    comp = dict(completeness) if isinstance(completeness, dict) else {
        "complete": status == "complete",
        "status": status,
    }
    prov = dict(provenance) if isinstance(provenance, dict) else {
        "target": job.get("target"),
        "source": src,
    }

    return {
        "protocol": proto,
        "job_id": str(job["job_id"]),
        "network": net,
        "source": src,
        "operation": job.get("operation", "profile"),
        "target": job["target"],
        "environment_id": env,
        "status": status,
        "completeness": comp,
        "provenance": prov,
        "records": list(records or []),
        "error": error,
    }


def to_v1_job(job):
    """Compatibility adapter: convert an extended job envelope to strict v1 format."""
    if not isinstance(job, dict):
        raise ValueError("Invalid job envelope")
    return {
        "protocol": PROTOCOL_V1,
        "job_id": str(job["job_id"]),
        "network": job.get("network") or network_for_url(job["target"]),
        "operation": job.get("operation", "profile"),
        "target": job["target"],
        "options": dict(job.get("options") or {}),
    }


def to_v1_result(result):
    """Compatibility adapter: convert an extended result envelope to strict v1 format."""
    if not isinstance(result, dict):
        raise ValueError("Invalid result envelope")
    return {
        "protocol": PROTOCOL_V1,
        "job_id": str(result["job_id"]),
        "network": result.get("network") or network_for_url(result["target"]),
        "operation": result.get("operation", "profile"),
        "target": result["target"],
        "status": result["status"],
        "records": list(result.get("records") or []),
        "error": result.get("error"),
    }


def from_v1_job(job, environment_id="shared", limits=None):
    """Compatibility adapter: upgrade a v1 job envelope to extended protocol."""
    if not isinstance(job, dict):
        raise ValueError("Invalid job envelope")
    opts = dict(job.get("options") or {})
    extracted_limits = dict(limits or {})
    if "max_posts" in opts and "max_posts" not in extracted_limits:
        extracted_limits["max_posts"] = opts["max_posts"]
    net = job.get("network") or network_for_url(job["target"])
    return {
        "protocol": PROTOCOL_V2,
        "job_id": str(job["job_id"]),
        "network": net,
        "source": job.get("source") or net,
        "operation": job.get("operation", "profile"),
        "target": job["target"],
        "environment_id": environment_id,
        "limits": extracted_limits,
        "options": opts,
    }


def from_v1_result(result, completeness=None, provenance=None):
    """Compatibility adapter: upgrade a v1 result envelope to extended protocol."""
    if not isinstance(result, dict):
        raise ValueError("Invalid result envelope")
    net = result.get("network") or network_for_url(result["target"])
    src = result.get("source") or net
    comp = dict(completeness) if isinstance(completeness, dict) else {
        "complete": result.get("status") == "complete",
        "status": result.get("status"),
    }
    prov = dict(provenance) if isinstance(provenance, dict) else {
        "target": result.get("target"),
        "source": src,
    }
    return {
        "protocol": PROTOCOL_V2,
        "job_id": str(result["job_id"]),
        "network": net,
        "source": src,
        "operation": result.get("operation", "profile"),
        "target": result["target"],
        "environment_id": "shared",
        "status": result.get("status"),
        "completeness": comp,
        "provenance": prov,
        "records": list(result.get("records") or []),
        "error": result.get("error"),
    }
