import json
from core.http import fetch_json

def fetch_data() -> str:
    try:
        data = fetch_json("https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP?alertlevel=Green,Orange,Red")
        return json.dumps({
            "source": "gdacs",
            "data": data
        })
    except Exception as e:
        return json.dumps({"source": "gdacs", "error": str(e)})

