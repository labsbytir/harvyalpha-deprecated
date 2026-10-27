"""Small authenticated HTTP bridge for the Cloudflare JudyRecords Workflow."""
import hmac
import os

from flask import Flask, jsonify, request

from v1.scrape.judyrecords import search_judyrecords

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024


@app.get("/healthz")
def healthz():
    return jsonify(status="ok"), 200


@app.post("/api/judyrecords/search")
def search():
    expected = os.environ.get("JUDY_SCRAPER_TOKEN", "")
    supplied = request.headers.get("Authorization", "")
    if not expected or not hmac.compare_digest(supplied, f"Bearer {expected}"):
        return jsonify(error="unauthorized"), 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSON object required"), 400
    query = payload.get("query")
    maximum = payload.get("max_records", 10)
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 200:
        return jsonify(error="query must be 2-200 characters"), 400
    if type(maximum) is not int or not 1 <= maximum <= 50:
        return jsonify(error="max_records must be an integer from 1 to 50"), 400

    try:
        result = search_judyrecords(query.strip(), max_records=maximum)
    except Exception as error:
        app.logger.error("JudyRecords search failed: %s", type(error).__name__)
        return jsonify(error="JudyRecords search failed"), 502
    if result.get("status") != "ok":
        return jsonify(error="JudyRecords returned no conclusive results", status=result.get("status")), 502
    return jsonify(cases=result.get("cases", []), result_count=result.get("result_count", 0))
