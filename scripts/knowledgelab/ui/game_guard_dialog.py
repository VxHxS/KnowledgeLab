"""Game Guard warning dialog for GPU conflict detection."""
from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING

from knowledgelab.llm.game_guard import collect_gpu_snapshot, is_gpu_snapshot_heavy

if TYPE_CHECKING:
    from main import KnowledgeChatApp


class GameGuardDialog:
    """Manages GPU monitoring and warning display."""

    def __init__(self, app: KnowledgeChatApp) -> None:
        self.app = app
        self.warning_until: float = 0

    def schedule_probe(self) -> None:
        """Schedule GPU probe after chat opens."""
        if not bool(self.app.settings.get("game_guard_enabled", True)):
            return
        delay = int(self.app.settings.get("game_guard_delay_seconds", 5) or 5)
        self.app.root.after(delay * 1000, self.start_probe)

    def start_probe(self) -> None:
        """Start background GPU probe."""
        if not bool(self.app.settings.get("game_guard_enabled", True)):
            return
        if time.time() < self.warning_until:
            return
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self) -> None:
        """Background worker for GPU snapshot."""
        first = self.collect_snapshot()
        if not self.is_heavy(first):
            return
        time.sleep(2)
        second = self.collect_snapshot()
        if not self.is_heavy(second):
            return
        self.app.root.after(0, self.show_warning, second)

    def collect_snapshot(self) -> dict:
        """Collect GPU snapshot."""
        return collect_gpu_snapshot()

    def is_heavy(self, snapshot: dict) -> bool:
        """Check if GPU load is heavy."""
        return is_gpu_snapshot_heavy(snapshot)

    def show_warning(self, snapshot: dict) -> None:
        """Show GPU conflict warning if appropriate."""
        if time.time() < self.warning_until:
            return
        self.warning_until = time.time() + 30 * 60
        processes = snapshot.get("processes") or []
        if isinstance(processes, dict):
            processes = [processes]
        heavy = sorted(processes, key=lambda item: float(item.get("gpu") or 0), reverse=True)[:5]
        heavy_text = ", ".join(f"{item.get('name')}#{item.get('pid')} ({item.get('gpu')}%)" for item in heavy) or "процессы не определены"
        lab = snapshot.get("lab") or []
        if isinstance(lab, dict):
            lab = [lab]
        lab_text = ", ".join(f"{item.get('name')}#{item.get('pid')}" for item in lab) or "LM Studio/lms/python не найдены"
        total = snapshot.get("gpu_total") or 0
        memory = snapshot.get("memory") or "VRAM неизвестна"
        warning = (
            f"Game Guard: заметна GPU-нагрузка ({total}%, VRAM {memory}). "
            f"Тяжелые процессы: {heavy_text}. Со стороны KnowledgeLab: {lab_text}. "
            "Если открыта игра, рекомендуется закрыть чат или остановить LM Studio через LightRAG-Control, чтобы избежать конфликтов."
        )
        self.app.append_warning_message(warning, persist=True)
