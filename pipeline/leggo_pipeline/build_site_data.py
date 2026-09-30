"""Turn tei/base into the static JSON the Express app serves (public/data)."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from lxml import etree

from . import paths
from .manifest import load_manifest

TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
NS = {"tei": "http://www.tei-c.org/ns/1.0"}
INDEX_KEYS = ("n", "roman", "title", "slug", "incipit", "status")


def _line_html(l) -> str:
    out = [html.escape(l.text or "", quote=False)]
    for ch in l:
        text = html.escape(ch.text or "", quote=False)
        if ch.tag == f"{TEI}ref":
            text = f'<sup class="noteref">{text}</sup>'
        elif ch.get("rend") == "italic":
            text = f"<em>{text}</em>"
        out.append(text)
        out.append(html.escape(ch.tail or "", quote=False))
    return "".join(out)


def _item(el) -> dict:
    if el.tag == f"{TEI}label":
        return {"type": "label", "text": el.text or ""}
    missing = el.find(f"{TEI}gap") is not None
    rend = el.get("rend") or ""
    return {
        "type": "l",
        "n": int(el.get("n")) if el.get("n") else None,
        "id": el.get(XML_ID),
        "indent": int(rend[len("indent"):]) if rend.startswith("indent") else 0,
        "missing": missing,
        "unnumbered": el.get("n") is None,
        "text": "" if missing else "".join(el.itertext()),
        "html": "" if missing else _line_html(el),
    }


def poem_json(entry: dict, tei_path: Path) -> dict:
    root = etree.parse(str(tei_path)).getroot()
    div = root.find(f".//{TEI}div")
    head_el = div.find(f"{TEI}head")
    head = [] if head_el is None else [head_el.text or ""] + [lb.tail or "" for lb in head_el]
    epigraph = [l.text or "" for l in div.findall(f"{TEI}epigraph/{TEI}l")]
    stanzas = [[_item(el) for el in lg] for lg in div.findall(f"{TEI}lg")]
    first = next((i for st in stanzas for i in st if i["type"] == "l" and not i["missing"]), None)
    return {
        "n": entry["n"],
        "roman": entry["roman"],
        "title": entry["title"],
        "slug": entry["slug"],
        "incipit": first["text"] if first else "",
        "status": entry["status"],
        "source": {
            "label": "WikiLeopardi",
            "status": root.xpath("string(//tei:revisionDesc/@status)", namespaces=NS),
            "pages": root.xpath("//tei:sourceDesc//tei:ptr/@target", namespaces=NS),
        },
        "head": head,
        "epigraph": epigraph,
        "stanzas": stanzas,
    }


def build_site(manifest: list[dict], tei_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for entry in manifest:
        data = poem_json(entry, Path(tei_dir) / f"c{entry['n']}.xml")
        (out_dir / f"c{entry['n']}.json").write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
        index.append({k: data[k] for k in INDEX_KEYS})
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    manifest = load_manifest(paths.CANTI)
    build_site(manifest, paths.TEI_BASE, paths.DATA)
    print(f"wrote {len(manifest)} poems to {paths.DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
