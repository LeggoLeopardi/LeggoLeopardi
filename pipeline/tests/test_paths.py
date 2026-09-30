from leggo_pipeline import paths


def test_root_is_repo_root():
    assert (paths.ROOT / "pipeline" / "pyproject.toml").is_file()
    assert paths.CANTI == paths.ROOT / "canti.json"
    assert paths.TEI_BASE == paths.ROOT / "tei" / "base"
    assert paths.SCHEMA.is_file()
