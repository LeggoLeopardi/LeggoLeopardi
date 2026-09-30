"""Absolute paths of the repository folders used by the pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANTI = ROOT / "canti.json"
TEI_BASE = ROOT / "tei" / "base"
CACHE = ROOT / "pipeline" / "cache"
LOCI = ROOT / "pipeline" / "work" / "loci"
SCHEMA = ROOT / "pipeline" / "schema" / "tei_all.rng"
DATA = ROOT / "public" / "data"
REPORTS = ROOT / "reports"
