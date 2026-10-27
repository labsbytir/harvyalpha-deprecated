import os
import json
import csv
import requests
from io import StringIO
from typing import List, Dict, Any, Optional

# NASA FIRMS API base URLs
FIRMS_API_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
# Fallback to public open data (e.g. MODIS 24h global) if no API key is provided
FALLBACK_CSV_URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv"

def fetch_active_fires(bbox: Optional[str] = None, days: int = 1) -> List[Dict[str, Any]]:
    """
    Fetch active fires from NASA FIRMS.
    Uses FIRMS_API_KEY if available, otherwise falls back to a public 24h CSV download.
    """
    api_key = os.environ.get("FIRMS_API_KEY")
    
    if not api_key:
        print("WARNING: FIRMS_API_KEY environment variable not set. Falling back to public global 24h CSV.")
        return _fetch_fallback_csv()
    
    # If using the API, default to a global bounding box if none is provided
    # bbox format: west,south,east,north
    if not bbox:
        bbox = "-180,-90,180,90"
        
    source = "VIIRS_SNPP_NRT"
    url = f"{FIRMS_API_URL}/{api_key}/{source}/{bbox}/{days}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return _parse_csv(response.text)
    except Exception as e:
        print(f"Error fetching FIRMS API data: {e}")
        print("Attempting to fall back to public global CSV...")
        return _fetch_fallback_csv()

def _fetch_fallback_csv() -> List[Dict[str, Any]]:
    try:
        response = requests.get(FALLBACK_CSV_URL)
        response.raise_for_status()
        return _parse_csv(response.text)
    except Exception as e:
        print(f"Error fetching fallback FIRMS CSV: {e}")
        return []

def _parse_csv(csv_data: str) -> List[Dict[str, Any]]:
    reader = csv.DictReader(StringIO(csv_data))
    records = []
    for row in reader:
        records.append(dict(row))
    return records

if __name__ == "__main__":
    print("Testing NASA FIRMS Connector...")
    fires = fetch_active_fires(days=1)
    print(f"Fetched {len(fires)} fire records.")
    if fires:
        print("Sample of first record:")
        print(json.dumps(fires[0], indent=2))
