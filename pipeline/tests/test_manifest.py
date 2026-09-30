from leggo_pipeline.manifest import build_manifest, merge_existing, roman_to_int, slugify


def test_roman_and_slug():
    assert [roman_to_int(r) for r in ["I", "IV", "IX", "XII", "XXXIX", "XL", "XLI"]] == [1, 4, 9, 12, 39, 40, 41]
    assert slugify("L'infinito") == "l-infinito"
    assert slugify("La sera del dì di festa") == "la-sera-del-di-di-festa"
    assert slugify("") == ""


def test_build_manifest_entries():
    entries = [("N35c I. p. 7", "I. All'Italia"), ("N35c XXXVII. p. 161", "XXXVII.")]
    chains = [["N35c I. p. 7", "N35c I. p. 8"], ["N35c XXXVII. p. 161"]]
    m = build_manifest(entries, chains)
    assert m[0] == {
        "n": 1, "roman": "I", "title": "All'Italia", "slug": "all-italia",
        "base_witness": "N35c", "witnesses": ["N35c"], "title_variants": [],
        "wiki_pages": ["N35c I. p. 7", "N35c I. p. 8"], "pre_roles": None,
        "status": {"leggo": "provisional", "traduco": "none", "collaziono": "none", "concordanza": "none"},
    }
    assert m[1]["n"] == 37 and m[1]["title"] == "" and m[1]["slug"] == "frammento-xxxvii"


def test_merge_keeps_hand_edits_but_refreshes_pages():
    new = build_manifest([("E p. 1", "XII. L'infinito")], [["E p. 1"]])
    old = [dict(new[0], title="L'infinito (rivisto)", pre_roles=["head", "head"], wiki_pages=["old"])]
    merged = merge_existing(new, old)
    assert merged[0]["title"] == "L'infinito (rivisto)"
    assert merged[0]["pre_roles"] == ["head", "head"]
    assert merged[0]["wiki_pages"] == ["E p. 1"]
