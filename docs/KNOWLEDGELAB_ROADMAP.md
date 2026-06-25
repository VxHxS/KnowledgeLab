# KnowledgeLab Roadmap

Audit date: 2026-06-25.

## Stage 1: Stabilize After Mimo

Status: in progress.

Goals:

- keep the current UI working;
- avoid another large rewrite;
- document actual architecture;
- fix obvious breakages only;
- make tests runnable from a documented environment.

Completed during this audit:

- restored `scripts/main.py --self-test`;
- fixed silent `launch_reindex()` failure;
- fixed custom vault topic creation;
- standardized LM Studio default URL to `http://127.0.0.1:1234/v1`;
- added/updated audit documentation.

Next:

- decide what to do with `.mimocode/`;
- decide what to do with generated vault test notes;
- install or document a pytest-capable environment;
- run full tests;
- compare staging with the active installed copy at `C:\MyFiles\KnowledgeLab`.

## Stage 2: Strengthen The Node Model

Goals:

- document current workflows as nodes;
- standardize node input/output payloads;
- add node-level logging;
- make node context explicit and separate from LightRAG retrieval context.

Do not immediately build a visual node editor. First define contracts around the existing workflows.

## Stage 3: Harden Vault And Material Intake

Goals:

- ensure every vault write respects selected `vault_path`;
- keep heavy files reference-only by default;
- make queue status transitions visible;
- improve duplicate-source detection;
- add safe handling for archives and large folders;
- keep deletion/move operations explicit and rare.

Priority checks:

- file/folder capture;
- GitHub repository intake;
- book photo and bookshelf intake;
- video intake;
- finished project reference cards.

## Stage 4: Improve LightRAG Operations

Goals:

- make index readiness visible per scope;
- show current storage path in diagnostics;
- add parity tests for PowerShell/Python storage naming;
- reduce surprise auto-indexing;
- support incremental indexing if feasible.

The first answer may still fall back to plain LM Studio while an index builds in the background, but the UI should always say that clearly.

## Stage 5: Improve Local Model Diagnostics

Goals:

- show LM Studio endpoint, loaded models, expected models, and vision availability;
- make reasoning-only model responses actionable;
- separate plain chat, retrieval chat, and vision tasks clearly;
- keep all external API behavior opt-in.

## Stage 6: Project Assistance Layer

Goals:

- keep finished projects as reference-only notes;
- create isolated runtime workspaces under `tmp/project-runtime` only when requested;
- support project analysis/specification workflows;
- prepare clean handoff data for a separate app builder.

KnowledgeLab should provide context, analysis, and specifications. The builder should remain a separate application.

## Stage 7: Future Builder Integration

Goals:

- expose KnowledgeLab as a local knowledge/backend service;
- provide structured context packs to the builder;
- let the builder request relevant notes, project examples, constraints, and safety rules;
- avoid turning KnowledgeLab into the builder itself.

## Near-Term Decision List

- Should `.mimocode/` be ignored, committed, or archived outside the repo?
- Should the active installed copy be synced from staging now?
- Should `C:\MyFiles\KnowledgeLab` become a proper git clone?
- Which Python environment should be the official test environment?
- Should online catalog lookup for books remain enabled by default?
- Should web search be off by default unless explicitly toggled?

