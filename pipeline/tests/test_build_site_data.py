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


from leggo_pipeline import paths
from leggo_pipeline.build_site_data import facsimile_json


def test_facsimile_json():
    data = facsimile_json(dict(INFINITO_ENTRY, status=STATUS), paths.TEI_GENETIC / "c12.xml", paths.TEI_FACS / "c12.xml")
    wits = {w["siglum"]: w for w in data["witnesses"]}
    assert list(wits) == ["AN", "AV", "NR25", "B26", "F31", "N35", "N35c"]
    assert wits["AN"]["image"] is None and wits["AN"]["zones"] is None
    n35c = wits["N35c"]
    assert n35c["image"] == "/img/facs/c12-N35c.jpg"
    assert list(n35c["zones"]) == [str(i) for i in range(1, 16)]
    assert all(0 <= v <= 100 for z in n35c["zones"].values() for v in z)
    verse = {v["n"]: v["html"] for v in n35c["verses"]}
    assert verse[3] == '<a class="place" href="#place-p4" data-place="p4">Dell\'ultimo orizzonte</a> il guardo esclude.'
    nr25 = {v["n"]: v["html"] for v in wits["NR25"]["verses"]}
    assert nr25[5].startswith('<a class="place" href="#place-p6" data-place="p6">spazio</a> di là da quella')
    assert n35c["head"] == ['<a class="place" href="#place-p1" data-place="p1">XII.</a>',
                            '<a class="place" href="#place-p1" data-place="p1">L\'INFINITO.</a>']
    p13 = data["places"]["p13"]
    assert p13["verses"] == [14]
    an = next(r for r in p13["readings"] if "AN" in r["wit"])
    assert [(l["label"], l["text"]) for l in an["layers"]][0] == ("Penna A 1819", "Immensità il mio pensier s'annega,")
    assert data["credits"] == ["Roberta Priore", "Beatrice Nava"]
    assert len(data["places"]) == 14


def test_build_site_marks_poems_with_facsimile(tmp_path):
    tei, out = tmp_path / "tei", tmp_path / "out"
    tei.mkdir()
    (tei / "c12.xml").write_bytes(etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    build_site([dict(INFINITO_ENTRY, status=STATUS)], tei, out, paths.TEI_GENETIC, paths.TEI_FACS)
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert index[0]["status"]["facsimile"] == "provisional"
    assert (out / "facs" / "c12.json").is_file()


from leggo_pipeline.build_site_data import translations_json

TRAD = paths.ROOT / "tei" / "traduzioni"


def test_translations_json(tmp_path):
    base = tmp_path / "c12.xml"
    base.write_bytes(etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    data = translations_json(dict(INFINITO_ENTRY, status=STATUS), TRAD, base)
    ids = [t["id"] for t in data["translations"]]
    assert len(ids) == 19
    assert ids[:4] == ["de_arentsschildt_1847", "de_hoffinger_1868", "en_townsend_1887", "en_cliffe_1893"]
    assert ids[-1] == "ru_akhmatova_1967" or ids[-1].startswith("ru_")
    sb = next(t for t in data["translations"] if t["id"] == "fr_sainte-beuve_1844")
    assert sb["lang"] == "fr" and sb["translator"] == "Charles-Augustin Sainte-Beuve" and sb["year"] == 1844
    assert sb["title"] == ["L’infini"]
    assert sb["bibl"].startswith("Sainte- Beve C. A. de, «Revue des deux mondes»")
    assert [s["label"] for s in sb["sources"]][1] == "Wikisource" and sb["sources"][1]["url"].startswith("https://fr.wikisource")
    assert sb["stanzas"][0][0] == "J’aimai toujours ce point de colline déserte,"
    assert sb["form"] == "verse" and sb["rights"] == "Pubblico dominio"
    aulard = next(t for t in data["translations"] if t["id"] == "fr_aulard_1880")
    assert aulard["form"] == "prose" and aulard["title"] == ["XII", "L’INFINI.", "(1819.)"]
    assert [i["text"] for i in data["italian"]["stanzas"][0]][0] == "Sempre caro mi fu quest’ermo colle,"


def test_build_site_marks_poems_with_translations(tmp_path):
    tei, out = tmp_path / "tei", tmp_path / "out"
    tei.mkdir()
    (tei / "c12.xml").write_bytes(etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    build_site([dict(INFINITO_ENTRY, status=STATUS)], tei, out, trad_dir=TRAD)
    assert json.loads((out / "index.json").read_text(encoding="utf-8"))[0]["status"]["traduco"] == "provisional"
    assert (out / "trad" / "c12.json").is_file()


from leggo_pipeline.build_site_data import commentaries_json

COMM = paths.ROOT / "tei" / "commenti"


def test_commentaries_json():
    data = commentaries_json(dict(INFINITO_ENTRY, status=STATUS), COMM)
    ids = [c["id"] for c in data["commentators"]]
    assert ids == ["fornaciari_1889", "castagnola_1893", "straccali_1895", "straccali-antognoni_1919", "levi_1921"]  # by year
    st = next(c for c in data["commentators"] if c["id"] == "straccali_1895")
    assert st["short"] == "Straccali" and st["year"] == 1895 and st["bibl"].startswith("I canti di Giacomo Leopardi")
    assert len(st["notes"]) == 10 and len(st["intro"]) == 2
    first = st["notes"][0]
    assert (first["from"], first["to"], first["lemma"]) == (1, 1, "ermo colle.")
    assert first["html"].startswith("Il monte Tabor. «Il quale oggidì»")
    assert "<em>Il passero solitario</em>" in first["html"]
    assert st["intro"][1] == "<strong>Metrica.</strong> Endecasillabi sciolti."
    ant = next(c for c in data["commentators"] if c["id"] == "straccali-antognoni_1919")
    assert ant["notes"][0]["added"] is True and st["notes"][0]["added"] is False
    fo = next(c for c in data["commentators"] if c["id"] == "fornaciari_1889")
    assert (fo["notes"][0]["from"], fo["notes"][0]["to"]) == (1, 3)


def test_build_site_marks_poems_with_commentaries(tmp_path):
    tei, out = tmp_path / "tei", tmp_path / "out"
    tei.mkdir()
    (tei / "c12.xml").write_bytes(etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    build_site([dict(INFINITO_ENTRY, status=STATUS)], tei, out, comm_dir=COMM)
    assert json.loads((out / "index.json").read_text(encoding="utf-8"))[0]["status"]["commenti"] == "provisional"
    assert (out / "comm" / "c12.json").is_file()


from leggo_pipeline.build_base import base_verses
from leggo_pipeline.build_site_data import lemma_spans

VV = {1: "Sempre caro mi fu quest’ermo colle,", 2: "E questa siepe, che da tanta parte",
      9: "Odo stormir tra queste piante, io quello", 10: "Infinito silenzio a questa voce"}


def test_lemma_spans_find_the_commented_words():
    cut = lambda v, s, e: VV[v][s:e]
    assert [cut(*s) for s in lemma_spans("ermo colle.", VV, 1, 1)] == ["ermo colle"]
    assert [cut(*s) for s in lemma_spans("Ermo;", VV, 1, 1)] == ["ermo"]  # case, apostrophe as a boundary
    assert [cut(*s) for s in lemma_spans("Sempre caro mi fu quest'ermo colle.", VV, 1, 3)] == ["Sempre caro mi fu quest’ermo colle"]
    assert [cut(*s) for s in lemma_spans("che da tanta ecc.:", VV, 2, 3)] == ["che da tanta"]  # "ecc." abbreviates the rest
    assert [cut(*s) for s in lemma_spans("quello Infinito silenzio:", VV, 9, 10)] == ["quello", "Infinito silenzio"]  # across verses
    assert lemma_spans("mare.", VV, 1, 2) == []  # not in the verses: no underline
    assert lemma_spans("fu", {1: "Sempre caro mi fu quest’ermo colle,"}, 1, 1) == [[1, 15, 17]]


def test_commentaries_json_every_lemma_is_found_in_the_base_text():
    data = commentaries_json(dict(INFINITO_ENTRY, status=STATUS), COMM, paths.TEI_BASE / "c12.xml")
    verses = base_verses(paths.TEI_BASE / "c12.xml")
    for c in data["commentators"]:
        for nt in c["notes"]:
            assert nt["spans"], (c["id"], nt["lemma"])
            assert all(nt["from"] <= v <= nt["to"] for v, _, _ in nt["spans"])
    st = next(c for c in data["commentators"] if c["id"] == "straccali_1895")
    assert [verses[v][s:e] for v, s, e in st["notes"][-1]["spans"]] == ["Immensità"]
