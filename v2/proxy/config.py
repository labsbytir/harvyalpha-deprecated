"""Read and validate the proxy endpoint without embedding credentials."""
import os
from urllib.parse import urlsplit


def get_proxy(env=None, *, required=False):
    """Return WEBSHARE_PROXY_URL from process env or a Worker env binding."""
    if env is None:
        value = os.environ.get("WEBSHARE_PROXY_URL", "")
    elif isinstance(env, dict):
        value = env.get("WEBSHARE_PROXY_URL", "")
    else:
        value = getattr(env, "WEBSHARE_PROXY_URL", "")

    if not value:
        if required:
            raise ValueError("WEBSHARE_PROXY_URL must be configured")
        return ""
    if not isinstance(value, str):
        raise ValueError("WEBSHARE_PROXY_URL must be a proxy endpoint URL")
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https", "socks5") or not parsed.hostname or not parsed.port:
            raise ValueError
    except ValueError:
        raise ValueError("WEBSHARE_PROXY_URL must be a proxy endpoint URL with a host and port") from None
    return value
