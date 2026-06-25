"""Goal-oriented nodes — high-level operations triggered by user intent."""
from __future__ import annotations

from typing import Any

from knowledgelab.nodes.base import BaseNode


class MakeWebsiteNode(BaseNode):
    id = "make_website"
    name = "Make Website"
    purpose = "Coordinate creating a website from scratch or a template."

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        description = str(payload.get("user_input", ""))
        template = str(payload.get("template", ""))
        project_path = str(payload.get("project_path", ""))

        steps: list[str] = []
        if project_path:
            steps.append(f"Using existing project at: {project_path}")
        elif template:
            steps.append(f"Creating from template: {template}")
        else:
            steps.append("Creating new website project")

        steps.append("Detecting project stack")
        steps.append("Installing dependencies if needed")
        steps.append("Starting local dev server")

        self.emit_result(payload, "steps", steps)
        self.emit_result(payload, "goal", "make_website")
        return payload


class RefactorProjectNode(BaseNode):
    id = "refactor_project"
    name = "Refactor Project"
    purpose = "Analyze and refactor an existing project codebase."

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        project_path = str(payload.get("project_path", ""))
        scope = str(payload.get("refactor_scope", "full"))

        steps: list[str] = []
        if not project_path:
            self.emit_warning(payload, "project_path is required for refactoring.")
            return payload

        steps.append(f"Analyzing project at: {project_path}")
        steps.append(f"Refactor scope: {scope}")
        steps.append("Generating refactoring suggestions via LLM")
        steps.append("Applying changes")

        self.emit_result(payload, "steps", steps)
        self.emit_result(payload, "goal", "refactor_project")
        return payload


class DeployProjectNode(BaseNode):
    id = "deploy_project"
    name = "Deploy Project"
    purpose = "Build and deploy a project for production or sharing."

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        project_path = str(payload.get("project_path", ""))
        target = str(payload.get("deploy_target", "local"))

        steps: list[str] = []
        if not project_path:
            self.emit_warning(payload, "project_path is required for deployment.")
            return payload

        steps.append(f"Building project at: {project_path}")
        steps.append(f"Deploy target: {target}")

        self.emit_result(payload, "steps", steps)
        self.emit_result(payload, "goal", "deploy_project")
        return payload


class AnalyzeProjectNode(BaseNode):
    id = "analyze_project"
    name = "Analyze Project"
    purpose = "Analyze a project's structure, dependencies, and code quality."

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        project_path = str(payload.get("project_path", ""))

        if not project_path:
            self.emit_warning(payload, "project_path is required for analysis.")
            return payload

        steps = [
            f"Scanning project at: {project_path}",
            "Detecting framework and dependencies",
            "Analyzing code structure",
            "Generating summary report",
        ]

        self.emit_result(payload, "steps", steps)
        self.emit_result(payload, "goal", "analyze_project")
        return payload


class CodeReviewNode(BaseNode):
    id = "code_review"
    name = "Code Review"
    purpose = "Analyze code quality: naming, smells, modularity, using Obsidian context."

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        code = str(payload.get("code", ""))
        language = str(payload.get("language", "python"))
        project_path = str(payload.get("project_path", ""))

        if not code and not project_path:
            self.emit_warning(payload, "Provide code text or project_path for review.")
            return payload

        if project_path and not code:
            code = self._read_project_files(project_path)

        obsidian_context = self._get_obsidian_context(context)

        review_prompt = self._build_review_prompt(code, language, obsidian_context)

        app = context.get("app")
        if app:
            self.emit_result(payload, "review_prompt", review_prompt)
            self.emit_result(payload, "status", "review_prompt_ready")
        else:
            self.emit_result(payload, "status", "no_app_context")

        self.emit_result(payload, "goal", "code_review")
        return payload

    def _read_project_files(self, project_path: str) -> str:
        from pathlib import Path
        path = Path(project_path)
        if not path.exists():
            return ""
        extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".cs", ".cpp", ".h"}
        files_content: list[str] = []
        for ext in extensions:
            for file in path.rglob(f"*{ext}"):
                if "node_modules" in str(file) or ".git" in str(file):
                    continue
                try:
                    content = file.read_text(encoding="utf-8", errors="replace")[:3000]
                    rel = file.relative_to(path)
                    files_content.append(f"--- {rel} ---\n{content}")
                except Exception:
                    continue
                if len(files_content) >= 10:
                    break
            if len(files_content) >= 10:
                break
        return "\n\n".join(files_content)

    def _get_obsidian_context(self, context: dict[str, Any]) -> str:
        app = context.get("app")
        if not app:
            return ""
        try:
            vault_dir = app.vault_dir()
            from pathlib import Path
            notes: list[str] = []
            for md in (vault_dir / "10 Programming").rglob("*.md") if (vault_dir / "10 Programming").exists() else []:
                try:
                    text = md.read_text(encoding="utf-8-sig", errors="replace")[:1500]
                    notes.append(text)
                except Exception:
                    continue
                if len(notes) >= 3:
                    break
            if notes:
                return "Relevant knowledge from Obsidian vault:\n" + "\n---\n".join(notes)
        except Exception:
            pass
        return ""

    def _build_review_prompt(self, code: str, language: str, obsidian_context: str) -> str:
        parts = [
            "Проанализируй качество кода и дай конкретные рекомендации.",
            "",
            "Проверь:",
            "1. осмысленные названия переменных/функций/классов",
            "2. размер интерфесов (слишком много параметров? слишком длинные функции?)",
            "3. 'плохие запахи' в коде (дублирование, длинные методы, глубокая вложенность, магические числа)",
            "4. разбивка на модули (если файл > 300 строк или содержит несколько ответственностей)",
            "5. следование принципам SOLID и DRY",
            "",
            f"Язык: {language}",
            "",
            "Код:",
            f"```{language}",
            code[:8000],
            "```",
        ]
        if obsidian_context:
            parts.extend(["", obsidian_context])
        parts.extend([
            "",
            "Формат ответа:",
            "### Проблемы",
            "- [критично/важно/мелочь] Описание проблемы → Файл:строка",
            "",
            "### Рекомендации",
            "- Конкретное исправление с примером кода",
            "",
            "### Итог",
            "- Общая оценка (1-10) и главные шаги для улучшения",
        ])
        return "\n".join(parts)


GOAL_NODES = [
    MakeWebsiteNode,
    RefactorProjectNode,
    DeployProjectNode,
    AnalyzeProjectNode,
    CodeReviewNode,
]
