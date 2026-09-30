from lxml import etree

from leggo_pipeline import paths
from leggo_pipeline.validate import validate
from test_build_base import INFINITO_ENTRY, SYN_ENTRY, SYN_PAGE, infinito_tree
from leggo_pipeline.build_base import build_poem_tei
from leggo_pipeline.wikitext import parse_pages


def write(tmp_path, n, data: bytes):
    (tmp_path / f"c{n}.xml").write_bytes(data)


def test_generated_tei_is_valid_against_tei_all(tmp_path):
    write(tmp_path, 12, etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    write(tmp_path, 99, build_poem_tei(SYN_ENTRY, parse_pages([("P", SYN_PAGE)])))
    assert validate(tmp_path, [{"n": 12}, {"n": 99}], paths.SCHEMA) == []


def test_missing_file_and_bad_numbering_and_duplicate_ids(tmp_path):
    data = etree.tostring(infinito_tree(), encoding="UTF-8").decode()
    write(tmp_path, 12, data.replace('n="7" xml:id="c12.v7"', 'n="70" xml:id="c12.v7"').encode())
    write(tmp_path, 13, data.replace("c12.v2.w1", "c12.v1.w1").replace('xml:id="c12"', 'xml:id="c13"').encode())
    errors = validate(tmp_path, [{"n": 12}, {"n": 13}, {"n": 14}], None)
    assert any("c12.xml" in e and "verse numbers" in e for e in errors)
    assert any("c13.xml" in e and "duplicate xml:id c12.v1.w1" in e for e in errors)
    assert any("c13.xml" in e and "id c12." in e for e in errors)
    assert "c14.xml: missing" in errors
