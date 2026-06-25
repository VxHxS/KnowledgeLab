from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

from knowledgelab.config import UI_THEME
from knowledgelab.utils.colors import mix_hex_color


@dataclass(frozen=True)
class MessageBubbleStyle:
    fill: str
    border: str
    text: str
    max_width: int
    align: str
    palette: tuple[str, ...]


ROLE_STYLES = {
    "assistant": MessageBubbleStyle(
        fill="#ffffff",
        border="#c0ceda",
        text=UI_THEME["text"],
        max_width=680,
        align="left",
        palette=("#5f8aa3", "#7d965f", "#9479ad", "#b4816e"),
    ),
    "user": MessageBubbleStyle(
        fill="#f0f1f3",
        border="#c8d2da",
        text="#202124",
        max_width=560,
        align="right",
        palette=("#5c879b", "#7f9c61", "#9a7caf", "#b9876f"),
    ),
    "error": MessageBubbleStyle(
        fill="#fff6f4",
        border="#e3c2bd",
        text=UI_THEME["danger"],
        max_width=680,
        align="left",
        palette=("#b45f54", "#ba8d43", "#799b80", "#8383a5"),
    ),
}


class AnimatedMessageBubble(tk.Canvas):
    """Chat bubble with a subtle animated edge accent."""

    _radius = 12
    _min_width = 220
    _margin_x = 18
    _pad_x = 14
    _pad_y = 10
    _frame_ms = 55

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        *,
        role: str = "assistant",
        canvas_width: int = 430,
        background: str | None = None,
        animated: bool = True,
    ) -> None:
        self.text = text.strip()
        self.role = role if role in ROLE_STYLES else "assistant"
        self.style = ROLE_STYLES[self.role]
        self.canvas_width = max(430, int(canvas_width or 430))
        self.background = background or UI_THEME["chat_bg"]
        self.animated = bool(animated)
        self._after_id: str | None = None
        self._phase = 0.0
        self._rect_coords = (0.0, 0.0, 0.0, 0.0)

        super().__init__(
            master,
            width=self.canvas_width,
            height=58,
            highlightthickness=0,
            bd=0,
            background=self.background,
        )
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.redraw()
        if self.animated:
            self.start_animation()

    def start_animation(self) -> None:
        if self._after_id is None:
            self._animation_ticks = 0
            self._tick()

    def stop_animation(self) -> None:
        if self._after_id is None:
            return
        try:
            self.after_cancel(self._after_id)
        except tk.TclError:
            pass
        self._after_id = None

    def redraw(self) -> None:
        self.delete("all")
        bubble_width = self._bubble_width()
        text_width = max(160, bubble_width - self._pad_x * 2)
        if self.style.align == "right":
            text_x = self.canvas_width - self._margin_x - self._pad_x
            anchor = "ne"
            justify = "left"
        else:
            text_x = self._margin_x + self._pad_x
            anchor = "nw"
            justify = "left"

        text_id = self.create_text(
            text_x,
            self._pad_y + 4,
            text=self.text,
            anchor=anchor,
            width=text_width,
            justify=justify,
            fill=self.style.text,
            font=("Segoe UI", 10),
        )
        fallback_right = self.canvas_width - self._margin_x
        fallback = (
            fallback_right - bubble_width,
            8,
            fallback_right,
            44,
        )
        bbox = self.bbox(text_id) or fallback
        x1 = max(10, float(bbox[0]) - self._pad_x)
        y1 = max(6, float(bbox[1]) - self._pad_y)
        x2 = min(self.canvas_width - 10, float(bbox[2]) + self._pad_x)
        y2 = float(bbox[3]) + self._pad_y
        height = max(46, int(y2 + 10))
        self.configure(width=self.canvas_width, height=height)

        rect_id = self._rounded_rect(x1, y1, x2, y2)
        self.tag_lower(rect_id, text_id)
        self._rect_coords = (x1, y1, x2, y2)
        if self.animated:
            self._draw_shimmer()
        self.tag_raise(text_id)

    def _bubble_width(self) -> int:
        side_allowance = 190 if self.style.align == "right" else 44
        by_canvas = max(self._min_width, self.canvas_width - side_allowance)
        return min(self.style.max_width, by_canvas)

    def _rounded_rect(self, x1: float, y1: float, x2: float, y2: float) -> int:
        radius = min(self._radius, max(4.0, (x2 - x1) / 2), max(4.0, (y2 - y1) / 2))
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return int(
            self.create_polygon(
                points,
                smooth=True,
                fill=self.style.fill,
                outline=self.style.border,
                width=1,
            )
        )

    def _draw_shimmer(self) -> None:
        x1, y1, x2, y2 = self._rect_coords
        width = max(1.0, x2 - x1)
        height = max(1.0, y2 - y1)
        perimeter = 2 * (width + height)
        runner_length = min(170.0, max(82.0, perimeter * 0.3))
        color_index = int(self._phase * len(self.style.palette)) % len(self.style.palette)
        self._draw_tapered_runner(self._phase * perimeter, runner_length, self.style.palette[color_index])

    def _draw_tapered_runner(self, center_distance: float, length: float, color: str) -> None:
        piece_count = 28
        piece = max(5.0, length / piece_count)
        pieces: list[tuple[float, float, str, int]] = []
        for step in range(piece_count):
            position = (step + 0.5) / piece_count
            weight = max(0.0, 1.0 - abs(position * 2.0 - 1.0))
            if weight <= 0.04:
                continue
            distance = center_distance - length / 2.0 + step * piece
            fade = max(0.0, 0.84 - weight * 0.78)
            segment_color = mix_hex_color(color, self.style.border, fade)
            line_width = max(1, int(round(1 + weight * 4)))
            pieces.append((weight, distance, segment_color, line_width))
        for _weight, distance, segment_color, line_width in sorted(pieces, key=lambda item: item[0]):
            self._draw_edge_piece(distance, piece * 1.18, segment_color, line_width)

    def _draw_edge_piece(self, distance: float, length: float, color: str, line_width: int) -> None:
        x1, y1, x2, y2 = self._rect_coords
        width = max(1.0, x2 - x1)
        height = max(1.0, y2 - y1)
        perimeter = 2 * (width + height)
        distance %= perimeter
        inset = min(self._radius * 0.72, width / 3, height / 3)
        if distance < width:
            start = x1 + min(max(inset, distance), max(inset, width - inset))
            end = min(x2 - inset, start + length)
            if end > start:
                self.create_line(start, y1, end, y1, fill=color, width=line_width, capstyle="round")
            return
        distance -= width
        if distance < height:
            start = y1 + min(max(inset, distance), max(inset, height - inset))
            end = min(y2 - inset, start + length)
            if end > start:
                self.create_line(x2, start, x2, end, fill=color, width=line_width, capstyle="round")
            return
        distance -= height
        if distance < width:
            start = x2 - min(max(inset, distance), max(inset, width - inset))
            end = max(x1 + inset, start - length)
            if start > end:
                self.create_line(start, y2, end, y2, fill=color, width=line_width, capstyle="round")
            return
        distance -= width
        start = y2 - min(max(inset, distance), max(inset, height - inset))
        end = max(y1 + inset, start - length)
        if start > end:
            self.create_line(x1, start, x1, end, fill=color, width=line_width, capstyle="round")

    def _tick(self) -> None:
        self._animation_ticks = getattr(self, "_animation_ticks", 0) + 1
        if self._animation_ticks > 70:
            self.stop_animation()
            return
        self._phase = (self._phase + 0.032) % 1.0
        self.redraw()
        self._after_id = self.after(self._frame_ms, self._tick)

    def _on_destroy(self, _event: tk.Event) -> None:
        self.stop_animation()
