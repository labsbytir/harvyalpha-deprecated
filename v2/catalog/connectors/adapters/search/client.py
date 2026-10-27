"""HTTP client for public, conventional website search forms."""

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlencode
from urllib.request import Request, urlopen
from typing import Optional

from .forms import discover_search_forms


class SearchError(RuntimeError):
    """A site-search request could not be completed."""


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str


@dataclass(frozen=True)
class SearchResponse:
    query: str
    url: str
    status: int
    results: tuple[SearchResult, ...]
    html: str


class _Links(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[SearchResult] = []
        self.href = None
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.text = []

    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            title = " ".join(part for part in self.text if part)
            if title:
                self.links.append(SearchResult(title, urljoin(self.base_url, self.href)))
            self.href = None


def _validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or not parsed.netloc:
        raise ValueError("Search URLs must be public HTTP(S) URLs without credentials")


class SearchClient:
    def __init__(self, timeout: float = 30, user_agent: str = "HarvySearch/1.0"):
        self.timeout = timeout
        self.user_agent = user_agent

    def _request(self, url: str, data: Optional[bytes] = None):
        _validate_url(url)
        headers = {"User-Agent": self.user_agent}
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(url, data=data, headers=headers)
        try:
            return urlopen(request, timeout=self.timeout)
        except (HTTPError, URLError) as error:
            raise SearchError("Site search request failed") from error

    def search(self, page_url: str, query: str) -> SearchResponse:
        """Discover the first conventional search form and submit ``query``."""
        if not query or not query.strip():
            raise ValueError("Search query must not be empty")
        _validate_url(page_url)
        with self._request(page_url) as response:
            landing_html = response.read().decode(response.headers.get_content_charset() or "utf-8", "replace")
            landing_url = response.geturl()
        forms = discover_search_forms(landing_html, landing_url)
        if not forms:
            raise SearchError("No conventional search form found")
        form = forms[0]
        data = None if form.method == "GET" else urlencode(form.payload(query)).encode()
        target = form.request_url(query) if form.method == "GET" else form.action
        with self._request(target, data=data) as response:
            html = response.read().decode(response.headers.get_content_charset() or "utf-8", "replace")
            result_url = response.geturl()
            status = response.status
        parser = _Links(result_url)
        parser.feed(html)
        return SearchResponse(query, result_url, status, tuple(parser.links), html)
