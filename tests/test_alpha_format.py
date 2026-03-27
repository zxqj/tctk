import pytest

from tctk.config import ALPHA_FORMAT_CODEPOINTS, AlphaFormat, FontVariant


def test_alpha_format_rejects_unsupported_styles():
    with pytest.raises(ValueError):
        AlphaFormat(FontVariant.Script, italic=True)

    with pytest.raises(ValueError):
        AlphaFormat(FontVariant.DoubleStruck, bold=True)

    with pytest.raises(ValueError):
        AlphaFormat(FontVariant.Monospace, italic=True)


def test_alpha_format_codepoint_maps_cover_all_letters():
    for codepoints in ALPHA_FORMAT_CODEPOINTS.values():
        assert len(codepoints) == 52
        assert all(len(letter) == 1 for letter in codepoints)


def test_alpha_format_codepoint_maps_include_special_unicode_fallbacks():
    assert ALPHA_FORMAT_CODEPOINTS[AlphaFormat(FontVariant.Script)]["A"] == 0x1D49C
    assert ALPHA_FORMAT_CODEPOINTS[AlphaFormat(FontVariant.Script)]["B"] == 0x212C
    assert ALPHA_FORMAT_CODEPOINTS[AlphaFormat(FontVariant.Script)]["e"] == 0x212F

    assert ALPHA_FORMAT_CODEPOINTS[AlphaFormat(FontVariant.Fraktur)]["C"] == 0x212D
    assert ALPHA_FORMAT_CODEPOINTS[AlphaFormat(FontVariant.DoubleStruck)]["C"] == 0x2102
    assert ALPHA_FORMAT_CODEPOINTS[AlphaFormat(FontVariant.SansSerif, bold=True, italic=True)]["z"] == 0x1D66F
