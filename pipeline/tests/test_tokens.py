from leggo_pipeline.tokens import tokenize
from leggo_pipeline.wikitext import Span


def kinds(text, **kw):
    return [(t.text, t.kind) for t in tokenize(text, **kw)]


def test_words_elisions_punctuation():
    assert kinds("Sempre caro mi fu quest’ermo colle,") == [
        ("Sempre", "w"), ("caro", "w"), ("mi", "w"), ("fu", "w"),
        ("quest’", "w"), ("ermo", "w"), ("colle", "w"), (",", "pc"),
    ]
    assert kinds("Dell'ultimo") == [("Dell'", "w"), ("ultimo", "w")]
    assert kinds("e ’l cor") == [("e", "w"), ("’l", "w"), ("cor", "w")]
    assert kinds("dì, lúgubri!") == [("dì", "w"), (",", "pc"), ("lúgubri", "w"), ("!", "pc")]


def test_offsets_rebuild_the_text():
    text = "Vo comparando: e mi sovvien l’eterno,"
    toks = tokenize(text)
    assert all(text[t.start : t.end] == t.text for t in toks)


def test_note_calls_and_italics():
    text = "progressive (12)."
    toks = tokenize(text, notes=[Span(13, 15, "N35c Note p. 176")], italic=[Span(0, 11)])
    assert [(t.text, t.kind, t.italic) for t in toks] == [
        ("progressive", "w", True), ("(", "pc", False), ("12", "ref", False), (")", "pc", False), (".", "pc", False),
    ]


def test_combining_accents_stay_with_their_letter():
    assert kinds("dì perché,") == [("dì", "w"), ("perché", "w"), (",", "pc")]
