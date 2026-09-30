"""Fetch WikiLeopardi pages (cached) and follow each poem's chain of pages."""
from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable
from pathlib import Path

import requests

API = "https://wikileopardi.altervista.org/wiki_leopardi/api.php"
USER_AGENT = "Mozilla/5.0 (compatible; LeggoLeopardi-pipeline/0.1; DH.ARC Bologna)"
INDEX_TITLE = "N35c Edizione critica"
NOTES_PREFIX = "N35c Note"
SKIP_INDEX = re.compile(r"FRONTESPIZIO|NOTIZIA|^N35c Note")
INDEX_ENTRY = re.compile(r"^\*\s*\[\[(N35c [^\]|]+)\|([^\]]+)\]\]", re.M)
NEXT = re.compile(r"\[\[([^\]|]+)\|\s*→[^\]]*\]\]")


class PageMissing(Exception):
    pass


class ChainError(Exception):
    pass


def _http_fetch(title: str) -> str | None:
    params = {
        "action": "query", "prop": "revisions", "rvprop": "content",
        "titles": title, "format": "json", "redirects": 1,
    }
    r = requests.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    page = next(iter(r.json()["query"]["pages"].values()))
    if "missing" in page or "revisions" not in page:
        return None
    return page["revisions"][0]["*"]


class WikiClient:
    def __init__(self, cache_dir: Path, fetch: Callable[[str], str | None] | None = None, delay: float = 0.5):
        self.cache_dir = Path(cache_dir)
        self.fetch = fetch or _http_fetch
        self.delay = delay

    def _path(self, title: str) -> Path:
        return self.cache_dir / (hashlib.sha1(title.encode("utf-8")).hexdigest() + ".wiki")

    def page(self, title: str) -> str:
        path = self._path(title)
        if path.exists():
            return path.read_text(encoding="utf-8")
        text = self.fetch(title)
        if self.delay:
            time.sleep(self.delay)
        if text is None:
            raise PageMissing(title)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return text


def parse_index(wikitext: str) -> list[tuple[str, str]]:
    return [
        (page.strip(), label.strip())
        for page, label in INDEX_ENTRY.findall(wikitext)
        if not SKIP_INDEX.search(page)
    ]


def next_page(wikitext: str) -> str | None:
    links = NEXT.findall(wikitext)
    return links[-1].strip() if links else None


def follow_chain(client: WikiClient, entry: str, stop: set[str], max_pages: int = 30) -> list[str]:
    pages = [entry]
    title = entry
    while True:
        try:
            text = client.page(title)
        except PageMissing as e:
            raise ChainError(f"poem starting at {entry!r}: page {e} does not exist") from e
        if text.lstrip().upper().startswith("#REDIRECT"):
            raise ChainError(f"poem starting at {entry!r}: page {title!r} is a redirect stub; delete it from the cache")
        nxt = next_page(text)
        # Every poem's last page links on to the next poem or to the notes; no link means a broken chain.
        if nxt is None:
            raise ChainError(f"poem starting at {entry!r}: page {title!r} has no forward link")
        if nxt in stop or nxt.startswith(NOTES_PREFIX):
            return pages
        if nxt in pages:
            raise ChainError(f"poem starting at {entry!r}: loop at {nxt!r}")
        pages.append(nxt)
        if len(pages) > max_pages:
            raise ChainError(f"poem starting at {entry!r}: more than {max_pages} pages")
        title = nxt
