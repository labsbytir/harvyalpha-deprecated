import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        data = fetch_json("https://ghoapi.azureedge.net/api/Indicator")
        return json.dumps({
            "source": "who_gho",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "who_gho", "error": str(e)})

