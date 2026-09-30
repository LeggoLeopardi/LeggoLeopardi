"""The committed translations of L'infinito (built locally from sources outside the repository)."""
from lxml import etree

from leggo_pipeline import paths

NS = {"tei": "http://www.tei-c.org/ns/1.0"}
TRAD = paths.ROOT / "tei" / "traduzioni"
EXPECTED = {  # id: (lines, first, last) as checked on 2026-09-30
    "en_townsend_1887": (15, "This lonely hill to me was ever dear,", "And sweet to me is shipwreck on this sea."),
    "en_cliffe_1893": (15, "I always loved this solitary hill", "And to be wrecked on such a sea is sweet."),
    "en_cliffe_1896": (15, "I always loved this solitary hill", "And to be wrecked on such a sea is sweet."),
    "en_johnson_1898": (9, "This lonely hill was always dear to me", "Yet makes sweet shipwreck upon those calm seas."),
    "fr_sainte-beuve_1844": (14, "J’aimai toujours ce point de colline déserte,", "Et sur ces mers sans fin j’aime jusqu’au naufrage."),
    "fr_montlaur_1846": (11, "E il naufragar m'è dolce in questo mare.", "Et le naufrage est doux sur celte mer profonde."),
    "fr_vernier_1867": (3, None, "de m’anéantir dans cet océan profond."),
    "fr_bouche-leclercq_1874": (1, None, None),
    "fr_amiel_1876": (1, None, None),
    "fr_aulard_1880": (1, None, None),
    "fr_lacaussade_1889": (19, "Toujours tu me fus chère, ô déserte colline,", "Et doux m’est le naufrage en une telle mer."),
    "de_arentsschildt_1847": (15, "Stets war mir theuer dieser öde Hügel", "Mir süß in diesem Meere."),
    "de_hoffinger_1868": (15, "Stets war mir lieb der abgeschiedne Hügel", "Und süß ist Schiffbruch mir in diesem Meere."),
    "es_oyuela_1883": (17, "Esta colina solitaria siempre", "Mayo de 1883."),
    "es_anonimo": (15, "Siempre querido me fue este yermo cerro", "y naufragar en este mar me es dulce."),
    "ru_pomyan_1893": (15, "Мнѣ этотъ милъ всегда уединенный холмъ", "И сладко мнѣ погибнуть въ этомъ морѣ."),
    "ru_ivanov": (15, "Всегда любил я холм пустынный этот", "И сладко мне крушенье в этом море."),
    "ru_tkhorzhevsky": (15, "Мне дорог этот одинокий холм", "Но сладко мне исчезнуть в этом море!"),
    "ru_akhmatova_1967": (16, "Всегда был мил мне этот холм пустынный", "И сладостно тонуть мне в этом море."),
}


def test_every_translation_is_there_valid_and_intact():
    rng = etree.RelaxNG(etree.parse(str(paths.SCHEMA)))
    assert sorted(p.name for p in TRAD.iterdir()) == sorted(EXPECTED)
    for tid, (count, first, last) in EXPECTED.items():
        doc = etree.parse(str(TRAD / tid / "c12.xml"))
        assert rng.validate(doc), (tid, rng.error_log.last_error)
        lines = doc.xpath("//tei:div/tei:lg/tei:l/text() | //tei:div/tei:p/text()", namespaces=NS)
        assert len(lines) == count, tid
        if first:
            assert lines[0] == first, tid
        if last:
            assert lines[-1] == last, tid
