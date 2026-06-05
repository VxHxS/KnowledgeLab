LightRAG launchers

Double-click CMD files from this folder:

01 Check LightRAG.cmd
Runs a full test: Obsidian Markdown -> LightRAG -> LM Studio -> answer.
The terminal explains the steps in Russian.

02 Ask Obsidian Vault.cmd
Asks for a question and sends it to the local Obsidian/RAG system.

03 Stop AI.cmd
Unloads models and stops the LM Studio server.

04 Open Obsidian Vault.cmd
Opens the test Obsidian vault folder and shows Russian instructions.

05 Import Telegram Export.cmd
Imports Telegram Desktop result.json into Obsidian Markdown with scope metadata.

06 Ask General Knowledge.cmd
Asks only the general knowledge scope.

07 Ask My Game.cmd
Asks only the game/project scope.

08 Reindex LightRAG Scope.cmd
Rebuilds a LightRAG index for all, general, or game scope.


Path behavior:
Launchers use Resolve-LightRAG-Paths.ps1. The resolver first checks whether scripts, LightRAG, and Obsidian-Test-Vault live inside or above this LightRAG-Control folder. If not, it uses the canonical Obsidian/LightRAG project root under Documents\Freelance\AI-Knowledge-Lab.

Obsidian note:
If you see notes like "Без названия..." instead of 00 Inbox / 10 Programming / 20 Music, you are probably in another vault or in Graph/Quick Switcher, not in the file explorer pane.
Use 04 Open Obsidian Vault.cmd to open the exact folder.