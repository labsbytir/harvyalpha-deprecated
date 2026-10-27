import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        data = fetch_json("https://www.imf.org/external/datamapper/api/v1/indicators")
        return json.dumps({
            "source": "imf_datamapper",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "imf_datamapper", "error": str(e)})

