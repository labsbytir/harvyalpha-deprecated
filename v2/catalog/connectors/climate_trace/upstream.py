import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        data = fetch_json("https://api.climatetrace.org/v4/country/emissions", params={"country": "USA"})
        return json.dumps({
            "source": "climate_trace",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "climate_trace", "error": str(e)})

