import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        data = fetch_json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson")
        return json.dumps({
            "source": "usgs_earthquakes",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "usgs_earthquakes", "error": str(e)})

