from leggo_pipeline.wikitext import clean_inline


def test_highlight_and_piped_link_show_displayed_text():
    raw = '<span style="background-color:yellow;">[[Dell\'ultimo|Dell\']]</span>ultimo orizzonte il guardo esclude.'
    c = clean_inline(raw)
    assert c.text == "Dell'ultimo orizzonte il guardo esclude."
    assert len(c.loci) == 1
    assert c.loci[0].target == "Dell'ultimo"
    assert c.text[c.loci[0].start : c.loci[0].end] == "Dell'"


def test_plain_link_and_trailing_space():
    c = clean_inline('<span style="background-color:yellow;">[[Immensità]]</span> s’annega il pensier mio: ')
    assert c.text == "Immensità s’annega il pensier mio:"
    assert c.text[c.loci[0].start : c.loci[0].end] == "Immensità"


def test_italic_inside_link_and_note_call():
    c = clean_inline('<span style="background-color:yellow;">[[Nè ... danzerà|D\'un \'\'walser\'\' danzerà]]</span>. Tanto la possa')
    assert c.text == "D'un walser danzerà. Tanto la possa"
    assert [c.text[s.start : s.end] for s in c.italic] == ["walser"]

    c = clean_inline("''Le magnifiche sorti e progressive'' ([[N35c Note p. 176|12]]).")
    assert c.text == "Le magnifiche sorti e progressive (12)."
    assert [c.text[s.start : s.end] for s in c.italic] == ["Le magnifiche sorti e progressive"]
    assert [(c.text[s.start : s.end], s.target) for s in c.notes] == [("12", "N35c Note p. 176")]
    assert c.loci == []


def test_navigation_arrows_are_not_loci():
    c = clean_inline("[[N35c I. ǁ ALL'ITALIA. p. 7|←]] [[N35c I. ǁ ALL'ITALIA. p. 9|→]]")
    assert c.text == "← →"
    assert c.loci == []


def test_nbsp_small_and_whitespace_runs_collapse_and_spans_follow():
    c = clean_inline("<small>SOPRA</small>&nbsp;&nbsp; IL  [[RITRATTO]]")
    assert c.text == "SOPRA IL RITRATTO"
    assert c.text[c.loci[0].start : c.loci[0].end] == "RITRATTO"


def test_characters_are_never_changed():
    raw = "Ai lúgubri miei giorni, quest’ermo, l'altro, dì"
    assert clean_inline(raw).text == raw
    nfd = "dì"  # decomposed "dì" must stay decomposed
    assert clean_inline(nfd).text == nfd


from pathlib import Path

from leggo_pipeline.wikitext import parse_pages

FIXTURES = Path(__file__).parent / "fixtures"

INFINITO = [
    "Sempre caro mi fu quest’ermo colle,",
    "E questa siepe, che da tanta parte",
    "Dell'ultimo orizzonte il guardo esclude.",
    "Ma sedendo e mirando, interminati",
    "Spazi di là da quella, e sovrumani",
    "Silenzi, e profondissima quiete",
    "Io nel pensier mi fingo; ove per poco",
    "Il cor non si spaura. E come il vento",
    "Odo stormir tra queste piante, io quello",
    "Infinito silenzio a questa voce",
    "Vo comparando: e mi sovvien l’eterno,",
    "E le morte stagioni, e la presente",
    "E viva, e il suon di lei. Così tra questa",
    "Immensità s’annega il pensier mio:",
    "E il naufragar m’è dolce in questo mare.",
]


def _infinito():
    text = (FIXTURES / "n35c_infinito_p62.wiki").read_text(encoding="utf-8")
    return parse_pages([("N35c XII. ‖ L'INFINITO. p. 62", text)])


def test_infinito_real_page():
    p = _infinito()
    assert p.pre == ["XII.", "L'INFINITO."]
    verses = [l for l in p.lines if l.kind == "verse"]
    assert [l.n for l in verses] == list(range(1, 16))
    assert [l.text for l in verses] == INFINITO
    assert sum(l.stanza_start for l in verses) == 1
    assert p.missing == [] and p.problems == []


def test_infinito_variant_loci():
    v = {l.n: l for l in _infinito().lines}
    assert [(s.target, v[4].text[s.start : s.end]) for s in v[4].loci] == [("interminati ‖ Spazi", "interminati")]
    assert [(s.target, v[5].text[s.start : s.end]) for s in v[5].loci] == [("interminati ‖ Spazi", "Spazi")]
    assert [(s.target, v[13].text[s.start : s.end]) for s in v[13].loci] == [("il suon", "il")]


def _page(body: str) -> str:
    return f"[[prev|←]] [[next|→]]\n<poem>\n{body}\n</poem>\n"


def test_stanzas_indent_blank_lines_and_page_breaks():
    p1 = _page(
        "X.\n[[Titolo: PROVA.|PROVA.]]\n\n"
        "1 Primo\n2 &nbsp;&nbsp;Secondo rientrato\n3 Terzo\n\n\n"
        "4&nbsp;&nbsp;&nbsp;&nbsp; Quarto nuova strofa\n5 Quinto\n\n"
    )
    p2 = _page("6 Sesto, stessa strofa dopo il cambio pagina\n\n7 Settimo dopo riga vuota")
    p = parse_pages([("p1", p1), ("p2", p2)])
    v = {l.n: l for l in p.lines}
    assert p.pre == ["X.", "PROVA."]
    assert [n for n, l in v.items() if l.stanza_start] == [1, 4, 7]
    assert v[2].indent == 2 and v[1].indent == 0 and v[4].indent == 0


def test_two_verses_on_one_line_are_split():
    p = parse_pages([("p", _page("136 Uno,\n137 Al vicino ed inciampo, 138 Stolto crede così qual fora in campo "))])
    v = {l.n: l.text for l in p.lines}
    assert v[137] == "Al vicino ed inciampo,"
    assert v[138] == "Stolto crede così qual fora in campo"
    assert p.missing == list(range(1, 136))


def test_gap_is_reported_not_invented():
    p = parse_pages([("N35c XVII. Consalvo p. 80", _page("1 a\n2 b\n4 d"))])
    assert [l.n for l in p.lines] == [1, 2, 4]
    assert p.missing == [3]
    assert p.problems == ["N35c XVII. Consalvo p. 80: verse(s) 3-3 missing in source"]


def test_duplicate_and_out_of_order_verses_are_dropped_and_reported():
    p = parse_pages([("p84", _page("1 a\n2 b")), ("p84bis", _page("2 b again\n3 c"))])
    assert [(l.n, l.text) for l in p.lines] == [(1, "a"), (2, "b"), (3, "c")]
    assert p.problems == ["p84bis: verse 2 after verse 2 (duplicate or out of order), dropped"]


def test_speakers_and_unnumbered_lines_after_verse_one():
    p = parse_pages([("p", _page("XXXVII.\nALCETA.\n1 Odi, Melisso\nMELISSO.\nEgli ci ha tante stelle,\n2 Che"))])
    assert p.pre == ["XXXVII.", "ALCETA."]
    assert [(l.kind, l.text) for l in p.lines] == [
        ("verse", "Odi, Melisso"),
        ("label", "MELISSO."),
        ("unnumbered", "Egli ci ha tante stelle,"),
        ("verse", "Che"),
    ]
    assert p.problems == ["p: line without verse number after verse 1: 'Egli ci ha tante stelle,'"]


def test_navigation_lines_inside_poem_are_dropped():
    p = parse_pages([("p", _page("1 a\n[[N35c X p. 7|←]] [[N35c X p. 9|→]]\n2 b"))])
    assert [l.kind for l in p.lines] == ["verse", "verse"]


def test_no_verses_is_a_problem():
    assert parse_pages([("p", "no poem here")]).problems == ["no verses found"]
