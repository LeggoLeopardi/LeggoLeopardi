"""Facsimile alignment: find the verse lines on a page image and write TEI <facsimile> zones.

Line detection is semi-automatic: a person marks once, in pipeline/facsimile.json, the rectangle
that holds the verses (fractions of the page); inside it the lines are found by their rows of ink.
If the number of lines is not exactly the number of verses, no zones are written and the page is
shown whole (page-by-page alignment).
"""
from __future__ import annotations

import numpy as np
from lxml import etree
from PIL import Image, ImageDraw, ImageFilter

from .build_base import STRUCTURAL, TEI_NS, XML_ID, _el, _layout

Zone = tuple[int, int, int, int]  # ulx, uly, lrx, lry in image pixels


def _bands(on: np.ndarray, min_height: int) -> list[list[int]]:
    bands, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]:
                j += 1
            if j - i >= min_height:
                bands.append([i, j])
            i = j
        else:
            i += 1
    return bands


def _merge_close(bands: list[list[int]]) -> list[list[int]]:
    """Merge fragments closer than half the usual line spacing (a drop capital, a descender)."""
    if len(bands) < 3:
        return bands
    centres = [(a + b) / 2 for a, b in bands]
    pitch = float(np.median(np.diff(centres)))
    out = [bands[0][:]]
    for a, b in bands[1:]:
        if (a + b) / 2 - (out[-1][0] + out[-1][1]) / 2 < 0.5 * pitch:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def detect_verse_zones(image: Image.Image, region: list[float], n: int) -> list[Zone] | None:
    """Exactly n verse cells inside region [x0, y0, x1, y1] (fractions), top to bottom; else None."""
    gray = image.convert("L")
    w, h = gray.size
    x0, y0, x1, y1 = (int(round(v)) for v in (region[0] * w, region[1] * h, region[2] * w, region[3] * h))
    crop = gray.crop((x0, y0, x1, y1))
    background = crop.filter(ImageFilter.GaussianBlur(max(5, crop.width // 40)))
    ink = (np.asarray(crop, dtype=np.float32) / (np.asarray(background, dtype=np.float32) + 1)) < 0.8
    rows = ink.mean(1)
    for threshold in (0.04, 0.06, 0.08, 0.10):
        bands = _merge_close(_bands(rows > threshold, max(2, (y1 - y0) // 200)))
        if len(bands) == n:
            break
    else:
        return None
    centres = [(a + b) / 2 for a, b in bands]
    pitch = float(np.median(np.diff(centres))) if n > 1 else float(bands[0][1] - bands[0][0])
    edges = [centres[0] - pitch / 2] + [(centres[k] + centres[k + 1]) / 2 for k in range(n - 1)] + [centres[-1] + pitch / 2]
    zones: list[Zone] = []
    for k in range(n):
        ya, yb = int(max(0, edges[k])), int(min(ink.shape[0], edges[k + 1]))
        cols = np.where(ink[ya:yb].mean(0) > 0.02)[0]
        xa, xb = (int(cols[0]), int(cols[-1]) + 1) if len(cols) else (0, ink.shape[1])
        zones.append((x0 + xa, y0 + ya, x0 + xb, y0 + yb))
    return zones


def scale_zones(zones: list[Zone], factor: float) -> list[Zone]:
    return [tuple(int(round(v * factor)) for v in z) for z in zones]


def web_copy(src: Image.Image, width: int = 1200) -> Image.Image:
    """The page as served on the site: at most `width` pixels wide, RGB."""
    im = src.convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    return im


def overlay(image: Image.Image, zones: list[Zone] | None, max_size: int = 900) -> Image.Image:
    """A small check image with the verse cells drawn in alternating colours."""
    im = image.convert("RGB")
    d = ImageDraw.Draw(im)
    for k, z in enumerate(zones or []):
        d.rectangle(z, outline=(200, 0, 0) if k % 2 == 0 else (0, 80, 200), width=max(2, im.width // 600))
    im.thumbnail((max_size, max_size))
    return im


def build_facsimile_tei(entry: dict, pages: dict[str, dict]) -> bytes:
    """pages: siglum -> {"url", "width", "height", "zones": [Zone] | None}, in display order."""
    n = entry["n"]
    tei = etree.Element(f"{{{TEI_NS}}}TEI", nsmap={None: TEI_NS})
    header = _el(tei, "teiHeader")
    fd = _el(header, "fileDesc")
    _el(_el(fd, "titleStmt"), "title", f"{entry['roman']}. {entry['title']} (facsimili delle stampe)".strip())
    _el(_el(fd, "publicationStmt"), "p", "LeggoLeopardi. Allineamento provvisorio testo-immagine, da verificare.")
    _el(_el(fd, "sourceDesc"), "bibl", "Immagini: WikiLeopardi. Zone dei versi: rilevamento semi-automatico.")
    fac = _el(tei, "facsimile")
    for siglum, p in pages.items():
        surface = _el(fac, "surface", n=siglum, ulx="0", uly="0", lrx=str(p["width"]), lry=str(p["height"]))
        surface.set(XML_ID, f"c{n}.{siglum}")
        _el(surface, "graphic", url=p["url"], width=f"{p['width']}px", height=f"{p['height']}px")
        for v, (ulx, uly, lrx, lry) in enumerate(p["zones"] or [], start=1):
            zone = _el(surface, "zone", n=str(v), ulx=str(ulx), uly=str(uly), lrx=str(lrx), lry=str(lry))
            zone.set(XML_ID, f"c{n}.{siglum}.v{v}")
    _layout(tei, STRUCTURAL | {"facsimile", "surface"})
    return etree.tostring(tei, xml_declaration=True, encoding="UTF-8")
