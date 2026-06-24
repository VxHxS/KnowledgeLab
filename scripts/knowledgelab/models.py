"""KnowledgeLab data models — all dataclasses used across the application."""

from __future__ import annotations

from dataclasses import dataclass

from knowledgelab.config import LAYER_ACTIVE, LAYER_FINISHED_PROJECTS


@dataclass(frozen=True)
class KnowledgeRoute:
    context_name: str
    scope: str
    project: str = ""
    layer: str = LAYER_ACTIVE
    project_title: str = ""
    project_section: str = ""

    @property
    def is_finished_projects(self) -> bool:
        return self.layer == LAYER_FINISHED_PROJECTS

    def for_finished_index(self) -> KnowledgeRoute:
        if not self.is_finished_projects:
            return self
        return KnowledgeRoute(
            context_name=self.context_name,
            scope="all",
            project="",
            layer=self.layer,
            project_title=self.project_title,
            project_section=self.project_section,
        )


@dataclass(frozen=True)
class ProjectGuess:
    title: str
    section: str
    scope: str
    confidence: float


@dataclass(frozen=True)
class MaterialRoutingReport:
    source_name: str
    kind: str
    topic: str
    rel_path: str
    created_topic: bool = False


@dataclass(frozen=True)
class BookDiscoveryReport:
    parent_note: str
    added: list[dict[str, object]]
    needs_clarification: list[dict[str, object]]
    not_found: list[dict[str, object]]


@dataclass(frozen=True)
class ManualBookEntry:
    title: str
    author: str = ""
    section: str = ""
    position: str = ""
    user_evidence: str = ""


@dataclass(frozen=True)
class VideoAnalysisReport:
    parent_note: str
    analysis_note: str
    source: str
    transcript_status: str
    frame_analysis_status: str
    frame_count: int = 0
    code_snippet_count: int = 0
    warning: str = ""


@dataclass
class BackgroundTaskRecord:
    task_id: str
    kind: str
    label: str
    status: str
    source_path: str = ""
    rel_path: str = ""
    detail: str = ""
    result: str = ""
    started_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ReferenceLink:
    url: str
    title: str
    context: str
    role: str


@dataclass(frozen=True)
class CodePenSnapshot:
    status: str
    title: str
    author: str
    description: str
    html_code: str = ""
    css_code: str = ""
    js_code: str = ""
    reason: str = ""
