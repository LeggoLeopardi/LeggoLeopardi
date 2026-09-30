import json

from lxml import etree

from leggo_pipeline import paths
from leggo_pipeline.build_base import base_verses
from leggo_pipeline.commentaries import build_commentary_tei, inline_segments

NS = {"tei": "http://www.tei-c.org/ns/1.0"}
CONFIG = json.loads((paths.ROOT / "pipeline" / "commenti.json").read_text(encoding="utf-8"))
POEM = {"n": 12, "roman": "XII", "title": "L'infinito"}


def test_inline_marks():
    assert inline_segments("Cfr. *Il passero solitario*, la nota. — **ove.** Mi par") == [
        ("", "Cfr. "), ("italic", "Il passero solitario"), ("", ", la nota. — "), ("bold", "ove."), ("", " Mi par"),
    ]
    assert inline_segments("senza segni") == [("", "senza segni")]


def tree(entry):
    return etree.fromstring(build_commentary_tei(entry, POEM))


def test_commentary_tei_is_valid_and_points_at_verses():
    rng = etree.RelaxNG(etree.parse(str(paths.SCHEMA)))
    base_ids = {f"c12.v{n}" for n in base_verses(paths.TEI_BASE / "c12.xml")}
    for entry in CONFIG["12"]:
        doc = tree(entry)
        assert rng.validate(etree.ElementTree(doc)), (entry["id"], rng.error_log.last_error)
        notes = doc.xpath("//tei:note[@type='comm']", namespaces=NS)
        assert len(notes) == len(entry["notes"]), entry["id"]
        for note in notes:
            for attr in ("target", "targetEnd"):
                ref = note.get(attr)
                assert ref.startswith("../../base/c12.xml#") and ref.split("#")[1] in base_ids, (entry["id"], ref)


def test_note_content_marks_and_added_notes():
    straccali = tree(CONFIG["12"][0])
    first = straccali.xpath("//tei:note[@type='comm']", namespaces=NS)[0]
    assert first.get("target").endswith("#c12.v1") and first.get("targetEnd").endswith("#c12.v1")
    assert first.find("tei:ref", NS).text == "ermo colle."
    assert first.xpath("tei:hi[@rend='italic']/text()", namespaces=NS) == ["ermo", "Il passero solitario"]
    assert "".join(first.itertext()).startswith("ermo colle. Il monte Tabor. «Il quale oggidì»")
    assert len(straccali.xpath("//tei:note[@type='intro']", namespaces=NS)) == 2
    assert straccali.xpath("string(//tei:titleStmt/tei:author)", namespaces=NS) == "Alfredo Straccali"
    assert straccali.xpath("string(//tei:sourceDesc/tei:bibl/tei:date/@when)", namespaces=NS) == "1895"
    antognoni = tree(CONFIG["12"][1])
    assert antognoni.xpath("//tei:note[@type='comm']/@subtype", namespaces=NS) == ["added"]
    fornaciari = tree(CONFIG["12"][2])
    note = fornaciari.xpath("//tei:note[@type='comm']", namespaces=NS)[0]
    assert (note.get("target").split("#")[1], note.get("targetEnd").split("#")[1]) == ("c12.v1", "c12.v1")


def test_one_note_per_printed_lemma():
    # Straccali prints "7. fingo, immagino. — ove. … — per poco ecc.: …" as one paragraph: three notes
    notes = tree(CONFIG["12"][0]).xpath("//tei:note[@type='comm']", namespaces=NS)
    lemmas = [(n.find("tei:ref", NS).text, n.get("target").split(".v")[-1], n.get("targetEnd").split(".v")[-1]) for n in notes]
    assert lemmas[4:7] == [("fingo,", "7", "7"), ("ove.", "7", "7"), ("per poco ecc.:", "7", "8")]
    assert lemmas[11:14] == [("le morte stagioni:", "12", "12"), ("e la presente.", "12", "12"), ("Suon.", "13", "13")]
    assert "".join(notes[4].itertext()) == "fingo, immagino."  # no run-on into the next lemma
