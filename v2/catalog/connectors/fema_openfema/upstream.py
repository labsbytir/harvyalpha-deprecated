import json
import requests
from typing import List, Dict, Any, Optional

BASE_URL = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"

def fetch_disaster_declarations(state: Optional[str] = None, incident_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch disaster declarations from FEMA OpenFEMA API.
    No API key needed.
    """
    params = {}
    filters = []
    
    if state:
        filters.append(f"state eq '{state}'")
    if incident_type:
        filters.append(f"incidentType eq '{incident_type}'")
        
    if filters:
        params["$filter"] = " and ".join(filters)
        
    params["$top"] = limit
    
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("DisasterDeclarationsSummaries", [])
    except Exception as e:
        print(f"Error fetching FEMA data: {e}")
        return []

if __name__ == "__main__":
    print("Testing FEMA OpenFEMA Connector...")
    print("Fetching recent disaster declarations (limit 5)...")
    results = fetch_disaster_declarations(limit=5)
    print(json.dumps(results, indent=2))
