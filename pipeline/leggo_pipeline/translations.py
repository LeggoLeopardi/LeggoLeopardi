"""Translations: take a poem's translation out of its source (docx table or text file) and write TEI.

Text is kept as in the source. The only normalisation: line ends trimmed and runs of ordinary
spaces collapsed; non-breaking spaces (French typography) are kept.
"""
from __future__ import annotations

import re
from pathlib import Path

import docx
from lxml import etree

from .build_base import STRUCTURAL, TEI_NS, _el, _layout

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
SPACES = re.compile(r"[ \t]+")


def read_block(source: dict, root: Path) -> list[str]:
    """Lines of a source range, exactly as they are.

    docx: paragraphs [start, end) of the translation cell (row 2, column 2) of table `table` (1-based).
    txt: lines [start, end) of the file.
    """
    if "docx" in source:
        table = docx.Document(str(Path(root) / source["docx"])).tables[source["table"] - 1]
        paragraphs = [p.text for p in table.rows[1].cells[1].paragraphs]
        return paragraphs[source["start"] : source["end"]]
    lines = (Path(root) / source["txt"]).read_text(encoding="utf-8").split("\n")
    return lines[source["start"] : source["end"]]


def _clean(line: str) -> str:
    return SPACES.sub(" ", line).strip(" \t\xa0")  # edge nbsp is indentation; inner nbsp is typography


def split_block(
    lines: list[str], title_lines: int = 1, stanza_breaks: bool = True
) -> tuple[list[str], list[list[str]]]:
    """The first `title_lines` non-empty lines are the title; the rest is split into stanzas at blank lines.

    stanza_breaks=False for sources that put a blank line after every verse (Wikisource copies).
    """
    cleaned = [_clean(l) for l in lines]
    title: list[str] = []
    k = 0
    while len(title) < title_lines and k < len(cleaned):
        if cleaned[k]:
            title.append(cleaned[k])
        k += 1
    stanzas: list[list[str]] = [[]]
    for line in cleaned[k:]:
        if line:
            stanzas[-1].append(line)
        elif stanza_breaks and stanzas[-1]:
            stanzas.append([])
    return title, [s for s in stanzas if s]


def build_translation_tei(entry: dict, poem: dict, title: list[str], stanzas: list[list[str]]) -> bytes:
    n = poem["n"]
    tei = etree.Element(f"{{{TEI_NS}}}TEI", nsmap={None: TEI_NS})
    header = _el(tei, "teiHeader")
    fd = _el(header, "fileDesc")
    ts = _el(fd, "titleStmt")
    _el(ts, "title", " / ".join(title) or f"{poem['roman']}. {poem['title']}")
    _el(ts, "author", entry["translator"])
    ps = _el(fd, "publicationStmt")
    _el(ps, "publisher", "LeggoLeopardi")
    _el(_el(ps, "availability"), "p", entry["rights"])
    ns = _el(fd, "notesStmt")
    _el(ns, "note", "Trascrizione dalla fonte indicata, non collazionata.")
    for note in entry.get("notes", []):
        _el(ns, "note", note)
    sd = _el(fd, "sourceDesc")
    bibl = _el(sd, "bibl", entry["bibl"])
    if entry.get("year"):
        _el(bibl, "date", str(entry["year"]), when=str(entry["year"]))
    for s in entry.get("sources", []):
        extra = _el(sd, "bibl", s["label"], type="source")
        if s.get("url"):
            _el(extra, "ptr", target=s["url"])
    _el(_el(_el(header, "profileDesc"), "langUsage"), "language", ident=entry["lang"])

    text = _el(tei, "text")
    text.set(XML_LANG, entry["lang"])
    div = _el(_el(text, "body"), "div", type="translation", corresp=f"../../base/c{n}.xml#c{n}")
    if title:
        head = _el(div, "head", title[0])
        for t in title[1:]:
            _el(head, "lb").tail = t
    for stanza in stanzas:
        if entry["form"] == "prose":
            for para in stanza:
                _el(div, "p", para)
        else:
            lg = _el(div, "lg")
            for line in stanza:
                _el(lg, "l", line)
    _layout(tei, STRUCTURAL | {"notesStmt", "langUsage", "profileDesc", "availability"})
    return etree.tostring(tei, xml_declaration=True, encoding="UTF-8")


def docx_heading(source: dict, root: Path) -> str:
    """The last non-empty paragraph above table `table` (Zecchini's bibliographic heading)."""
    document = docx.Document(str(Path(root) / source["docx"]))
    body = document.element.body
    target = document.tables[source["table"] - 1]._tbl
    heading = ""
    for el in body.iterchildren():
        if el is target:
            return heading
        if el.tag.endswith("}p"):
            text = "".join(t.text or "" for t in el.iter() if t.tag.endswith("}t")).strip()
            if text:
                heading = text
    raise ValueError(f"table {source['table']} not found in {source['docx']}")
