"""Shared access to the configured outbound proxy secret."""
from .config import get_proxy

__all__ = ["get_proxy"]
