"""Discover and encode conventional HTML search forms."""

from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin


@dataclass
class SearchForm:
    action: str
    method: str = "GET"
    query_name: str = "q"
    fields: dict[str, str] = field(default_factory=dict)

    def payload(self, query: str) -> dict[str, str]:
        values = dict(self.fields)
        values[self.query_name] = query
        return values

    def request_url(self, query: str) -> str:
        if self.method == "POST":
            return self.action
        separator = "&" if "?" in self.action else "?"
        return self.action + separator + urlencode(self.payload(query))


class _FormParser(HTMLParser):
    def __init__(self, page_url: str):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.forms: list[SearchForm] = []
        self.current: SearchForm | None = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form":
            self.current = SearchForm(
                action=urljoin(self.page_url, attributes.get("action") or self.page_url),
                method=(attributes.get("method") or "GET").upper(),
                query_name="",
            )
        elif self.current and tag in {"input", "textarea", "select"}:
            name = attributes.get("name")
            if not name:
                return
            input_type = (attributes.get("type") or "text").lower()
            if input_type in {"submit", "button", "image", "reset", "file"}:
                return
            query_names = {"q", "query", "search", "keyword", "keywords", "term", "searchterm"}
            placeholder = (attributes.get("placeholder") or "").lower()
            if input_type == "search" or name.lower() in query_names or "search" in placeholder:
                self.current.query_name = name
            else:
                self.current.fields[name] = attributes.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form" and self.current:
            self.forms.append(self.current)
            self.current = None


def discover_search_forms(html: str, page_url: str) -> list[SearchForm]:
    """Return forms containing a likely search input, in document order."""
    parser = _FormParser(page_url)
    parser.feed(html)
    return [form for form in parser.forms if form.query_name]
