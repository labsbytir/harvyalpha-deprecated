"""Reusable site-search primitives."""

from .client import SearchClient, SearchError, SearchResponse, SearchResult
from .forms import SearchForm, discover_search_forms

__all__ = [
    "SearchClient",
    "SearchError",
    "SearchForm",
    "SearchResponse",
    "SearchResult",
    "discover_search_forms",
]
