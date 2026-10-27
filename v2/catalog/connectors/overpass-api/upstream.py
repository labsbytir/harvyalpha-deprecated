import json
import time
import logging
from typing import Optional, List, Dict, Tuple

import requests

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {
    "User-Agent": "OpenTIR/1.0 (Emergency Services Connector)"
}

# Default continental US bounding box: (west, south, east, north)
DEFAULT_BBOX = (-125.0, 24.0, -66.9, 49.3)

def _build_emergency_query(south: float, west: float, north: float, east: float, timeout: int = 30) -> str:
    bbox = f"{south},{west},{north},{east}"
    query = f"""
    [out:json][timeout:{timeout}];
    (
      node["amenity"="hospital"]({bbox});
      way["amenity"="hospital"]({bbox});
      node["amenity"="fire_station"]({bbox});
      way["amenity"="fire_station"]({bbox});
      node["amenity"="police"]({bbox});
      way["amenity"="police"]({bbox});
      node["emergency"="shelter"]({bbox});
      way["emergency"="shelter"]({bbox});
      node["emergency"="ambulance_station"]({bbox});
      way["emergency"="ambulance_station"]({bbox});
    );
    out center;
    """
    return query

def _build_global_emergency_query(timeout: int = 300) -> str:
    query = f"""
    [out:json][timeout:{timeout}];
    (
      node["amenity"="hospital"];
      way["amenity"="hospital"];
      node["amenity"="fire_station"];
      way["amenity"="fire_station"];
      node["amenity"="police"];
      way["amenity"="police"];
      node["emergency"="shelter"];
      way["emergency"="shelter"];
      node["emergency"="ambulance_station"];
      way["emergency"="ambulance_station"];
    );
    out center;
    """
    return query

def _execute_query(query: str, timeout: int = 30) -> List[Dict]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.post(OVERPASS_URL, data={"data": query}, timeout=timeout, headers=HEADERS)
            if r.status_code == 429:
                logger.warning("Rate limited (429). Retrying after 2s...")
                time.sleep(2)
                continue
            r.raise_for_status()
            
            data = r.json()
            elements = data.get("elements", [])
            results = []
            
            for el in elements:
                tags = el.get("tags", {})
                
                # Determine category
                category = "unknown"
                if tags.get("amenity") == "hospital":
                    category = "hospital"
                elif tags.get("amenity") == "fire_station":
                    category = "fire"
                elif tags.get("amenity") == "police":
                    category = "police"
                elif tags.get("emergency") == "shelter":
                    category = "shelter"
                elif tags.get("emergency") == "ambulance_station":
                    category = "ambulance"
                
                lat = el.get("lat") or el.get("center", {}).get("lat")
                lon = el.get("lon") or el.get("center", {}).get("lon")
                
                results.append({
                    "osm_id": el["id"],
                    "osm_type": el["type"],
                    "name": tags.get("name", "Unnamed"),
                    "category": category,
                    "lat": lat,
                    "lon": lon,
                    "tags": tags
                })
            return results
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Overpass API: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)
    return []

def fetch_data(bbox: Optional[Tuple[float, float, float, float]] = None) -> str:
    """
    Fetch emergency services for a bounding box (west, south, east, north).
    Defaults to the Continental US.
    Returns JSON string.
    """
    if bbox is None:
        bbox = DEFAULT_BBOX
        
    west, south, east, north = bbox
    query = _build_emergency_query(south, west, north, east, timeout=30)
    
    try:
        # Increase connection timeout slightly over the query timeout to allow the API to return the timeout message
        results = _execute_query(query, timeout=35)
        return json.dumps({
            "source": "overpass_api",
            "bbox": bbox,
            "count": len(results),
            "data": results
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def query_emergency_services_global() -> str:
    """
    Fetch emergency services globally with a generous timeout.
    Returns JSON string.
    """
    query = _build_global_emergency_query(timeout=300)
    try:
        results = _execute_query(query, timeout=305)
        return json.dumps({
            "source": "overpass_api",
            "bbox": "global",
            "count": len(results),
            "data": results
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing Overpass API connector for central Washington DC...")
    dc_bbox = (-77.10, 38.85, -77.00, 38.95)
    
    print(f"Querying bounding box: {dc_bbox}")
    result_json = fetch_data(dc_bbox)
    
    result = json.loads(result_json)
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Success! Found {result['count']} emergency services.")
        for item in result["data"][:5]:
            print(f"- {item['category'].title()}: {item['name']} ({item['osm_type']}/{item['osm_id']}) at {item['lat']}, {item['lon']}")
        if result.get('count', 0) > 5:
            print(f"... and {result['count'] - 5} more.")


