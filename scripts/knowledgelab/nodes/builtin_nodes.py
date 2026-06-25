"""Built-in nodes wrapping existing KnowledgeLab workflows."""
from __future__ import annotations

from typing import Any

from knowledgelab.nodes.base import BaseNode


class IntentParserNode(BaseNode):
    id = "intent_parser"
    name = "Intent Parser"
    purpose = "Classify user input as chat, save, knowledge lookup, or goal intent."

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("user_input", ""))
        from knowledgelab.routing.intent import classify_intent
        intent = classify_intent(text)
        self.emit_result(payload, "intent", intent)
        return payload


class FileCaptureNode(BaseNode):
    id = "file_capture"
    name = "File Capture"
    purpose = "Save files, folders, URLs, and attachments as vault capture notes."

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        source_path = str(payload.get("source_path", ""))
        source_url = str(payload.get("source_url", ""))
        route = payload.get("route")
        if not source_path and not source_url:
            self.emit_warning(payload, "No source_path or source_url provided.")
            return payload
        self.emit_result(payload, "status", "delegated_to_capture_workflow")
        return payload


class ProjectActionNode(BaseNode):
    id = "project_action"
    name = "Project Action"
    purpose = "Create project actions from folder/GitHub intake and manage runtime workspaces."

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        source_type = str(payload.get("source_type", ""))
        source_path = str(payload.get("source_path", ""))
        source_url = str(payload.get("source_url", ""))
        route = payload.get("route")
        title = str(payload.get("title", ""))
        if not source_type:
            self.emit_warning(payload, "source_type is required.")
            return payload
        self.emit_result(payload, "status", "delegated_to_project_actions")
        return payload


class LaunchOnServerNode(BaseNode):
    id = "launch_on_server"
    name = "Launch On Server"
    purpose = "Start a local dev server for an imported project."

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        action_id = str(payload.get("action_id", ""))
        if not action_id:
            self.emit_warning(payload, "action_id is required to launch on server.")
            return payload
        app = context.get("app")
        if app is None:
            self.emit_warning(payload, "app context is required.")
            return payload
        self.emit_result(payload, "action_id", action_id)
        self.emit_result(payload, "status", "server_launch_queued")
        return payload


BUILTIN_NODES = [
    IntentParserNode,
    FileCaptureNode,
    ProjectActionNode,
    LaunchOnServerNode,
]
