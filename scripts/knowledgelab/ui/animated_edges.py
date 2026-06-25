from __future__ import annotations

import tkinter as tk

from knowledgelab.config import UI_THEME
from knowledgelab.utils.colors import mix_hex_color


class AnimatedEdgeFrame(tk.Frame):
    """Frame with a muted moving accent around its outer edge."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        background: str | None = None,
        border: str | None = None,
        palette: tuple[str, ...] | None = None,
        thickness: int = 3,
        animated: bool = True,
    ) -> None:
        self.background = background or UI_THEME["chat_bg"]
        self.border = border or "#c6d6e2"
        self.palette = palette or ("#527f9d", "#6f8c58", "#8970a6", "#aa735f")
        self.thickness = max(2, int(thickness or 3))
        self.animated = bool(animated)
        self._phase = 0.0
        self._after_id: str | None = None

        super().__init__(master, bg=self.background)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        self.top = tk.Canvas(self, height=self.thickness, bg=self.border, highlightthickness=0, bd=0)
        self.left = tk.Canvas(self, width=self.thickness, bg=self.border, highlightthickness=0, bd=0)
        self.right = tk.Canvas(self, width=self.thickness, bg=self.border, highlightthickness=0, bd=0)
        self.bottom = tk.Canvas(self, height=self.thickness, bg=self.border, highlightthickness=0, bd=0)
        self.content = tk.Frame(self, bg=self.background)

        self._corner(0, 0)
        self._corner(0, 2)
        self._corner(2, 0)
        self._corner(2, 2)
        self.top.grid(row=0, column=1, sticky="ew")
        self.left.grid(row=1, column=0, sticky="ns")
        self.content.grid(row=1, column=1, sticky="nsew")
        self.right.grid(row=1, column=2, sticky="ns")
        self.bottom.grid(row=2, column=1, sticky="ew")

        self.bind("<Destroy>", self._on_destroy, add="+")
        self.bind("<Configure>", lambda _event: self.redraw(), add="+")
        self.redraw()
        if self.animated:
            self.start_animation()

    def start_animation(self) -> None:
        if self._after_id is None:
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
        for canvas in (self.top, self.left, self.right, self.bottom):
            canvas.delete("all")
            width = max(1, canvas.winfo_width())
            height = max(1, canvas.winfo_height())
            canvas.create_rectangle(0, 0, width, height, fill=self.border, outline="")

        if self.animated:
            self._draw_shimmer()

    def _corner(self, row: int, column: int) -> None:
        frame = tk.Frame(self, bg=self.border, width=self.thickness, height=self.thickness)
        frame.grid(row=row, column=column, sticky="nsew")
        frame.grid_propagate(False)

    def _draw_shimmer(self) -> None:
        width = max(1.0, float(self.top.winfo_width()))
        height = max(1.0, float(self.left.winfo_height()))
        perimeter = 2 * (width + height)
        runner_length = min(360.0, max(190.0, perimeter * 0.32))
        color_index = int(self._phase * len(self.palette)) % len(self.palette)
        self._draw_tapered_runner(self._phase * perimeter, runner_length, self.palette[color_index])

    def _draw_tapered_runner(self, center_distance: float, length: float, color: str) -> None:
        piece_count = 36
        piece = max(6.0, length / piece_count)
        pieces: list[tuple[float, float, str, int]] = []
        for step in range(piece_count):
            position = (step + 0.5) / piece_count
            weight = max(0.0, 1.0 - abs(position * 2.0 - 1.0))
            if weight <= 0.04:
                continue
            distance = center_distance - length / 2.0 + step * piece
            fade = max(0.0, 0.82 - weight * 0.78)
            segment_color = mix_hex_color(color, self.border, fade)
            line_width = max(1, int(round(1 + weight * (self.thickness + 3))))
            pieces.append((weight, distance, segment_color, line_width))
        for _weight, distance, segment_color, line_width in sorted(pieces, key=lambda item: item[0]):
            self._draw_edge_piece(distance, piece * 1.18, segment_color, line_width)

    def _draw_edge_piece(self, distance: float, length: float, color: str, line_width: int) -> None:
        width = max(1.0, float(self.top.winfo_width()))
        height = max(1.0, float(self.left.winfo_height()))
        perimeter = 2 * (width + height)
        distance %= perimeter
        center = max(1.0, self.thickness / 2)

        if distance < width:
            start = min(width, max(0.0, distance))
            end = min(width, start + length)
            self.top.create_line(start, center, end, center, fill=color, width=line_width, capstyle="round")
            return
        distance -= width
        if distance < height:
            start = min(height, max(0.0, distance))
            end = min(height, start + length)
            self.right.create_line(center, start, center, end, fill=color, width=line_width, capstyle="round")
            return
        distance -= height
        if distance < width:
            start = width - min(width, max(0.0, distance))
            end = max(0.0, start - length)
            self.bottom.create_line(start, center, end, center, fill=color, width=line_width, capstyle="round")
            return
        distance -= width
        start = height - min(height, max(0.0, distance))
        end = max(0.0, start - length)
        self.left.create_line(center, start, center, end, fill=color, width=line_width, capstyle="round")

    def _tick(self) -> None:
        self._phase = (self._phase + 0.045) % 1.0
        self.redraw()
        self._after_id = self.after(45, self._tick)

    def _on_destroy(self, _event: tk.Event) -> None:
        self.stop_animation()
