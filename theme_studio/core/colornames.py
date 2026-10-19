"""Colour words in a directive -> the accents that honour them.

Small models get colour names roughly right in words but wrong in hex ("orange" ->
coral pink, "brown" -> a dark red that turns pink when lightened). So colour words
the user wrote are applied in code: the colours named first become primary, then
secondary, then tertiary, and those roles are locked against later fix-ups.

Neutral words count too: "grey" / "steel" make a steel accent, "black" asks for a
plain black background, "white" is already the text colour.
"""
import re
from dataclasses import dataclass

from .color import from_oklch, hue_distance, to_oklch


@dataclass(frozen=True)
class Spec:
    hue: float
    lo: float = 0.66          # lightness range the accent is pulled into
    hi: float = 0.80
    cmin: float = 0.14        # chroma range
    cmax: float = 0.40
    kind: str = "accent"      # accent | background | text


RED = dict(lo=0.56, hi=0.63, cmin=0.19)      # reds turn salmon when light
BROWN = dict(lo=0.62, hi=0.72, cmin=0.09, cmax=0.12)
STEEL = Spec(250, lo=0.76, hi=0.82, cmin=0.0, cmax=0.02)

WORDS = {
    # reds / oranges / yellows
    "crimson": Spec(18, **RED), "scarlet": Spec(28, **RED), "red": Spec(27, **RED),
    "maroon": Spec(20, **RED), "burgundy": Spec(10, **RED), "rose": Spec(5),
    "coral": Spec(38), "rust": Spec(45, lo=0.6, hi=0.68, cmin=0.13), "orange": Spec(58),
    "peach": Spec(50, lo=0.76, hi=0.84, cmin=0.08), "amber": Spec(72), "gold": Spec(88, cmin=0.11),
    "golden": Spec(88, cmin=0.11), "yellow": Spec(100, lo=0.80, hi=0.88, cmin=0.15),
    # browns
    "brown": Spec(56, **BROWN), "copper": Spec(55, lo=0.64, hi=0.72, cmin=0.11, cmax=0.14),
    "bronze": Spec(72, lo=0.64, hi=0.72, cmin=0.09, cmax=0.12), "tan": Spec(70, lo=0.72, hi=0.80, cmin=0.06, cmax=0.09),
    "beige": Spec(80, lo=0.80, hi=0.86, cmin=0.03, cmax=0.05), "khaki": Spec(95, lo=0.72, hi=0.80, cmin=0.06, cmax=0.09),
    "cream": Spec(90, lo=0.86, hi=0.92, cmin=0.03, cmax=0.05), "bone": Spec(85, lo=0.84, hi=0.9, cmin=0.02, cmax=0.04),
    # greens / blues / purples
    "lime": Spec(128), "chartreuse": Spec(125), "olive": Spec(115, lo=0.66, hi=0.74, cmin=0.08, cmax=0.11),
    "green": Spec(145), "emerald": Spec(155), "mint": Spec(165, lo=0.8, hi=0.88, cmin=0.09),
    "jade": Spec(170), "seafoam": Spec(170, lo=0.8, hi=0.88, cmin=0.07), "teal": Spec(190),
    "turquoise": Spec(192), "aqua": Spec(198), "cyan": Spec(205), "sky": Spec(230),
    "azure": Spec(240), "blue": Spec(258), "cobalt": Spec(262), "indigo": Spec(278),
    "violet": Spec(295), "purple": Spec(305), "lavender": Spec(300, lo=0.78, hi=0.86, cmin=0.08),
    "lilac": Spec(305, lo=0.78, hi=0.86, cmin=0.08), "plum": Spec(320, lo=0.6, hi=0.7),
    "magenta": Spec(330), "fuchsia": Spec(335), "pink": Spec(350, lo=0.74, hi=0.84),
    # neutrals
    "grey": STEEL, "gray": STEEL, "silver": STEEL, "steel": STEEL, "chrome": STEEL, "iron": STEEL,
    "black": Spec(0, kind="background"), "navy": Spec(262, kind="background"),
    "white": Spec(0, kind="text"),
}
PAIRS = {"lime green": Spec(128), "neon green": Spec(135), "sky blue": Spec(230),
         "deep purple": Spec(300, lo=0.62, hi=0.72), "hot pink": Spec(355),
         "blood red": Spec(25, **RED), "royal blue": Spec(265), "sea green": Spec(160),
         "forest green": Spec(145, lo=0.6, hi=0.7), "electric blue": Spec(245),
         "dark brown": Spec(50, **BROWN), "light brown": Spec(68, lo=0.72, hi=0.8, cmin=0.07, cmax=0.1)}
TOLERANCE = 20   # degrees: an accent this close in hue (and colourful enough) already counts


LIGHT = ("light", "pale", "soft", "pastel")
DARK = ("deep", "dark", "rich")


def _base(word):
    """'brownish' -> 'brown', 'purplish' -> 'purple', 'reddish' -> 'red'."""
    if word in WORDS:
        return word
    for cut, add in (("dish", "d"), ("ish", ""), ("ish", "e"), ("y", "")):
        if word.endswith(cut) and (word[: -len(cut)] + add) in WORDS:
            return word[: -len(cut)] + add
    return None


def _shade(spec, mod):
    """A lighter or darker version of a colour word ("light purple", "deep red")."""
    from dataclasses import replace
    if mod in LIGHT:
        return replace(spec, lo=max(spec.lo, 0.80), hi=max(spec.hi, 0.88), cmin=min(spec.cmin, 0.07))
    if mod in DARK:
        return replace(spec, lo=min(spec.lo, 0.56), hi=min(spec.hi, 0.64))
    return spec


def named(prompt):
    """Colour words in the prompt, in the order written: [(word, Spec)]."""
    text = (prompt or "").lower()
    for pair in PAIRS:   # "lime green" counts as lime green, not green
        text = text.replace(pair, f" {pair.replace(' ', '_')} ")
    tokens = re.findall(r"[a-z_]+", text)
    seen, out = set(), []
    for i, w in enumerate(tokens):
        word = w.replace("_", " ")
        spec = PAIRS.get(word)
        if spec is None:
            base = _base(word)
            if base is None:
                continue
            spec, word = WORDS[base], base
            mod = tokens[i - 1] if i else ""
            if mod in LIGHT + DARK and spec.kind == "accent" and spec.cmax > 0.02:
                spec, word = _shade(spec, mod), f"{mod} {base}"
        if word not in seen:
            seen.add(word)
            out.append((word, spec))
    return out


def named_hues(prompt):
    """[(word, hue)] for the chromatic accent words (kept for older callers)."""
    return [(w, s.hue) for w, s in named(prompt) if s.kind == "accent" and s.cmax > 0.02]


def wants_black(prompt):
    return any(s.kind == "background" and w == "black" for w, s in named(prompt))


def _fits(hexcol, spec):
    L, C, H = to_oklch(hexcol)
    if spec.cmax <= 0.02:                       # a neutral: just has to be neutral and light
        return C <= 0.03 and L >= spec.lo - 0.05
    return hue_distance(H, spec.hue) <= TOLERANCE and spec.cmin - 0.03 <= C <= spec.cmax + 0.06 \
        and spec.lo - 0.08 <= L <= spec.hi + 0.08


def _make(hexcol, spec):
    L, C, _ = to_oklch(hexcol)
    return from_oklch(min(max(L, spec.lo), spec.hi), min(max(C, spec.cmin), spec.cmax), spec.hue)


def apply(picks, prompt, roles=("primary", "secondary", "tertiary")):
    """Accent colours named in `prompt` become `roles`, in the order they were written.
    Returns (picks, notes, locked_roles)."""
    picks, notes, locked = dict(picks), [], []
    accents = [(w, s) for w, s in named(prompt) if s.kind == "accent"]
    # Three shades of one colour make a flat theme: if the first three named colours are
    # all one family and something different was named later (brown after three purples),
    # the different one takes the last slot.
    chosen = accents[:len(roles)]
    def chromatic(s):
        return s.cmax > 0.02
    if len(chosen) == len(roles) == 3 and all(chromatic(s) for _w, s in chosen) and \
            all(hue_distance(s.hue, chosen[0][1].hue) <= 35 for _w, s in chosen):
        other = next(((w, s) for w, s in accents[3:]
                      if not chromatic(s) or hue_distance(s.hue, chosen[0][1].hue) > 35), None)
        if other:
            chosen[2] = other
    for (word, spec), role in zip(chosen, roles):
        if not _fits(picks[role], spec):
            new = _make(picks[role], spec)
            notes.append(f"{role} {picks[role]} -> {new} (you said {word})")
            picks[role] = new
        locked.append(role)
    return picks, notes, locked


def honour(picks, prompt, roles=("primary", "secondary", "tertiary")):
    """Older interface: (picks, notes)."""
    picks, notes, _locked = apply(picks, prompt, roles)
    return picks, notes
