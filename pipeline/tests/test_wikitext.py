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
