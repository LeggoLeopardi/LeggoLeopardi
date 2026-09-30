from lxml import etree
from PIL import Image, ImageDraw

from leggo_pipeline import paths
from leggo_pipeline.facsimile import build_facsimile_tei, detect_verse_zones, scale_zones

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def page(lines: int, w=800, h=1200) -> Image.Image:
    """A fake printed page: a title, then `lines` evenly spaced text lines, then a footer."""
    im = Image.new("L", (w, h), 235)
    d = ImageDraw.Draw(im)
    d.rectangle([300, 100, 500, 130], fill=20)  # title, outside the verse region
    for k in range(lines):
        y = 300 + k * 40
        d.rectangle([150, y, 150 + 400 + (k % 3) * 60, y + 14], fill=25)
    d.rectangle([150, 1150, 650, 1165], fill=20)  # footer, outside the region
    return im


REGION = [0.1, 0.22, 0.95, 0.85]


def test_fifteen_lines_give_fifteen_ordered_zones():
    zones = detect_verse_zones(page(15), REGION, 15)
    assert zones is not None and len(zones) == 15
    tops = [z[1] for z in zones]
    assert tops == sorted(tops)
    x0, y0, x1, y1 = zones[0]
    assert x0 <= 150 < 550 <= x1 and y0 <= 300 < 314 <= y1
    assert all(zones[k][3] <= zones[k + 1][1] + 1 for k in range(14))  # cells do not overlap


def test_wrong_line_count_means_no_zones():
    assert detect_verse_zones(page(14), REGION, 15) is None


def test_scale_zones():
    assert scale_zones([(100, 200, 300, 400)], 0.5) == [(50, 100, 150, 200)]


def test_facsimile_tei_is_valid_and_keeps_pages_without_zones():
    pages = {
        "N35c": {"url": "/img/facs/c12-N35c.jpg", "width": 1200, "height": 1800, "zones": [(10, 20, 300, 60)] * 15},
        "B26": {"url": "/img/facs/c12-B26.jpg", "width": 560, "height": 924, "zones": None},
    }
    data = build_facsimile_tei({"n": 12, "roman": "XII", "title": "L'infinito"}, pages)
    doc = etree.fromstring(data)
    rng = etree.RelaxNG(etree.parse(str(paths.SCHEMA)))
    assert rng.validate(etree.ElementTree(doc)), rng.error_log.last_error
    surfaces = doc.xpath("//tei:surface", namespaces=NS)
    assert [s.get("n") for s in surfaces] == ["N35c", "B26"]
    assert doc.xpath("//tei:surface[@n='N35c']/tei:zone/@n", namespaces=NS) == [str(i) for i in range(1, 16)]
    assert doc.xpath("//tei:surface[@n='B26']/tei:zone", namespaces=NS) == []
    assert doc.xpath("string(//tei:surface[@n='B26']/tei:graphic/@url)", namespaces=NS) == "/img/facs/c12-B26.jpg"
    z = doc.xpath("//tei:surface[@n='N35c']/tei:zone[@n='1']", namespaces=NS)[0]
    assert [z.get(k) for k in ("ulx", "uly", "lrx", "lry")] == ["10", "20", "300", "60"]
    assert z.get("{http://www.w3.org/XML/1998/namespace}id") == "c12.N35c.v1"
