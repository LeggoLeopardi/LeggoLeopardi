"""Commentaries: notes transcribed from the commented editions, written as TEI notes pointing at base verses.

Notes are stand-off: <note type="comm" target=".../base/c12.xml#c12.v1" targetEnd="...#c12.v3">,
the model used by LeggoManzoni. The text comes from pipeline/commenti.json, transcribed by reading
the page images; inline marks there are *italic* and **bold**.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from lxml import etree

from . import paths
from .build_base import STRUCTURAL, TEI_NS, _el, _layout
from .manifest import load_manifest

MARK = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*")
CONFIG = paths.ROOT / "pipeline" / "commenti.json"
OUT = paths.ROOT / "tei" / "commenti"


def inline_segments(text: str) -> list[tuple[str, str]]:
    """Split text at *italic* and **bold** marks: [(style, text)], style "" for plain."""
    out, pos = [], 0
    for m in MARK.finditer(text):
        if m.start() > pos:
            out.append(("", text[pos : m.start()]))
        out.append(("bold", m.group(1)) if m.group(1) is not None else ("italic", m.group(2)))
        pos = m.end()
    if pos < len(text):
        out.append(("", text[pos:]))
    return out


def _fill(el, text: str) -> None:
    """Append text with <hi rend="..."> for marked spans after whatever el already holds."""
    last = el[-1] if len(el) else None
    for style, chunk in inline_segments(text):
        if style:
            last = _el(el, "hi", chunk, rend=style)
        elif last is None:
            el.text = (el.text or "") + chunk
        else:
            last.tail = (last.tail or "") + chunk


def build_commentary_tei(entry: dict, poem: dict) -> bytes:
    n = poem["n"]
    base = f"../../base/c{n}.xml#c{n}"
    tei = etree.Element(f"{{{TEI_NS}}}TEI", nsmap={None: TEI_NS})
    header = _el(tei, "teiHeader")
    fd = _el(header, "fileDesc")
    ts = _el(fd, "titleStmt")
    _el(ts, "title", f"Commento a {poem['roman']}. {poem['title']}")
    _el(ts, "title", entry["short"], type="short")
    _el(ts, "author", entry["author"])
    ps = _el(fd, "publicationStmt")
    _el(ps, "publisher", "LeggoLeopardi")
    _el(_el(ps, "availability"), "p", "Pubblico dominio")
    ns = _el(fd, "notesStmt")
    _el(ns, "note", "Trascrizione dall'immagine della pagina, da verificare.")
    _el(ns, "note", f"Selezione: {entry['selection']}.")
    bibl = _el(_el(fd, "sourceDesc"), "bibl", entry["bibl"])
    _el(bibl, "date", str(entry["year"]), when=str(entry["year"]))
    _el(bibl, "note", entry["source"], type="source")

    div = _el(_el(_el(tei, "text"), "body"), "div", type="commentary", corresp=base)
    for para in entry.get("intro", []):
        _fill(_el(div, "note", type="intro", target=base), para)
    for i, note in enumerate(entry["notes"], start=1):
        start, end = note["verses"]
        el = _el(div, "note", type="comm", n=str(i), target=f"{base}.v{start}", targetEnd=f"{base}.v{end}")
        if note.get("added"):
            el.set("subtype", "added")
        _el(el, "ref", note["lemma"]).tail = " "
        _fill(el, note["text"])
    _layout(tei, STRUCTURAL | {"notesStmt", "availability"})
    return etree.tostring(tei, xml_declaration=True, encoding="UTF-8")


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    manifest = {e["n"]: e for e in load_manifest(paths.CANTI)}
    for key, entries in config.items():
        if key.startswith("_"):
            continue
        poem = manifest[int(key)]
        for entry in entries:
            target = OUT / entry["id"] / f"c{poem['n']}.xml"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(build_commentary_tei(entry, poem))
            print(f"wrote {target.relative_to(paths.ROOT)} ({len(entry['notes'])} notes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
