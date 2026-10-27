import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        data = fetch_json("https://api.blockchair.com/bitcoin/stats")
        return json.dumps({
            "source": "blockchair",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "blockchair", "error": str(e)})

