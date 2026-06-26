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
        border="#d1d5db",
        text=UI_THEME["text"],
        max_width=680,
        align="left",
        palette=("#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899"),
    ),
    "user": MessageBubbleStyle(
        fill="#f0f4f8",
        border="#d1d5db",
        text="#1a202c",
        max_width=560,
        align="right",
        palette=("#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899"),
    ),
    "error": MessageBubbleStyle(
        fill="#fef2f2",
        border="#fca5a5",
        text="#dc2626",
        max_width=680,
        align="left",
        palette=("#ef4444", "#f97316", "#eab308", "#84cc16", "#06b6d4", "#8b5cf6", "#ec4899"),
    ),
}


class AnimatedMessageBubble(tk.Canvas):
    """Chat bubble with subtle edge animation when model is thinking."""

    _radius = 10
    _min_width = 220
    _margin_x = 18
    _pad_x = 14
    _pad_y = 10
    _frame_ms = 150

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
        self._after_id: str | None = None
        self._phase = 0.0
        self._rect_coords = (0.0, 0.0, 0.0, 0.0)
        self._line_positions: list[float] = []
        self._line_colors: list[str] = []

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

    def start_animation(self) -> None:
        if self._after_id is None:
            self._phase = 0.0
            self._init_line_positions()
            self._tick()

    def _init_line_positions(self) -> None:
        import random
        random.seed(42)
        num_lines = random.randint(2, 4)
        self._line_positions = [random.random() for _ in range(num_lines)]
        self._line_colors = [self.style.palette[i % len(self.style.palette)] for i in range(num_lines)]

    def stop_animation(self) -> None:
        if self._after_id is None:
            return
        try:
            self.after_cancel(self._after_id)
        except tk.TclError:
            pass
        self._after_id = None
        self._rect_coords = (0.0, 0.0, 0.0, 0.0)
        self.redraw()

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
        if self._after_id is not None:
            self._draw_thinking_pulse()
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

    def _on_destroy(self, _event: tk.Event) -> None:
        self.stop_animation()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.015) % 1.0
        self.redraw()
        self._after_id = self.after(self._frame_ms, self._tick)

    def _draw_thinking_pulse(self) -> None:
        x1, y1, x2, y2 = self._rect_coords
        if x2 <= x1 or y2 <= y1:
            return
        width = x2 - x1
        height = y2 - y1
        perimeter = 2 * (width + height)
        inset = min(self._radius + 1, width / 5, height / 5)
        for i, pos in enumerate(self._line_positions):
            phase_offset = (self._phase + i * 0.37) % 1.0
            alpha = max(0.0, 1.0 - abs(phase_offset * 2.0 - 1.0) * 2.0)
            if alpha < 0.05:
                continue
            color = self._line_colors[i]
            seg_len = perimeter * 0.06
            center_dist = pos * perimeter
            points: list[float] = []
            steps = 8
            for s in range(steps + 1):
                frac = s / steps
                dist = (center_dist - seg_len / 2.0 + frac * seg_len) % perimeter
                seg_alpha = alpha * (1.0 - abs(frac * 2.0 - 1.0))
                if dist < width:
                    px = x1 + inset + (dist / width) * (width - 2 * inset)
                    py = y1
                elif dist < width + height:
                    px = x2
                    py = y1 + inset + ((dist - width) / height) * (height - 2 * inset)
                elif dist < 2 * width + height:
                    px = x2 - inset - ((dist - width - height) / width) * (width - 2 * inset)
                    py = y2
                else:
                    px = x1
                    py = y2 - inset - ((dist - 2 * width - height) / height) * (height - 2 * inset)
                points.extend([px, py])
            if len(points) >= 4:
                self.create_line(
                    points,
                    fill=color,
                    width=1,
                    smooth=True,
                    capstyle="round",
                )
