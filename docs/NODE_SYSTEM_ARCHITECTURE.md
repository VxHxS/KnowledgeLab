# Node System Architecture

Audit date: 2026-06-25.

## Current Reality

KnowledgeLab does not yet have a formal node runtime with a single `Node` interface, node registry, graph executor, and persisted node state. The current system is a set of workflows and helper modules that already behave like nodes in practice:

- intent/scope routing;
- input/material analysis;
- vault capture;
- queueing;
- background workers;
- LightRAG retrieval;
- runtime context building;
- LM Studio answer generation;
- review/formatting of reports.

The next architecture step should be to describe these pieces as nodes before rewriting them as nodes.

## What A Node Means In KnowledgeLab

A node is a local processing unit with:

- `id`: stable identifier;
- `name`: human-readable name;
- `purpose`: why this node exists;
- `input`: message, file, URL, route, queue item, or prior node output;
- `local_context`: instructions, settings, state, and allowed tools for this node;
- `output`: structured result for the next node or final UI;
- `errors`: recoverable failures that should be visible, not swallowed;
- `side_effects`: file writes, queue writes, process starts, or network calls.

## Current Workflow As Nodes

1. Intent Parser Node

Current code:

- `scripts/knowledgelab/routing/intent.py`
- `KnowledgeChatApp.selected_route()`

Responsibility:

- decide whether a message is normal chat, save intent, knowledge lookup, LightRAG help, finished-project lookup, web/game/general topic, or project request.

2. Input Analyzer Node

Current code:

- `scripts/knowledgelab/vault/capture_workflow.py`
- `scripts/knowledgelab/vault/capture.py`
- `scripts/knowledgelab/utils/urls.py`
- `scripts/knowledgelab/utils/paths.py`

Responsibility:

- classify pasted text, URLs, files, folders, images, videos, archives, GitHub repos, and book photos.

3. Knowledge Retriever Node

Current code:

- `scripts/query-vault-scope-lmstudio.ps1`
- `scripts/query-vault-lmstudio.py`
- `scripts/vault_sources.py`
- `scripts/lightrag_query_audit.py`

Responsibility:

- choose LightRAG storage, retrieve local indexed context, audit whether context is usable, and fall back to plain LM Studio when needed.

4. Node Context Builder

Current code:

- `scripts/knowledgelab/llm/runtime_context.py`
- `KnowledgeChatApp.runtime_context_prompt()`

Responsibility:

- build an authoritative runtime context block with app root, vault, current route, model settings, loaded models, LightRAG index readiness, DnD backend, material queue summary, book discovery state, and project server state.

5. LLM Response Node

Current code:

- `scripts/knowledgelab/llm/lmstudio.py`
- `scripts/lmstudio_common.py`
- `scripts/query-vault-lmstudio.py`

Responsibility:

- call LM Studio through the local OpenAI-compatible API and normalize `content` vs `reasoning_content`.

6. File Processing Node

Current code:

- `scripts/knowledgelab/vault/capture_workflow.py`
- `scripts/knowledgelab/material/queue.py`
- `scripts/knowledgelab/material/workers.py`

Responsibility:

- save lightweight Markdown intake notes, queue heavy processing, and launch background reindexing.

7. Image Analysis Node

Current code:

- `scripts/knowledgelab/vision/book_discovery.py`
- `scripts/knowledgelab/material/workers.py`

Responsibility:

- detect books or unreadable regions, call local vision models when configured, enrich book metadata, and write book notes.

8. Video Analysis Node

Current code:

- `scripts/knowledgelab/material/video.py`

Responsibility:

- sample frames with FFmpeg, ask a vision model to extract screen/code text, write video analysis notes, and leave ASR as pending until implemented.

9. Project Request Node

Current code:

- `scripts/knowledgelab/tasks/project_actions.py`
- `scripts/knowledgelab/ui/project_panel.py`
- `KnowledgeChatApp.finished_project_route()`
- `KnowledgeChatApp.custom_project_route()`

Responsibility:

- turn project/folder/GitHub intake into reference notes and optional isolated runtime workspaces under `tmp/project-runtime`.

10. Memory Writer Node

Current code:

- `scripts/knowledgelab/vault/capture.py`
- `scripts/knowledgelab/vault/capture_workflow.py`

Responsibility:

- write Markdown notes with frontmatter into the Obsidian vault and avoid duplicate source notes when possible.

11. Review Node

Current code:

- report formatters in `vision/book_discovery.py`;
- warnings through `::knowledge-warning`;
- chat rendering in `KnowledgeChatApp`.

Responsibility:

- show compact user-facing reports and surface missing indexes, queue state, reasoning-only model responses, or pending processing.

## Data Passed Between Nodes

The current informal data shape is:

- `KnowledgeRoute`: context, scope, project, layer, project title, section.
- `MaterialRoutingReport`: source name, kind, topic, vault note, created-topic flag.
- `BookDiscoveryReport`: parent note, added books, clarification needs, unresolved books.
- `VideoAnalysisReport`: parent note, analysis note, source, transcript/frame status, counts, warning.
- JSONL queue items under `tmp/material-processing-queue.jsonl`.

These should become the first stable node payloads before adding a larger graph executor.

## Node Context Vs LightRAG Context

Node context is internal operational context:

- role of the node;
- current route;
- settings;
- previous node output;
- allowed actions;
- input/output contract.

LightRAG context is external knowledge context retrieved from indexed Markdown. It should not replace node context. A node can decide whether LightRAG is needed; it should not become LightRAG itself.

## Minimal Future Node Interface

Before a full rewrite, a minimal Python protocol could look like:

```python
class KnowledgeNode(Protocol):
    id: str
    name: str
    purpose: str

    def run(self, payload: dict, context: dict) -> dict:
        ...
```

Recommended payload keys:

- `route`
- `user_input`
- `source_path`
- `source_url`
- `vault_note`
- `material_kind`
- `topic`
- `llm_required`
- `retrieval_required`
- `warnings`
- `result`

## Expansion Path

1. Document current workflows as nodes.
2. Add node-level logging around existing workflow functions.
3. Standardize node input/output dictionaries.
4. Only then introduce a registry/executor.
5. Keep the desktop UI as an orchestrator, not as the node implementation itself.

