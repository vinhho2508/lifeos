"""Fetch a web page for URL ingest, refusing to reach private networks (SSRF guard)."""

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 5
TIMEOUT = 15.0
USER_AGENT = "LifeOS/1.0 (+knowledge-base ingest)"


class FetchError(Exception):
    """The URL could not be fetched; the message is safe to show the user."""


@dataclass
class Fetched:
    url: str
    data: bytes
    content_type: str


def validate_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FetchError("Only http(s) URLs are supported.")
    return parts.geturl()


async def _resolve(host: str) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


async def _check_public(host: str) -> None:
    try:
        addresses = await _resolve(host)
    except OSError:
        raise FetchError(f"Could not resolve {host}.") from None
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
        if not ip.is_global or ip.is_multicast:
            raise FetchError("URLs pointing at private or local addresses are not allowed.")


async def fetch_url(url: str) -> Fetched:
    url = validate_url(url)
    async with httpx.AsyncClient(
        timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": USER_AGENT}
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await _check_public(urlsplit(url).hostname)
            try:
                async with client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = validate_url(urljoin(url, response.headers["location"]))
                        continue
                    if response.status_code >= 400:
                        raise FetchError(f"The page returned HTTP {response.status_code}.")
                    data = bytearray()
                    async for part in response.aiter_bytes():
                        data.extend(part)
                        if len(data) > MAX_BYTES:
                            raise FetchError("The page is larger than 10 MB.")
                    content_type = response.headers.get("content-type", "").split(";")[0]
                    return Fetched(str(response.url), bytes(data), content_type.strip().lower())
            except httpx.HTTPError as e:
                raise FetchError(f"Could not fetch the page: {type(e).__name__}.") from None
    raise FetchError("Too many redirects.")
