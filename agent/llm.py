# -*- coding: utf-8 -*-
"""Единая точка доступа к локальной модели (Ollama).

Зачем отдельный модуль: `chat_service.py` импортировал модель и разбор фраз из
`web_app.py`, которого там не было — из-за этого падал импорт `base_agent`, а с
ним координатор и все специализированные агенты. Веб-сервер не должен быть
библиотекой модели: и он, и сервис диалога берут её отсюда.

Правила:
- модель и таймаут берутся из `config.json`, а не зашиты в код;
- недоступная модель возвращает None, а не текст-заглушку, похожий на ответ;
- разбор фразы (`route`) — подсказка для маршрутизации, а не факт о данных.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
DEFAULT_MODEL = "qwen2.5:1.5b"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
TIMEOUT = 60


def _load_model() -> str:
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return str(cfg.get("model") or DEFAULT_MODEL)
    except (OSError, json.JSONDecodeError, ValueError):
        return DEFAULT_MODEL


def _load_timeout() -> int:
    """Таймаут генерации. 60 с мало: крупная модель на CPU отвечает дольше,
    и ответ молча превращался в «модель недоступна»."""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return int(cfg.get("llm_timeout_sec") or 180)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return 180


OLLAMA_MODEL = _load_model()
TIMEOUT = _load_timeout()


# ---------------------------------------------------------------- демо-данные
# Списки нужны только для распознавания названий во фразе; факт наличия
# контрагента или товара проверяет 1С, а не эти значения.
FULL_PARTIES = (
    "ООО Альфа", "ООО Бета", "ИП Гамма", "ООО Дельта",
    "ООО Ромашка", "ООО Ветка", "ИП Иванов",
)
FULL_ITEMS = (
    "Ноутбук ASUS", 'Монитор 27"', "Клавиатура механическая",
    "Бумага А4", "Картриджи", "Тонер",
    "Принтер HP", "Сканер", "МФУ",
    "Товар А", "Товар Б", "Услуга монтажа",
)

# Живые запросы вместо демо-шаблонов, которые смотрят в отсутствующие регистры.
# ВНИМАНИЕ: имена объектов проверяются на этапе A; неверное имя вернёт
# execution_error от моста, а не выдуманные данные.
LIVE_SALES_Q = ("ВЫБРАТЬ ПЕРВЫЕ 50 Наименование, Артикул "
                "ИЗ Справочник.Номенклатура")
LIVE_PARTNERS_Q = "ВЫБРАТЬ ПЕРВЫЕ 50 Наименование, ИНН, КПП ИЗ Справочник.Контрагенты"
LIVE_DOCS_Q = ("ВЫБРАТЬ ПЕРВЫЕ 50 Номер, Дата ИЗ Документ.ЗаказПокупателя "
               "ГДЕ НЕ ПометкаУдаления")


# ---------------------------------------------------------------- вызовы модели
def generate(prompt: str, system: str = "", model: str | None = None) -> str | None:
    """Один ответ модели. None — если модель недоступна."""
    payload = {"model": model or OLLAMA_MODEL, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None
    text = (data.get("response") or "").strip()
    return text or None


def chat(messages: list, system: str = "", model: str | None = None) -> str | None:
    """Ответ модели в режиме диалога. None — если модель недоступна."""
    full = list(messages)
    if system:
        full = [{"role": "system", "content": system}] + full
    payload = {"model": model or OLLAMA_MODEL, "messages": full, "stream": False}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_CHAT_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None
    text = ((data.get("message") or {}).get("content") or "").strip()
    return text or None


# ---------------------------------------------------------------- разбор фразы
ROUTE_SYSTEM = (
    "Ты — маршрутизатор запросов к 1С. Верни ТОЛЬКО JSON без пояснений.\n"
    'Схема: {"intent": "check|stock|debt|orders|party|create|query|smalltalk", '
    '"query": "запрос на встроенном языке 1С или пустая строка", '
    '"counterparty": "", "item": "", "qty": 0, "price": 0}\n'
    "Правила: только чтение (ВЫБРАТЬ), без «;», без параметров «&»; "
    "если запрос в 1С не нужен — intent=smalltalk."
)


def route(phrase: str) -> dict | None:
    """Намерение по фразе. None — модель недоступна или ответ не разобран."""
    text = generate(phrase[:500], ROUTE_SYSTEM)
    if not text:
        return None
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------- документы
def find_name(text: str, names) -> str | None:
    """Найти название из списка в тексте. Возвращает написание из списка."""
    t = (text or "").lower().replace("ё", "е")
    if not t:
        return None
    for name in names:
        if name.lower().replace("ё", "е") in t:
            return name
    for name in names:
        words = [w for w in re.split(r"\W+", name.lower().replace("ё", "е")) if len(w) > 3]
        if words and all(w in t for w in words):
            return name
    return None


def enrich_doc_params(phrase: str, params: dict) -> dict:
    """Дополнить параметры документа тем, что действительно сказано во фразе.

    Ничего не додумывает: количество и цена подставляются только если число
    есть в тексте, иначе остаются как были.
    """
    result = dict(params or {})
    positions = [dict(p) for p in (result.get("positions") or [])]
    if not positions:
        positions = [{"item": "", "qty": 0, "price": 0}]
    numbers = [int(n) for n in re.findall(r"\b(\d{1,6})\b", phrase or "")]
    if numbers and not positions[0].get("qty"):
        positions[0]["qty"] = numbers[0]
    if len(numbers) > 1 and not positions[0].get("price"):
        positions[0]["price"] = numbers[1]
    result["positions"] = positions
    result.setdefault("doc_type", "РеализацияТоваровУслуг")
    return result
