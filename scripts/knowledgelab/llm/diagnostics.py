"""System diagnostics — check LM Studio, Obsidian, LightRAG, Python environment."""

from __future__ import annotations

import os
from pathlib import Path

from knowledgelab.config import ROOT
from knowledgelab.llm.lmstudio import check_lmstudio_ready


def diagnose_system(
    settings: dict,
    lmstudio_base_url: str,
    llm_model_id: str,
    vault_dir: Path,
    is_lightrag_ready: callable,
    find_obsidian_path: callable,
    lmstudio_cli_path: callable,
    route_context_name: str = "",
    route_scope: str = "",
    route_project: str = "",
    route_layer: str = "active",
) -> list[str]:
    warnings: list[str] = []
    if not (ROOT / "LightRAG" / ".venv" / "Scripts" / "python.exe").exists():
        warnings.append("Python environment не найден. Запустите installer или откройте LightRAG-Control для проверки установки.")

    lms = lmstudio_cli_path()
    if not lms:
        warnings.append("LM Studio CLI не найден. Обыный чат может работать через API, но для загрузки/выгрузки моделей откройте LightRAG-Control после установки LM Studio.")
    ok, lm_message, _models = check_lmstudio_ready(lmstudio_base_url, llm_model_id, require_models=False)
    if not ok:
        warnings.append(lm_message)

    if not find_obsidian_path():
        warnings.append("Obsidian не найден автоматически. Нажмите фиолетовую иконку Obsidian, чтобы выбрать Obsidian.exe или открыть официальный сайт.")
    if not vault_dir.exists():
        warnings.append("Obsidian vault path не найден. Откройте Settings и выберите папку vault.")

    if bool(settings.get("use_lightrag", False)) and not is_lightrag_ready(route_scope, route_project, route_layer):
        warnings.append(f"LightRAG был включен, но индекс для {route_context_name} не найден. Я отключил LightRAG, чтобы обычный чат продолжал работать.")
    return warnings
