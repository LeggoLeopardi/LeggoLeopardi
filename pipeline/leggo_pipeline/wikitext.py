"""Parse WikiLeopardi <poem> blocks into verses, keeping the text exactly."""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field

LINK = re.compile(r"\[\[(?P<target>[^\]|]+?)(?:\|(?P<shown>[^\]]*))?\]\]", re.S)
INLINE = re.compile(
    r"\[\[(?P<target>[^\]|]+?)(?:\|(?P<shown>[^\]]*))?\]\]"
    r"|<span[^>]*>|</span>|</?small>|&nbsp;|''",
    re.S,
)
POEM = re.compile(r"<poem>(.*?)</poem>", re.S)
VERSE = re.compile(r"^(\d+)((?:&nbsp;|\s)*)(.*)$", re.S)
ARROWS_ONLY = re.compile(r"^[\s←→]*$")
SPEAKER = re.compile(r"^[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ’' ]*\.$")
NOTE_PREFIX = "N35c Note"


@dataclass
class Span:
    start: int
    end: int
    target: str = ""


@dataclass
class Cleaned:
    text: str
    italic: list[Span] = field(default_factory=list)
    loci: list[Span] = field(default_factory=list)
    notes: list[Span] = field(default_factory=list)


def _squeeze(c: Cleaned) -> Cleaned:
    """Trim the ends and collapse whitespace runs to one space, remapping every span."""
    text = c.text
    keep: list[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        is_space = ch.isspace()
        if is_space and prev_space:
            continue
        keep.append(i)
        prev_space = is_space
    while keep and text[keep[-1]].isspace():
        keep.pop()
    new = "".join(" " if text[i].isspace() else text[i] for i in keep)

    def fix(spans: list[Span]) -> list[Span]:
        return [
            Span(bisect.bisect_left(keep, s.start), bisect.bisect_left(keep, s.end), s.target)
            for s in spans
        ]

    return Cleaned(new, fix(c.italic), fix(c.loci), fix(c.notes))


def clean_inline(raw: str) -> Cleaned:
    """Remove wiki markup from one line; record italic, variant-locus and note-call spans."""
    parts: list[str] = []
    italic: list[Span] = []
    loci: list[Span] = []
    notes: list[Span] = []
    open_italic: int | None = None
    pos = 0

    def length() -> int:
        return sum(len(p) for p in parts)

    for m in INLINE.finditer(raw):
        parts.append(raw[pos : m.start()])
        pos = m.end()
        token = m.group(0)
        if m.group("target") is not None:
            target = m.group("target").strip()
            shown = m.group("shown")
            inner = clean_inline(m.group("target") if shown is None else shown)
            start = length()
            parts.append(inner.text)
            italic += [Span(start + s.start, start + s.end) for s in inner.italic]
            end = length()
            if target.startswith(NOTE_PREFIX):
                notes.append(Span(start, end, target))
            elif not ARROWS_ONLY.match(inner.text):
                loci.append(Span(start, end, target))
        elif token == "&nbsp;":
            parts.append(" ")
        elif token == "''":
            if open_italic is None:
                open_italic = length()
            else:
                italic.append(Span(open_italic, length()))
                open_italic = None
    parts.append(raw[pos:])
    return _squeeze(Cleaned("".join(parts), italic, loci, notes))


@dataclass
class Line:
    kind: str  # "verse", "label" (speaker) or "unnumbered"
    text: str
    n: int | None = None
    stanza_start: bool = False
    indent: int = 0
    italic: list[Span] = field(default_factory=list)
    loci: list[Span] = field(default_factory=list)
    notes: list[Span] = field(default_factory=list)
    page: str = ""


@dataclass
class ParsedPoem:
    pre: list[str] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    missing: list[int] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _join_multiline_links(block: str) -> str:
    return LINK.sub(lambda m: m.group(0).replace("\n", " "), block)


def _split_run_on(n: int, rest: str) -> list[tuple[int, str]]:
    """'137 A, 138 B' arrives as n=137, rest='A, 138 B': split at the next expected number."""
    out: list[tuple[int, str]] = []
    while True:
        m = re.search(rf"\s{n + 1}\s", rest)
        if not m:
            break
        out.append((n, rest[: m.start()]))
        n, rest = n + 1, rest[m.end() :]
    out.append((n, rest))
    return out


def parse_pages(pages: list[tuple[str, str]]) -> ParsedPoem:
    """Parse the ordered (title, wikitext) pages of one poem."""
    poem = ParsedPoem()
    last = 0
    for title, wikitext in pages:
        for block in POEM.findall(wikitext):
            blank_before = False
            seen_in_block = False
            for raw in _join_multiline_links(block).split("\n"):
                raw = raw.strip()
                if not raw:
                    blank_before = True
                    continue
                m = VERSE.match(raw)
                if m:
                    nbsp = m.group(2).count("&nbsp;")
                    for i, (n, rest) in enumerate(_split_run_on(int(m.group(1)), m.group(3))):
                        if n <= last:
                            poem.problems.append(
                                f"{title}: verse {n} after verse {last} (duplicate or out of order), dropped"
                            )
                            continue
                        if n > last + 1:
                            gap = list(range(last + 1, n))
                            poem.missing += gap
                            poem.problems.append(f"{title}: verse(s) {gap[0]}-{gap[-1]} missing in source")
                        first_part = i == 0
                        c = clean_inline(rest)
                        poem.lines.append(
                            Line(
                                "verse",
                                c.text,
                                n,
                                stanza_start=last == 0
                                or (first_part and (nbsp >= 3 or (blank_before and seen_in_block))),
                                indent=nbsp if first_part and nbsp < 3 else 0,
                                italic=c.italic,
                                loci=c.loci,
                                notes=c.notes,
                                page=title,
                            )
                        )
                        last = n
                    seen_in_block = True
                    blank_before = False
                    continue
                c = clean_inline(raw)
                if not c.text or ARROWS_ONLY.match(c.text):
                    continue
                if last == 0:
                    poem.pre.append(c.text)
                elif SPEAKER.match(c.text):
                    poem.lines.append(Line("label", c.text, page=title))
                else:
                    poem.lines.append(
                        Line("unnumbered", c.text, italic=c.italic, loci=c.loci, notes=c.notes, page=title)
                    )
                    poem.problems.append(f"{title}: line without verse number after verse {last}: {c.text!r}")
                seen_in_block = True
                blank_before = False
    if last == 0:
        poem.problems.append("no verses found")
    return poem
