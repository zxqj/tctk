
from dataclasses import dataclass
from enum import IntFlag, StrEnum, auto
from string import ascii_lowercase, ascii_uppercase
import unicodedata


class FontVariant(StrEnum):
    Script = auto()
    Fraktur = auto()
    DoubleStruck = auto()
    SansSerif = auto()
    Monospace = auto()

_VALID_ALPHA_FORMAT_COMBINATIONS = frozenset({
    (FontVariant.Script, False, False),
    (FontVariant.Script, True, False),
    (FontVariant.Fraktur, False, False),
    (FontVariant.Fraktur, True, False),
    (FontVariant.DoubleStruck, False, False),
    (FontVariant.SansSerif, False, False),
    (FontVariant.SansSerif, True, False),
    (FontVariant.SansSerif, False, True),
    (FontVariant.SansSerif, True, True),
    (FontVariant.Monospace, False, False),
})

@dataclass(eq=True, frozen=True)
class AlphaFormat:
    variant: FontVariant
    bold: bool = False
    italic: bool = False

    def __post_init__(self):
        if (self.variant, self.bold, self.italic) not in _VALID_ALPHA_FORMAT_COMBINATIONS:
            raise ValueError(
                f"unsupported alphabet format: variant={self.variant}, bold={self.bold}, italic={self.italic}"
            )


AlphaCodePointMap = dict[AlphaFormat, dict[str, int]]


_ALPHA_FORMAT_NAME_PATTERNS: dict[AlphaFormat, tuple[str, str]] = {
    AlphaFormat(FontVariant.Script): (
        "MATHEMATICAL SCRIPT CAPITAL {}",
        "MATHEMATICAL SCRIPT SMALL {}",
    ),
    AlphaFormat(FontVariant.Script, bold=True): (
        "MATHEMATICAL BOLD SCRIPT CAPITAL {}",
        "MATHEMATICAL BOLD SCRIPT SMALL {}",
    ),
    AlphaFormat(FontVariant.Fraktur): (
        "MATHEMATICAL FRAKTUR CAPITAL {}",
        "MATHEMATICAL FRAKTUR SMALL {}",
    ),
    AlphaFormat(FontVariant.Fraktur, bold=True): (
        "MATHEMATICAL BOLD FRAKTUR CAPITAL {}",
        "MATHEMATICAL BOLD FRAKTUR SMALL {}",
    ),
    AlphaFormat(FontVariant.DoubleStruck): (
        "MATHEMATICAL DOUBLE-STRUCK CAPITAL {}",
        "MATHEMATICAL DOUBLE-STRUCK SMALL {}",
    ),
    AlphaFormat(FontVariant.SansSerif): (
        "MATHEMATICAL SANS-SERIF CAPITAL {}",
        "MATHEMATICAL SANS-SERIF SMALL {}",
    ),
    AlphaFormat(FontVariant.SansSerif, bold=True): (
        "MATHEMATICAL SANS-SERIF BOLD CAPITAL {}",
        "MATHEMATICAL SANS-SERIF BOLD SMALL {}",
    ),
    AlphaFormat(FontVariant.SansSerif, italic=True): (
        "MATHEMATICAL SANS-SERIF ITALIC CAPITAL {}",
        "MATHEMATICAL SANS-SERIF ITALIC SMALL {}",
    ),
    AlphaFormat(FontVariant.SansSerif, bold=True, italic=True): (
        "MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL {}",
        "MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL {}",
    ),
    AlphaFormat(FontVariant.Monospace): (
        "MATHEMATICAL MONOSPACE CAPITAL {}",
        "MATHEMATICAL MONOSPACE SMALL {}",
    ),
}


_ALPHA_FORMAT_FALLBACK_NAMES: dict[AlphaFormat, dict[str, str]] = {
    AlphaFormat(FontVariant.Script): {
        "B": "SCRIPT CAPITAL B",
        "E": "SCRIPT CAPITAL E",
        "F": "SCRIPT CAPITAL F",
        "H": "SCRIPT CAPITAL H",
        "I": "SCRIPT CAPITAL I",
        "L": "SCRIPT CAPITAL L",
        "M": "SCRIPT CAPITAL M",
        "R": "SCRIPT CAPITAL R",
        "e": "SCRIPT SMALL E",
        "g": "SCRIPT SMALL G",
        "o": "SCRIPT SMALL O",
    },
    AlphaFormat(FontVariant.Fraktur): {
        "C": "BLACK-LETTER CAPITAL C",
        "H": "BLACK-LETTER CAPITAL H",
        "I": "BLACK-LETTER CAPITAL I",
        "R": "BLACK-LETTER CAPITAL R",
        "Z": "BLACK-LETTER CAPITAL Z",
    },
    AlphaFormat(FontVariant.DoubleStruck): {
        "C": "DOUBLE-STRUCK CAPITAL C",
        "H": "DOUBLE-STRUCK CAPITAL H",
        "N": "DOUBLE-STRUCK CAPITAL N",
        "P": "DOUBLE-STRUCK CAPITAL P",
        "Q": "DOUBLE-STRUCK CAPITAL Q",
        "R": "DOUBLE-STRUCK CAPITAL R",
        "Z": "DOUBLE-STRUCK CAPITAL Z",
    },
}


def _build_alpha_codepoint_map(alpha_format: AlphaFormat) -> dict[str, int]:
    uppercase_pattern, lowercase_pattern = _ALPHA_FORMAT_NAME_PATTERNS[alpha_format]
    fallback_names = _ALPHA_FORMAT_FALLBACK_NAMES.get(alpha_format, {})
    codepoints: dict[str, int] = {}

    for letter in ascii_uppercase:
        char_name = fallback_names.get(letter, uppercase_pattern.format(letter))
        codepoints[letter] = ord(unicodedata.lookup(char_name))

    for letter in ascii_lowercase:
        char_name = fallback_names.get(letter, lowercase_pattern.format(letter.upper()))
        codepoints[letter] = ord(unicodedata.lookup(char_name))

    return codepoints


ALPHA_FORMAT_CODEPOINTS: AlphaCodePointMap = {
    alpha_format: _build_alpha_codepoint_map(alpha_format)
    for alpha_format in _ALPHA_FORMAT_NAME_PATTERNS
}

class AlphaFormatIO:
    def __init__(self, fmt: AlphaFormat):
        self.fmt = fmt
    
    
