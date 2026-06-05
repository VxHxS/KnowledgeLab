import asyncio
import os
from pathlib import Path

from lightrag.constants import DEFAULT_ENTITY_TYPES, DEFAULT_SUMMARY_LANGUAGE
from lightrag.prompt import PROMPTS
from openai import AsyncOpenAI


ROOT = Path(__file__).resolve().parents[1]
NOTE_PATH = ROOT / "Obsidian-Test-Vault" / "10 Programming" / "Unity Workflow Notes.md"
BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LMSTUDIO_LLM_MODEL", "qwen/qwen3-14b")


async def main() -> None:
    text = "# Source: 10 Programming/Unity Workflow Notes.md\n\n"
    text += NOTE_PATH.read_text(encoding="utf-8")

    example_context = {
        "tuple_delimiter": PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        "completion_delimiter": PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
        "entity_types": ", ".join(DEFAULT_ENTITY_TYPES),
        "language": DEFAULT_SUMMARY_LANGUAGE,
    }
    examples = "\n".join(PROMPTS["entity_extraction_examples"]).format(
        **example_context
    )
    context = {
        "tuple_delimiter": PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        "completion_delimiter": PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
        "entity_types": ",".join(DEFAULT_ENTITY_TYPES),
        "examples": examples,
        "language": DEFAULT_SUMMARY_LANGUAGE,
        "input_text": text,
    }

    client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": PROMPTS["entity_extraction_system_prompt"].format(**context),
            },
            {
                "role": "user",
                "content": PROMPTS["entity_extraction_user_prompt"].format(**context),
            },
        ],
        temperature=0.2,
        max_tokens=512,
        stream=False,
    )
    message = response.choices[0].message
    print("finish_reason:", response.choices[0].finish_reason)
    print("content:", repr(message.content))
    print("reasoning_content:", repr(getattr(message, "reasoning_content", "")))


if __name__ == "__main__":
    asyncio.run(main())
