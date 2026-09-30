"""Build, merge and load canti.json, the list of the 41 Canti."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

from . import paths
from .harvest import INDEX_TITLE, WikiClient, follow_chain, parse_index

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}
HAND_KEYS = ("title", "title_variants", "pre_roles", "status", "base_witness", "witnesses")


def roman_to_int(r: str) -> int:
    total = 0
    for i, ch in enumerate(r):
        v = ROMAN[ch]
        total += -v if i + 1 < len(r) and ROMAN[r[i + 1]] > v else v
    return total


def slugify(title: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


def build_manifest(entries: list[tuple[str, str]], chains: list[list[str]]) -> list[dict]:
    manifest = []
    for (entry, label), chain in zip(entries, chains, strict=True):
        m = re.match(r"\s*([IVXL]+)\.\s*(.*)$", label)
        if not m:
            raise ValueError(f"index label without roman numeral: {label!r}")
        roman, title = m.group(1), m.group(2).strip()
        manifest.append(
            {
                "n": roman_to_int(roman),
                "roman": roman,
                "title": title,
                "slug": slugify(title) or f"frammento-{roman.lower()}",
                "base_witness": "N35c",
                "witnesses": ["N35c"],
                "title_variants": [],
                "wiki_pages": chain,
                "pre_roles": None,
                "status": {"leggo": "provisional", "traduco": "none", "collaziono": "none", "concordanza": "none"},
            }
        )
    return manifest


def merge_existing(new: list[dict], old: list[dict]) -> list[dict]:
    by_n = {e["n"]: e for e in old}
    merged = []
    for e in new:
        keep = by_n.get(e["n"], {})
        merged.append({**e, **{k: keep[k] for k in HAND_KEYS if k in keep}})
    return merged


def load_manifest(path: Path = paths.CANTI) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    client = WikiClient(paths.CACHE)
    entries = parse_index(client.page(INDEX_TITLE))
    stop = {page for page, _ in entries}
    chains = [follow_chain(client, page, stop) for page, _ in entries]
    manifest = build_manifest(entries, chains)
    if paths.CANTI.exists():
        manifest = merge_existing(manifest, load_manifest())
    ns = [e["n"] for e in manifest]
    if ns != list(range(1, len(ns) + 1)):
        raise SystemExit(f"poem numbers are not 1..{len(ns)}: {ns}")
    paths.CANTI.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {paths.CANTI} with {len(manifest)} poems, {sum(len(e['wiki_pages']) for e in manifest)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
