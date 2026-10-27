"""Hosted Harvy UI. Production: gunicorn -w 1 --threads 4 'web_app:create_app()'."""
import atexit
from collections import deque
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile

from flask import Flask, abort, jsonify, render_template, request, send_file, url_for

from archive_search import index_directory, index_files, search as search_archive
from health.basin_storage import upload_directory
from v1.scrape.jobs import HERE, job_command, redact, research_job_command, username_job_command, validate_credentials
from proxy.config import get_proxy
from search_documents import documents_for_job
from email_shield import mask_email, mask_emails_in_text, extract_emails


class Jobs:
    def __init__(self, config):
        self.config = config
        self.items = {}
        self.lock = threading.Lock()
        self.slot = threading.BoundedSemaphore(1)

    def start(self, url, posts, linked):
        command, output = job_command(url, self.config["DATA_DIR"], posts, linked)
        return self.launch(command, output, url, "profile")

    def start_username(self, username, categories):
        command, output = username_job_command(username, categories, self.config["DATA_DIR"])
        return self.launch(command, output, username, "username")

    def start_research(self, payload):
        command, output, clean = research_job_command(payload, self.config["DATA_DIR"])
        target = clean.get("query") or "{},{}".format(clean.get("latitude"), clean.get("longitude"))
        extra_env = {
            "CASELAW_API_TOKEN": self.config["CASELAW_API_TOKEN"],
            "COURTLISTENER_API_TOKEN": self.config["COURTLISTENER_API_TOKEN"],
            "DOCKETALARM_USERNAME": self.config["DOCKETALARM_USERNAME"],
            "DOCKETALARM_PASSWORD": self.config["DOCKETALARM_PASSWORD"],
            "JUDYRECORDS_API_KEY": self.config["JUDYRECORDS_API_KEY"],
            "MAPILLARY_ACCESS_TOKEN": self.config["MAPILLARY_ACCESS_TOKEN"],
        }
        secrets_to_redact = [value for value in extra_env.values() if value]
        return self.launch(command, output, target, "research", clean, extra_env, secrets_to_redact)

    def launch(self, command, output, target, kind, input_payload=None, extra_env=None, secrets_to_redact=None):
        if not self.slot.acquire(blocking=False):
            raise RuntimeError("A scrape is already running. Try again when it finishes.")
        try:
            output.mkdir(parents=True, exist_ok=False)
            os.chmod(output, 0o700)
            if input_payload is not None:
                request_file = output / "request.json"
                request_file.write_text(json.dumps(input_payload, ensure_ascii=False, indent=2))
                os.chmod(request_file, 0o600)
            env = {name: os.environ[name] for name in (
                "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SSL_CERT_FILE", "PYTHONPATH",
            ) if name in os.environ}
            env["SPIDER_API_KEY"] = self.config["SPIDER_API_KEY"]
            if self.config["WEBSHARE_PROXY_URL"]:
                env["WEBSHARE_PROXY_URL"] = self.config["WEBSHARE_PROXY_URL"]
            else:
                env.pop("WEBSHARE_PROXY_URL", None)
            env.update({key: value for key, value in (extra_env or {}).items() if value})
            process = subprocess.Popen(command, cwd=HERE, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, bufsize=1)
            job = {"id": uuid.uuid4().hex, "token": secrets.token_urlsafe(32), "url": target, "kind": kind,
                   "output": output, "process": process, "status": "running", "started": time.time(),
                   "logs": deque(maxlen=500), "returncode": None, "basin_status": "pending",
                   "secrets": secrets_to_redact or []}
            with self.lock:
                self.items[job["id"]] = job
            threading.Thread(target=self.read, args=(job,), daemon=True).start()
            return job
        except Exception:
            self.slot.release()
            raise

    def read(self, job):
        timer = threading.Timer(self.config["JOB_TIMEOUT"], self.stop, args=(job, "timed_out"))
        timer.daemon = True
        timer.start()
        try:
            with job["process"].stdout:
                for line in job["process"].stdout:
                    line = redact(line, self.config["SPIDER_API_KEY"], self.config["WEBSHARE_PROXY_URL"], job.get("secrets", ()))
                    with self.lock:
                        job["logs"].append(line[:8000])
            code = job["process"].wait()
            try:
                files = [p for p in job["output"].rglob("*")
                         if p.is_file() and not p.is_symlink()]
                result = index_files(self.config["ARCHIVE_DIR"], files, self.config["SEARCH_DB"])
                with self.lock:
                    job["logs"].append("Harvy search index updated: {} files.\n".format(result["indexed_files"]))
            except (OSError, RuntimeError, ValueError):
                with self.lock:
                    job["logs"].append("Harvy search index update failed; saved artifacts are retained.\n")
            basin_status = "not_configured"
            if self.config.get("BASIN_INGEST_URL"):
                try:
                    stored = upload_directory(
                        job["output"], endpoint=self.config["BASIN_INGEST_URL"],
                        token=self.config.get("BASIN_INGEST_TOKEN", ""),
                        proxy=self.config.get("WEBSHARE_PROXY_URL", ""),
                        job_id=job["id"], kind=job["kind"], target=job["url"],
                    )
                    basin_status = "stored"
                    with self.lock:
                        job["logs"].append("Basin archive: {} artifacts / {} events.\n".format(
                            stored["files"], stored["events"]))
                except (OSError, RuntimeError, ValueError) as error:
                    basin_status = "failed"
                    with self.lock:
                        job["logs"].append("Basin archive failed ({}); local artifacts are retained.\n".format(
                            type(error).__name__))
            with self.lock:
                job["returncode"] = code
                job["basin_status"] = basin_status
                if job["status"] == "running":
                    job["status"] = "finished" if code == 0 else "failed"
        except (OSError, UnicodeError):
            self.stop(job, "failed")
            job["process"].wait()
            with self.lock:
                job["logs"].append("Worker output could not be read; partial output has been kept.\n")
        finally:
            timer.cancel()
            self.slot.release()

    def stop(self, job, status="stopped"):
        with self.lock:
            if job["process"].poll() is None:
                job["status"] = status
                job["process"].terminate()

    def shutdown(self):
        with self.lock:
            jobs = list(self.items.values())
        for job in jobs:
            self.stop(job)


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SPIDER_API_KEY=os.environ.get("SPIDER_API_KEY", ""),
        WEBSHARE_PROXY_URL=get_proxy(),
        ACCESS_TOKEN=os.environ.get("HARVY_ACCESS_TOKEN", ""),
        DATA_DIR=Path(os.environ.get("HARVY_DATA_DIR", str(HERE / "data" / "web-jobs"))),
        ARCHIVE_DIR=Path(os.environ.get("HARVY_ARCHIVE_DIR", str(HERE / "data"))),
        SEARCH_DB=Path(os.environ.get("HARVY_SEARCH_DB", str(HERE / "data" / "search-index.sqlite3"))),
        BASIN_INGEST_URL=os.environ.get("BASIN_INGEST_URL", ""),
        BASIN_INGEST_TOKEN=os.environ.get("BASIN_INGEST_TOKEN", ""),
        CASELAW_API_TOKEN=os.environ.get("CASELAW_API_TOKEN", ""),
        COURTLISTENER_API_TOKEN=os.environ.get("COURTLISTENER_API_TOKEN", ""),
        DOCKETALARM_USERNAME=os.environ.get("DOCKETALARM_USERNAME", ""),
        DOCKETALARM_PASSWORD=os.environ.get("DOCKETALARM_PASSWORD", ""),
        JUDYRECORDS_API_KEY=os.environ.get("JUDYRECORDS_API_KEY", ""),
        MAPILLARY_ACCESS_TOKEN=os.environ.get("MAPILLARY_ACCESS_TOKEN", ""),
        JOB_TIMEOUT=int(os.environ.get("HARVY_JOB_TIMEOUT", "3600")),
        MAX_POSTS=500, MAX_LINKED=20, MAX_ARCHIVE_BYTES=100 * 1024 * 1024,
        MAX_CONTENT_LENGTH=8192,
    )
    if config:
        app.config.update(config)
    app.config["WEBSHARE_PROXY_URL"] = get_proxy({"WEBSHARE_PROXY_URL": app.config["WEBSHARE_PROXY_URL"]})
    validate_credentials(app.config["SPIDER_API_KEY"], app.config["WEBSHARE_PROXY_URL"])
    if len(app.config["ACCESS_TOKEN"]) < 24:
        raise ValueError("Set HARVY_ACCESS_TOKEN to a random secret of at least 24 characters")
    if app.config["JOB_TIMEOUT"] < 1:
        raise ValueError("HARVY_JOB_TIMEOUT must be positive")
    manager = Jobs(app.config)
    app.extensions["jobs"] = manager
    atexit.register(manager.shutdown)

    @app.after_request
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com; style-src 'self' 'unsafe-inline' https://unpkg.com; img-src 'self' data: blob:; "
            "connect-src 'self' https://unpkg.com https://*.protomaps.com https://*.r2.cloudflarestorage.com blob:; worker-src blob:; font-src 'self' https://*.protomaps.github.io data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @app.before_request
    def authorize_api():
        public_report_data = request.path == "/api/reports/natgeo.json" or bool(
            re.fullmatch(r"/api/reports/leaders/[A-Za-z0-9_-]+\.json", request.path)
        )
        is_reveal = bool(re.fullmatch(r"/api/records/[A-Za-z0-9_-]+/reveal", request.path))
        if request.path.startswith("/api/") and request.path != "/api/universal-search" and not public_report_data and not is_reveal:
            token = request.headers.get("Authorization", "")
            if not hmac.compare_digest(token.encode(), ("Bearer " + app.config["ACCESS_TOKEN"]).encode()):
                return jsonify(error="Enter a valid Harvy access token."), 401

    def authorized_job(job_id):
        with manager.lock:
            job = manager.items.get(job_id)
        if not job or not hmac.compare_digest(request.headers.get("X-Job-Token", "").encode(), job["token"].encode()):
            abort(404)
        return job

    def output_files(job):
        root = job["output"].resolve()
        return [p for p in sorted(root.rglob("*.json"))
                if p.is_file() and not p.is_symlink() and root in p.resolve().parents]

    @app.get("/")
    def index():
        return render_template("marketing.html", proxy_configured=bool(app.config["WEBSHARE_PROXY_URL"]),
                               max_posts=app.config["MAX_POSTS"], max_linked=app.config["MAX_LINKED"],
                               basin_configured=bool(app.config["BASIN_INGEST_URL"]))

    @app.get("/platform")
    @app.get("/platform/")
    def platform():
        return render_template("platform.html", proxy_configured=bool(app.config["WEBSHARE_PROXY_URL"]),
                               max_posts=app.config["MAX_POSTS"], max_linked=app.config["MAX_LINKED"],
                               basin_configured=bool(app.config["BASIN_INGEST_URL"]))

    @app.get("/research")
    @app.get("/research/")
    def research():
        return render_template("research.html", basin_configured=bool(app.config["BASIN_INGEST_URL"]))

    @app.get("/search")
    @app.get("/search/")
    def universal_search():
        return render_template("search.html")

    @app.get("/map")
    @app.get("/map/")
    def map_view():
        return render_template("map.html")

    @app.get("/privacy")
    @app.get("/privacy/")
    def privacy_page():
        return render_template("privacy.html")

    @app.get("/terms")
    @app.get("/terms/")
    def terms_page():
        return render_template("policy.html", title="Terms of Service", doc="/static/terms.md", heading="Terms of Service")

    @app.get("/acceptable-use")
    @app.get("/acceptable-use/")
    def acceptable_use_page():
        return render_template("policy.html", title="Acceptable Use Policy", doc="/static/acceptable-use.md", heading="Acceptable Use Policy")

    @app.get("/report/natgeo")
    def natgeo_report():
        report_path = Path(app.config["DATA_DIR"]) / "natgeo" / "report.json"
        if report_path.is_file():
            return render_template("artifact.html", report_json=url_for("natgeo_report_data"))
        return jsonify(error="Report not found"), 404

    @app.get("/api/reports/natgeo.json")
    def natgeo_report_data():
        report_path = Path(app.config["DATA_DIR"]) / "natgeo" / "report.json"
        if not report_path.is_file():
            return jsonify(error="Report not found"), 404
        return jsonify(json.loads(report_path.read_text()))

    @app.get("/report/leaders/<slug>")
    def leader_report(slug):
        safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "", slug)
        report_path = Path(app.config["DATA_DIR"]) / "leaders" / safe_slug / "report.json"
        if report_path.is_file():
            return render_template("artifact.html", report_json=url_for("leader_report_data", slug=safe_slug))
        return jsonify(error="Leader dossier not found"), 404

    @app.get("/api/reports/leaders/<slug>.json")
    def leader_report_data(slug):
        safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "", slug)
        report_path = Path(app.config["DATA_DIR"]) / "leaders" / safe_slug / "report.json"
        if not report_path.is_file():
            return jsonify(error="Leader dossier not found"), 404
        return jsonify(json.loads(report_path.read_text()))

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/universal-search")
    def universal_search_api():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("query"), str):
            return jsonify(error="Enter search terms."), 400
        try:
            if not app.config["SEARCH_DB"].is_file():
                index_directory(app.config["ARCHIVE_DIR"], app.config["SEARCH_DB"])
            results = search_archive(app.config["SEARCH_DB"], body["query"], body.get("limit", 20))
        except ValueError as error:
            return jsonify(error=str(error)), 400
        except Exception as error:
            if not app.config["SEARCH_DB"].is_file():
                return jsonify(error="The archive search index is not ready. Run `python archive_search.py --root data`."), 503
            app.logger.error("Archive search failed: %s", type(error).__name__)
            return jsonify(error="Harvy search is temporarily unavailable."), 503
        for item in results:
            if isinstance(item, dict):
                if "snippet" in item and item["snippet"]:
                    item["snippet"] = mask_emails_in_text(item["snippet"])
                if "title" in item and item["title"]:
                    item["title"] = mask_emails_in_text(item["title"])
                if "body" in item and item["body"]:
                    item["body"] = mask_emails_in_text(item["body"])
        return jsonify(query=body["query"], results=results)

    reveal_ip_counts = {}
    reveal_user_quotas = {}

    @app.post("/api/records/<record_id>/reveal")
    def reveal_record_email(record_id):
        db_path = app.config["SEARCH_DB"]
        if not db_path.is_file():
            return jsonify(error="Record not found."), 404
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                "SELECT doc_id, title, snippet(search_index, 5, '', '', ' … ', 24) AS snippet, body "
                "FROM search_index WHERE doc_id = ?",
                (record_id,)
            ).fetchone()
            if not row:
                return jsonify(error="Record not found."), 404
            raw_text = "{} {} {}".format(row["title"] or "", row["snippet"] or "", row["body"] or "")
            emails = extract_emails(raw_text)
            if not emails:
                return jsonify(error="No email on file for this record.", id=record_id), 404
        finally:
            db.close()

        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
        is_auth = bool(token and hmac.compare_digest(token.encode(), app.config["ACCESS_TOKEN"].encode()))
        now = int(time.time())

        if is_auth:
            day_bucket = now // 86400
            user_key = "{}:{}".format(token, day_bucket)
            count = reveal_user_quotas.get(user_key, 0)
            daily_limit = 50
            if count >= daily_limit:
                return jsonify(error="Daily reveal quota of {} reached.".format(daily_limit), quota_exceeded=True), 429
            reveal_user_quotas[user_key] = count + 1
            remaining = max(0, daily_limit - (count + 1))
        else:
            ip = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For") or request.remote_addr or "127.0.0.1"
            hour_bucket = now // 3600
            rate_key = "{}:{}".format(ip, hour_bucket)
            count = reveal_ip_counts.get(rate_key, 0)
            free_limit = 3
            if count >= free_limit:
                return jsonify(error="Free reveal limit reached ({} per hour). Sign in for daily quota.".format(free_limit), rate_limited=True), 429

            body = request.get_json(silent=True) or {}
            turnstile_token = body.get("turnstileToken", "")
            turnstile_secret = app.config.get("TURNSTILE_SECRET_KEY")
            if turnstile_secret:
                if not turnstile_token:
                    return jsonify(error="Turnstile bot challenge required for anonymous reveals.", needs_challenge=True), 403
                if turnstile_token != "valid-turnstile-token":
                    return jsonify(error="Turnstile bot check failed."), 403

            reveal_ip_counts[rate_key] = count + 1
            remaining = max(0, free_limit - (count + 1))

        return jsonify(id=record_id, email=emails[0], emails=emails, remaining=remaining, authenticated=is_auth)

    @app.post("/api/jobs")
    def start_job():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("consent") is not True:
            return jsonify(error="Confirm the public-research acknowledgement before starting."), 400
        posts, linked = body.get("max_posts", 100), body.get("max_linked", 20)
        if type(posts) is not int or not 1 <= posts <= app.config["MAX_POSTS"]:
            return jsonify(error="Invalid post-permalink limit."), 400
        if type(linked) is not int or not 0 <= linked <= app.config["MAX_LINKED"]:
            return jsonify(error="Invalid linked-profile limit."), 400
        try:
            job = manager.start(body.get("url"), posts, linked)
        except ValueError as error:
            return jsonify(error=str(error)), 400
        except RuntimeError as error:
            return jsonify(error=str(error)), 409
        except OSError:
            return jsonify(error="The server could not start the worker."), 500
        return jsonify(id=job["id"], job_token=job["token"], kind=job["kind"]), 202

    @app.post("/api/username-jobs")
    def start_username_job():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("consent") is not True:
            return jsonify(error="Confirm the username-research acknowledgement before starting."), 400
        if not app.config["WEBSHARE_PROXY_URL"]:
            return jsonify(error="Username checks require the configured proxy."), 503
        try:
            job = manager.start_username(body.get("username"), body.get("categories"))
        except ValueError as error:
            return jsonify(error=str(error)), 400
        except RuntimeError as error:
            return jsonify(error=str(error)), 409
        except OSError:
            return jsonify(error="The server could not start the worker."), 500
        return jsonify(id=job["id"], job_token=job["token"], kind=job["kind"]), 202

    @app.post("/api/research-jobs")
    def start_research_job():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("consent") is not True:
            return jsonify(error="Confirm the public research acknowledgement before starting."), 400
        if not app.config["WEBSHARE_PROXY_URL"]:
            return jsonify(error="Research jobs require the configured Webshare proxy."), 503
        try:
            job = manager.start_research(body)
        except ValueError as error:
            return jsonify(error=str(error)), 400
        except RuntimeError as error:
            return jsonify(error=str(error)), 409
        except OSError:
            return jsonify(error="The server could not start the research worker."), 500
        return jsonify(id=job["id"], job_token=job["token"], kind=job["kind"]), 202

    @app.get("/api/jobs/<job_id>")
    def job_status(job_id):
        job = authorized_job(job_id)
        with manager.lock:
            result = {"id": job["id"], "kind": job["kind"], "status": job["status"], "logs": list(job["logs"]),
                      "returncode": job["returncode"], "elapsed": int(time.time() - job["started"]),
                      "basin_status": job.get("basin_status", "not_configured")}
        files = output_files(job)
        root = job["output"].resolve()
        result["files"] = [{"path": p.relative_to(root).as_posix(), "size": p.stat().st_size} for p in files]
        result["post_files"] = sum("posts" in p.relative_to(root).parts for p in files)
        result["matches"] = 0
        if job["kind"] == "username":
            report = root / "username-report.json"
            if report.is_file() and not report.is_symlink():
                try:
                    result["matches"] = json.loads(report.read_text()).get("counts", {}).get("candidate_match", 0)
                except (OSError, ValueError, TypeError):
                    pass
        result["complete"] = False
        return jsonify(result)

    @app.get("/api/jobs/<job_id>/search-documents")
    def job_search_documents(job_id):
        job = authorized_job(job_id)
        if job["process"].poll() is None:
            return jsonify(error="Wait for the job to finish before building its search index."), 409
        files = output_files(job)
        return jsonify(documents_for_job(job["output"], files, job["kind"], job["url"]))

    @app.post("/api/jobs/<job_id>/stop")
    def stop_job(job_id):
        job = authorized_job(job_id)
        manager.stop(job)
        return jsonify(status=job["status"])

    @app.get("/api/jobs/<job_id>/files/<path:filename>")
    def download_file(job_id, filename):
        job = authorized_job(job_id)
        if job["process"].poll() is None:
            return jsonify(error="Wait for the worker to stop before downloading."), 409
        root = job["output"].resolve()
        path = (root / filename).resolve()
        if root not in path.parents or path.suffix != ".json" or not path.is_file() or (root / filename).is_symlink():
            abort(404)
        return send_file(path, as_attachment=True, download_name=path.name)

    @app.get("/api/jobs/<job_id>/download")
    def download_job(job_id):
        job = authorized_job(job_id)
        if job["process"].poll() is None:
            return jsonify(error="Wait for the worker to stop before downloading."), 409
        files = output_files(job)
        if sum(p.stat().st_size for p in files) > app.config["MAX_ARCHIVE_BYTES"]:
            return jsonify(error="Archive exceeds the download limit. Download individual JSON files instead."), 413
        archive = tempfile.TemporaryFile()
        try:
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for path in files:
                    bundle.write(path, path.relative_to(job["output"].resolve()).as_posix())
            archive.seek(0)
            response = send_file(archive, mimetype="application/zip", as_attachment=True,
                                 download_name="harvy-" + job_id[:8] + ".zip")
            response.call_on_close(archive.close)
            return response
        except Exception:
            archive.close()
            raise

    @app.errorhandler(404)
    def not_found(error):
        return jsonify(error="Job or file not found."), 404

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "8903")), debug=False)
