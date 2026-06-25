from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any


DEFAULT_LOCALE = "ru"


@lru_cache(maxsize=8)
def message_catalog(locale: str = DEFAULT_LOCALE) -> dict[str, Any]:
    resource = resources.files("knowledgelab.resources").joinpath(f"messages.{locale}.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def _lookup(key: str, locale: str = DEFAULT_LOCALE) -> Any:
    current: Any = message_catalog(locale)
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Missing message key: {key}")
        current = current[part]
    return current


def msg(key: str, locale: str = DEFAULT_LOCALE, **kwargs: Any) -> str:
    value = _lookup(key, locale)
    if not isinstance(value, str):
        raise TypeError(f"Message key is not a string: {key}")
    return value.format(**kwargs) if kwargs else value


def msg_list(key: str, locale: str = DEFAULT_LOCALE) -> tuple[str, ...]:
    value = _lookup(key, locale)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"Message key is not a string list: {key}")
    return tuple(value)
