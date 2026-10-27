import json
import os
from core.http import get_session

def fetch_data() -> str:
    """
    MediaCloud Connector
    Currently fetches the health and version endpoints (no auth).
    To pull stories, export MEDIACLOUD_API_KEY in the worker environment.
    """
    try:
        session = get_session()
        api_key = os.environ.get("MEDIACLOUD_API_KEY")
        if api_key:
            session.headers.update({"Authorization": f"Token {api_key}"})
            
        # 1. Fetch version (public)
        version_resp = session.get("https://search.mediacloud.org/api/version", timeout=15)
        version_data = version_resp.json() if version_resp.status_code == 200 else {}
        
        payload = {
            "version": version_data
        }

        # 2. If we have a key, fetch story count for major topics
        if api_key:
            US_NATIONAL = "34412234"
            queries = ["climate change", "ukraine", "election"]
            story_counts = {}
            for q in queries:
                count_resp = session.get(
                    "https://search.mediacloud.org/api/stories_public/count",
                    params={"q": q, "fq": f"collection_ids:{US_NATIONAL}"}
                )
                if count_resp.status_code == 200:
                    story_counts[q] = count_resp.json().get("count", 0)
            
            payload["story_counts"] = story_counts
            
        return json.dumps({
            "source": "mediacloud",
            "data": payload
        })
    except Exception as e:
        return json.dumps({"source": "mediacloud", "error": str(e)})

