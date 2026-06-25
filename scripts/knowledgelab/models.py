"""KnowledgeLab data models — all dataclasses used across the application."""

from __future__ import annotations

from dataclasses import dataclass, field

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
class BookCandidate:
    title: str
    author: str = ""
    isbn: str = ""
    evidence: str = ""
    status: str = "found"
    confidence: float = 0.0
    region: str = ""
    visible_text: str = ""
    visual_guess: str = ""
    guess_reason: str = ""

    @classmethod
    def from_book_dict(cls, book: dict[str, object]) -> "BookCandidate":
        return cls(
            title=str(book.get("title") or ""),
            author=str(book.get("author") or ""),
            isbn=str(book.get("isbn") or ""),
            evidence=str(book.get("evidence") or ""),
            status=str(book.get("status") or "found"),
            confidence=float(book.get("confidence") or 0.0),
            region=str(book.get("region") or ""),
            visible_text=str(book.get("visible_text") or ""),
            visual_guess=str(book.get("visual_guess") or ""),
            guess_reason=str(book.get("guess_reason") or ""),
        )

    def to_book_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "author": self.author,
            "isbn": self.isbn,
            "evidence": self.evidence,
            "status": self.status,
            "confidence": self.confidence,
            "region": self.region,
            "visible_text": self.visible_text,
            "visual_guess": self.visual_guess,
            "guess_reason": self.guess_reason,
        }


@dataclass(frozen=True)
class BookLookupResult:
    status: str
    reason: str = ""
    book: dict[str, object] = field(default_factory=dict)
    candidates: list[dict[str, object]] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BookDownloadResult:
    status: str
    reason: str = ""
    source_name: str = ""
    url: str = ""
    local_file_rel_path: str = ""
    file_name: str = ""
    file_format: str = ""
    size_bytes: int = 0


@dataclass(frozen=True)
class BookPipelineResult:
    status: str
    detection_result: dict[str, list[dict[str, object]]]
    created_notes: list[str]
    report: BookDiscoveryReport
    parent_note_updated: bool = False
    error: str = ""


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
