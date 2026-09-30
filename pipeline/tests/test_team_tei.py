from leggo_pipeline import paths
from leggo_pipeline.team_tei import read_team_poem

POEM = read_team_poem(paths.TEI_GENETIC / "c12.xml")


def text(w, n):
    return "".join(t for t, _ in POEM.texts[w]["verses"][n])


def test_header_witnesses_layers_credits():
    assert [w["siglum"] for w in POEM.witnesses] == ["AN", "AV", "NR25", "B26", "F31", "N35", "N35c"]
    assert POEM.witnesses[3]["label"].startswith("Versi del Conte Giacomo Leopardi, Bologna")
    assert POEM.layers == {"layer0": "Penna A 1819", "layer1": "Penna B 1820", "layer2": "Penna C 1821", "layer3": "Penna D 1825"}
    assert POEM.credits == ["Roberta Priore", "Beatrice Nava"]


def test_base_witness_text():
    assert text("N35c", 1) == "Sempre caro mi fu quest’ermo colle,"
    assert text("N35c", 3) == "Dell'ultimo orizzonte il guardo esclude."
    assert text("N35c", 4) == "Ma sedendo e mirando, interminati"
    assert text("N35c", 5) == "Spazi di là da quella, e sovrumani"
    assert text("N35c", 15) == "E il naufragar m’è dolce in questo mare."
    assert ["".join(t for t, _ in line) for line in POEM.texts["N35c"]["head"]] == ["XII.", "L'INFINITO."]


def test_older_witnesses_follow_their_readings():
    assert text("NR25", 3) == "De l'ultimo orizzonte il guardo esclude."
    assert text("NR25", 4) == "Ma sedendo e mirando, interminato"
    assert text("NR25", 5) == "spazio di là da quella, e sovrumani"
    assert text("NR25", 7) == "Io nel pensier mi fingo, ove per poco"
    assert text("B26", 13) == "E viva, e 'l suon di lei. Così tra questa"
    assert text("B26", 14) == "Infinità s'annega il pensier mio:"
    assert text("F31", 14) == "Immensità s’annega il pensier mio:"
    assert ["".join(t for t, _ in line) for line in POEM.texts["F31"]["head"]] == ["XI.", "L'INFINITO."]


def test_manuscript_final_layer_and_places():
    assert text("AN", 14) == "Infinità s'annega il pensier mio:"
    p = next(p for p in POEM.places if p.verses == [14])
    an = next(r for r in p.readings if "AN" in r["wit"])
    assert [(l["seq"], l["layer"], l["text"]) for l in an["layers"]] == [
        (1, "layer0", "Immensità il mio pensier s'annega,"),
        (2, "layer1", "Infinità s'annega il pensier mio;"),
        (3, "layer3", "Infinità s'annega il pensier mio:"),
    ]
    assert p.readings[0] == {"wit": ["F31", "N35", "N35c"], "text": "Immensità s’annega il pensier mio:", "lem": True, "layers": []}


def test_place_marks_and_the_two_verse_variant():
    four_five = next(p for p in POEM.places if p.verses == [4, 5])
    assert [s for s, pid in POEM.texts["N35c"]["verses"][4] if pid == four_five.id] == ["interminati"]
    assert [s for s, pid in POEM.texts["B26"]["verses"][5] if pid == four_five.id] == ["spazio"]
    assert len(POEM.places) == 14
    assert [p.verses for p in POEM.places][:3] == [[0], [1], [2]]


def test_compare_with_base_reports_differences():
    from leggo_pipeline.build_facsimile import compare_with_base

    base = {n: "".join(t for t, _ in POEM.texts["N35c"]["verses"][n]) for n in range(1, 16)}
    assert compare_with_base(POEM, base) == []
    base[2] = "E questa siepe, che da tanta parte"
    assert compare_with_base(POEM, base) == [
        "v2: team TEI 'E questa siepe,che da tanta parte' ≠ WikiLeopardi 'E questa siepe, che da tanta parte'"
    ]
