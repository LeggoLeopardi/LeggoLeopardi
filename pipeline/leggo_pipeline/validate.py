"""Check tei/base: schema validity, unique well-formed ids, verse numbering, one file per poem."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from lxml import etree

from . import paths
from .manifest import load_manifest

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def validate(tei_dir: Path, manifest: list[dict], schema_path: Path | None) -> list[str]:
    errors: list[str] = []
    rng = etree.RelaxNG(etree.parse(str(schema_path))) if schema_path else None
    for entry in manifest:
        n = entry["n"]
        path = Path(tei_dir) / f"c{n}.xml"
        if not path.exists():
            errors.append(f"{path.name}: missing")
            continue
        try:
            # collect_ids=False: report duplicate ids ourselves instead of failing the parse on them
            doc = etree.parse(str(path), etree.XMLParser(collect_ids=False))
        except etree.XMLSyntaxError as e:
            errors.append(f"{path.name}: not well-formed: {e}")
            continue
        if rng is not None and not rng.validate(doc):
            errors.append(f"{path.name}: schema: {rng.error_log.last_error}")
        ids = doc.xpath("//@xml:id")
        errors += [f"{path.name}: duplicate xml:id {i}" for i, c in Counter(ids).items() if c > 1]
        pattern = re.compile(rf"^c{n}(\.v\d+(\.u\d+)?(\.w\d+)?)?$")
        errors += [f"{path.name}: id {i} does not match c{n}.v…" for i in ids if not pattern.match(i)]
        numbers = [int(x) for x in doc.xpath("//tei:lg/tei:l/@n", namespaces=NS)]
        if numbers != list(range(1, len(numbers) + 1)):
            errors.append(f"{path.name}: verse numbers are not 1..{len(numbers)}")
    return errors


def main() -> int:
    errors = validate(paths.TEI_BASE, load_manifest(paths.CANTI), paths.SCHEMA)
    for e in errors:
        print(e)
    print(f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
