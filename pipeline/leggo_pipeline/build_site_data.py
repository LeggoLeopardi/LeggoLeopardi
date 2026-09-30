"""Turn tei/base into the static JSON the Express app serves (public/data)."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from lxml import etree

from . import paths
from .manifest import load_manifest
from .team_tei import read_team_poem

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


def _esc(s: str | None) -> str:
    return html.escape(s or "", quote=False)


def _segments_html(segs) -> str:
    out = []
    for text, pid in segs:
        if pid:
            out.append(f'<a class="place" href="#place-{pid}" data-place="{pid}">{_esc(text)}</a>')
        else:
            out.append(_esc(text))
    return "".join(out)


def facsimile_json(entry: dict, team_path: Path, facs_path: Path) -> dict:
    """Text of every witness (with its variant places marked), page images and verse zones in percent."""
    team = read_team_poem(team_path)
    facs = etree.parse(str(facs_path)).getroot()
    surfaces = {}
    for s in facs.iter(f"{TEI}surface"):
        w, h = float(s.get("lrx")), float(s.get("lry"))
        zones = {
            z.get("n"): [
                round(100 * int(z.get("ulx")) / w, 2), round(100 * int(z.get("uly")) / h, 2),
                round(100 * (int(z.get("lrx")) - int(z.get("ulx"))) / w, 2),
                round(100 * (int(z.get("lry")) - int(z.get("uly"))) / h, 2),
            ]
            for z in s.findall(f"{TEI}zone")
        }
        surfaces[s.get("n")] = {"image": s.find(f"{TEI}graphic").get("url"), "zones": zones or None}
    witnesses = []
    for wit in team.witnesses:
        sig = wit["siglum"]
        text = team.texts[sig]
        surface = surfaces.get(sig, {"image": None, "zones": None})
        witnesses.append({
            "siglum": sig,
            "label": wit["label"],
            "image": surface["image"],
            "zones": surface["zones"],
            "head": [_segments_html(line) for line in text["head"]],
            "verses": [{"n": n, "html": _segments_html(segs)} for n, segs in sorted(text["verses"].items())],
        })
    places = {
        p.id: {
            "verses": p.verses,
            "readings": [
                dict(r, layers=[dict(l, label=team.layers.get(l["layer"])) for l in r["layers"]])
                for r in p.readings
            ],
        }
        for p in team.places
    }
    return {
        "n": entry["n"], "roman": entry["roman"], "title": entry["title"], "slug": entry["slug"],
        "credits": team.credits, "layers": team.layers, "witnesses": witnesses, "places": places,
    }


def _translation(tid: str, path: Path) -> dict:
    root = etree.parse(str(path)).getroot()
    x = lambda q: root.xpath(q, namespaces=NS)
    div = root.find(f".//{TEI}div")
    head = div.find(f"{TEI}head")
    title = [] if head is None else [head.text or ""] + [lb.tail or "" for lb in head]
    prose = div.find(f"{TEI}p") is not None
    stanzas = [[p.text or "" for p in div.findall(f"{TEI}p")]] if prose else [
        [l.text or "" for l in lg.findall(f"{TEI}l")] for lg in div.findall(f"{TEI}lg")
    ]
    year = x("string(//tei:sourceDesc/tei:bibl[1]/tei:date/@when)")
    bibl = x("//tei:sourceDesc/tei:bibl[1]")[0]
    return {
        "id": tid,
        "lang": x("string(//tei:langUsage/tei:language/@ident)"),
        "translator": x("string(//tei:titleStmt/tei:author)"),
        "year": int(year) if year else None,
        "title": title,
        "bibl": " ".join((bibl.text or "").split()),
        "sources": [
            {"label": " ".join((b.text or "").split()), "url": b.xpath("string(tei:ptr/@target)", namespaces=NS) or None}
            for b in x("//tei:sourceDesc/tei:bibl[@type='source']")
        ],
        "rights": " ".join(x("string(//tei:availability)").split()),
        "notes": [" ".join("".join(n.itertext()).split()) for n in x("//tei:notesStmt/tei:note")],
        "form": "prose" if prose else "verse",
        "stanzas": stanzas,
    }


def translations_json(entry: dict, trad_dir: Path, base_path: Path) -> dict:
    """The Italian base text and every translation of the poem, by language then year."""
    n = entry["n"]
    items = [_translation(d.name, d / f"c{n}.xml") for d in sorted(Path(trad_dir).iterdir()) if (d / f"c{n}.xml").exists()]
    items.sort(key=lambda t: (t["lang"], t["year"] is None, t["year"] or 0, t["id"]))
    italian = poem_json(entry, base_path)
    return {
        "n": n, "roman": entry["roman"], "title": entry["title"], "slug": entry["slug"],
        "italian": {"head": italian["head"], "stanzas": italian["stanzas"]},
        "translations": items,
    }


def _rich(el, skip_ref: bool = False) -> str:
    """HTML of a note: <hi rend="italic|bold"> as <em>/<strong>; the <ref> lemma left out when skip_ref."""
    parts = [] if skip_ref else [_esc(el.text)]
    for ch in el:
        name = etree.QName(ch).localname
        if name == "ref" and skip_ref:
            parts.append(_esc((ch.tail or "").lstrip()))
            continue
        tag = {"italic": "em", "bold": "strong"}.get(ch.get("rend"), "span")
        parts.append(f"<{tag}>{_esc(ch.text)}</{tag}>{_esc(ch.tail)}")
    return "".join(parts).strip()


def commentaries_json(entry: dict, comm_dir: Path) -> dict:
    """Every commentator's notes on the poem, oldest edition first."""
    n = entry["n"]
    items = []
    for d in sorted(Path(comm_dir).iterdir()):
        path = d / f"c{n}.xml"
        if not path.exists():
            continue
        root = etree.parse(str(path)).getroot()
        x = lambda q, r=root: r.xpath(q, namespaces=NS)
        notes = []
        for note in x("//tei:note[@type='comm']"):
            verse = lambda attr: int(note.get(attr).rsplit(".v", 1)[1])
            notes.append({
                "from": verse("target"), "to": verse("targetEnd"),
                "lemma": note.findtext(f"{TEI}ref") or "",
                "html": _rich(note, skip_ref=True),
                "added": note.get("subtype") == "added",
            })
        bibl = x("//tei:sourceDesc/tei:bibl")[0]
        items.append({
            "id": d.name,
            "author": x("string(//tei:titleStmt/tei:author)"),
            "short": x("string(//tei:titleStmt/tei:title[@type='short'])"),
            "year": int(x("string(//tei:sourceDesc/tei:bibl/tei:date/@when)")),
            "bibl": " ".join((bibl.text or "").split()),
            "source": x("string(//tei:sourceDesc/tei:bibl/tei:note[@type='source'])"),
            "status": [" ".join("".join(t.itertext()).split()) for t in x("//tei:notesStmt/tei:note")],
            "intro": [_rich(p) for p in x("//tei:note[@type='intro']")],
            "notes": notes,
        })
    items.sort(key=lambda c: (c["year"], c["id"]))
    return {"n": n, "roman": entry["roman"], "title": entry["title"], "slug": entry["slug"], "commentators": items}


def build_site(
    manifest: list[dict], tei_dir: Path, out_dir: Path,
    team_dir: Path | None = None, facs_dir: Path | None = None, trad_dir: Path | None = None,
    comm_dir: Path | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for entry in manifest:
        n = entry["n"]
        team_path = Path(team_dir) / f"c{n}.xml" if team_dir else None
        facs_path = Path(facs_dir) / f"c{n}.xml" if facs_dir else None
        if team_path and facs_path and team_path.exists() and facs_path.exists():
            entry = dict(entry, status=dict(entry["status"], facsimile="provisional"))
            (out_dir / "facs").mkdir(exist_ok=True)
            (out_dir / "facs" / f"c{n}.json").write_text(
                json.dumps(facsimile_json(entry, team_path, facs_path), ensure_ascii=False) + "\n", encoding="utf-8"
            )
        if comm_dir and any((d / f"c{n}.xml").exists() for d in Path(comm_dir).iterdir()):
            entry = dict(entry, status=dict(entry["status"], commenti="provisional"))
            (out_dir / "comm").mkdir(exist_ok=True)
            (out_dir / "comm" / f"c{n}.json").write_text(
                json.dumps(commentaries_json(entry, comm_dir), ensure_ascii=False) + "\n", encoding="utf-8"
            )
        if trad_dir and any((d / f"c{n}.xml").exists() for d in Path(trad_dir).iterdir()):
            entry = dict(entry, status=dict(entry["status"], traduco="provisional"))
            (out_dir / "trad").mkdir(exist_ok=True)
            (out_dir / "trad" / f"c{n}.json").write_text(
                json.dumps(translations_json(entry, trad_dir, Path(tei_dir) / f"c{n}.xml"), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        data = poem_json(entry, Path(tei_dir) / f"c{n}.xml")
        (out_dir / f"c{n}.json").write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
        index.append({k: data[k] for k in INDEX_KEYS})
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    manifest = load_manifest(paths.CANTI)
    build_site(manifest, paths.TEI_BASE, paths.DATA, paths.TEI_GENETIC, paths.TEI_FACS, paths.ROOT / "tei" / "traduzioni",
               paths.ROOT / "tei" / "commenti")
    print(f"wrote {len(manifest)} poems to {paths.DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
