"""Read the team's parallel-segmentation TEI of a poem (Priore/Nava): witness texts and variant places.

The file is used exactly as the team encoded it. Whitespace from XML indentation is collapsed
(the only normalisation); readings are never corrected.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

T = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
NS = {"tei": "http://www.tei-c.org/ns/1.0"}

Segment = tuple[str, str | None]  # (text, place id or None)


@dataclass
class Place:
    id: str
    verses: list[int]  # [0] is the title
    readings: list[dict]  # lem first: {"wit", "text", "lem", "layers"}


@dataclass
class TeamPoem:
    witnesses: list[dict] = field(default_factory=list)  # [{"siglum", "label"}]
    layers: dict[str, str] = field(default_factory=dict)
    credits: list[str] = field(default_factory=list)
    places: list[Place] = field(default_factory=list)
    texts: dict[str, dict] = field(default_factory=dict)  # siglum -> {"head": [[Segment]], "verses": {n: [Segment]}}


def _local(el) -> str:
    return etree.QName(el).localname


def _wits(el) -> list[str]:
    return [t.lstrip("#") for t in (el.get("wit") or "").split()]


def _squeeze(s: str) -> str:
    return " ".join(s.split())


def _flat(el) -> str:
    """Text of a reading: <lb/> becomes ' / ', <del> is dropped (a <subst> keeps its addition)."""
    parts = [el.text or ""]
    for ch in el:
        name = _local(ch)
        if name == "lb":
            parts.append(" / ")
        elif name == "subst":
            # only the addition, without the indentation whitespace between <del> and <add>
            parts.append("".join(_flat(a) for a in ch if _local(a) == "add"))
        elif name != "del":
            parts.append(_flat(ch))
        parts.append(ch.tail or "")
    return "".join(parts)


def _mods(rdg) -> list:
    return sorted((m for m in rdg if _local(m) == "mod"), key=lambda m: int(m.get("seq") or 0))


def reading_text(rdg) -> str:
    """A witness's final reading: the last revision step (highest @seq) when the reading has <mod>s."""
    mods = _mods(rdg)
    return _squeeze(_flat(mods[-1] if mods else rdg))


def _layers(rdg) -> list[dict]:
    return [
        {
            "seq": int(m.get("seq") or 0),
            "layer": (m.get("change") or "").lstrip("#") or None,
            "type": m.get("type"),
            "text": _squeeze(_flat(m)),
        }
        for m in _mods(rdg)
    ]


def _pick(app, w: str) -> str:
    lem = app.find(f"{T}lem")
    if lem is not None and w in _wits(lem):
        return _squeeze(_flat(lem))
    for rdg in app.findall(f"{T}rdg"):
        if w in _wits(rdg):
            return reading_text(rdg)
    return _squeeze(_flat(lem)) if lem is not None else ""


def _normalize(segs: list[Segment]) -> list[Segment]:
    """Collapse whitespace across segments without losing their place ids; trim the ends."""
    out: list[Segment] = []
    prev_space = True
    for text, pid in segs:
        buf = []
        for ch in text:
            if ch.isspace():
                if prev_space:
                    continue
                buf.append(" ")
                prev_space = True
            else:
                buf.append(ch)
                prev_space = False
        if buf:
            out.append(("".join(buf), pid))
    if out and out[-1][0].endswith(" "):
        text, pid = out[-1]
        out[-1] = (text.rstrip(), pid)
        if not out[-1][0]:
            out.pop()
    return out


def _split_lines(segs: list[Segment]) -> list[list[Segment]]:
    """Split title segments into printed lines: at ' / ' (an <lb/>) or ' | ' (the team's newer title encoding)."""
    lines: list[list[Segment]] = [[]]
    for text, pid in segs:
        parts = re.split(r" [/|] ", text)
        for k, part in enumerate(parts):
            if k:
                lines.append([])
            lines[-1].append((part, pid))
    return [_normalize(l) for l in lines if _normalize(l)]


def read_team_poem(path: Path) -> TeamPoem:
    root = etree.parse(str(path)).getroot()
    poem = TeamPoem()
    poem.witnesses = [
        {"siglum": w.get(XML_ID), "label": _squeeze("".join(w.itertext()))}
        for w in root.iter(f"{T}witness")
    ]
    poem.layers = {c.get(XML_ID): _squeeze("".join(c.itertext())) for c in root.iter(f"{T}change") if c.get(XML_ID)}
    poem.credits = [_squeeze("".join(p.itertext())) for p in root.xpath("//tei:titleStmt//tei:persName", namespaces=NS)]

    body = root.find(f".//{T}body")
    head = body.find(f".//{T}head")
    lines = body.findall(f".//{T}lg/{T}l")

    # Places in document order: the title first, then each verse.
    place_of: dict = {}
    anchor_line = {a.get(XML_ID): int(l.get("n")) for l in lines for a in l.iter(f"{T}anchor")}
    for el, n in [(head, 0)] + [(l, int(l.get("n"))) for l in lines]:
        if el is None:
            continue
        for app in el.iter(f"{T}app"):
            pid = f"p{len(place_of) + 1}"
            place_of[app] = pid
            verses = [n]
            if app.get("from"):
                verses = [anchor_line[app.get("from").lstrip("#")], n]
            readings = []
            lem = app.find(f"{T}lem")
            if lem is not None:
                readings.append({"wit": _wits(lem), "text": _squeeze(_flat(lem)), "lem": True, "layers": []})
            for rdg in app.findall(f"{T}rdg"):
                readings.append({"wit": _wits(rdg), "text": reading_text(rdg), "lem": False, "layers": _layers(rdg)})
            poem.places.append(Place(pid, verses, readings))

    for wit in poem.witnesses:
        w = wit["siglum"]
        verses: dict[int, list[Segment]] = {}
        pending: list[tuple] = []  # apps with @from, resolved after all lines are built
        for l in lines:
            n = int(l.get("n"))
            segs: list[Segment] = [(l.text or "", None)]
            for ch in l:
                name = _local(ch)
                if name == "app" and ch.get("from"):
                    segs.append(("", ("FROM", ch)))
                elif name == "app":
                    segs.append((_pick(ch, w), place_of[ch]))
                elif name == "anchor":
                    segs.append(("", ("ANCHOR", ch.get(XML_ID))))
                else:
                    segs.append((_flat(ch), None))
                segs.append((ch.tail or "", None))
            verses[n] = segs
            pending += [(n, s[1][1]) for s in segs if isinstance(s[1], tuple) and s[1][0] == "FROM"]
        for n, app in pending:
            _resolve_span(verses, n, app, w, place_of[app], anchor_line)
        text = {"verses": {}, "head": []}
        for n, segs in verses.items():
            text["verses"][n] = _normalize([(t, p) for t, p in segs if not isinstance(p, tuple)])
        if head is not None:
            hsegs: list[Segment] = [(head.text or "", None)]
            for ch in head:
                if _local(ch) == "app":
                    hsegs.append((_pick(ch, w), place_of[ch]))
                elif _local(ch) == "lb":
                    hsegs.append((" / ", None))
                else:
                    hsegs.append((_flat(ch), None))
                hsegs.append((ch.tail or "", None))
            text["head"] = _split_lines(hsegs)
        poem.texts[w] = text
    return poem


def _resolve_span(verses: dict, n: int, app, w: str, pid: str, anchor_line: dict) -> None:
    """An app with @from covers the text from its <anchor> (previous line) up to the app itself.

    Witnesses in the lemma keep that text, marked as the place; the others get their reading,
    split at its line break over the two verses.
    """
    anchor_id = app.get("from").lstrip("#")
    j = anchor_line[anchor_id]
    first, second = verses[j], verses[n]
    a = next(k for k, s in enumerate(first) if s[1] == ("ANCHOR", anchor_id))
    b = next(k for k, s in enumerate(second) if s[1] == ("FROM", app))
    lem = app.find(f"{T}lem")
    if lem is not None and w in _wits(lem):
        verses[j] = first[: a + 1] + [(t, pid if p is None else p) for t, p in first[a + 1 :]]
        verses[n] = [(t, pid if p is None else p) for t, p in second[:b]] + second[b:]
        return
    reading = _pick(app, w)
    parts = reading.split(" / ", 1) + [""]
    verses[j] = first[: a + 1] + [(parts[0], pid)]
    verses[n] = [(parts[1], pid), (" ", None)] + second[b:]
