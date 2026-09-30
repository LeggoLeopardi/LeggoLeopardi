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
