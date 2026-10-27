"""Import connector metadata from a local Civontology Stream Catalog checkout."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

REPO_URL = "https://github.com/pennytir/obsidian-civontology"
CATALOG_PATH = "Ingestion/Stream Catalog"

DIRECTORY_SOURCES = [
	("census-places-v2025", "Census V2025 Places CSV", "bulk_dataset"),
	("census-government-organizations", "Census government organization data", "bulk_dataset"),
	("census-tigerweb", "Census TIGERweb", "api"),
	("usa-gov-local-governments", "USA.gov local governments", "directory"),
	("state-government-directories", "State government directories", "directory"),
	("nj-gov-municipal-directory", "NJ.gov municipal directory", "directory"),
	("city-data", "City-Data", "directory"),
	("citydirectory-us", "CityDirectory.us", "directory"),
	("falling-rain", "Falling Rain", "directory"),
	("statsamerica", "StatsAmerica", "directory"),
	("uoregon-geocoding", "University of Oregon geocoding resources", "reference"),
	("wikipedia-context", "Wikipedia context and revision data", "reference"),
	("nces-common-core-of-data", "NCES Common Core of Data", "bulk_dataset"),
	("state-education-agencies", "State education agencies", "directory"),
	("state-legislature-websites", "State legislature websites", "directory"),
	("county-government-directories", "County government directories", "directory"),
	("municipal-government-websites", "Municipal government websites", "directory"),
	("school-district-websites", "School district websites", "directory"),
	("special-district-websites", "Special-district websites", "directory"),
	("official-agency-directories", "Official agency directories", "directory"),
]

MUNICIPAL_SOURCES = [
	("civicplus-civicengage", "CivicPlus / CivicEngage", "cms"),
	("civicplus-central", "CivicPlus Central", "cms"),
	("civicplus-evolve", "CivicPlus Evolve", "cms"),
	("civicplus-open", "CivicPlus Open", "cms"),
	("granicus-govaccess", "Granicus govAccess", "cms"),
	("granicus-opencities", "Granicus OpenCities", "cms"),
	("revize", "Revize", "cms"),
	("catalis-govoffice", "Catalis / GovOffice", "cms"),
	("civiclive", "CivicLive", "cms"),
	("town-web", "Town Web", "cms"),
	("wordpress", "WordPress municipal sites", "cms"),
	("drupal", "Drupal municipal sites", "cms"),
	("custom-municipal-sites", "Custom or unknown municipal sites", "cms"),
	("rss-feeds", "RSS feeds", "feed"),
	("atom-feeds", "Atom feeds", "feed"),
	("ics-calendars", "ICS calendars", "feed"),
	("schema-org-events", "Schema.org event data", "structured_web"),
	("municipal-document-centers", "Municipal document centers", "document_portal"),
	("meeting-calendar-portals", "Meeting/calendar portals", "document_portal"),
	("jobs-procurement-portals", "Jobs and procurement portals", "document_portal"),
]

SOCIAL_SOURCES = [
	("reddit-api", "Reddit API", "social_api"),
	("locationreddits-wiki", "LocationReddits community wiki", "community_reference"),
	("reddit-public-communities", "Public Reddit communities", "social_api"),
	("facebook-public-groups", "Public Facebook groups", "social_capability_gated"),
	("facebook-official-pages", "Official Facebook pages", "social_capability_gated"),
	("instagram", "Instagram", "social_capability_gated"),
	("x-twitter", "X/Twitter", "social_capability_gated"),
	("bluesky", "Bluesky", "social_api"),
	("linkedin", "LinkedIn", "social_capability_gated"),
	("youtube-channels", "YouTube channels", "social_api"),
	("vimeo-channels", "Vimeo channels", "social_api"),
	("official-social-profile-links", "Other official social-profile links", "link_discovery"),
	("community-source-validation", "Community-source validation feeds", "validation"),
]

DATA_PORTALS = [
	("dataportal-search", "DataPortals.org search", "discovery_catalog", "https://dataportal.org/search/"),
	("better-data-portal", "Better Data Portal", "discovery_catalog", "https://www.betterdataportal.com/"),
	("our-world-in-data", "Our World in Data", "data_and_catalog", "https://ourworldindata.org/"),
	("statista", "Statista", "commercial_gated", "https://www.statista.com/"),
	("usafacts", "USAFacts", "data_and_catalog", "https://usafacts.org/"),
	("tableau-public-data", "Tableau free public-data sets", "discovery_catalog", "https://www.tableau.com/learn/articles/free-public-data-sets"),
	("humanitarian-data-exchange", "Humanitarian Data Exchange", "data_and_catalog", "https://data.humdata.org/"),
]

BULK_SCOPES = [
	("bulk.openaddresses", "OpenAddresses US bulk download", "bulk_dataset", "Ingestion/Stream Catalog/Bulk Data/Addresses.md"),
	("bulk.un-comtrade", "UN Comtrade imports/exports", "bulk_or_api", "Ingestion/Stream Catalog/Bulk Data/Import & Exports.md"),
	("bulk.initial-seed-campaign", "Initial seed campaign sources", "manifest_driven_campaign", "Ingestion/Stream Catalog/Bulk Data/Seed Data Plan (Bare Metal GPU or Worker (Cloudflare worker or Browser Run)).md"),
]


def frontmatter_value(text: str, label: str) -> str | None:
	match = re.search(rf"(?m)^- \*\*{re.escape(label)}:\*\*\s*(.+?)\s*$", text)
	return match.group(1).strip() if match else None


def catalog_state(value: str | None) -> str:
	if not value:
		return "unclassified"
	first = value.split("(", 1)[0].strip().lower()
	return first if first in {"approved", "proposed", "planned"} else "unclassified"


def stream_entry(path: Path, root: Path) -> dict[str, object]:
	text = path.read_text(encoding="utf-8", errors="replace")
	relative = path.relative_to(root).as_posix()
	connector_id = path.stem.removeprefix("STR_").lower()
	spec_match = re.search(r"(?m)^- \*\*Source specification:\*\* .*?\((https?://[^)]+)\)", text)
	return {
		"id": f"stream.{connector_id}",
		"source_id": connector_id,
		"label": path.stem.removeprefix("STR_").replace("_", " ").replace("-", " "),
		"family": path.parent.name,
		"catalog_disposition": catalog_state(frontmatter_value(text, "Catalog disposition")),
		"implementation_status": frontmatter_value(text, "Civontology implementation status") or "unverified; no implementation status recorded",
		"rollout_horizon": frontmatter_value(text, "Rollout horizon") or "unclassified",
		"source_specification_url": spec_match.group(1) if spec_match else None,
		"source_catalog_url": f"{REPO_URL}/blob/main/{quote(CATALOG_PATH + '/' + relative, safe='/')}",
		"enabled": False,
		"code_copied": False,
	}


def reference_entry(path: Path, root: Path) -> dict[str, object]:
	text = path.read_text(encoding="utf-8", errors="replace")
	relative = path.relative_to(root).as_posix()
	ref_id = path.stem.removeprefix("REF_").lower()
	return {
		"id": f"reference.{ref_id}",
		"label": path.stem.removeprefix("REF_").replace("_", " ").replace("-", " "),
		"family": path.parent.name,
		"kind": "reference_only",
		"source_catalog_url": f"{REPO_URL}/blob/main/{quote(CATALOG_PATH + '/' + relative, safe='/')}",
		"enabled": False,
	}


def import_catalog(catalog_root: Path, commit: str | None = None) -> dict[str, object]:
	streams_dir = catalog_root / "Streams"
	streams = [stream_entry(path, streams_dir) for path in sorted(streams_dir.rglob("STR_*.md"))]
	references = [reference_entry(path, streams_dir) for path in sorted(streams_dir.rglob("REF_*.md"))]
	requested = []
	for family, sources in (("directory_government", DIRECTORY_SOURCES), ("municipal_sites", MUNICIPAL_SOURCES), ("social_community", SOCIAL_SOURCES)):
		for source_id, label, source_type in sources:
			requested.append({
				"id": f"scope.{source_id}",
				"label": label,
				"family": family,
				"source_type": source_type,
				"status": "catalog_only",
				"enabled": False,
				"source": "user-provided scope list",
			})
	portals = [
		{"id": f"portal.{source_id}", "label": label, "source_type": source_type, "url": url, "enabled": False}
		for source_id, label, source_type, url in DATA_PORTALS
	]
	return {
		"schema_version": 1,
		"upstream": {"repository": REPO_URL, "catalog_path": CATALOG_PATH, "commit": commit},
		"connector_policy": "Catalog disposition is not deployment approval. All imported entries remain disabled until their own access, license, schema, and implementation checks pass.",
		"streams": streams,
		"references": references,
		"named_connectors": [{
			"id": "sam-gov",
			"label": "SAM.gov Contract Opportunities API v2",
			"source_catalog_url": f"{REPO_URL}/blob/main/{quote(CATALOG_PATH + '/Scrapers/SAM_GOV.md', safe='/')}",
			"api_documentation_url": "https://open.gsa.gov/api/get-opportunities-public-api/",
			"implementation_status": "implemented; disabled pending SAM_GOV_API_KEY and operator verification",
			"enabled": False,
		}, {
			"id": "civic-scraper-reference",
			"label": "Civic scraper tool reference",
			"source_catalog_url": f"{REPO_URL}/blob/main/{quote(CATALOG_PATH + '/Scrapers/SAM_GOV.md', safe='/')}",
			"reference_url": "https://civic-scraper.readthedocs.io/en/latest/",
			"implementation_status": "reference_only; dependency not added",
			"enabled": False,
		}],
		"requested_scopes": requested,
		"data_portals": portals,
		"bulk_data": [{
			"id": source_id,
			"label": label,
			"source_type": source_type,
			"source_note": note,
			"status": "catalog_only",
			"enabled": False,
		} for source_id, label, source_type, note in BULK_SCOPES],
	}


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("catalog_root", type=Path, help="Local Ingestion/Stream Catalog directory")
	parser.add_argument("--output", type=Path, default=Path("v2/catalog/connector-scopes.json"))
	args = parser.parse_args()
	repo_root = args.catalog_root.parent.parent
	try:
		commit = subprocess.check_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
	except (OSError, subprocess.CalledProcessError):
		commit = None
	manifest = import_catalog(args.catalog_root, commit)
	args.output.parent.mkdir(parents=True, exist_ok=True)
	args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
	print(f"Wrote {len(manifest['streams'])} stream candidates, {len(manifest['references'])} references, "
		f"{len(manifest['requested_scopes'])} requested scopes, {len(manifest['data_portals'])} data portals.")


if __name__ == "__main__":
	main()
