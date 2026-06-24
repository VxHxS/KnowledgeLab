from __future__ import annotations

from knowledgelab.utils.colors import (
    adjust_hex_color,
    mix_hex_color,
    readable_text_color,
    valid_hex_color,
)


def test_valid_hex_color_valid():
    assert valid_hex_color("#ff0000", "#000000") == "#ff0000"


def test_valid_hex_color_normalizes_case():
    assert valid_hex_color("#FF00FF", "#000") == "#ff00ff"


def test_valid_hex_color_invalid_returns_fallback():
    assert valid_hex_color("not-a-color", "#123456") == "#123456"


def test_valid_hex_color_empty_returns_fallback():
    assert valid_hex_color("", "#abcdef") == "#abcdef"


def test_adjust_hex_color_brighten():
    result = adjust_hex_color("#000000", 1.5)
    assert result != "#000000"
    r = int(result[1:3], 16)
    g = int(result[3:5], 16)
    b = int(result[5:7], 16)
    assert r > 0 or g > 0 or b > 0


def test_adjust_hex_color_darken():
    result = adjust_hex_color("#ffffff", 0.5)
    r = int(result[1:3], 16)
    assert r < 255


def test_adjust_hex_color_invalid_fallback():
    result = adjust_hex_color("invalid", 1.0)
    assert result.startswith("#")


def test_mix_hex_color_equal():
    result = mix_hex_color("#000000", "#ffffff", 0.5)
    r = int(result[1:3], 16)
    assert 120 <= r <= 135


def test_mix_hex_color_amount_zero():
    result = mix_hex_color("#ff0000", "#0000ff", 0.0)
    assert result == "#ff0000"


def test_mix_hex_color_amount_one():
    result = mix_hex_color("#ff0000", "#0000ff", 1.0)
    assert result == "#0000ff"


def test_readable_text_color_light_bg():
    assert readable_text_color("#ffffff") == "#1f2933"


def test_readable_text_color_dark_bg():
    assert readable_text_color("#000000") == "#ffffff"


def test_readable_text_color_invalid():
    result = readable_text_color("bad")
    assert result in ("#1f2933", "#ffffff")
