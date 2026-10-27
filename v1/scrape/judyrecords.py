"""JudyRecords scraper with candidate entity feedback mining."""
import http.cookiejar
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from urllib.error import HTTPError, URLError

from proxy.config import get_proxy
from search.forms import SearchForm, discover_search_forms

JUDY_BASE = "https://www.judyrecords.com"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _search_parameters(html, query):
    forms = discover_search_forms(html, JUDY_BASE)
    form = next((item for item in forms if item.query_name == "search"), None)
    return (form or SearchForm(JUDY_BASE, query_name="search")).payload(query)

LEGAL_STOPWORDS = {
    "court", "county", "state", "district", "circuit", "records", "record",
    "case", "division", "versus", "judicial", "department", "index", "only",
    "disposed", "pending", "civil", "criminal", "probate", "family", "plaintiff",
    "defendant", "respondent", "petitioner", "appellant", "appellee", "the",
    "and", "for", "with", "from", "inc", "llc", "corp", "corporation",
}


def build_algorithmic_query(query, first_name="", last_name="", state=""):
    """Format query according to JudyRecords search syntax."""
    first = (first_name or "").strip()
    last = (last_name or "").strip()
    st = (state or "").strip().lower()

    if first and last:
        # Lenient 2-comma name match with optional state qualifier
        base = f"{first} {last},,"
        return f"{base} {st}".strip() if st else base
    q = (query or "").strip()
    return f"{q} {st}".strip() if st else q


def create_opener(proxy_url=None):
    """Build cookie-preserving opener with proxy support."""
    handlers = [urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())]
    if proxy_url:
        handlers.append(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))
    return urllib.request.build_opener(*handlers)


def _clean(value):
    return re.sub(r"\s+", " ", value or "").strip(" -|–,:;")


def parse_case_page(html, record_url):
    """Extract structured legal case and party details from JudyRecords HTML."""
    case_info = {
        "url": record_url,
        "title": "",
        "case_number": "",
        "court": "",
        "division": "",
        "file_date": "",
        "case_type": "",
        "case_status": "",
        "parties": [],
        "raw_text": "",
    }

    # Legacy layout: caseInformationDiv
    section_m = re.search(r"<div[^>]*id=[\"']caseInformationDiv[\"'][^>]*>(.*?)</div>", html, re.S)
    if section_m:
        sec_text = re.sub(r"<[^>]+>", " ", section_m.group(1))
        case_info["raw_text"] = " ".join(sec_text.split())

        num_m = re.search(r"Case Number\s+([A-Za-z0-9_.-]+)", sec_text)
        if num_m:
            case_info["case_number"] = num_m.group(1).strip()
        div_m = re.search(r"Court Division\s+([A-Za-z0-9_.\s-]+?)(?=\s+File Date|\s+Case Type|\s+Case Status|\s*$)", sec_text)
        if div_m:
            case_info["division"] = div_m.group(1).strip()
        date_m = re.search(r"File Date\s+(\d{1,2}/\d{1,2}/\d{4})", sec_text)
        if date_m:
            case_info["file_date"] = date_m.group(1).strip()
        type_m = re.search(r"Case Type\s+([A-Za-z0-9_.\s]+?)(?=\s+Case Status|\s+Court|\s*$)", sec_text)
        if type_m:
            case_info["case_type"] = type_m.group(1).strip()
        status_m = re.search(r"Case Status\s+([A-Za-z0-9_.\s]+?)(?=\s+Case Type|\s+Court|\s*$)", sec_text)
        if status_m:
            case_info["case_status"] = status_m.group(1).strip()

    # Modern layout text scope
    article_m = re.search(r"<article[^>]*class=[\"'][^\"']*record[^\"']*page[^\"']*[\"'][^>]*>(.*?)</article>", html, re.S)
    scope_html = article_m.group(1) if article_m else html
    text = " ".join(re.sub(r"<[^>]+>", " ", scope_html).split())
    if not case_info["raw_text"]:
        case_info["raw_text"] = text[:4000]

    # OSCN records use a stable server-rendered layout.
    if re.search(r'id=["\']oscn-content["\']', scope_html, re.I):
        m = re.search(r"\bNo\.\s*([A-Za-z]{1,5}-\d{4}-\d+[A-Za-z0-9-]*)", text, re.I)
        if m:
            case_info["case_number"] = m.group(1)
        m = re.search(r"No\.\s*[A-Za-z0-9-]+\s*\(([^)]+)\)", text, re.I)
        if m:
            case_info["case_type"] = _clean(m.group(1))
        heading_m = re.search(r'<h2[^>]*class=["\'][^"\']*styletop[^"\']*["\'][^>]*>(.*?)</h2>', scope_html, re.I | re.S)
        heading_text = " ".join(re.sub(r"<[^>]+>", " ", heading_m.group(1)).split()) if heading_m else text
        m = re.search(r"District Court in and for\s+([A-Za-z ]+?)\s+County\s*,\s*([A-Za-z ]+)$", heading_text, re.I)
        if m:
            case_info["court"] = _clean(f"{m.group(1)} County, {m.group(2)} District Court")
        m = re.search(r"Filed:\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.I)
        if m:
            case_info["file_date"] = m.group(1)
        if re.search(r"Closed:\s*\d{1,2}/\d{1,2}/\d{4}", text, re.I):
            case_info["case_status"] = "Closed"
        party_m = re.search(r'<h2[^>]*class=["\'][^"\']*section\s+party[^"\']*["\'][^>]*>.*?</h2>\s*<p[^>]*>(.*?)</p>', scope_html, re.I | re.S)
        if party_m:
            party_lines = re.sub(r"<br\s*/?>", "\n", party_m.group(1), flags=re.I)
            party_lines = re.sub(r"<[^>]+>", "", party_lines)
            for line in party_lines.splitlines():
                pm = re.match(r"\s*(.*?)\s*,\s*(Plaintiff|Defendant|ARRESTING AGENCY)\s*$", line, re.I)
                if pm:
                    case_info["parties"].append({"name": _clean(pm.group(1)), "role": pm.group(2).lower().replace(" ", "_")})

    # Title
    title_line = ""
    for pat in (r'class=["\']titlegen["\']>(.*?)</', r'class=["\']recordContext[^"\']*["\']>(.*?)</h2>'):
        m = re.search(pat, html, re.I | re.S)
        if m:
            title_line = _clean(m.group(1))
            if title_line:
                break
    if not title_line:
        m = re.search(r"^(.+?)\s+(?:vs\.?|v\.|VS)\s+(.+?)(?=\s+-\s+|\s{2,}|\||$)", text, re.I)
        if m:
            title_line = _clean(m.group(0))
    page_title_m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if title_line:
        case_info["title"] = title_line
    elif page_title_m:
        case_info["title"] = re.split(r"\s+-\s+", _clean(page_title_m.group(1)), maxsplit=1)[0]

    # Fields (fallback if missing)
    if not case_info["case_number"]:
        for pat in (
            r"Case Number[:\s]+([A-Za-z0-9_.-]+)",
            r"Case No\.?[:\s]+([A-Za-z0-9_.-]+)",
            r"\bCase[:\s]+([A-Za-z0-9_.-]+)",
        ):
            m = re.search(pat, text, re.I)
            if m:
                case_info["case_number"] = m.group(1).strip()
                break

    if not case_info["court"]:
        m = re.search(r"Court[:\s]+([A-Za-z0-9,.\s-]{3,80}?)(?=\s+(?:Judicial|File|Case|Party|Location|Register|$))", text, re.I)
        if m:
            case_info["court"] = _clean(m.group(1))
        elif page_title_m:
            case_info["court"] = _clean(page_title_m.group(1))

    if not case_info["division"]:
        m = re.search(r"Court Division[:\s]+([A-Za-z0-9_.\s-]{2,60}?)(?=\s+(?:File|Case|Status|Party|$))", text, re.I)
        if m:
            case_info["division"] = _clean(m.group(1))

    if not case_info["file_date"]:
        date_val = ""
        for pat in (r"(?:File|Filing|Filed|Date Filed|Filing Date)[:\s]+([A-Za-z0-9, /-]{6,24})",):
            m = re.search(pat, text, re.I)
            if m:
                date_val = m.group(1)
                break
        dm = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", date_val) or re.search(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}", date_val, re.I)
        if dm:
            case_info["file_date"] = _clean(dm.group(0))
        else:
            dm = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", text) or re.search(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}", text, re.I)
            if dm:
                case_info["file_date"] = _clean(dm.group(0))

    if not case_info["case_type"]:
        for pat in (
            r"Case Type[:\s]+([A-Za-z0-9_.\s-]{2,60}?)(?=\s+(?:Case Status|Court|File|Party|Location|Register|$))",
            r"Subtype[:\s]+([A-Za-z0-9_.\s-]{2,60}?)(?=\s+(?:Judge|Status|Party|$))",
        ):
            m = re.search(pat, text, re.I)
            if m:
                case_info["case_type"] = _clean(m.group(1))
                break

    if not case_info["case_status"]:
        for pat in (
            r"Case Status[:\s]+([A-Za-z0-9_.\s-]{2,40}?)(?=\s+(?:Party|Disposition|Register|Case|$))",
            r"Status[:\s]+([A-Za-z ]{2,40}?)(?=\s+(?:Next|Date|Party|Disposition|Register|$))",
        ):
            m = re.search(pat, text, re.I)
            if m:
                case_info["case_status"] = _clean(m.group(1))
                break

    # Parties
    if not case_info["parties"]:
        m = re.search(r"(.+?)\s+(?:vs\.?|v\.|VS)\s+(.+?)(?:\s{2,}|\||$)", case_info["title"], re.I)
        if m:
            p1 = _clean(m.group(1))
            p2 = _clean(m.group(2))
            p2 = re.sub(r"\s+et\s*al\.?$", "", p2, flags=re.I).strip()
            p1 = re.sub(r"\s+et\s*al\.?$", "", p1, flags=re.I).strip()
            if p1 and len(p1) < 100:
                case_info["parties"].append({"name": p1, "role": "plaintiff"})
            if p2 and len(p2) < 100:
                case_info["parties"].append({"name": p2, "role": "defendant"})

    seen = {p["name"].lower() for p in case_info["parties"]}
    for role, label in (("plaintiff", "Plaintiff"), ("defendant", "Defendant")):
        for m in re.finditer(rf"{label}s?\s*[:]\s*(.+?)(?=\s+(?:Plaintiff|Defendant|Disposition|Register|Party\s+Details|Party\s+Information|Case|Court|File|Status|$))", text, re.I):
            name = _clean(m.group(1))
            if name and len(name) < 120 and name.lower() not in seen:
                name = re.sub(r"\s+(Plaintiff|Defendant)$", "", name, flags=re.I).strip()
                if name:
                    case_info["parties"].append({"name": name, "role": role})
                    seen.add(name.lower())

    for m in re.finditer(r"\b(Plaintiff|Defendant)\s+([A-Z][A-Za-z0-9,.\s'-]{2,60}?)(?=\s+(?:Address|Active|DOB|Party|$))", text):
        role = "plaintiff" if m.group(1).lower().startswith("plaintiff") else "defendant"
        name = _clean(m.group(2))
        if name and len(name) < 80 and name.lower() not in seen:
            case_info["parties"].append({"name": name, "role": role})
            seen.add(name.lower())

    return case_info


def extract_candidate_terms(cases, max_candidates=10):
    """Generate next algorithmic search terms from parsed cases."""
    words = Counter()
    for case in cases:
        for party in case.get("parties", []):
            name = party.get("name", "").strip()
            if len(name) >= 3 and name.lower() not in LEGAL_STOPWORDS:
                words[name] += 5
        # Words from case title
        title_tokens = re.findall(r"\b[A-Za-z][A-Za-z-]{2,25}\b", case.get("title", ""))
        for token in title_tokens:
            low = token.lower()
            if low not in LEGAL_STOPWORDS and not token.isupper():
                words[token] += 1

    candidates = []
    for term, score in words.most_common(max_candidates):
        candidates.append({"query": term, "score": score, "origin": "case_entity"})
    return candidates


def search_judyrecords(query, first_name="", last_name="", state="", max_records=10, proxy_url=None):
    """Execute search flow on JudyRecords using session cookies and proxy."""
    proxy = proxy_url or get_proxy()
    opener = create_opener(proxy)
    formatted_query = build_algorithmic_query(query, first_name=first_name, last_name=last_name, state=state)

    common_headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    ajax_headers = {
        **common_headers,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{JUDY_BASE}/",
    }

    # 1. Warm session cookies and discover the site's search field.
    with opener.open(urllib.request.Request(JUDY_BASE, headers=common_headers), timeout=25) as home:
        home_html = home.read().decode("utf-8", "replace")

    # 2. Add search job using the discovered search field.
    add_url = f"{JUDY_BASE}/addSearchJob?" + urllib.parse.urlencode(_search_parameters(home_html, formatted_query))
    with opener.open(urllib.request.Request(add_url, headers=ajax_headers), timeout=25) as resp:
        try:
            add_res = json.loads(resp.read().decode())
        except Exception:
            add_res = {}
        if add_res.get("status") != "succeeded":
            return {"status": "inconclusive", "query": formatted_query, "cases": [], "candidate_terms": []}

    # Judy's search is asynchronous; poll when the response supplies a job ID.
    search_job_id = add_res.get("searchJobId")
    if search_job_id:
        status_url = f"{JUDY_BASE}/getSearchJobStatus?" + urllib.parse.urlencode({"searchJobId": search_job_id})
        processing_status = ""
        for _ in range(50):
            time.sleep(0.2)
            with opener.open(urllib.request.Request(status_url, headers=ajax_headers), timeout=25) as resp:
                try:
                    status_res = json.loads(resp.read().decode())
                except Exception:
                    status_res = {}
            if status_res.get("status") != "succeeded":
                return {"status": "inconclusive", "query": formatted_query, "cases": [], "candidate_terms": []}
            processing_status = status_res.get("processingStatus", "")
            if processing_status in ("failed", "succeeded"):
                break
        if processing_status != "succeeded":
            return {"status": "inconclusive", "query": formatted_query, "cases": [], "candidate_terms": []}
    else:
        time.sleep(1.2)

    # 3. Retrieve results page
    results_url = f"{JUDY_BASE}/getSearchResults/?page=1"
    req_res = urllib.request.Request(results_url, headers={**common_headers, "Referer": f"{JUDY_BASE}/"})
    with opener.open(req_res, timeout=25) as resp:
        results_html = resp.read().decode()

    # 4. Extract record links
    record_slugs = re.findall(r"href=[\"'](/record/[a-z0-9]+)[\"']", results_html)
    record_slugs = list(dict.fromkeys(record_slugs))[:max_records]

    # 5. Fetch and parse each case. Spider is preferred when configured.
    cases = []
    spider_key = os.environ.get("SPIDER_API_KEY", "").strip()
    if spider_key:
        from v1.scrape.client import scrape as spider_scrape
    for slug in record_slugs:
        rec_url = f"{JUDY_BASE}{slug}"
        try:
            if spider_key:
                pages = spider_scrape(rec_url, spider_key, proxy, request="http", return_format="raw", metadata=True, cache=False)
                good = next((page for page in pages if page.get("status") == 200 and not page.get("error") and page.get("content")), None)
                if not good:
                    continue
                case_data = parse_case_page(good["content"], rec_url)
            else:
                with opener.open(urllib.request.Request(rec_url, headers=common_headers), timeout=25) as resp:
                    case_data = parse_case_page(resp.read().decode(), rec_url)
            cases.append(case_data)
        except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError):
            continue

    candidate_terms = extract_candidate_terms(cases)
    return {
        "status": "ok" if cases else "inconclusive",
        "query": formatted_query,
        "result_count": len(cases),
        "cases": cases,
        "candidate_terms": candidate_terms,
    }
