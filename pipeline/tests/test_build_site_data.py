import json

from lxml import etree

from leggo_pipeline.build_base import build_poem_tei
from leggo_pipeline.build_site_data import build_site, poem_json
from leggo_pipeline.wikitext import parse_pages
from test_build_base import INFINITO_ENTRY, SYN_ENTRY, SYN_PAGE, infinito_tree
from test_wikitext import INFINITO

STATUS = {"leggo": "provisional", "traduco": "none", "collaziono": "none", "concordanza": "none"}


def test_infinito_json(tmp_path):
    (tmp_path / "c12.xml").write_bytes(etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    data = poem_json(dict(INFINITO_ENTRY, status=STATUS), tmp_path / "c12.xml")
    assert data["head"] == ["XII.", "L'INFINITO."]
    assert data["incipit"] == INFINITO[0]
    assert data["source"]["status"] == "provisional" and data["source"]["label"] == "WikiLeopardi"
    assert len(data["source"]["pages"]) == 1 and data["source"]["pages"][0].startswith("https://wikileopardi")
    [stanza] = data["stanzas"]
    assert [i["text"] for i in stanza] == INFINITO
    assert stanza[0] == {
        "type": "l", "n": 1, "id": "c12.v1", "indent": 0, "missing": False, "unnumbered": False,
        "text": INFINITO[0], "html": INFINITO[0],
    }


def test_special_items_and_html(tmp_path):
    (tmp_path / "c99.xml").write_bytes(build_poem_tei(SYN_ENTRY, parse_pages([("P", SYN_PAGE)])))
    data = poem_json(dict(SYN_ENTRY, status=STATUS), tmp_path / "c99.xml")
    items = [i for st in data["stanzas"] for i in st]
    assert items[0] == {"type": "label", "text": "ALCETA."}
    missing = next(i for i in items if i.get("n") == 3)
    assert missing["missing"] is True and missing["html"] == ""
    assert next(i for i in items if i.get("n") == 2)["indent"] == 2
    unnumbered = next(i for i in items if i.get("unnumbered"))
    assert unnumbered["n"] is None and unnumbered["id"] == "c99.v4.u1"
    v5 = next(i for i in items if i.get("n") == 5)
    assert v5["html"] == 'il lúgubri dì d’un <em>walser</em> (<sup class="noteref">12</sup>).'


def test_build_site_writes_index(tmp_path):
    tei, out = tmp_path / "tei", tmp_path / "out"
    tei.mkdir()
    (tei / "c12.xml").write_bytes(etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    build_site([dict(INFINITO_ENTRY, status=STATUS)], tei, out)
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert index == [{"n": 12, "roman": "XII", "title": "L'infinito", "slug": "l-infinito", "incipit": INFINITO[0], "status": STATUS}]
    assert (out / "c12.json").is_file()
