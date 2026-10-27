#!/usr/bin/env python3
"""Start a bounded Platform v2 JudyRecords bulk run without handling secrets."""
import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

ALLOWED_HOSTS = {"judyrecords.com", "www.judyrecords.com"}
ENVIRONMENT_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")


def _valid_seed(seed):
    try:
        url = urllib.parse.urlparse(seed)
    except ValueError:
        return False
    return url.scheme == "https" and url.hostname in ALLOWED_HOSTS and not url.username and not url.password


def build_run(seeds, mode="links", limit=50, environment_id="shared", idempotency_key=None):
    if not isinstance(seeds, list):
        raise ValueError("seeds must contain 1-20 HTTPS JudyRecords URLs without credentials")
    normalized_seeds = []
    for seed in seeds:
        if not isinstance(seed, str):
            raise ValueError("seeds must contain 1-20 HTTPS JudyRecords URLs without credentials")
        seed = seed.strip()
        if not _valid_seed(seed):
            raise ValueError("seeds must contain 1-20 HTTPS JudyRecords URLs without credentials")
        normalized_seeds.append(seed)
    if not 1 <= len(normalized_seeds) <= 20:
        raise ValueError("seeds must contain 1-20 HTTPS JudyRecords URLs without credentials")
    normalized_seeds = list(dict.fromkeys(normalized_seeds))
    if mode not in ("links", "crawl"):
        raise ValueError("mode must be links or crawl")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 to 100")
    if not isinstance(environment_id, str) or not ENVIRONMENT_RE.fullmatch(environment_id):
        raise ValueError("environment_id must be 1-100 characters from A-Za-z0-9._:-")
    if idempotency_key is None:
        digest_input = json.dumps(
            {"seeds": normalized_seeds, "mode": mode, "limit": limit, "environment_id": environment_id},
            sort_keys=True,
        )
        idempotency_key = "judy-" + hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:32]
    elif not isinstance(idempotency_key, str) or not IDEMPOTENCY_RE.fullmatch(idempotency_key):
        raise ValueError("idempotency_key must be 1-160 characters from A-Za-z0-9._:-")
    return {
        "connector": "judyrecords",
        "environment_id": environment_id,
        "idempotency_key": idempotency_key,
        "input": {"seeds": normalized_seeds, "mode": mode, "limit": limit},
    }


def post_run(base_url, token, run, timeout=30):
    parsed = urllib.parse.urlparse(base_url or "")
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("V2_SUPERVISOR_URL must be an HTTPS URL without credentials")
    if not isinstance(token, str) or not token or any(character.isspace() for character in token):
        raise ValueError("V2_SUPERVISOR_TOKEN must be a non-empty bearer token")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v2/runs",
        data=json.dumps(run).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read(100_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read(100_000).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("Could not connect to the v2 supervisor.") from None
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        data = {"error": "supervisor returned a non-JSON response"}
    return status, data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", action="append", required=True,
                        help="HTTPS JudyRecords seed URL; repeat for up to 20 seeds")
    parser.add_argument("--mode", choices=["links", "crawl"], default="links")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--environment", default="shared")
    parser.add_argument("--idempotency-key")
    args = parser.parse_args(argv)
    base_url = os.environ.get("V2_SUPERVISOR_URL", "")
    token = os.environ.get("V2_SUPERVISOR_TOKEN", "")
    if not base_url or not token:
        parser.error("V2_SUPERVISOR_URL and V2_SUPERVISOR_TOKEN are required")
    try:
        run = build_run(args.seed, mode=args.mode, limit=args.limit,
                        environment_id=args.environment, idempotency_key=args.idempotency_key)
        status, data = post_run(base_url, token, run)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({"status": status, "response": data}, ensure_ascii=False))
    return 0 if status in (200, 202) else 1


if __name__ == "__main__":
    raise SystemExit(main())
