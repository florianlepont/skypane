"""Automatic splitting of a destination name into stacked lettering lines.

Each line is stretched to the full frame width, so the lines must have
balanced natural widths. The rule is deterministic and purely metric based
(real Anton widths); there is no table of per-city corrections.
"""
import itertools
import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator, List, Sequence, Tuple

from server.plane.render.giant import fonts

PORTRAIT = "portrait"
LANDSCAPE = "landscape"

# Longest destination considered; bounds the partition search.
MAX_NAME_CHARS = 80
MAX_LINES = 3
# A name of at most this many letters stays on one line.
SHORT_NAME_LETTERS = 3
# A line shorter than this is rejected unless the whole name is that short.
MIN_LINE_LETTERS = 2

# Lettering box in portrait: stretched to this width, stacked in this height.
BOX_WIDTH_PX = 1120
BOX_HEIGHT_PX = 1160
LINE_GAP_PX = 14

# Size at which lines are measured; ratios are size independent.
MEASURE_PX = 600

# Natural width below this fraction of the box (ln of it) asks the caller to
# shrink the block height rather than squeeze the letters further.
SQUEEZE_FLOOR = math.log(0.6)
# Added to the stretch cost for every cut inside a word.
CUT_PENALTY = 0.12

_VOWELS = frozenset("AEIOUYÀÁÂÃÄÅÆÈÉÊËÌÍÎÏÒÓÔÕÖØÙÚÛÜÝŒ")
_PROTECTED = ("CH", "PH", "TH", "GN", "QU", "SH", "CK", "GH", "EAU",
              "OU", "EU", "AU", "AI", "EI", "OI")
_DASHES = re.compile("[‐-―−]")
_TOKEN_SEPARATORS = re.compile(r"[\s\-]+")


@dataclass(frozen=True)
class Split:
    """Lettering lines plus the hint to shrink the block height."""
    lines: Tuple[str, ...]
    shrink_block: bool = False


def normalise_destination(text: str) -> str:
    """NFC, dashes as "-", whitespace collapsed, upper case, capped length."""
    text = unicodedata.normalize("NFC", text or "")
    text = _DASHES.sub("-", text)
    text = " ".join(text.split()).upper()
    return text[:MAX_NAME_CHARS].strip()


@lru_cache(maxsize=4096)
def _natural_ratio(line: str) -> float:
    """Width over cap height of `line` in Anton, ink extent."""
    left, _top, right, _bottom = fonts.anton(MEASURE_PX).getbbox(line)
    return (right - left) / fonts.cap_height(MEASURE_PX)


def _log_stretches(lines: Sequence[str]) -> List[float]:
    """ln(box width / natural width) of each line at its slot's cap height."""
    slot_h = BOX_HEIGHT_PX / len(lines) - LINE_GAP_PX
    return [math.log(BOX_WIDTH_PX / (_natural_ratio(line) * slot_h)) for line in lines]


def _cost(lines: Sequence[str], cuts: int) -> float:
    return max(abs(s) for s in _log_stretches(lines)) + CUT_PENALTY * cuts


def _letters(text: str) -> int:
    return len(text.replace(" ", ""))


def _compositions(n: int, parts: int) -> Iterator[Tuple[int, ...]]:
    """Sizes of `parts` contiguous groups covering `n` items."""
    for cuts in itertools.combinations(range(1, n), parts - 1):
        bounds = (0,) + cuts + (n,)
        yield tuple(b - a for a, b in zip(bounds, bounds[1:]))


def _group(tokens: Sequence[str], sizes: Tuple[int, ...]) -> Tuple[str, ...]:
    out, at = [], 0
    for size in sizes:
        out.append(" ".join(tokens[at:at + size]))
        at += size
    return tuple(out)


def _word_partitions(tokens: Sequence[str]) -> Iterator[Tuple[str, ...]]:
    for parts in range(2, min(MAX_LINES, len(tokens)) + 1):
        for sizes in _compositions(len(tokens), parts):
            yield _group(tokens, sizes)


def _best(candidates: Iterator[Tuple[Tuple[str, ...], int]]) -> Tuple[str, ...]:
    """Lowest cost candidate; ties keep the earliest (fewer lines first)."""
    best: Tuple[str, ...] = ()
    best_cost = math.inf
    for lines, cuts in candidates:
        cost = _cost(lines, cuts)
        if cost < best_cost - 1e-12:
            best, best_cost = lines, cost
    return best


def _split_words(tokens: Sequence[str]) -> Tuple[str, ...]:
    options = list(_word_partitions(tokens))
    strict = [p for p in options if all(_letters(x) > MIN_LINE_LETTERS for x in p)]
    return _best(((p, 0) for p in strict or options))


def _has_vowel(chunk: str) -> bool:
    base = unicodedata.normalize("NFC", chunk)
    return any(ch in _VOWELS for ch in base)


def _inside_protected(word: str, cut: int) -> bool:
    for pattern in _PROTECTED:
        start = word.find(pattern)
        while start != -1:
            if start < cut < start + len(pattern):
                return True
            start = word.find(pattern, start + 1)
    return False


def _cut_positions(word: str, need_vowel: bool) -> List[int]:
    out = []
    for cut in range(MIN_LINE_LETTERS, len(word) - MIN_LINE_LETTERS + 1):
        if _inside_protected(word, cut):
            continue
        if need_vowel and not (_has_vowel(word[:cut]) and _has_vowel(word[cut:])):
            continue
        out.append(cut)
    return out


def _chunks(word: str, cuts: Tuple[int, ...]) -> Tuple[str, ...]:
    bounds = (0,) + cuts + (len(word),)
    return tuple(word[a:b] for a, b in zip(bounds, bounds[1:]))


def _legal_chunkings(word: str, need_vowel: bool) -> Iterator[Tuple[Tuple[str, ...], int]]:
    positions = _cut_positions(word, need_vowel)
    for count in range(1, MAX_LINES):
        for cuts in itertools.combinations(positions, count):
            chunks = _chunks(word, cuts)
            if all(len(c) >= MIN_LINE_LETTERS for c in chunks) and (
                    not need_vowel or all(_has_vowel(c) for c in chunks)):
                yield chunks, count


def _split_word(word: str) -> Tuple[str, ...]:
    for need_vowel in (True, False):
        found = _best(_legal_chunkings(word, need_vowel))
        if found:
            return found
    return (word,)


def _shrink_hint(lines: Sequence[str]) -> bool:
    return len(lines) > 1 and min(_log_stretches(lines)) < SQUEEZE_FLOOR


def split_destination(text: str, orientation: str = PORTRAIT) -> Split:
    """Lines to letter for `text`.

    Landscape and names of three letters or fewer stay on one line. Names with
    a space or hyphen break only between words (two or three lines); single
    words break at balanced legal cuts. `shrink_block` is set when even the
    best split squeezes a line below the floor.
    """
    name = normalise_destination(text)
    if not name:
        return Split(())
    if orientation == LANDSCAPE:
        return Split((name.replace("-", " "),))
    tokens = [t for t in _TOKEN_SEPARATORS.split(name) if t]
    if not tokens:
        return Split(())
    if _letters(" ".join(tokens)) <= SHORT_NAME_LETTERS:
        return Split((" ".join(tokens),))
    lines = _split_words(tokens) if len(tokens) > 1 else _split_word(tokens[0])
    return Split(lines, _shrink_hint(lines))
