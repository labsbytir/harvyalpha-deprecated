import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        data = fetch_json("https://opensky-network.org/api/states/all")
        return json.dumps({
            "source": "opensky",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "opensky", "error": str(e)})

