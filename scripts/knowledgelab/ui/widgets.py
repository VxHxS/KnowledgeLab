from __future__ import annotations

import tkinter as tk
from abc import ABC, abstractmethod

from knowledgelab.config import BUTTON_COLOR_PRESETS, UI_THEME
from knowledgelab.utils.colors import (
    adjust_hex_color,
    mix_hex_color,
    readable_text_color,
    valid_hex_color,
)


class InteractiveButton(tk.Canvas, ABC):
    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._state = "normal"
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<space>", self._on_keyboard)
        self.bind("<Return>", self._on_keyboard)

    def _set_state(self, state: str) -> None:
        self._state = state

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        if self._state == "disabled":
            return
        self._set_state("hover")
        self._draw()

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        if self._state in ("normal", "disabled"):
            return
        self._set_state("normal")
        self._draw()

    def _on_press(self, _event: tk.Event | None = None) -> None:
        if self._state == "disabled":
            return
        self._set_state("pressed")
        self._draw()

    def _on_release(self, _event: tk.Event | None = None) -> None:
        if self._state == "disabled":
            return
        self._set_state("normal")
        self._draw()

    def _on_keyboard(self, _event: tk.Event | None = None) -> str:
        self._on_release()
        return "break"

    @abstractmethod
    def _draw(self) -> None:
        ...


class RoundedButton(InteractiveButton):
    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command,
        *,
        bg: str,
        active_bg: str,
        fg: str,
        radius: int = 7,
        height: int = 36,
    ) -> None:
        super().__init__(
            parent,
            height=height,
            background=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.text = text
        self.command = command
        self.normal_bg = bg
        self.active_bg = active_bg
        self.fg = fg
        self.radius = radius
        self.enabled = True
        self.hover = False
        self.hover_amount = 0.0
        self.hover_after_id: str | None = None
        self.bind("<Configure>", lambda _event: self.redraw())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<space>", self.on_keyboard)
        self.bind("<Return>", self.on_keyboard)
        self.bind("<FocusIn>", lambda _event: self.redraw())
        self.bind("<FocusOut>", lambda _event: self.redraw())
        self.redraw()

    def configure(self, cnf=None, **kwargs):  # type: ignore[override]
        if cnf:
            kwargs.update(cnf)
        state = kwargs.pop("state", None)
        if state is not None:
            self.enabled = state != "disabled"
            super().configure(cursor="hand2" if self.enabled else "arrow")
            self.redraw()
        if "text" in kwargs:
            self.text = str(kwargs.pop("text"))
            self.redraw()
        if kwargs:
            super().configure(**kwargs)

    config = configure

    def set_colors(self, *, bg: str, active_bg: str, fg: str) -> None:
        self.normal_bg = bg
        self.active_bg = active_bg
        self.fg = fg
        self.redraw()

    def on_enter(self, _event: tk.Event | None = None) -> None:
        self.hover = True
        self.animate_hover()

    def on_leave(self, _event: tk.Event | None = None) -> None:
        self.hover = False
        self.animate_hover()

    def on_click(self, _event: tk.Event | None = None) -> None:
        if self.enabled and self.command:
            self.command()

    def on_keyboard(self, _event: tk.Event | None = None) -> str:
        self.on_click()
        return "break"

    def rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, fill: str) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline="")

    def redraw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 80)
        height = max(self.winfo_height(), 30)
        fill = mix_hex_color(self.normal_bg, self.active_bg, self.hover_amount if self.enabled else 0.0)
        if not self.enabled:
            fill = "#c9d0d7"
        self.rounded_rect(1, 1, width - 1, height - 1, self.radius, fill)
        self.create_text(
            width // 2,
            height // 2,
            text=self.text,
            fill=self.fg if self.enabled else "#eef2f6",
            font=("Segoe UI Semibold", 10),
        )
        if self.focus_get() == self:
            self.rounded_rect(2, 2, width - 2, height - 2, self.radius, "")
            self.create_rectangle(2, 2, width - 2, height - 2, outline=UI_THEME["focus_ring"], width=2, dash=(4, 2))

    def animate_hover(self) -> None:
        if self.hover_after_id:
            try:
                self.after_cancel(self.hover_after_id)
            except tk.TclError:
                pass
            self.hover_after_id = None
        target = 1.0 if self.hover and self.enabled else 0.0
        if abs(self.hover_amount - target) < 0.05:
            self.hover_amount = target
            self.redraw()
            return
        self.hover_amount += 0.18 if self.hover_amount < target else -0.18
        self.hover_amount = max(0.0, min(1.0, self.hover_amount))
        self.redraw()
        self.hover_after_id = self.after(18, self.animate_hover)

    _draw = redraw


class IconButton(InteractiveButton):
    def __init__(
        self,
        parent: tk.Widget,
        image: tk.PhotoImage,
        command,
        *,
        size: int = 34,
        background: str = "#eef2f5",
        hover_bg: str = "#f6f8fb",
        pressed_bg: str = "#e8f0fe",
        outline: str = "#cfd7e2",
        active_outline: str = "#7aa2ff",
        radius: int = 9,
    ) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            background=background,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.image = image
        self.command = command
        self.size = size
        self.normal_bg = background
        self.hover_bg = hover_bg
        self.pressed_bg = pressed_bg
        self.outline = outline
        self.active_outline = active_outline
        self.radius = radius
        self.hover = False
        self.pressed = False
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<space>", self.on_keyboard)
        self.bind("<Return>", self.on_keyboard)
        self.bind("<FocusIn>", lambda _event: self.redraw())
        self.bind("<FocusOut>", lambda _event: self.redraw())
        self.redraw()

    def on_enter(self, _event: tk.Event | None = None) -> None:
        self.hover = True
        self.redraw()

    def on_leave(self, _event: tk.Event | None = None) -> None:
        self.hover = False
        self.pressed = False
        self.redraw()

    def on_press(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = True
        self.redraw()

    def on_click(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = False
        self.redraw()
        if self.command:
            self.command()

    def on_keyboard(self, _event: tk.Event | None = None) -> str:
        self.on_click()
        return "break"

    def redraw(self) -> None:
        self.delete("all")
        fill = self.pressed_bg if self.pressed else (self.hover_bg if self.hover else self.normal_bg)
        outline = self.active_outline if self.pressed or self.hover else self.normal_bg
        self.rounded_rect(1, 1, self.size - 1, self.size - 1, self.radius, fill=fill, outline=outline)
        self.create_image(self.size // 2, self.size // 2, image=self.image)
        if self.focus_get() == self:
            self.create_rectangle(2, 2, self.size - 2, self.size - 2, outline=UI_THEME["focus_ring"], width=2, dash=(3, 2))

    def rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, *, fill: str, outline: str) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline)

    _draw = redraw


class MiniToolButton(InteractiveButton):
    def __init__(
        self,
        parent: tk.Widget,
        command,
        *,
        image: tk.PhotoImage | None = None,
        active_image: tk.PhotoImage | None = None,
        fallback_icon: str = "attachment",
        size: int = 30,
        background: str = "#ffffff",
    ) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            background=background,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.image = image
        self.active_image = active_image or image
        self.fallback_icon = fallback_icon
        self.command = command
        self.size = size
        self.background = background
        self.active = False
        self.hover = False
        self.pressed = False
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<space>", self.on_keyboard)
        self.bind("<Return>", self.on_keyboard)
        self.bind("<FocusIn>", lambda _event: self.redraw())
        self.bind("<FocusOut>", lambda _event: self.redraw())
        self.redraw()

    def configure(self, cnf=None, **kwargs):  # type: ignore[override]
        if cnf:
            kwargs.update(cnf)
        state = kwargs.get("state")
        result = super().configure(**kwargs)
        if state is not None:
            super().configure(cursor="hand2" if state != "disabled" else "arrow")
            self.redraw()
        return result

    config = configure

    def set_active(self, value: bool) -> None:
        self.active = bool(value)
        self.redraw()

    def on_enter(self, _event: tk.Event | None = None) -> None:
        self.hover = True
        self.redraw()

    def on_leave(self, _event: tk.Event | None = None) -> None:
        self.hover = False
        self.pressed = False
        self.redraw()

    def on_press(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = True
        self.redraw()

    def on_click(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = False
        self.redraw()
        if self.command:
            self.command()

    def on_keyboard(self, _event: tk.Event | None = None) -> str:
        self.on_click()
        return "break"

    def redraw(self) -> None:
        self.delete("all")
        disabled = str(self.cget("state")) == "disabled"
        active_visual = (self.active or self.pressed) and not disabled
        bg = "#e8f0f8" if active_visual else ("#f6f8fb" if self.hover else self.background)
        outline = "#a8bed6" if active_visual else ("#c7d2de" if self.hover else self.background)
        icon = "#9aa5b1" if disabled else ("#4f78a8" if active_visual else "#384655")
        self.create_rectangle(0, 0, self.size, self.size, fill=self.background, outline="")
        self.rounded_rect(1, 1, self.size - 1, self.size - 1, 8, fill=bg, outline=outline)
        image = self.active_image if active_visual else self.image
        if image:
            self.create_image(self.size // 2, self.size // 2, image=image)
        elif self.fallback_icon == "microphone":
            self.draw_microphone(icon)
        elif self.fallback_icon == "folder":
            self.draw_folder(icon)
        else:
            self.draw_attachment(icon)
        if self.focus_get() == self:
            self.create_rectangle(2, 2, self.size - 2, self.size - 2, outline=UI_THEME["focus_ring"], width=2, dash=(3, 2))

    def draw_microphone(self, color: str) -> None:
        cx = self.size // 2
        self.create_oval(cx - 5, 6, cx + 5, 18, outline=color, width=2)
        self.create_line(cx - 9, 15, cx - 9, 17, cx - 6, 21, cx, 23, cx + 6, 21, cx + 9, 17, cx + 9, 15, fill=color, width=2, smooth=True)
        self.create_line(cx, 23, cx, 26, fill=color, width=2)
        self.create_line(cx - 5, 26, cx + 5, 26, fill=color, width=2)

    def draw_attachment(self, color: str) -> None:
        self.create_arc(9, 6, 23, 24, start=215, extent=290, outline=color, width=2, style="arc")
        self.create_arc(12, 9, 20, 20, start=215, extent=290, outline=color, width=2, style="arc")
        self.create_line(13, 21, 22, 12, fill=color, width=2)

    def draw_folder(self, color: str) -> None:
        self.create_line(7, 11, 12, 11, 14, 8, 21, 8, 23, 11, 25, 11, fill=color, width=2)
        self.create_rectangle(6, 11, 24, 23, outline=color, width=2)

    def rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, *, fill: str, outline: str) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline)

    _draw = redraw


class WebSearchToggleButton(InteractiveButton):
    def __init__(
        self,
        parent: tk.Widget,
        command,
        *,
        image: tk.PhotoImage | None = None,
        width: int = 46,
        height: int = 30,
        background: str = "#ffffff",
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            background=background,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.command = command
        self.image = image
        self.width_value = width
        self.height_value = height
        self.active = False
        self.hover = False
        self.pressed = False
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<space>", self.on_keyboard)
        self.bind("<Return>", self.on_keyboard)
        self.bind("<FocusIn>", lambda _event: self.redraw())
        self.bind("<FocusOut>", lambda _event: self.redraw())
        self.redraw()

    def set_active(self, value: bool) -> None:
        self.active = bool(value)
        self.redraw()

    def on_enter(self, _event: tk.Event | None = None) -> None:
        self.hover = True
        self.redraw()

    def on_leave(self, _event: tk.Event | None = None) -> None:
        self.hover = False
        self.pressed = False
        self.redraw()

    def on_press(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = True
        self.redraw()

    def on_click(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = False
        self.redraw()
        if self.command:
            self.command()

    def on_keyboard(self, _event: tk.Event | None = None) -> str:
        self.on_click()
        return "break"

    def redraw(self) -> None:
        self.delete("all")
        width = self.width_value
        height = self.height_value
        bg = "#dce8ff" if self.pressed else ("#e8f0fe" if self.active else ("#f7f9fc" if self.hover else "#ffffff"))
        outline = "#7aa2ff" if self.pressed else ("#8fb4ff" if self.active else ("#c9d2dc" if self.hover else "#d8dde4"))
        icon = "#1a73e8" if self.active else "#384655"
        self.create_rectangle(0, 0, width, height, fill="#ffffff", outline="")
        self.rounded_rect(1, 1, width - 1, height - 1, height // 2 - 1, fill=bg, outline=outline)
        if self.image:
            self.create_image(width // 2, height // 2, image=self.image)
        else:
            cx = width // 2
            cy = height // 2
            radius = min(width, height) // 2 - 8
            self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=icon, width=1)
            self.create_arc(cx - radius + 3, cy - radius, cx + radius - 3, cy + radius, start=90, extent=180, outline=icon, width=1)
            self.create_arc(cx - radius + 3, cy - radius, cx + radius - 3, cy + radius, start=270, extent=180, outline=icon, width=1)
            self.create_line(cx - radius, cy, cx + radius, cy, fill=icon, width=1)
            self.create_line(cx, cy - radius, cx, cy + radius, fill=icon, width=1)
        if self.active:
            self.create_oval(width - 10, 7, width - 5, 12, fill="#34a853", outline="")
        if self.focus_get() == self:
            self.create_rectangle(2, 2, width - 2, height - 2, outline=UI_THEME["focus_ring"], width=2, dash=(3, 2))

    def rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, *, fill: str, outline: str) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline)

    _draw = redraw
