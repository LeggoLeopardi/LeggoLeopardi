"""Split a verse into words (w), punctuation (pc) and author-note calls (ref)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .wikitext import Span

# A word may end with an elision apostrophe (quest’, Dell'); a word may start with one (’l).
TOKEN = re.compile(r"[^\W\d_]+['’]?|['’][^\W\d_]+|\d+|[^\w\s]")


@dataclass
class Token:
    text: str
    kind: str  # "w", "pc" or "ref"
    start: int
    end: int
    italic: bool = False


def _inside(start: int, end: int, spans) -> bool:
    return any(s.start <= start and end <= s.end for s in spans)


def tokenize(text: str, italic: list[Span] = (), notes: list[Span] = ()) -> list[Token]:
    tokens: list[Token] = []
    for m in TOKEN.finditer(text):
        s, e, t = m.start(), m.end(), m.group(0)
        if _inside(s, e, notes):
            kind = "ref"
        elif t[0].isalnum() or (t[0] in "'’" and len(t) > 1):
            kind = "w"
        else:
            kind = "pc"
        tokens.append(Token(t, kind, s, e, italic=_inside(s, e, italic)))
    return tokens
