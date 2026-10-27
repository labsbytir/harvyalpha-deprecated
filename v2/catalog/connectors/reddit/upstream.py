import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        # Reddit blocks generic user agents. Spoof heavily or use OAuth in prod.
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
        data = fetch_json("https://www.reddit.com/r/worldnews/new.json?limit=25", headers=headers)
        return json.dumps({
            "source": "reddit",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "reddit", "error": str(e)})

