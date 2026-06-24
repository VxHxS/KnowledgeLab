from __future__ import annotations

import re

from knowledgelab.config import BUTTON_COLOR_PRESETS


def valid_hex_color(value: str, fallback: str) -> str:
    value = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.lower()
    return fallback


def adjust_hex_color(value: str, factor: float) -> str:
    value = valid_hex_color(value, BUTTON_COLOR_PRESETS["Blue"]).lstrip("#")
    channels = [int(value[index:index + 2], 16) for index in (0, 2, 4)]
    adjusted = []
    for channel in channels:
        if factor >= 1:
            channel = int(channel + (255 - channel) * (factor - 1))
        else:
            channel = int(channel * factor)
        adjusted.append(max(0, min(255, channel)))
    return "#{:02x}{:02x}{:02x}".format(*adjusted)


def mix_hex_color(left: str, right: str, amount: float) -> str:
    left = valid_hex_color(left, BUTTON_COLOR_PRESETS["Blue"]).lstrip("#")
    right = valid_hex_color(right, BUTTON_COLOR_PRESETS["Blue"]).lstrip("#")
    amount = max(0.0, min(1.0, amount))
    left_channels = [int(left[index:index + 2], 16) for index in (0, 2, 4)]
    right_channels = [int(right[index:index + 2], 16) for index in (0, 2, 4)]
    mixed = [
        int(left_channels[index] + (right_channels[index] - left_channels[index]) * amount)
        for index in range(3)
    ]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def readable_text_color(background: str) -> str:
    value = valid_hex_color(background, BUTTON_COLOR_PRESETS["Blue"]).lstrip("#")
    r, g, b = [int(value[index:index + 2], 16) for index in (0, 2, 4)]
    luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    return "#1f2933" if luminance > 150 else "#ffffff"
