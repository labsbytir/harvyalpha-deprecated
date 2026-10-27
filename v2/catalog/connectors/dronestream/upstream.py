import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        data = fetch_json("https://api.dronestre.am/data")
        return json.dumps({
            "source": "dronestream",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "dronestream", "error": str(e)})

