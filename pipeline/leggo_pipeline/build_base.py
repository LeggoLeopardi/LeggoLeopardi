"""Build tei/base/c{n}.xml (N35c reading text) from cached WikiLeopardi pages."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

from lxml import etree

from . import paths
from .harvest import WikiClient
from .manifest import load_manifest
from .tokens import tokenize
from .wikitext import Line, ParsedPoem, parse_pages

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
WIKI_URL = "https://wikileopardi.altervista.org/wiki_leopardi/index.php?title="
ROLES = {"head", "epigraph", "speaker"}
# Elements whose children are laid out one per line. Mixed-content elements (l, head, bibl)
# are never re-indented, so their string value stays exactly the source text.
STRUCTURAL = {
    "TEI", "teiHeader", "fileDesc", "titleStmt", "publicationStmt", "sourceDesc",
    "revisionDesc", "text", "body", "div", "lg", "epigraph",
}


def _el(parent, tag: str, text: str | None = None, **attrs: str):
    el = etree.SubElement(parent, f"{{{TEI_NS}}}{tag}")
    for k, v in attrs.items():
        el.set(k, v)
    if text:
        el.text = text
    return el


def _layout(root, structural: set[str] = STRUCTURAL) -> None:
    for el in root.iter():
        name = etree.QName(el).localname
        if name in structural and len(el) and not (el.text and el.text.strip()):
            el.text = "\n"
        parent = el.getparent()
        if parent is not None and etree.QName(parent).localname in structural and not (el.tail and el.tail.strip()):
            el.tail = "\n"


def _fill_line(l, line: Line, id_prefix: str) -> None:
    toks = tokenize(line.text, line.italic, line.notes)
    l.text = (line.text[: toks[0].start] if toks else line.text) or None
    last, prev_end, w = None, 0, 0
    for t in toks:
        if last is not None:
            last.tail = line.text[prev_end : t.start] or None
        if t.kind == "w":
            w += 1
            el = _el(l, "w", t.text)
            el.set(XML_ID, f"{id_prefix}.w{w}")
        elif t.kind == "ref":
            el = _el(l, "ref", t.text, type="authorNote")
        else:
            el = _el(l, "pc", t.text)
        if t.italic:
            el.set("rend", "italic")
        last, prev_end = el, t.end
    if last is not None:
        last.tail = line.text[prev_end:] or None


def build_poem_tei(entry: dict, parsed: ParsedPoem) -> bytes:
    n = entry["n"]
    roles = entry.get("pre_roles") or ["head"] * len(parsed.pre)
    if len(roles) != len(parsed.pre) or not set(roles) <= ROLES:
        raise ValueError(
            f"c{n}: pre_roles {roles} does not fit the {len(parsed.pre)} lines before verse 1: {parsed.pre}"
        )

    tei = etree.Element(f"{{{TEI_NS}}}TEI", nsmap={None: TEI_NS})
    header = _el(tei, "teiHeader")
    fd = _el(header, "fileDesc")
    _el(_el(fd, "titleStmt"), "title", f"{entry['roman']}. {entry['title']}".strip())
    _el(_el(fd, "publicationStmt"), "p", "LeggoLeopardi. Testo base provvisorio, da verificare.")
    bibl = _el(
        _el(fd, "sourceDesc"),
        "bibl",
        "Canti, Napoli, Starita, 1835, esemplare corretto (N35c). Trascrizione: WikiLeopardi.",
    )
    for page in entry["wiki_pages"]:
        _el(bibl, "ptr", target=WIKI_URL + quote(page.replace(" ", "_")))
    rd = _el(header, "revisionDesc", status="provisional")
    _el(rd, "change", "Generato da pipeline/leggo_pipeline/build_base.py a partire da WikiLeopardi.")

    div = _el(_el(_el(tei, "text"), "body"), "div", type="canto", n=str(n))
    div.set(XML_ID, f"c{n}")
    heads = [t for t, r in zip(parsed.pre, roles) if r == "head"]
    if heads:
        head = _el(div, "head", heads[0])
        for t in heads[1:]:
            _el(head, "lb").tail = t
    epigraph = [t for t, r in zip(parsed.pre, roles) if r == "epigraph"]
    if epigraph:
        ep = _el(div, "epigraph")
        for t in epigraph:
            _el(ep, "l", t)
    speakers = [t for t, r in zip(parsed.pre, roles) if r == "speaker"]

    pending = sorted(parsed.missing)
    lg = None
    last_n = 0
    unnumbered = 0
    for line in parsed.lines:
        if line.kind == "verse":
            if lg is None or line.stanza_start:
                first = lg is None
                lg = _el(div, "lg", type="stanza")
                if first:
                    for s in speakers:
                        _el(lg, "label", s, type="speaker")
            while pending and pending[0] < line.n:
                g = pending.pop(0)
                gl = _el(lg, "l", n=str(g))
                gl.set(XML_ID, f"c{n}.v{g}")
                _el(gl, "gap", reason="missing-in-source")
            l = _el(lg, "l", n=str(line.n))
            l.set(XML_ID, f"c{n}.v{line.n}")
            if line.indent:
                l.set("rend", f"indent{line.indent}")
            _fill_line(l, line, f"c{n}.v{line.n}")
            last_n, unnumbered = line.n, 0
        else:
            if lg is None:
                lg = _el(div, "lg", type="stanza")
            if line.kind == "label":
                _el(lg, "label", line.text, type="speaker")
            else:
                unnumbered += 1
                pid = f"c{n}.v{last_n}.u{unnumbered}"
                l = _el(lg, "l")
                l.set(XML_ID, pid)
                _fill_line(l, line, pid)
    _layout(tei)
    return etree.tostring(tei, xml_declaration=True, encoding="UTF-8")


def render_report(rows: list[tuple[dict, ParsedPoem]]) -> str:
    out = [
        "# Base text report (WikiLeopardi → tei/base)",
        "",
        "Generated by `python -m leggo_pipeline.build_base`. Review every line under *Problems*.",
        "",
        "| n | canto | verses | stanzas | missing | speakers | unnumbered |",
        "|---|---|---|---|---|---|---|",
    ]
    problems: list[str] = []
    for entry, p in rows:
        verses = [l for l in p.lines if l.kind == "verse"]
        out.append(
            f"| {entry['n']} | {entry['roman']}. {entry['title']} | {len(verses)} | "
            f"{sum(l.stanza_start for l in verses)} | {', '.join(map(str, p.missing)) or '–'} | "
            f"{sum(l.kind == 'label' for l in p.lines)} | {sum(l.kind == 'unnumbered' for l in p.lines)} |"
        )
        problems += [f"- c{entry['n']}: {x}" for x in p.problems]
        if len(verses) > 30 and sum(l.stanza_start for l in verses) == 1:
            problems.append(f"- c{entry['n']}: one stanza only in {len(verses)} verses; check stanza breaks")
    out += ["", "## Problems", ""] + (problems or ["None."])
    return "\n".join(out) + "\n"


def _parse(client: WikiClient, entry: dict) -> ParsedPoem:
    return parse_pages([(t, client.page(t)) for t in entry["wiki_pages"]])


def build_all(manifest: list[dict], client: WikiClient, tei_dir: Path, loci_dir: Path, report_path: Path) -> None:
    tei_dir.mkdir(parents=True, exist_ok=True)
    loci_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for entry in manifest:
        parsed = _parse(client, entry)
        (tei_dir / f"c{entry['n']}.xml").write_bytes(build_poem_tei(entry, parsed))
        loci = [
            {"verse": l.n, "target": s.target, "shown": l.text[s.start : s.end], "start": s.start, "end": s.end}
            for l in parsed.lines
            if l.kind == "verse"
            for s in l.loci
        ]
        (loci_dir / f"c{entry['n']}.json").write_text(
            json.dumps(loci, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        rows.append((entry, parsed))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--show-pre", action="store_true", help="print the lines before verse 1 of every poem and exit")
    args = ap.parse_args(argv)
    manifest = load_manifest(paths.CANTI)
    client = WikiClient(paths.CACHE)
    if args.show_pre:
        for e in manifest:
            print(f"c{e['n']} {e['roman']}: {_parse(client, e).pre}  pre_roles={e.get('pre_roles')}")
        return 0
    build_all(manifest, client, paths.TEI_BASE, paths.LOCI, paths.REPORTS / "base_report.md")
    print(f"wrote {len(manifest)} files to {paths.TEI_BASE}; report: {paths.REPORTS / 'base_report.md'}")
    return 0


def base_verses(path: Path) -> dict[int, str | None]:
    """Numbered verses of tei/base/c{n}.xml; None for a verse missing in the source."""
    root = etree.parse(str(path)).getroot()
    out: dict[int, str | None] = {}
    for l in root.iter(f"{{{TEI_NS}}}l"):
        if l.get("n") and etree.QName(l.getparent()).localname == "lg":
            out[int(l.get("n"))] = None if l.find(f"{{{TEI_NS}}}gap") is not None else "".join(l.itertext())
    return out

if __name__ == "__main__":
    sys.exit(main())
