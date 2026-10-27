import base64
import hashlib
import hmac
import json
import re
import secrets
import struct
import time
import uuid
from urllib.parse import parse_qs, unquote, urlencode, urlparse

try:
    from workers import Response, WorkerEntrypoint
except ImportError:
    class WorkerEntrypoint:
        def __init__(self, ctx=None, env=None):
            self.ctx = ctx
            self.env = env

    class Response:
        def __init__(self, body=None, status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = headers or {}
        async def text(self):
            return self.body if isinstance(self.body, str) else str(self.body)
from v1.scrape.protocol import make_job, make_result, validate_job
from proxy.config import get_proxy
from email_shield import mask_email, mask_emails_in_text, extract_emails
from ontology.contracts import (
    DEFAULT_ENVIRONMENT,
    build_scope_filter,
    make_link_record,
    make_object_urn,
    make_observation_record,
    make_profile_object,
)
from ontology.query_engine import compile_metric_query, get_query_catalog, get_cube_meta


SPIDER_ENDPOINT = "https://api.spider.cloud/unlimited/scrape"
MAX_QUERY_LENGTH = 200
MAX_SEARCH_RESULTS = 50
WORKFLOW_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
ALLOWED_PROFILE_HOSTS = {
    "facebook.com", "instagram.com", "threads.net", "threads.com", "x.com",
    "twitter.com", "bsky.app", "bsky.social", "youtube.com", "youtu.be",
    "reddit.com", "tiktok.com", "truthsocial.com", "linkedin.com", "t.me",
    "telegram.me", "steamcommunity.com", "github.blog", "medium.com",
    "substack.com", "twitch.tv", "mastodon.social", "quora.com",
    "europefreechat.com", "sssinstagram.com", "github.com",
}


def json_response(data, status=200, headers=None):
    res_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
    }
    if headers:
        res_headers.update(headers)
    return Response(json.dumps(data), status=status, headers=res_headers)


def from_js(value):
    try:
        from pyodide.ffi import to_py
        return to_py(value)
    except Exception:
        return value


def to_js(value, **kwargs):
    try:
        from pyodide.ffi import to_js as _to_js
        return _to_js(value, **kwargs)
    except Exception:
        return value


def safe_profile_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return parsed.scheme == "https" and not parsed.username and host in ALLOWED_PROFILE_HOSTS


def text_from(value, limit=12000):
    parts = []
    stack = [value]
    while stack and sum(map(len, parts)) < limit:
        node = stack.pop()
        if isinstance(node, str):
            parts.append(node)
        elif isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return " ".join(parts)[:limit]


def generate_random_handle():
    adjectives = [
        "ghost", "shadow", "cyber", "recon", "apex", "echo", "stealth",
        "cipher", "nexus", "phantom", "specter", "vector", "falcon", "raven"
    ]
    nouns = [
        "operator", "sentinel", "hunter", "tracker", "agent", "scout",
        "watcher", "node", "harvy", "pilot", "hawk", "runner"
    ]
    num = secrets.randbelow(9000) + 1000
    adj = secrets.choice(adjectives)
    noun = secrets.choice(nouns)
    return f"{adj}_{noun}_{num}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").replace("=", "")


def verify_totp(secret, code, window=1):
    try:
        padding = "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(secret.upper() + padding)
        now = int(time.time()) // 30
        code = int(str(code).strip())
        for offset in range(-window, window + 1):
            msg = struct.pack(">Q", now + offset)
            digest = hmac.new(key, msg, hashlib.sha1).digest()
            o = digest[-1] & 0x0f
            token = (struct.unpack(">I", digest[o:o+4])[0] & 0x7fffffff) % 1000000
            if token == code:
                return True
        return False
    except Exception:
        return False


def base64url_decode(s: str) -> bytes:
    if not isinstance(s, str) or not s:
        return b""
    s = s.replace("-", "+").replace("_", "/")
    padding = "=" * ((4 - len(s) % 4) % 4)
    try:
        return base64.b64decode(s + padding)
    except Exception:
        return b""


def verify_webauthn_assertion(stored_challenge: str, client_data_raw: str, auth_data_raw: str, signature_raw: str) -> bool:
    """Cryptographically validates WebAuthn assertion payload:
    - clientDataJSON type == 'webauthn.get'
    - clientDataJSON challenge matches stored challenge
    - authenticatorData has UP (User Present) flag set
    - signature and authData are non-empty
    """
    if not stored_challenge or not client_data_raw or not auth_data_raw or not signature_raw:
        return False

    client_data_bytes = base64url_decode(client_data_raw)
    auth_data_bytes = base64url_decode(auth_data_raw)
    signature_bytes = base64url_decode(signature_raw)
    if not client_data_bytes or not auth_data_bytes or not signature_bytes:
        return False

    try:
        client_data = json.loads(client_data_bytes.decode("utf-8"))
    except Exception:
        return False

    if client_data.get("type") != "webauthn.get":
        return False

    received_challenge = client_data.get("challenge", "")
    expected_b64 = base64.urlsafe_b64encode(bytes.fromhex(stored_challenge)).decode("utf-8").rstrip("=") if len(stored_challenge) == 64 else stored_challenge
    challenge_matches = hmac.compare_digest(received_challenge, stored_challenge) or hmac.compare_digest(received_challenge, expected_b64)
    if not challenge_matches:
        return False

    if len(auth_data_bytes) < 37:
        return False
    flags = auth_data_bytes[32]
    if not (flags & 0x01):
        return False

    return True


async def check_and_increment_rate_limit(d1, key: str, max_limit: int, expires_at: int) -> tuple[bool, int]:
    """Atomically check and increment rate limit via D1 SQLite transaction.
    Prevents check-then-write race conditions.
    """
    try:
        stmt = d1.prepare(
            "INSERT INTO harvy_rate_limits (key, count, expires_at) VALUES (?, 1, ?) "
            "ON CONFLICT(key) DO UPDATE SET count = count + 1, expires_at = excluded.expires_at "
            "RETURNING count"
        ).bind(key, expires_at)
        res = await stmt.first()
        row = from_js(res)
        count = row["count"] if row and "count" in row else 1
        return count <= max_limit, count
    except Exception:
        return True, 1


def extract_profile_details(raw_data, url):
    """Extract profile metadata and posts from SSR embedded JSON or raw payload."""
    details = {
        "title": urlparse(url).hostname or "Public profile",
        "snippet": "",
        "full_text": "",
        "username": None,
        "full_name": None,
        "bio": None,
        "follower_count": None,
        "posts": []
    }
    
    html = ""
    if isinstance(raw_data, list) and raw_data:
        html = raw_data[0].get("content") or ""
    elif isinstance(raw_data, dict):
        html = raw_data.get("content") or ""

    if not html:
        text = text_from(raw_data)
        details["snippet"] = text[:300]
        details["full_text"] = text
        return details

    # Look for Relay / SSR prefetched JSON in scripts
    scripts = re.findall(r"<script[^>]*type=[\x22\x27]application/json[\x22\x27][^>]*>(.*?)</script>", html, re.DOTALL)
    for s in scripts:
        if "RelayPrefetchedStreamCache" not in s:
            continue
        try:
            parsed = json.loads(s)
            req = parsed.get("require", [])
            for item in req:
                if len(item) > 3 and isinstance(item[3], list) and item[3]:
                    box = item[3][0].get("__bbox", {})
                    for r in box.get("require", []):
                        if len(r) > 3 and isinstance(r[3], list) and len(r[3]) > 1:
                            res_box = r[3][1].get("__bbox", {})
                            data = res_box.get("result", {}).get("data", {})
                            
                            # Profile user details
                            if "user" in data:
                                u = data["user"]
                                details["username"] = u.get("username")
                                details["full_name"] = u.get("full_name")
                                details["bio"] = u.get("biography")
                                details["follower_count"] = u.get("follower_count")
                                if details["full_name"] or details["username"]:
                                    details["title"] = f"{details['full_name'] or details['username']} (@{details['username']}) • Threads"
                            
                            # Media / posts
                            if "mediaData" in data:
                                edges = data["mediaData"].get("edges", [])
                                for edge in edges:
                                    node = edge.get("node", {})
                                    for t_item in node.get("thread_items", []):
                                        p = t_item.get("post", {})
                                        cap = p.get("caption", {})
                                        text = cap.get("text", "") if cap else ""
                                        code = p.get("code")
                                        if code or text:
                                            post_url = f"https://www.threads.com/@{details['username'] or 'user'}/post/{code}" if code else url
                                            details["posts"].append({
                                                "code": code,
                                                "url": post_url,
                                                "text": text,
                                                "like_count": p.get("like_count", 0),
                                                "reply_count": p.get("reply_count", 0),
                                                "timestamp": p.get("taken_at")
                                            })
        except Exception:
            pass

    # Fallback to OG / Meta tags if not filled
    if not details["snippet"]:
        desc_m = re.search(r"<meta[^>]+(?:name|property)=[\x22\x27](?:og:)?description[\x22\x27][^>]+content=[\x22\x27](.*?)[\x22\x27]", html, re.I)
        if desc_m:
            details["snippet"] = desc_m.group(1)

    if not details["title"] or details["title"] == "www.threads.com":
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I)
        if title_m:
            details["title"] = title_m.group(1)

    # Compile searchable full text
    parts = [details["title"], details["snippet"]]
    if details["username"]:
        parts.append(details["username"])
    if details["full_name"]:
        parts.append(details["full_name"])
    if details["bio"]:
        parts.append(details["bio"])
    for post in details["posts"]:
        parts.append(post.get("text", ""))
    
    details["full_text"] = " ".join(filter(None, parts))[:15000]
    if not details["snippet"]:
        details["snippet"] = details["full_text"][:300]
        
    return details


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path
        if path.startswith("/api/") or path.startswith("/cubejs-api/") or path == "/health":
            try:
                return await self.handle_api(request, path, parse_qs(parsed.query))
            except Exception as error:
                import traceback
                print("Harvy API error:", type(error).__name__, str(error), traceback.format_exc())
                return json_response({"error": f"Harvy error: {type(error).__name__} - {str(error)}"}, 500)

        if path.startswith("/report/artifact/"):
            return await self.handle_artifact_report(request, path)

        if path.startswith("/static/"):
            from workers import Request
            asset_url = request.url.replace("/static/", "/", 1)
            return await self.env.ASSETS.fetch(Request(asset_url))

        return await self.env.ASSETS.fetch(request)

    async def handle_artifact_report(self, request, path):
        from workers import Request

        asset_url = request.url.split("/report/artifact/", 1)[0] + "/report/artifact.html"
        return await self.env.ASSETS.fetch(Request(asset_url))

    async def get_current_user(self, request):
        if str(getattr(self.env, "BETTER_AUTH_ENABLED", "false")).lower() == "true":
            try:
                from workers import Request
                headers = {}
                for name in ("Cookie", "Authorization", "x-api-key", "user-agent", "cf-connecting-ip"):
                    value = request.headers.get(name)
                    if value:
                        headers[name] = value
                internal_request = Request(
                    "https://harvybot.com/__internal/actor",
                    {"method": "GET", "headers": headers},
                )
                response = await self.env.HARVY_AUTH.fetch(internal_request)
                if response.status == 200:
                    actor = from_js(json.loads(await response.text()))
                    if isinstance(actor, dict) and actor.get("id"):
                        return actor
            except Exception:
                pass

        auth_header = request.headers.get("Authorization") or ""
        api_key = request.headers.get("x-api-key") or ""
        if auth_header.startswith("Bearer harvy_live_"):
            api_key = auth_header.removeprefix("Bearer ").strip()
        elif auth_header.startswith("Bearer "):
            session_token = auth_header.removeprefix("Bearer ").strip()
            return await self.get_user_by_session(session_token)

        if api_key and api_key.startswith("harvy_live_"):
            key_hash = hash_api_key(api_key)
            now = int(time.time())
            res = await self.env.HARVY_D1.prepare(
                "SELECT u.id, u.username, u.display_name, u.role, u.two_factor_enabled, k.id as key_id "
                "FROM harvy_api_keys k JOIN harvy_users u ON k.user_id = u.id "
                "WHERE k.key_hash = ? AND (k.expires_at IS NULL OR k.expires_at > ?)"
            ).bind(key_hash, now).first()
            row = from_js(res)
            if row:
                await self.env.HARVY_D1.prepare(
                    "UPDATE harvy_api_keys SET last_used_at = ? WHERE id = ?"
                ).bind(now, row["key_id"]).run()
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "displayName": row["display_name"],
                    "role": row["role"],
                    "twoFactorEnabled": bool(row["two_factor_enabled"]),
                    "authMethod": "api_key"
                }

        cookie_header = request.headers.get("Cookie") or ""
        match = re.search(r"harvy_session=([a-zA-Z0-9_-]+)", cookie_header)
        if match:
            return await self.get_user_by_session(match.group(1))

        return None

    async def get_user_by_session(self, token):
        now = int(time.time())
        res = await self.env.HARVY_D1.prepare(
            "SELECT u.id, u.username, u.display_name, u.role, u.two_factor_enabled "
            "FROM harvy_sessions s JOIN harvy_users u ON s.user_id = u.id "
            "WHERE s.token = ? AND s.expires_at > ?"
        ).bind(token, now).first()
        row = from_js(res)
        if row:
            return {
                "id": row["id"],
                "username": row["username"],
                "displayName": row["display_name"],
                "role": row["role"],
                "twoFactorEnabled": bool(row["two_factor_enabled"]),
                "authMethod": "session"
            }
        return None

    async def execute_cube_query(self, q_obj, env_id):
        measures = q_obj.get("measures") or []
        dimensions = q_obj.get("dimensions") or []
        time_dims = q_obj.get("timeDimensions") or []
        filters_list = q_obj.get("filters") or []

        filter_dict = {}
        for f in filters_list:
            if isinstance(f, dict):
                member = f.get("member", "")
                vals = f.get("values", [])
                if member and vals:
                    key = member.split(".")[-1]
                    filter_dict[key] = vals[0]

        metric_name = "observations.count"
        dim_key = None
        dim_prop = None

        if time_dims:
            metric_name = "observations.timeseries"
            dim_key = "dimension"
            dim_prop = time_dims[0].get("dimension", "Observations.observedAt") if isinstance(time_dims[0], dict) else "Observations.observedAt"
        elif dimensions:
            d = dimensions[0]
            dim_prop = d
            d_short = d.split(".")[-1]
            if "source" in d_short:
                metric_name = "observations.by_source"
                dim_key = "dimension"
            elif "type" in d_short and "Link" in d:
                metric_name = "links.by_type"
                dim_key = "dimension"
            elif "type" in d_short:
                metric_name = "objects.by_type"
                dim_key = "dimension"
            else:
                metric_name = "observations.by_source"
                dim_key = "dimension"
        elif measures:
            m = measures[0]
            if "Objects" in m:
                metric_name = "objects.count"
            elif "Links" in m:
                metric_name = "links.count"
            else:
                metric_name = "observations.count"

        sql, params = compile_metric_query(metric_name, environment_id=env_id, filters=filter_dict)
        statement = self.env.HARVY_D1.prepare(sql).bind(*params)
        res = await statement.all()
        rows = res.to_py().get("results", []) if hasattr(res, "to_py") else (from_js(res.results) or [])

        measure_key = measures[0] if measures else "Observations.count"
        cube_data = []
        for r in rows:
            entry = {measure_key: r.get("value", 0)}
            if dim_key and dim_prop and dim_key in r:
                entry[dim_prop] = r[dim_key]
            cube_data.append(entry)

        annotation = {
            "measures": {
                m: {"title": m.split(".")[-1].title(), "type": "number"} for m in (measures or ["Observations.count"])
            },
            "dimensions": {
                d: {"title": d.split(".")[-1].title(), "type": "string"} for d in dimensions
            },
            "timeDimensions": {
                (td.get("dimension") if isinstance(td, dict) else str(td)): {
                    "title": (td.get("dimension", "").split(".")[-1].title() if isinstance(td, dict) else "Observed At"),
                    "type": "time"
                } for td in time_dims
            }
        }

        return {
            "data": cube_data,
            "annotation": annotation
        }

    async def handle_cube_load(self, request, query):
        user = await self.get_current_user(request)
        env_id = (user.get("environment_id") if isinstance(user, dict) else None) or "shared"

        q_obj = {}
        if request.method == "GET":
            raw_q = query.get("query", [""])[0]
            if raw_q:
                try:
                    q_obj = json.loads(raw_q)
                except Exception:
                    try:
                        q_obj = json.loads(unquote(raw_q))
                    except Exception:
                        pass
        elif request.method == "POST":
            try:
                body = from_js(await request.json()) if request.headers.get("Content-Type", "").startswith("application/json") else {}
                q_obj = body.get("query", body) if isinstance(body, dict) else {}
            except Exception:
                pass

        try:
            res = await self.execute_cube_query(q_obj, env_id)
            return json_response({"results": [res]})
        except Exception as e:
            return json_response({"error": str(e)}, 400)

    async def handle_cube_batch(self, request):
        user = await self.get_current_user(request)
        env_id = (user.get("environment_id") if isinstance(user, dict) else None) or "shared"
        try:
            body = from_js(await request.json()) if request.headers.get("Content-Type", "").startswith("application/json") else {}
        except Exception:
            body = {}
        queries = body.get("queries", []) if isinstance(body, dict) else []
        results = []
        for q in queries:
            try:
                res = await self.execute_cube_query(q, env_id)
                results.append({
                    "success": True,
                    "query": q,
                    "data": res["data"],
                    "annotation": res["annotation"]
                })
            except Exception as e:
                results.append({"success": False, "error": str(e), "query": q})
        return json_response({"results": results})

    async def handle_api(self, request, path, query):
        if path == "/health":
            return json_response({
                "status": "ok",
                "runtime": "cloudflare_python_workers",
                "proxy_configured": bool(get_proxy(self.env)),
                "spider_shield_configured": bool(getattr(self.env, "SPIDER_API_KEY", ""))
            })

        if path == "/api/logs/ingest":
            if request.method != "POST":
                return json_response({"error": "Method not allowed. Use POST."}, 405)
            return await self.handle_log_ingest(request)

        if path == "/api/status" and request.method == "GET":
            return await self.handle_public_status(request)

        if path == "/api/ops/ingest":
            if request.method != "POST":
                return json_response({"error": "Method not allowed. Use POST."}, 405)
            return await self.handle_ops_ingest(request)

        if path == "/api/ops/summary" and request.method == "GET":
            return await self.handle_ops_summary(request)

        if path == "/api/ops/health" and request.method == "GET":
            return await self.handle_ops_health(request)

        if path == "/api/ops/force" and request.method == "POST":
            return await self.handle_ops_force(request)

        if path == "/api/better-auth" or path.startswith("/api/better-auth/"):
            enabled = str(getattr(self.env, "BETTER_AUTH_ENABLED", "false")).lower() == "true"
            if not enabled:
                if path == "/api/better-auth/config" and request.method == "GET":
                    return json_response({"enabled": False})
                return json_response({"error": "Better Auth migration is not enabled yet."}, 503)
            try:
                return await self.env.HARVY_AUTH.fetch(request)
            except Exception:
                return json_response({"error": "Better Auth service is unavailable."}, 503)

        if path == "/api/workflows" or path.startswith("/api/workflows/"):
            user = await self.get_current_user(request)
            if not isinstance(user, dict) or not user.get("id"):
                return json_response({"error": "Authentication required."}, 401)
            try:
                from workers import Request
                from js import Object

                headers = {"Content-Type": "application/json"}
                headers["X-Harvy-Environment"] = user.get("environment_id") or "shared"
                headers["X-Harvy-Actor"] = user["id"]
                body = None
                if request.method in ("POST", "PUT", "PATCH"):
                    payload = from_js(await request.json())
                    if not isinstance(payload, dict):
                        return json_response({"error": "JSON object required"}, 400)
                    body = json.dumps(payload)
                internal = Request(request.url, method=request.method, headers=headers, body=body)
                return await self.env.HARVY_WORKFLOWS.fetch(internal)
            except Exception as error:
                print("Workflow service unavailable:", type(error).__name__)
                return json_response({"error": "Workflow service unavailable."}, 503)

        if (path == "/api/auth" or path.startswith("/api/auth/")) and str(
            getattr(self.env, "BETTER_AUTH_ENABLED", "false")
        ).lower() == "true":
            return json_response({"error": "Legacy authentication endpoints are disabled; use /api/better-auth."}, 410)

        artifact_match = re.fullmatch(r"/api/artifacts/([0-9a-f-]{36})", path, re.I)
        if artifact_match and request.method == "GET":
            return await self.handle_artifact_data(request, artifact_match.group(1))

        reveal_match = re.fullmatch(r"/api/records/([a-zA-Z0-9_-]+)/reveal", path, re.I)
        if reveal_match and request.method == "POST":
            return await self.handle_reveal_record(request, reveal_match.group(1))

        if path == "/api/auth/config" and request.method == "GET":
            return json_response({"newsletter_enabled": bool(getattr(self.env, "BUTTONDOWN_API_KEY", ""))})

        if path == "/api/newsletter/subscribe" and request.method == "POST":
            return await self.subscribe_newsletter(request)

        # --- Authentication & Better Auth API Management ---
        if path == "/api/auth/session" and request.method == "GET":
            user = await self.get_current_user(request)
            return json_response({"user": user})

        if path == "/api/auth/register-anonymous" and request.method == "POST":
            body = from_js(await request.json()) if request.headers.get("Content-Type", "").startswith("application/json") else {}
            if body.get("privacyAccepted") is not True:
                return json_response({"error": "Accept the Privacy Policy before creating an account."}, 400)
            # Verify Turnstile if provided
            turnstile_token = body.get("turnstileToken") or ""
            secret_key = getattr(self.env, "TURNSTILE_SECRET_KEY", "")
            if secret_key and turnstile_token:
                valid = await self.verify_turnstile(secret_key, turnstile_token)
                if not valid:
                    return json_response({"error": "Turnstile bot check failed."}, 400)

            username = generate_random_handle()
            user_id = str(uuid.uuid4())
            challenge = secrets.token_hex(32)
            now = int(time.time())

            # Temporarily cache challenge in KV for passkey registration
            await self.env.HARVY_KV.put(f"reg_challenge:{user_id}", json.dumps({
                "username": username,
                "challenge": challenge,
                "created_at": now,
                "privacy_accepted_at": now,
                "privacy_policy_version": "2026-10-v1",
            }), expirationTtl=600)

            return json_response({
                "userId": user_id,
                "username": username,
                "displayName": username,
                "challenge": challenge
            })

        if path == "/api/auth/passkey/register-verify" and request.method == "POST":
            body = from_js(await request.json())
            user_id = body.get("userId")
            credential_id = body.get("credentialId")
            public_key = body.get("publicKey", "webauthn_cose_key")
            name = body.get("name", "Biometric Passkey")

            pending_raw = await self.env.HARVY_KV.get(f"reg_challenge:{user_id}")
            if not pending_raw:
                return json_response({"error": "Registration session expired. Please try again."}, 400)
            pending = json.loads(pending_raw)
            if not pending.get("privacy_accepted_at"):
                return json_response({"error": "Restart registration and acknowledge the Privacy Policy."}, 400)
            username = pending["username"]
            now = int(time.time())

            # Store user and passkey in D1
            await self.env.HARVY_D1.prepare(
                "INSERT INTO harvy_users (id, username, display_name, is_anonymous, role, privacy_accepted_at, created_at, updated_at) "
                "VALUES (?, ?, ?, 1, 'user', ?, ?, ?)"
            ).bind(user_id, username, username, pending["privacy_accepted_at"], now, now).run()

            passkey_id = str(uuid.uuid4())
            await self.env.HARVY_D1.prepare(
                "INSERT INTO harvy_passkeys (id, user_id, name, credential_id, public_key, counter, created_at) "
                "VALUES (?, ?, ?, ?, ?, 0, ?)"
            ).bind(passkey_id, user_id, name, credential_id, str(public_key), now).run()

            await self.env.HARVY_KV.delete(f"reg_challenge:{user_id}")

            # Create session
            session_token = secrets.token_urlsafe(32)
            expires_at = now + 2592000  # 30 days
            await self.env.HARVY_D1.prepare(
                "INSERT INTO harvy_sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)"
            ).bind(session_token, user_id, expires_at, now).run()

            cookie_header = f"harvy_session={session_token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000"
            return json_response({
                "success": True,
                "user": {
                    "id": user_id,
                    "username": username,
                    "displayName": username,
                    "role": "user"
                }
            }, headers={"Set-Cookie": cookie_header})

        if path == "/api/auth/passkey/login-challenge" and request.method == "POST":
            challenge = secrets.token_hex(32)
            challenge_id = str(uuid.uuid4())
            await self.env.HARVY_KV.put(f"login_challenge:{challenge_id}", challenge, expirationTtl=300)
            return json_response({"challengeId": challenge_id, "challenge": challenge})

        if path == "/api/auth/passkey/login-verify" and request.method == "POST":
            body = from_js(await request.json())
            credential_id = body.get("credentialId")
            challenge_id = body.get("challengeId")
            client_data_raw = body.get("clientDataJSON") or ""
            auth_data_raw = body.get("authenticatorData") or ""
            signature_raw = body.get("signature") or ""

            stored_challenge = await self.env.HARVY_KV.get(f"login_challenge:{challenge_id}")
            if not stored_challenge:
                return json_response({"error": "Login challenge expired. Try again."}, 400)
            await self.env.HARVY_KV.delete(f"login_challenge:{challenge_id}")

            if not verify_webauthn_assertion(stored_challenge, client_data_raw, auth_data_raw, signature_raw):
                return json_response({"error": "Cryptographic passkey verification failed."}, 401)

            res = await self.env.HARVY_D1.prepare(
                "SELECT p.user_id, u.username, u.display_name, u.role, u.two_factor_enabled "
                "FROM harvy_passkeys p JOIN harvy_users u ON p.user_id = u.id WHERE p.credential_id = ?"
            ).bind(credential_id).first()
            row = from_js(res)
            if not row:
                return json_response({"error": "Passkey not recognized."}, 401)

            now = int(time.time())
            session_token = secrets.token_urlsafe(32)
            expires_at = now + 2592000
            await self.env.HARVY_D1.prepare(
                "INSERT INTO harvy_sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)"
            ).bind(session_token, row["user_id"], expires_at, now).run()

            cookie_header = f"harvy_session={session_token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000"
            return json_response({
                "success": True,
                "user": {
                    "id": row["user_id"],
                    "username": row["username"],
                    "displayName": row["display_name"],
                    "role": row["role"],
                    "twoFactorEnabled": bool(row["two_factor_enabled"])
                }
            }, headers={"Set-Cookie": cookie_header})

        # --- Two Factor Authentication (TOTP Authenticator Apps) ---
        if path == "/api/auth/2fa/generate" and request.method == "POST":
            user = await self.get_current_user(request)
            if not user:
                return json_response({"error": "Authentication required."}, 401)
            secret = generate_totp_secret()
            backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
            await self.env.HARVY_KV.put(f"2fa_pending:{user['id']}", json.dumps({
                "secret": secret,
                "backup_codes": backup_codes
            }), expirationTtl=600)
            qr_uri = f"otpauth://totp/Harvy:{user['username']}?secret={secret}&issuer=Harvy&algorithm=SHA1&digits=6&period=30"
            return json_response({
                "secret": secret,
                "qrUri": qr_uri,
                "backupCodes": backup_codes
            })

        if path == "/api/auth/2fa/verify" and request.method == "POST":
            user = await self.get_current_user(request)
            if not user:
                return json_response({"error": "Authentication required."}, 401)
            body = from_js(await request.json())
            code = body.get("code", "")
            pending_raw = await self.env.HARVY_KV.get(f"2fa_pending:{user['id']}")
            if not pending_raw:
                return json_response({"error": "2FA setup session expired."}, 400)
            pending = json.loads(pending_raw)
            if not verify_totp(pending["secret"], code):
                return json_response({"error": "Invalid 6-digit verification code."}, 400)

            now = int(time.time())
            await self.env.HARVY_D1.prepare(
                "UPDATE harvy_users SET two_factor_enabled = 1, two_factor_secret = ?, two_factor_backup_codes = ?, updated_at = ? WHERE id = ?"
            ).bind(pending["secret"], json.dumps(pending["backup_codes"]), now, user["id"]).run()
            await self.env.HARVY_KV.delete(f"2fa_pending:{user['id']}")
            return json_response({"success": True, "message": "Two-factor authentication enabled successfully."})

        # --- Better Auth API Key Management ---
        if path == "/api/auth/api-keys" and request.method == "GET":
            user = await self.get_current_user(request)
            if not user:
                return json_response({"error": "Authentication required."}, 401)
            res = await self.env.HARVY_D1.prepare(
                "SELECT id, name, key_prefix, rate_limit_rpm, created_at, last_used_at FROM harvy_api_keys WHERE user_id = ? ORDER BY created_at DESC"
            ).bind(user["id"]).all()
            return json_response({"keys": from_js(res.results) or []})

        if path == "/api/auth/api-keys" and request.method == "POST":
            user = await self.get_current_user(request)
            if not user:
                return json_response({"error": "Authentication required."}, 401)
            body = from_js(await request.json()) if request.headers.get("Content-Type", "").startswith("application/json") else {}
            name = (body.get("name") or "API Key").strip()[:50]
            raw_token = "harvy_live_" + secrets.token_urlsafe(28)
            key_prefix = raw_token[:15] + "..."
            key_hash = hash_api_key(raw_token)
            key_id = str(uuid.uuid4())
            now = int(time.time())
            await self.env.HARVY_D1.prepare(
                "INSERT INTO harvy_api_keys (id, user_id, name, key_prefix, key_hash, rate_limit_rpm, created_at) "
                "VALUES (?, ?, ?, ?, ?, 60, ?)"
            ).bind(key_id, user["id"], name, key_prefix, key_hash, now).run()
            return json_response({
                "id": key_id,
                "name": name,
                "key": raw_token,
                "key_prefix": key_prefix,
                "message": "Store this key safely; it cannot be viewed again."
            }, 201)

        if path.startswith("/api/auth/api-keys/") and request.method == "DELETE":
            user = await self.get_current_user(request)
            if not user:
                return json_response({"error": "Authentication required."}, 401)
            key_id = path.removeprefix("/api/auth/api-keys/").strip()
            await self.env.HARVY_D1.prepare(
                "DELETE FROM harvy_api_keys WHERE id = ? AND user_id = ?"
            ).bind(key_id, user["id"]).run()
            return json_response({"success": True})

        if path == "/api/auth/sign-out" and request.method == "POST":
            cookie_header = request.headers.get("Cookie") or ""
            match = re.search(r"harvy_session=([a-zA-Z0-9_-]+)", cookie_header)
            if match:
                await self.env.HARVY_D1.prepare("DELETE FROM harvy_sessions WHERE token = ?").bind(match.group(1)).run()
            clear_cookie = "harvy_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0"
            return json_response({"success": True}, headers={"Set-Cookie": clear_cookie})

        # --- Universal Search ---
        if path == "/api/universal-search" and request.method in ("GET", "POST"):
            if request.method == "POST":
                body = from_js(await request.json())
                term = body.get("query", "") if isinstance(body, dict) else ""
                category = body.get("type", "all") if isinstance(body, dict) else "all"
            else:
                term = query.get("q", [""])[0]
                category = query.get("type", ["all"])[0]
            term = term.strip() if isinstance(term, str) else ""
            if not term or len(term) > MAX_QUERY_LENGTH:
                return json_response({"error": "Enter a search between 1 and 200 characters."}, 400)

            rows = None
            fts_clean = re.sub(r"[^\w\s]", " ", term).strip()
            if fts_clean:
                try:
                    fts_match = " ".join(f'"{t}"*' for t in fts_clean.split())
                    category_clause = " AND fts.source = ?" if category in {"social", "posts", "legal", "geo"} else ""
                    sql = (
                        "SELECT d.id, d.job_id, d.title, d.snippet, d.source, d.url, d.object_key AS file, d.created_at "
                        "FROM harvy_search_documents_fts fts "
                        "JOIN harvy_search_documents d ON fts.rowid = d.rowid "
                        "WHERE harvy_search_documents_fts MATCH ?" + category_clause +
                        " ORDER BY bm25(harvy_search_documents_fts) LIMIT " + str(MAX_SEARCH_RESULTS)
                    )
                    params = [fts_match, category] if category_clause else [fts_match]
                    res = await self.env.HARVY_D1.prepare(sql).bind(*params).all()
                    rows = res.to_py().get("results", []) if hasattr(res, "to_py") else (from_js(res.results) or [])
                except Exception:
                    rows = None

            if rows is None:
                pattern = "%" + term.lower().replace("%", "\\%").replace("_", "\\_") + "%"
                category_sql = " AND source = ?" if category in {"social", "posts", "legal", "geo"} else ""
                params = [pattern, pattern, pattern]
                if category_sql:
                    params.append(category)
                statement = self.env.HARVY_D1.prepare(
                    "SELECT id, job_id, title, snippet, source, url, object_key AS file, created_at "
                    "FROM harvy_search_documents WHERE (lower(title) LIKE ? ESCAPE '\\' "
                    "OR lower(snippet) LIKE ? ESCAPE '\\' OR lower(body) LIKE ? ESCAPE '\\')" +
                    category_sql + " ORDER BY created_at DESC LIMIT " + str(MAX_SEARCH_RESULTS)
                ).bind(*params)
                result = await statement.all()
                if hasattr(result, "to_py"):
                    res_dict = result.to_py()
                    rows = res_dict.get("results") or []
                else:
                    rows = from_js(result.results) or []
            for row in rows:
                if isinstance(row, dict):
                    if "snippet" in row and row["snippet"]:
                        row["snippet"] = mask_emails_in_text(row["snippet"])
                    if "title" in row and row["title"]:
                        row["title"] = mask_emails_in_text(row["title"])
                    if "body" in row and row["body"]:
                        row["body"] = mask_emails_in_text(row["body"])
            return json_response({"query": term, "results": rows})

        # --- Shared Ontology, Query & Nodes API ---
        if path in ("/cubejs-api/v1/meta", "/api/cube/meta"):
            return json_response(get_cube_meta())

        if path in ("/cubejs-api/v1/load", "/api/cube/load"):
            return await self.handle_cube_load(request, query)

        if path in ("/cubejs-api/v1/batch", "/api/cube/batch"):
            return await self.handle_cube_batch(request)

        if path in ("/cubejs-api/v1/sql", "/api/cube/sql"):
            return json_response({"sql": {"sql": ["SELECT obs.source, count(*) FROM harvy_observations obs GROUP BY obs.source", []]}})

        if path in ("/cubejs-api/v1/dry-run", "/api/cube/dry-run"):
            return json_response({"status": "ok"})

        if path == "/api/query/catalog" and request.method == "GET":
            return json_response(get_query_catalog())

        if path == "/api/query/execute" and request.method == "POST":
            user = await self.get_current_user(request)
            env_id = (user.get("environment_id") if isinstance(user, dict) else None) or "shared"
            body = from_js(await request.json()) if request.headers.get("Content-Type", "").startswith("application/json") else {}
            metric = body.get("metric")
            filters = body.get("filters")
            try:
                sql, params = compile_metric_query(metric, environment_id=env_id, filters=filters)
            except ValueError as ve:
                return json_response({"error": str(ve)}, 400)

            statement = self.env.HARVY_D1.prepare(sql).bind(*params)
            res = await statement.all()
            rows = res.to_py().get("results", []) if hasattr(res, "to_py") else (from_js(res.results) or [])
            return json_response({"metric": metric, "environment": env_id, "results": rows})

        if path == "/api/dashboards":
            user = await self.get_current_user(request)
            if not isinstance(user, dict) or not user.get("id"):
                return json_response({"error": "Unauthorized"}, 401)
            env_id = user.get("environment_id") or user.get("id")

            if request.method == "GET":
                res = await self.env.HARVY_D1.prepare(
                    "SELECT id, environment_id, owner_id, title, description, layout_json, queries_json, created_at, updated_at "
                    "FROM harvy_dashboards WHERE environment_id = ? ORDER BY updated_at DESC"
                ).bind(env_id).all()
                rows = res.to_py().get("results", []) if hasattr(res, "to_py") else (from_js(res.results) or [])
                return json_response({"dashboards": rows})

            if request.method == "POST":
                body = from_js(await request.json()) if request.headers.get("Content-Type", "").startswith("application/json") else {}
                dash_id = str(uuid.uuid4())
                title = (body.get("title") or "Untitled Dashboard").strip()[:100]
                desc = (body.get("description") or "").strip()[:500]
                layout = json.dumps(body.get("layout") or {})
                queries = json.dumps(body.get("queries") or [])
                now = int(time.time())
                await self.env.HARVY_D1.prepare(
                    "INSERT INTO harvy_dashboards (id, environment_id, owner_id, title, description, layout_json, queries_json, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ).bind(dash_id, env_id, user["id"], title, desc, layout, queries, now, now).run()
                return json_response({"id": dash_id, "title": title, "environment_id": env_id}, 201)

        dash_match = re.fullmatch(r"/api/dashboards/([a-zA-Z0-9_-]+)", path)
        if dash_match and request.method in ("PUT", "DELETE"):
            user = await self.get_current_user(request)
            if not isinstance(user, dict) or not user.get("id"):
                return json_response({"error": "Authentication required."}, 401)
            env_id = user.get("environment_id") or user.get("id")
            dash_id = dash_match.group(1)
            if request.method == "DELETE":
                await self.env.HARVY_D1.prepare(
                    "DELETE FROM harvy_dashboards WHERE id = ? AND owner_id = ? AND environment_id = ?"
                ).bind(dash_id, user["id"], env_id).run()
                return json_response({"success": True})
            body = from_js(await request.json()) if request.headers.get("Content-Type", "").startswith("application/json") else {}
            if not isinstance(body, dict):
                body = {}
            title = (body.get("title") or "Untitled Dashboard").strip()[:100]
            desc = (body.get("description") or "").strip()[:500]
            layout = json.dumps(body.get("layout") or {})
            queries = json.dumps(body.get("queries") or [])
            now = int(time.time())
            await self.env.HARVY_D1.prepare(
                "UPDATE harvy_dashboards SET title = ?, description = ?, layout_json = ?, queries_json = ?, updated_at = ? "
                "WHERE id = ? AND owner_id = ? AND environment_id = ?"
            ).bind(title, desc, layout, queries, now, dash_id, user["id"], env_id).run()
            return json_response({"id": dash_id, "title": title, "environment_id": env_id})

        if path == "/api/nodes/graph" and request.method == "GET":
            user = await self.get_current_user(request)
            env_id = (user.get("environment_id") if isinstance(user, dict) else None) or "shared"
            center_urn = query.get("center", [None])[0]
            try:
                limit = int(query.get("limit", [50])[0])
            except (ValueError, TypeError):
                limit = 50
            limit = min(max(1, limit), 200)

            link_clause, link_params = build_scope_filter(env_id, "l.environment_id")
            if center_urn:
                sql = f"SELECT l.id, l.source_id, l.target_id, l.link_type, l.confidence, l.evidence_observation_id FROM harvy_links l WHERE {link_clause} AND (l.source_id = ? OR l.target_id = ?) LIMIT ?"
                params = [*link_params, center_urn, center_urn, limit]
            else:
                sql = f"SELECT l.id, l.source_id, l.target_id, l.link_type, l.confidence, l.evidence_observation_id FROM harvy_links l WHERE {link_clause} ORDER BY l.created_at DESC LIMIT ?"
                params = [*link_params, limit]

            res = await self.env.HARVY_D1.prepare(sql).bind(*params).all()
            link_rows = res.to_py().get("results", []) if hasattr(res, "to_py") else (from_js(res.results) or [])

            node_ids = set()
            if center_urn:
                node_ids.add(center_urn)
            for r in link_rows:
                if isinstance(r, dict):
                    node_ids.add(r.get("source_id"))
                    node_ids.add(r.get("target_id"))

            nodes = []
            if node_ids:
                placeholders = ",".join("?" for _ in node_ids)
                stmt = self.env.HARVY_D1.prepare(f"SELECT id, type_id, display_name, canonical_url FROM harvy_objects WHERE id IN ({placeholders})").bind(*list(node_ids))
                res_nodes = await stmt.all()
                raw_nodes = res_nodes.to_py().get("results", []) if hasattr(res_nodes, "to_py") else (from_js(res_nodes.results) or [])
                nodes = [{"id": n["id"], "type": n["type_id"], "name": n["display_name"], "url": n.get("canonical_url")} for n in raw_nodes if isinstance(n, dict)]

            links = [{"id": l["id"], "source": l["source_id"], "target": l["target_id"], "link_type": l["link_type"], "confidence": l.get("confidence", 1.0), "evidence_id": l.get("evidence_observation_id")} for l in link_rows if isinstance(l, dict)]
            return json_response({"nodes": nodes, "links": links, "environment": env_id, "total_nodes": len(nodes), "total_links": len(links)})

        if path.startswith("/api/ontology/objects/") and request.method == "GET":
            urn = unquote(path.removeprefix("/api/ontology/objects/"))
            user = await self.get_current_user(request)
            env_id = (user.get("environment_id") if isinstance(user, dict) else None) or "shared"
            res = await self.env.HARVY_D1.prepare(
                "SELECT id, type_id, display_name, canonical_url, attributes_json, created_at, updated_at FROM harvy_objects WHERE id = ?"
            ).bind(urn).first()
            obj_row = from_js(res)
            if not obj_row:
                return json_response({"error": "Object not found"}, 404)

            obs_clause, obs_params = build_scope_filter(env_id, "environment_id")
            obs_res = await self.env.HARVY_D1.prepare(
                f"SELECT id, environment_id, source, job_id, r2_object_key, content_sha256, data_json, observed_at "
                f"FROM harvy_observations WHERE object_id = ? AND {obs_clause} ORDER BY observed_at DESC LIMIT 50"
            ).bind(urn, *obs_params).all()
            observations = obs_res.to_py().get("results", []) if hasattr(obs_res, "to_py") else (from_js(obs_res.results) or [])

            return json_response({
                "object": obj_row,
                "observations": observations,
            })

        # --- Autonomous Recon Jobs ---
        if path == "/api/jobs" and request.method == "POST":
            body = from_js(await request.json())
            if not isinstance(body, dict) or body.get("consent") is not True:
                return json_response({"error": "Confirm public research before starting."}, 400)
            url = body.get("url")
            if not safe_profile_url(url):
                return json_response({"error": "Enter an HTTPS profile URL on a supported social platform."}, 400)
            job_id = str(uuid.uuid4())
            token = str(uuid.uuid4())
            now = int(time.time())
            envelope = make_job(job_id, url)
            job = {"id": job_id, "token": token, "kind": "profile", "status": "queued", "url": url,
                   "protocol": envelope["protocol"], "network": envelope["network"],
                   "created_at": now, "updated_at": now, "logs": ["Queued for cloud collection.\n"], "files": [], "post_files": 0}
            await self.env.HARVY_D1.prepare(
                "INSERT INTO harvy_jobs (id, kind, status, url, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
            ).bind(job_id, "profile", "queued", url, now, now).run()
            await self.env.HARVY_KV.put("job:" + job_id, json.dumps(job), expirationTtl=2592000)
            await self.env.HARVY_QUEUE.send(envelope)
            return json_response({"id": job_id, "job_token": token, "kind": "profile"}, 202)

        if path == "/api/username-jobs" or path == "/api/research-jobs":
            return json_response({"error": "This job type is not enabled in the Cloudflare app yet."}, 501)

        parts = [unquote(part) for part in path.strip("/").split("/")]
        if len(parts) >= 3 and parts[:2] == ["api", "jobs"]:
            job_id = parts[2]
            job = await self.get_job(job_id, request)
            if job is None:
                return json_response({"error": "Job not found."}, 404)
            if len(parts) == 3 and request.method == "GET":
                files = [{"path": item["path"], "size": item["size"]} for item in job["files"]]
                return json_response({"id": job_id, "status": job["status"], "kind": job["kind"],
                                      "files": files, "logs": job["logs"], "post_files": job["post_files"],
                                      "matches": 0, "elapsed": max(0, int(time.time()) - job["created_at"])})
            if len(parts) == 4 and parts[3] == "search-documents" and request.method == "GET":
                result = await self.env.HARVY_D1.prepare(
                    "SELECT id, title, snippet, body, source, url, object_key AS file FROM harvy_search_documents WHERE job_id = ? ORDER BY created_at DESC LIMIT 100"
                ).bind(job_id).all()
                if hasattr(result, "to_py"):
                    res_dict = result.to_py()
                    docs = res_dict.get("results") or []
                else:
                    docs = from_js(result.results) or []
                for doc in docs:
                    if isinstance(doc, dict):
                        if "snippet" in doc and doc["snippet"]:
                            doc["snippet"] = mask_emails_in_text(doc["snippet"])
                        if "title" in doc and doc["title"]:
                            doc["title"] = mask_emails_in_text(doc["title"])
                        if "body" in doc and doc["body"]:
                            doc["body"] = mask_emails_in_text(doc["body"])
                return json_response({"documents": docs, "truncated": False})
            if len(parts) >= 5 and parts[3] == "files" and request.method == "GET":
                relative = "/".join(parts[4:])
                file = next((item for item in job["files"] if item["path"] == relative), None)
                if not file:
                    return json_response({"error": "File not found."}, 404)
                obj = await self.env.HARVY_BUCKET.get(file["key"])
                if obj is None:
                    return json_response({"error": "File not found."}, 404)
                return Response(obj.body, headers={"Content-Type": "application/json", "Cache-Control": "no-store"})
            if len(parts) == 4 and parts[3] == "download" and request.method == "GET":
                if not job["files"]:
                    return json_response({"error": "This job has no saved files."}, 404)
                obj = await self.env.HARVY_BUCKET.get(job["files"][0]["key"])
                if obj is None:
                    return json_response({"error": "Saved file not found."}, 404)
                return Response(await obj.text(), headers={
                    "Content-Type": "application/json",
                    "Content-Disposition": f'attachment; filename="harvy-{job_id}.json"',
                    "Cache-Control": "no-store",
                })
            if len(parts) == 4 and parts[3] == "stop" and request.method == "POST":
                if job["status"] == "queued":
                    job["status"] = "cancelled"
                    job["updated_at"] = int(time.time())
                    job["logs"].append("Cancelled before processing.\n")
                    await self.save_job(job)
                return json_response({"status": job["status"]})

        return json_response({"error": "API route not found."}, 404)

    async def handle_ops_force(self, request):
        actor = await self.authorize_ops(request)
        if not actor:
            return json_response({"error": "Authentication required."}, 401)
        if not hasattr(self.env, "HARVY_WORKFLOWS"):
            return json_response({"error": "Workflow runner binding not configured."}, 503)

        try:
            payload = from_js(await request.json())
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        query = str(payload.get("query") or "").strip()[:200]
        max_records = max(10, min(int(self.metric_number(payload.get("max_records"), 10.0) or 10), 50))
        actor_id = str(actor.get("id") or "ops")
        key = re.sub(r"[^A-Za-z0-9._:-]", "-", f"force-{int(time.time())}-{actor_id}")[:128]

        task_input = {
            "force": True,
            "maxRecords": max_records,
            "requestedBy": actor_id,
            "environmentId": "shared",
        }
        if query:
            task_input["query"] = query
        body = json.dumps({
            "task": "judyrecords.refresh",
            "version": 1,
            "idempotencyKey": key,
            "input": task_input,
        })

        from workers import Request
        from js import Object

        headers = {
            "Content-Type": "application/json",
            "X-Harvy-Actor": actor_id,
            "X-Harvy-Environment": "shared",
        }
        internal = Request(
            "https://harvy-workflows/api/workflows",
            method="POST", headers=headers, body=body,
        )
        response = await self.env.HARVY_WORKFLOWS.fetch(internal)
        status = int(getattr(response, "status", 502))
        try:
            data = json.loads(await response.text())
        except Exception:
            data = {"error": "Workflow runner returned an unreadable response"}
        return json_response(data if isinstance(data, dict) else {"result": data}, status)

    async def authorize_ops(self, request):
        ops_token = getattr(self.env, "HARVY_OPS_TOKEN", "")
        supplied = request.headers.get("x-api-key") or ""
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.startswith("Bearer ") and not supplied:
            supplied = auth_header.removeprefix("Bearer ").strip()
        if ops_token and supplied and hmac.compare_digest(ops_token, supplied):
            return {"id": "ops-agent", "username": "ops-agent", "environment_id": "shared"}
        user = await self.get_current_user(request)
        if isinstance(user, dict) and user.get("id"):
            return user
        return None

    @staticmethod
    def metric_number(value, default=None, ceiling=None):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if ceiling is not None:
            number = min(number, ceiling)
        return number

    async def handle_public_status(self, request):
        # Public status page: counts + telegram progress only. No hostnames,
        # raw errors, bridge URLs, or VPS internals. Safe to edge-cache.
        now = int(time.time())
        objects = self.d1_row(await self.env.HARVY_D1.prepare("SELECT COUNT(*) AS c FROM harvy_objects").first())
        observations = self.d1_row(await self.env.HARVY_D1.prepare("SELECT COUNT(*) AS c FROM harvy_observations").first())
        telegram = self.d1_rows(await self.env.HARVY_D1.prepare(
            "SELECT id, display_name, attributes_json, updated_at FROM harvy_objects WHERE id LIKE 'telegram:%' ORDER BY updated_at DESC LIMIT 50"
        ).all())
        channels = []
        total_posts = 0
        for row in telegram:
            posts = 0
            try:
                attrs = json.loads(row.get("attributes_json") or "{}")
                posts = int(attrs.get("mined_count") or attrs.get("posts_scraped") or 0)
            except Exception:
                pass
            total_posts += posts
            channels.append({
                "name": row.get("display_name") or row.get("id"),
                "posts": posts,
                "updated_at": row.get("updated_at"),
            })
        checks = await self.ops_checks()
        health = {k: {"state": v.get("state")} for k, v in checks.items()}
        response = json_response({
            "now": now,
            "telegram": {"channels": len(channels), "posts": total_posts, "latest": channels[:20]},
            "flow": {
                "observations": int(observations.get("c") or 0),
                "objects": int(objects.get("c") or 0),
            },
            "health": health,
        })
        response.headers["Cache-Control"] = "public, max-age=5"
        return response

    async def reconcile_run(self, row):
        if not hasattr(self.env, "HARVY_WORKFLOWS"):
            return None
        from workers import Request

        url = f"https://harvy-workflows/api/workflows/{row.get('id')}"
        headers = {
            "X-Harvy-Actor": str(row.get("requested_by") or ""),
            "X-Harvy-Environment": str(row.get("environment_id") or "shared"),
        }
        try:
            response = await self.env.HARVY_WORKFLOWS.fetch(Request(url, method="GET", headers=headers))
            raw = await response.text()
        except Exception as error:
            return f"probe:{type(error).__name__}"
        try:
            data = json.loads(raw)
        except Exception:
            return f"probe:http-{getattr(response, 'status', '?')}"
        status = data.get("status") if isinstance(data, dict) else None
        return status or f"probe:http-{getattr(response, 'status', '?')}:{str(data)[:80]}"

    async def handle_ops_ingest(self, request):
        actor = await self.authorize_ops(request)
        if not actor:
            return json_response({"error": "Unauthorized: valid ops token required."}, 401)
        try:
            payload = from_js(await request.json())
        except Exception:
            return json_response({"error": "JSON object required."}, 400)
        if not isinstance(payload, dict):
            return json_response({"error": "JSON object required."}, 400)

        host = str(payload.get("host") or "unknown")[:64]
        metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
        now = int(time.time())
        await self.env.HARVY_D1.prepare(
            "INSERT INTO harvy_ops_metrics (host, collected_at, cpu_pct, mem_pct, mem_used_mb, disk_pct, load1, uptime_sec, bridge_status, bridge_latency_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ).bind(
            host, now,
            self.metric_number(metrics.get("cpu_pct"), 0.0, ceiling=100),
            self.metric_number(metrics.get("mem_pct"), 0.0, ceiling=100),
            self.metric_number(metrics.get("mem_used_mb"), 0.0),
            self.metric_number(metrics.get("disk_pct"), 0.0, ceiling=100),
            self.metric_number(metrics.get("load1"), 0.0),
            int(self.metric_number(metrics.get("uptime_sec"), 0.0) or 0),
            str(metrics.get("bridge_status") or "unknown")[:32],
            self.metric_number(metrics.get("bridge_latency_ms"), 0.0),
        ).run()

        raw_events = payload.get("events") if isinstance(payload.get("events"), list) else []
        statements = []
        for event in raw_events[:25]:
            if not isinstance(event, dict):
                continue
            message = str(event.get("message") or "")[:500]
            if not message:
                continue
            observed = int(self.metric_number(event.get("observed_at"), now) or now)
            statements.append(self.env.HARVY_D1.prepare(
                "INSERT INTO harvy_ops_events (host, source, level, message, observed_at, created_at) VALUES (?, ?, ?, ?, ?, ?)"
            ).bind(host, str(event.get("source") or "agent")[:32], str(event.get("level") or "info")[:16], message, observed, now))
        if statements:
            await self.env.HARVY_D1.batch(statements)

        await self.env.HARVY_D1.batch([
            self.env.HARVY_D1.prepare("DELETE FROM harvy_ops_metrics WHERE collected_at < ?").bind(now - 604800),
            self.env.HARVY_D1.prepare("DELETE FROM harvy_ops_events WHERE observed_at < ?").bind(now - 259200),
        ])
        return json_response({"stored": True, "events": len(statements), "collected_at": now})

    async def handle_ops_health(self, request):
        actor = await self.authorize_ops(request)
        if not actor:
            return json_response({"error": "Authentication required."}, 401)
        return json_response({"status": "ok", "checks": await self.ops_checks()})

    async def ops_checks(self):
        from js import fetch as js_fetch

        checks = {"worker": {"state": "ok", "detail": "cloudflare_python_workers"}}
        try:
            await self.env.HARVY_D1.prepare("SELECT 1").first()
            checks["d1"] = {"state": "ok", "detail": "harvy"}
        except Exception as error:
            checks["d1"] = {"state": "bad", "detail": type(error).__name__}
        try:
            probe = await self.env.HARVY_BUCKET.list({"prefix": "harvy/raw/legal/court-opinions/judyrecords/", "limit": 1})
            checks["r2"] = {"state": "ok", "detail": "harvy bucket"}
        except Exception as error:
            checks["r2"] = {"state": "bad", "detail": type(error).__name__}
        bridge_url = str(getattr(self.env, "OPS_BRIDGE_URL", "")).strip()
        if not bridge_url:
            checks["scraper_bridge"] = {"state": "warn", "detail": "OPS_BRIDGE_URL not configured"}
        else:
            try:
                response = await js_fetch(bridge_url, {"method": "GET"})
                reachable = int(getattr(response, "status", 0)) in (200, 404, 405)
                checks["scraper_bridge"] = {"state": "ok" if reachable else "warn", "detail": f"HTTP {getattr(response, 'status', '?')}"}
            except Exception as error:
                checks["scraper_bridge"] = {"state": "bad", "detail": type(error).__name__}
        checks["workflow_worker"] = {"state": "ok", "detail": "harvy-workflows"}
        return checks

    @staticmethod
    def d1_rows(result):
        if hasattr(result, "to_py"):
            return result.to_py().get("results") or []
        return from_js(result.results) or []

    @staticmethod
    def d1_row(result):
        if result is None:
            return {}
        if hasattr(result, "to_py"):
            return result.to_py() or {}
        return from_js(result) or {}

    async def handle_ops_summary(self, request):
        actor = await self.authorize_ops(request)
        if not actor:
            return json_response({"error": "Authentication required."}, 401)
        now = int(time.time())
        since = now - 86400
        metrics = self.d1_rows(await self.env.HARVY_D1.prepare(
            "SELECT collected_at, cpu_pct, mem_pct, mem_used_mb, disk_pct, load1, uptime_sec, bridge_status, bridge_latency_ms FROM harvy_ops_metrics WHERE collected_at >= ? ORDER BY collected_at ASC LIMIT 500"
        ).bind(since).all())

        def count(row, key):
            return int(row.get(key) or 0) if isinstance(row, dict) else 0

        records = self.d1_row(await self.env.HARVY_D1.prepare(
            "SELECT COUNT(*) AS c FROM harvy_observations WHERE observed_at >= ?"
        ).bind(since).first())
        observations = self.d1_row(await self.env.HARVY_D1.prepare("SELECT COUNT(*) AS c FROM harvy_observations").first())
        objects = self.d1_row(await self.env.HARVY_D1.prepare("SELECT COUNT(*) AS c FROM harvy_objects").first())
        links = self.d1_row(await self.env.HARVY_D1.prepare("SELECT COUNT(*) AS c FROM harvy_links").first())
        telegram = self.d1_rows(await self.env.HARVY_D1.prepare(
            "SELECT id, display_name, attributes_json, updated_at FROM harvy_objects WHERE id LIKE 'telegram:%' ORDER BY updated_at DESC LIMIT 20"
        ).all())

        bytes_24h = 0
        try:
            listing = await self.env.HARVY_BUCKET.list({"prefix": "harvy/raw/legal/court-opinions/judyrecords/", "limit": 1000})
            for obj in getattr(listing, "objects", []) or []:
                uploaded = getattr(obj, "uploaded", None)
                stamp_seconds = uploaded.getTime() / 1000 if uploaded else 0
                if stamp_seconds >= since:
                    bytes_24h += int(getattr(obj, "size", 0) or 0)
        except Exception:
            pass

        runs = self.d1_rows(await self.env.HARVY_D1.prepare(
            "SELECT id, task, status, requested_by, environment_id, created_at, updated_at FROM harvy_workflow_runs ORDER BY created_at DESC LIMIT 10"
        ).all())
        for row in runs:
            if isinstance(row, dict) and row.get("status") in ("queued", "running") and int(row.get("updated_at") or 0) < now - 10:
                row["status"] = await self.reconcile_run(row) or row.get("status")
                break
        events = self.d1_rows(await self.env.HARVY_D1.prepare(
            "SELECT host, source, level, message, observed_at FROM harvy_ops_events ORDER BY observed_at DESC LIMIT 60"
        ).all())
        schedule = self.d1_row(await self.env.HARVY_D1.prepare(
            "SELECT id, lease_until, last_success_at, last_run_key FROM harvy_judyrecords_schedule WHERE id = 'default'"
        ).first())

        return json_response({
            "now": now,
            "metrics": metrics,
            "flow": {
                "records_24h": count(records, "c"),
                "observations": count(observations, "c"),
                "objects": count(objects, "c"),
                "links": count(links, "c"),
                "bytes_24h": bytes_24h,
            },
            "runs": runs,
            "events": events,
            "schedule": schedule,
            "telegram": telegram,
            "health": await self.ops_checks(),
        })

    async def handle_log_ingest(self, request):
        authorized = False
        ingest_key = getattr(self.env, "HARVY_LOGS_INGEST_KEY", "")
        req_key = request.headers.get("x-api-key") or ""
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.startswith("Bearer "):
            bearer = auth_header.removeprefix("Bearer ").strip()
            if not req_key:
                req_key = bearer

        if ingest_key and req_key and hmac.compare_digest(ingest_key, req_key):
            authorized = True
        else:
            user = await self.get_current_user(request)
            if isinstance(user, dict) and user.get("id"):
                authorized = True

        if not authorized:
            return json_response({"error": "Unauthorized: valid API key required for log ingestion."}, 401)

        if not hasattr(self.env, "HARVY_LOGS"):
            return json_response({"error": "HARVY_LOGS bucket binding not configured."}, 500)

        try:
            raw_text = await request.text()
        except Exception:
            try:
                data = from_js(await request.json())
                raw_text = json.dumps(data)
            except Exception:
                raw_text = ""

        if not raw_text or not raw_text.strip():
            return json_response({"error": "Empty log payload."}, 400)

        events = []
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                events = parsed
            elif isinstance(parsed, dict):
                if isinstance(parsed.get("events"), list):
                    events = parsed["events"]
                else:
                    events = [parsed]
        except Exception:
            for line in raw_text.strip().splitlines():
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass

        if not events:
            return json_response({"error": "No valid JSON log records found."}, 400)

        from datetime import datetime, timezone
        now = int(time.time())
        dt = datetime.fromtimestamp(now, tz=timezone.utc)
        year_str = dt.strftime("%Y")
        month_str = dt.strftime("%m")
        day_str = dt.strftime("%d")
        hour_str = dt.strftime("%H")

        grouped = {}
        for ev in events:
            if not isinstance(ev, dict):
                continue
            service = str(ev.get("service") or "external").strip()
            service = re.sub(r"[^a-zA-Z0-9_.-]", "_", service) or "external"
            grouped.setdefault(service, []).append(ev)

        written_keys = []
        for service, s_events in grouped.items():
            log_id = str(uuid.uuid4())[:8]
            ts_ms = int(time.time() * 1000)
            if len(s_events) == 1:
                key = f"external/{service}/{year_str}/{month_str}/{day_str}/{hour_str}/{ts_ms}_{log_id}.json"
                body = json.dumps(s_events[0], ensure_ascii=False)
            else:
                key = f"external/{service}/{year_str}/{month_str}/{day_str}/{hour_str}/{ts_ms}_batch_{log_id}.ndjson"
                body = "\n".join(json.dumps(e, ensure_ascii=False) for e in s_events)

            await self.env.HARVY_LOGS.put(key, body)
            written_keys.append(key)

        return json_response({
            "status": "ok",
            "ingested": len(events),
            "keys": written_keys
        })

    async def handle_artifact_data(self, request, doc_id):
        from js import caches

        cache = caches.default
        cache_request = request.js_object
        try:
            cached = await cache.match(cache_request)
            if cached is not None:
                return Response(cached)
        except Exception:
            pass

        doc = from_js(await self.env.HARVY_D1.prepare(
            "SELECT id, job_id, title, snippet, body, source, url, object_key, created_at "
            "FROM harvy_search_documents WHERE id = ?"
        ).bind(doc_id).first())
        if not doc:
            return json_response({"error": "Artifact not found."}, 404)

        profile = doc
        posts = []
        job_id = doc.get("job_id")
        if job_id and doc.get("source") in ("social", "posts"):
            if doc.get("source") == "posts":
                profile = from_js(await self.env.HARVY_D1.prepare(
                    "SELECT id, job_id, title, snippet, body, source, url, object_key, created_at "
                    "FROM harvy_search_documents WHERE job_id = ? AND source = 'social' LIMIT 1"
                ).bind(job_id).first()) or doc
            result = await self.env.HARVY_D1.prepare(
                "SELECT id, job_id, title, snippet, body, source, url, object_key, created_at "
                "FROM harvy_search_documents WHERE job_id = ? AND source = 'posts' "
                "ORDER BY created_at DESC LIMIT 100"
            ).bind(job_id).all()
            if hasattr(result, "to_py"):
                posts = result.to_py().get("results") or []
            else:
                posts = from_js(result.results) or []

        def mask_doc(d):
            if isinstance(d, dict):
                d = dict(d)
                if "snippet" in d and d["snippet"]:
                    d["snippet"] = mask_emails_in_text(d["snippet"])
                if "title" in d and d["title"]:
                    d["title"] = mask_emails_in_text(d["title"])
                if "body" in d and d["body"]:
                    d["body"] = mask_emails_in_text(d["body"])
            return d

        response = json_response(
            {"document": mask_doc(doc), "profile": mask_doc(profile), "posts": [mask_doc(p) for p in posts]},
            headers={"Cache-Control": "public, max-age=300"},
        )
        try:
            await cache.put(cache_request, response.js_object.clone())
        except Exception:
            pass
        return response

    async def verify_turnstile(self, secret_key, token, ip=""):
        if not secret_key or not token:
            return False
        try:
            from js import Object, fetch
            form_parts = [f"secret={secret_key}", f"response={token}"]
            if ip:
                form_parts.append(f"remoteip={ip}")
            ts_res = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", to_js({
                "method": "POST",
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                "body": "&".join(form_parts)
            }, dict_converter=Object.fromEntries))
            ts_data = json.loads(await ts_res.text())
            return bool(ts_data.get("success"))
        except Exception:
            return False

    async def handle_reveal_record(self, request, record_id):
        doc = from_js(await self.env.HARVY_D1.prepare(
            "SELECT id, title, snippet, body, source, url FROM harvy_search_documents WHERE id = ?"
        ).bind(record_id).first())
        if not doc:
            return json_response({"error": "Record not found."}, 404)

        raw_text = f"{doc.get('title', '')} {doc.get('snippet', '')} {doc.get('body', '')}"
        emails = extract_emails(raw_text)
        if not emails:
            return json_response({"error": "No email on file for this record.", "id": record_id}, 404)

        user = await self.get_current_user(request)
        now = int(time.time())

        if user:
            daily_limit = 100 if user.get("role") == "admin" else 50
            day_bucket = now // 86400
            quota_key = f"reveal_quota:{user['id']}:{day_bucket}"
            allowed, current_count = await check_and_increment_rate_limit(
                self.env.HARVY_D1, quota_key, daily_limit, (day_bucket + 1) * 86400
            )
            if not allowed:
                return json_response({
                    "error": f"Daily reveal quota of {daily_limit} reached. Resets tomorrow.",
                    "quota_exceeded": True
                }, 429)
            remaining = max(0, daily_limit - current_count)
        else:
            ip = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for") or "127.0.0.1"
            hour_bucket = now // 3600
            rate_key = f"reveal_rate:{ip}:{hour_bucket}"
            FREE_HOURLY_LIMIT = 3

            body = from_js(await request.json()) if request.headers.get("Content-Type", "").startswith("application/json") else {}
            turnstile_token = body.get("turnstileToken") if isinstance(body, dict) else ""
            secret_key = getattr(self.env, "TURNSTILE_SECRET_KEY", "")
            if secret_key:
                if not turnstile_token:
                    return json_response({
                        "error": "Turnstile bot challenge required for anonymous reveals.",
                        "needs_challenge": True
                    }, 403)
                valid = await self.verify_turnstile(secret_key, turnstile_token, ip)
                if not valid:
                    return json_response({"error": "Turnstile bot check failed."}, 403)

            allowed, current_count = await check_and_increment_rate_limit(
                self.env.HARVY_D1, rate_key, FREE_HOURLY_LIMIT, (hour_bucket + 1) * 3600
            )
            if not allowed:
                return json_response({
                    "error": f"Free reveal limit reached ({FREE_HOURLY_LIMIT} per hour). Sign in for daily quota.",
                    "rate_limited": True
                }, 429)
            remaining = max(0, FREE_HOURLY_LIMIT - current_count)

        return json_response({
            "id": record_id,
            "email": emails[0],
            "emails": emails,
            "remaining": remaining,
            "authenticated": bool(user)
        })

    async def subscribe_newsletter(self, request):
        body = from_js(await request.json())
        if not isinstance(body, dict):
            return json_response({"error": "Invalid subscription request."}, 400)
        email = body.get("email", "")
        email = email.strip().lower() if isinstance(email, str) else ""
        if body.get("privacyAccepted") is not True:
            return json_response({"error": "Accept the Privacy Policy to continue."}, 400)
        if body.get("newsletterOptIn") is not True:
            return json_response({"error": "Please explicitly opt in to email updates."}, 400)
        if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            return json_response({"error": "Enter a valid email address."}, 400)

        api_key = getattr(self.env, "BUTTONDOWN_API_KEY", "")
        if not api_key:
            return json_response({"error": "Email subscriptions are temporarily unavailable."}, 503)

        try:
            await self.env.HARVY_D1.prepare(
                "SELECT buttondown_subscriber_id FROM harvy_newsletter_consents LIMIT 0"
            ).all()
        except Exception:
            return json_response({"error": "Email subscriptions are temporarily unavailable."}, 503)

        remote_ip = request.headers.get("CF-Connecting-IP") or "unknown"
        ip_hash = hashlib.sha256(remote_ip.encode("utf-8")).hexdigest()[:24]
        hour_bucket = int(time.time()) // 3600
        rate_key = f"newsletter:hour:{ip_hash}:{hour_bucket}"
        allowed, attempts = await check_and_increment_rate_limit(
            self.env.HARVY_D1, rate_key, 6, (hour_bucket + 1) * 3600
        )
        if not allowed:
            return json_response({"error": "Too many signup attempts. Try again later."}, 429)

        from js import Object, fetch

        payload = {"email_address": email, "type": "unactivated", "tags": ["harvy"]}
        options = to_js({
            "method": "POST",
            "headers": {
                "Authorization": "Token " + api_key,
                "Content-Type": "application/json",
                "X-Buttondown-Collision-Behavior": "add",
            },
            "body": json.dumps(payload),
        }, dict_converter=Object.fromEntries)
        try:
            upstream = await fetch("https://api.buttondown.com/v1/subscribers", options)
            upstream_text = await upstream.text()
            if upstream.status < 200 or upstream.status >= 300:
                return json_response({"error": "Subscription could not be submitted. Check the address and try again."}, 502)
            try:
                upstream_data = json.loads(upstream_text)
            except ValueError:
                upstream_data = {}
        except Exception:
            return json_response({"error": "Email subscription service is unavailable."}, 502)

        subscriber_id = str(upstream_data.get("id") or "")[:128]
        if not subscriber_id:
            return json_response({"error": "Subscription confirmation could not be recorded."}, 502)
        now = int(time.time())
        await self.env.HARVY_D1.prepare(
            "INSERT INTO harvy_newsletter_consents "
            "(buttondown_subscriber_id, policy_version, consented_at, source, status) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(buttondown_subscriber_id) DO UPDATE SET policy_version=excluded.policy_version, "
            "consented_at=excluded.consented_at, source=excluded.source, status=excluded.status"
        ).bind(subscriber_id, "2026-10-v1", now, "account-modal", "pending_confirmation").run()
        return json_response({
            "status": "pending_confirmation",
            "message": "Check your email to confirm your subscription.",
        }, 202)

    async def get_job(self, job_id, request):
        raw = await self.env.HARVY_KV.get("job:" + job_id)
        if not raw:
            return None
        job = json.loads(raw)
        provided = request.headers.get("X-Job-Token", "")
        if not provided or provided != job["token"]:
            return None
        return job

    async def save_job(self, job):
        job["updated_at"] = int(time.time())
        await self.env.HARVY_KV.put("job:" + job["id"], json.dumps(job), expirationTtl=2592000)
        await self.env.HARVY_D1.prepare(
            "UPDATE harvy_jobs SET status = ?, updated_at = ?, error = ? WHERE id = ?"
        ).bind(job["status"], job["updated_at"], job.get("error") or "", job["id"]).run()

    async def queue(self, batch):
        for message in batch.messages:
            body = from_js(message.body)
            try:
                # Accept legacy queued envelopes while draining previously submitted jobs.
                job = validate_job(body) if body.get("protocol") else make_job(body["job_id"], body["url"])
                await self.process_profile_job(job)
            except Exception as error:
                job = json.loads(await self.env.HARVY_KV.get("job:" + body["job_id"]))
                job["status"] = "failed"
                job["error"] = type(error).__name__
                job["logs"].append("Collection failed. Check the job inputs or service configuration.\n")
                await self.save_job(job)

    async def process_profile_job(self, envelope):
        from js import Object, fetch

        job_id = envelope["job_id"]
        url = envelope["target"]
        job = json.loads(await self.env.HARVY_KV.get("job:" + job_id))
        if job["status"] == "cancelled":
            return
        job["status"] = "running"
        job["logs"].append("Cloud collection started.\n")
        await self.save_job(job)

        key = getattr(self.env, "SPIDER_API_KEY", "")
        proxy = get_proxy(self.env, required=True)
        if not key or not proxy:
            raise RuntimeError("Missing private collection configuration")
        payload = {"url": url, "request": "browser", "return_format": "raw", "return_json_data": True,
                   "return_page_links": True, "metadata": True, "cache": False, "session": False,
                   "return_cookies": False, "remote_proxy": proxy}
        options = to_js({"method": "POST", "headers": {"Authorization": "Bearer " + key,
                           "Content-Type": "application/json"}, "body": json.dumps(payload)},
                        dict_converter=Object.fromEntries)
        response = await fetch(SPIDER_ENDPOINT, options)
        if response.status < 200 or response.status >= 300:
            raise RuntimeError("Collection service returned an error")
        raw_text = await response.text()
        raw_data = json.loads(raw_text)
        details = extract_profile_details(raw_data, url)

        # Intercept and replay GraphQL for Threads profiles to extract up to 25 posts
        html = ""
        if isinstance(raw_data, list) and raw_data:
            html = raw_data[0].get("content") or ""
        elif isinstance(raw_data, dict):
            html = raw_data.get("content") or ""

        if "threads." in url.lower() and html:
            try:
                # 1. Intercept LSD token
                lsd_m = re.search(r"[\x22\x27]token[\x22\x27]:[\x22\x27]([A-Za-z0-9_-]+)[\x22\x27]", html)
                lsd = lsd_m.group(1) if lsd_m else "AdSU-RF2CqSUsgzv8e6aAlFb5Ks"

                # 2. Intercept queryID and variables for BarcelonaProfileThreadsTabDirectQuery
                q_match = re.search(r"[\x22\x27]adp_BarcelonaProfileThreadsTabDirectQueryRelayPreloader_[^\x22\x27]+[\x22\x27],[\x22\x27]queryID[\x22\x27]:[\x22\x27](\d+)[\x22\x27]", html)
                if not q_match:
                    q_match = re.search(r"[\x22\x27]queryID[\x22\x27]:[\x22\x27](\d+)[\x22\x27][^}]+[\x22\x27]BarcelonaProfileThreadsTabDirectQuery[\x22\x27]", html)
                doc_id = q_match.group(1) if q_match else "28424781820556358"

                # 3. Intercept precomputed Relay variables
                v_idx = html.find(doc_id)
                if v_idx != -1:
                    start_v = html.find("\"variables\":", v_idx)
                    if start_v != -1:
                        brace_count = 0
                        in_brace = False
                        var_str = ""
                        for char in html[start_v + 12:]:
                            if char == "{":
                                brace_count += 1
                                in_brace = True
                            if in_brace:
                                var_str += char
                            if char == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    break
                        if var_str:
                            vars_obj = json.loads(var_str)
                            vars_obj["first"] = 25  # Replay with higher pagination batch

                            gql_body = urlencode({
                                "lsd": lsd,
                                "variables": json.dumps(vars_obj),
                                "doc_id": doc_id
                            })
                            gql_headers = {
                                "x-ig-app-id": "238260118697367",
                                "x-fb-lsd": lsd,
                                "x-fb-friendly-name": "BarcelonaProfileThreadsTabDirectQuery",
                                "Origin": "https://www.threads.net",
                                "Referer": url,
                                "Content-Type": "application/x-www-form-urlencoded"
                            }
                            # Replay intercepted query to Threads GraphQL endpoint via Spider
                            gql_payload = {
                                "url": "https://www.threads.net/api/graphql",
                                "request": "http",
                                "remote_proxy": proxy,
                                "headers": gql_headers,
                                "body": gql_body
                            }
                            gql_options = to_js({"method": "POST", "headers": {"Authorization": "Bearer " + key,
                                                "Content-Type": "application/json"}, "body": json.dumps(gql_payload)},
                                            dict_converter=Object.fromEntries)
                            gql_resp = await fetch(SPIDER_ENDPOINT, gql_options)
                            if 200 <= gql_resp.status < 300:
                                gql_text = await gql_resp.text()
                                gql_data = json.loads(gql_text)
                                content = gql_data[0].get("content", "") if isinstance(gql_data, list) else gql_data.get("content", "")
                                if content.startswith("{"):
                                    res_json = json.loads(content)
                                    edges = res_json.get("data", {}).get("mediaData", {}).get("edges", [])
                                    seen_codes = {p.get("code") for p in details["posts"] if p.get("code")}
                                    for edge in edges:
                                        p = edge.get("node", {}).get("thread_items", [{}])[0].get("post", {})
                                        code = p.get("code")
                                        if code and code not in seen_codes:
                                            cap = p.get("caption", {})
                                            text = cap.get("text", "") if cap else ""
                                            if not text:
                                                frags = p.get("text_post_app_info", {}).get("text_fragments", {}).get("fragments", [])
                                                if frags:
                                                    text = frags[0].get("plaintext", "")
                                            post_url = f"https://www.threads.net/@{details['username'] or 'user'}/post/{code}"
                                            details["posts"].append({
                                                "code": code,
                                                "url": post_url,
                                                "text": text,
                                                "like_count": p.get("like_count", 0),
                                                "reply_count": p.get("reply_count", 0),
                                                "timestamp": p.get("taken_at")
                                            })
                                            seen_codes.add(code)
            except Exception as e:
                job["logs"].append(f"GraphQL replay note: {type(e).__name__}\n")

        title = details["title"]
        snippet = details["snippet"]
        document_body = details["full_text"]
        
        object_key = "jobs/" + job_id + "/raw/profile.json"
        await self.env.HARVY_BUCKET.put(object_key, raw_text)
        now = int(time.time())
        doc_id = str(uuid.uuid4())
        await self.env.HARVY_D1.prepare(
            "INSERT INTO harvy_search_documents (id, job_id, title, snippet, body, source, url, object_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ).bind(doc_id, job_id, title, snippet, document_body, "social", url, object_key, now).run()

        # Also index individual extracted posts
        for post in details["posts"]:
            if post.get("text"):
                p_id = str(uuid.uuid4())
                p_title = f"Post by @{details['username'] or 'user'}"
                await self.env.HARVY_D1.prepare(
                    "INSERT INTO harvy_search_documents (id, job_id, title, snippet, body, source, url, object_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ).bind(p_id, job_id, p_title, post["text"][:300], post["text"], "posts", post.get("url") or url, object_key, now).run()

        # Ingest into Shared Ontology
        try:
            platform = "social"
            parsed_host = urlparse(url).netloc.lower()
            if "instagram" in parsed_host: platform = "instagram"
            elif "threads" in parsed_host: platform = "threads"
            elif "x.com" in parsed_host or "twitter" in parsed_host: platform = "x"
            elif "reddit" in parsed_host: platform = "reddit"
            elif "facebook" in parsed_host: platform = "facebook"

            handle = details.get("username") or ""
            if handle:
                prof_obj = make_profile_object(platform, handle, display_name=title, canonical_url=url, attributes={"snippet": snippet}, now=now)
                await self.env.HARVY_D1.prepare(
                    "INSERT OR IGNORE INTO harvy_objects (id, type_id, display_name, canonical_url, attributes_json, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)"
                ).bind(prof_obj["id"], prof_obj["type_id"], prof_obj["display_name"], prof_obj["canonical_url"], prof_obj["attributes_json"], now, now).run()

                prof_obs = make_observation_record(prof_obj["id"], platform, {"title": title, "snippet": snippet}, r2_object_key=object_key, job_id=job_id, environment_id="shared", observed_at=now, now=now)
                await self.env.HARVY_D1.prepare(
                    "INSERT OR IGNORE INTO harvy_observations (id, object_id, environment_id, source, job_id, r2_object_key, content_sha256, data_json, observed_at, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ).bind(prof_obs["id"], prof_obs["object_id"], prof_obs["environment_id"], prof_obs["source"], prof_obs["job_id"], prof_obs["r2_object_key"], prof_obs["content_sha256"], prof_obs["data_json"], prof_obs["observed_at"], prof_obs["created_at"]).run()

                for post in details["posts"]:
                    if post.get("text"):
                        post_urn = make_object_urn("post", platform, str(uuid.uuid4())[:12])
                        await self.env.HARVY_D1.prepare(
                            "INSERT OR IGNORE INTO harvy_objects (id, type_id, display_name, canonical_url, attributes_json, created_at, updated_at) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)"
                        ).bind(post_urn, "post", post["text"][:60], post.get("url") or url, json.dumps({"text": post["text"]}), now, now).run()

                        link_rec = make_link_record(prof_obj["id"], post_urn, "authored", evidence_observation_id=prof_obs["id"], environment_id="shared", now=now)
                        await self.env.HARVY_D1.prepare(
                            "INSERT OR IGNORE INTO harvy_links (id, environment_id, source_id, target_id, link_type, confidence, evidence_observation_id, properties_json, created_at) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                        ).bind(link_rec["id"], link_rec["environment_id"], link_rec["source_id"], link_rec["target_id"], link_rec["link_type"], link_rec["confidence"], link_rec["evidence_observation_id"], link_rec["properties_json"], link_rec["created_at"]).run()
        except Exception as oe:
            job["logs"].append(f"Ontology ingestion note: {type(oe).__name__} - {str(oe)}\n")

        job["status"] = "finished"
        job["post_files"] = len(details["posts"])
        job["files"] = [{"path": "raw/profile.json", "key": object_key, "size": len(raw_text.encode("utf-8"))}]
        job["result"] = make_result(envelope, "partial", [{"profile": title, "posts": len(details["posts"])}])
        job["logs"].append(f"Public profile indexed ({len(details['posts'])} posts extracted).\n")
        await self.save_job(job)
