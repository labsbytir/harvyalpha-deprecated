import os
import json
import requests
from typing import Dict, Any

BASE_URL = "https://api.poweroutage.us/v1"

def _get_api_key() -> str:
    return os.environ.get('POWEROUTAGE_US_API_KEY', '')

def _make_request(endpoint: str) -> Dict[str, Any]:
    api_key = _get_api_key()
    if not api_key:
        print("WARNING: POWEROUTAGE_US_API_KEY environment variable not set. Returning empty data.")
        return {}
    
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "WebKey": api_key,
        "x-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {endpoint}: {e}")
        return {}

def fetch_national_outages() -> Dict[str, Any]:
    """Fetch national outage summary."""
    return _make_request("/national")

def fetch_state_outages() -> Dict[str, Any]:
    """Fetch state-level outage summary."""
    return _make_request("/states")

def fetch_county_outages_geojson() -> Dict[str, Any]:
    """Fetch county-level outages as GeoJSON."""
    return _make_request("/geojson/counties")

if __name__ == "__main__":
    print("Testing PowerOutage.us Connector...")
    print("Fetching National Outages...")
    national_data = fetch_national_outages()
    print(json.dumps(national_data, indent=2))
