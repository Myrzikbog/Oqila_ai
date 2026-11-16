"""
legal_faq.py — the FAQ of the legal tab. The texts live in services/legal_faq.json with {placeholders} for every
number that is a legal fact ({brv}, {ecp_person}, {threshold_brv}, ...); they are filled from the knowledge base,
so a changed rate is changed in one place (services/legal_kb.json) and the FAQ, the AI and the calculator agree.
"""
from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from services.legal_kb import kb

FAQ_PATH = Path(__file__).with_name("legal_faq.json")


@lru_cache(maxsize=1)
def _raw() -> Dict[str, List[Dict[str, Any]]]:
    return json.loads(FAQ_PATH.read_text(encoding="utf-8"))


def _fill(value: Any) -> Any:
    if isinstance(value, str):
        return kb.fill(value)
    if isinstance(value, list):
        return [_fill(v) for v in value]
    if isinstance(value, dict):
        return {k: _fill(v) for k, v in value.items()}
    return value


def get_faq(lang: str = "ru") -> List[Dict[str, Any]]:
    """FAQ items for a language, with the numbers filled in from the knowledge base."""
    return _fill(deepcopy(_raw()["uz" if lang == "uz" else "ru"]))
