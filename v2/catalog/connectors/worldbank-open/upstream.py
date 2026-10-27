import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        data = fetch_json("http://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL", params={"format": "json"})
        return json.dumps({
            "source": "worldbank_open",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "worldbank_open", "error": str(e)})

