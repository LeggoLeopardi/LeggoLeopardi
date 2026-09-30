from pathlib import Path

import pytest

from leggo_pipeline.harvest import ChainError, PageMissing, WikiClient, follow_chain, next_page, parse_index

FIXTURES = Path(__file__).parent / "fixtures"


def fake_client(tmp_path, pages):
    calls = []

    def fetch(title):
        calls.append(title)
        return pages.get(title)

    return WikiClient(tmp_path, fetch=fetch, delay=0), calls


def test_parse_index_real_fixture():
    entries = parse_index((FIXTURES / "n35c_index.wiki").read_text(encoding="utf-8"))
    assert len(entries) == 41
    assert entries[0] == ("N35c I. ǁ ALL'ITALIA. p. 7", "I. All'Italia")
    assert entries[11] == ("N35c XII. ‖ L'INFINITO. p. 62", "XII. L'infinito")
    assert entries[-1] == ("N35c XLI. Dello stesso p. 169", "XLI. Dello stesso")


def test_next_page_uses_last_forward_link():
    text = (FIXTURES / "n35c_infinito_p62.wiki").read_text(encoding="utf-8")
    assert next_page(text) == "N35c XIII. La sera del dì di festa p. 63"
    assert next_page("no links") is None


def test_client_caches_pages(tmp_path):
    client, calls = fake_client(tmp_path, {"A": "text of A"})
    assert client.page("A") == "text of A"
    assert client.page("A") == "text of A"
    assert calls == ["A"]
    again, calls2 = fake_client(tmp_path, {})
    assert again.page("A") == "text of A" and calls2 == []


def test_missing_page_raises(tmp_path):
    client, _ = fake_client(tmp_path, {})
    with pytest.raises(PageMissing):
        client.page("Nope")


def test_follow_chain_stops_at_next_poem_and_notes(tmp_path):
    pages = {
        "P1 a": "[[P1 b|→]]",
        "P1 b": "[[P2 a|→]]",
        "P2 a": "[[N35c Note p. 171|→]]",
    }
    client, _ = fake_client(tmp_path, pages)
    assert follow_chain(client, "P1 a", stop={"P1 a", "P2 a"}) == ["P1 a", "P1 b"]
    assert follow_chain(client, "P2 a", stop={"P1 a", "P2 a"}) == ["P2 a"]


def test_follow_chain_errors_name_the_poem(tmp_path):
    client, _ = fake_client(tmp_path, {"P1 a": "[[P1 gone|→]]"})
    with pytest.raises(ChainError, match="P1 a"):
        follow_chain(client, "P1 a", stop={"P1 a"})
    client, _ = fake_client(tmp_path / "loop", {"L a": "[[L b|→]]", "L b": "[[L a bis|→]]", "L a bis": "[[L b|→]]"})
    with pytest.raises(ChainError, match="loop"):
        follow_chain(client, "L a", stop=set())


def test_chain_without_forward_link_is_an_error_not_a_short_poem(tmp_path):
    client, _ = fake_client(tmp_path, {"P1 a": "[[P1 b|→]]", "P1 b": "verses, but the → link was removed"})
    with pytest.raises(ChainError, match="P1 a.*no forward link"):
        follow_chain(client, "P1 a", stop={"P1 a", "P2 a"})


def test_redirect_stub_is_an_error(tmp_path):
    client, _ = fake_client(tmp_path, {"P1 a": "[[P1 b|→]]", "P1 b": "#REDIRECT [[P1 b renamed]]"})
    with pytest.raises(ChainError, match="P1 a.*redirect"):
        follow_chain(client, "P1 a", stop={"P1 a"})
