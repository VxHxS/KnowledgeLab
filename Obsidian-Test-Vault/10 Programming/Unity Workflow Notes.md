# Unity Workflow Notes

## Project structure

Use clear folder boundaries for scripts, scenes, prefabs, materials, audio, and third-party assets. Keep prototype scenes separate from production scenes.

## Programming habits

- Prefer small MonoBehaviour components with explicit responsibilities.
- Keep serialized fields private unless another script must access them.
- Put runtime configuration in ScriptableObjects when values are shared across scenes.
- Profile before optimizing. Confirm whether the bottleneck is CPU, GPU, memory, physics, animation, or asset loading.

## AI assistance targets

Codex is useful for refactoring C# scripts, writing editor utilities, reviewing architecture, generating tests, and explaining unfamiliar Unity APIs.

LightRAG is useful for answering questions over project notes, imported documentation, asset-store manuals, issue logs, and technical decisions.
