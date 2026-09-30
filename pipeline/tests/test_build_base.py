from pathlib import Path

import pytest
from lxml import etree

from leggo_pipeline.build_base import TEI_NS, build_poem_tei
from leggo_pipeline.wikitext import parse_pages

FIXTURES = Path(__file__).parent / "fixtures"
NS = {"tei": TEI_NS}
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

INFINITO_ENTRY = {
    "n": 12, "roman": "XII", "title": "L'infinito", "slug": "l-infinito",
    "wiki_pages": ["N35c XII. ‖ L'INFINITO. p. 62"], "pre_roles": None,
}
SYN_ENTRY = {"n": 99, "roman": "X", "title": "Prova", "slug": "prova", "wiki_pages": ["P"], "pre_roles": ["head", "head", "speaker"]}
SYN_PAGE = """<poem>
X.
[[Titolo: PROVA.|PROVA.]]
ALCETA.
1 Prima verso,
2 &nbsp;&nbsp;secondo rientrato;
4&nbsp;&nbsp;&nbsp;&nbsp; quarto, nuova strofa.
MELISSO.
mezzo verso senza numero,
5 il lúgubri dì d’un ''walser'' ([[N35c Note p. 176|12]]).
</poem>"""


def infinito_tree():
    text = (FIXTURES / "n35c_infinito_p62.wiki").read_text(encoding="utf-8")
    parsed = parse_pages([(INFINITO_ENTRY["wiki_pages"][0], text)])
    return etree.fromstring(build_poem_tei(INFINITO_ENTRY, parsed))


def syn_tree():
    return etree.fromstring(build_poem_tei(SYN_ENTRY, parse_pages([("P", SYN_PAGE)])))


def test_infinito_verses_are_exact():
    from test_wikitext import INFINITO

    root = infinito_tree()
    ls = root.xpath("//tei:l[@n]", namespaces=NS)
    assert [l.get("n") for l in ls] == [str(i) for i in range(1, 16)]
    assert ["".join(l.itertext()) for l in ls] == INFINITO


def test_infinito_ids_head_and_header():
    root = infinito_tree()
    ws = root.xpath("//tei:l[@n='1']/tei:w", namespaces=NS)
    assert [w.get(XML_ID) for w in ws] == [f"c12.v1.w{i}" for i in range(1, 8)]
    assert ws[4].text == "quest’"
    head = root.xpath("//tei:head", namespaces=NS)[0]
    assert [head.text] + [lb.tail for lb in head] == ["XII.", "L'INFINITO."]
    assert root.xpath("string(//tei:revisionDesc/@status)", namespaces=NS) == "provisional"
    assert root.xpath("//tei:div/@xml:id", namespaces=NS) == ["c12"]


def test_build_is_deterministic():
    text = (FIXTURES / "n35c_infinito_p62.wiki").read_text(encoding="utf-8")
    parsed = parse_pages([("p", text)])
    assert build_poem_tei(INFINITO_ENTRY, parsed) == build_poem_tei(INFINITO_ENTRY, parsed)


def test_gap_indent_speakers_unnumbered_italic_ref():
    root = syn_tree()
    lgs = root.xpath("//tei:lg", namespaces=NS)
    assert len(lgs) == 2
    assert lgs[0][0].tag == f"{{{TEI_NS}}}label" and lgs[0][0].text == "ALCETA."
    assert root.xpath("//tei:l[@n='2']/@rend", namespaces=NS) == ["indent2"]
    assert root.xpath("//tei:l[@n='3']/tei:gap/@reason", namespaces=NS) == ["missing-in-source"]
    assert root.xpath("//tei:lg[2]/tei:label/text()", namespaces=NS) == ["MELISSO."]
    unnumbered = root.xpath("//tei:l[not(@n)]", namespaces=NS)
    assert [l.get(XML_ID) for l in unnumbered if l.getparent().tag.endswith("lg")] == ["c99.v4.u1"]
    v5 = root.xpath("//tei:l[@n='5']", namespaces=NS)[0]
    assert "".join(v5.itertext()) == "il lúgubri dì d’un walser (12)."
    assert v5.xpath("tei:w[@rend='italic']/text()", namespaces=NS) == ["walser"]
    assert v5.xpath("tei:ref[@type='authorNote']/text()", namespaces=NS) == ["12"]


def test_characters_survive_byte_for_byte():
    data = build_poem_tei(SYN_ENTRY, parse_pages([("P", SYN_PAGE)]))
    for s in ["lúgubri", "dì", "d’"]:
        assert s.encode("utf-8") in data
    nfd_page = SYN_PAGE.replace("dì", "dì")
    nfd = build_poem_tei(SYN_ENTRY, parse_pages([("P", nfd_page)]))
    assert "dì".encode("utf-8") in nfd and "dì".encode("utf-8") not in nfd


def test_pre_roles_must_fit():
    bad = dict(SYN_ENTRY, pre_roles=["head"])
    with pytest.raises(ValueError, match="pre_roles"):
        build_poem_tei(bad, parse_pages([("P", SYN_PAGE)]))


def test_epigraph_role():
    page = "<poem>\nXXVII.\nAMORE E MORTE.\nὋν οἱ θεοί φιλοῦσιν, ἀποθνήσκει νέος.\nmenandro.\n1 Fratelli, a un tempo stesso, Amore e Morte\n</poem>"
    entry = dict(SYN_ENTRY, n=27, pre_roles=["head", "head", "epigraph", "epigraph"])
    root = etree.fromstring(build_poem_tei(entry, parse_pages([("P", page)])))
    assert root.xpath("//tei:epigraph/tei:l/text()", namespaces=NS) == ["Ὃν οἱ θεοί φιλοῦσιν, ἀποθνήσκει νέος.", "menandro."]
