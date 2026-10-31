# -*- coding: utf-8 -*-
"""Выбор модели под роль агента (ТЗ §6: роль ≠ модель ≠ процесс).

Зачем отдельный модуль: у системы разные по стоимости задачи. Разбор заявки
пользователя нужен за секунды, анализ BSL-кода или ночной разбор инцидентов
может идти минуты. Одна модель на всё означает либо медленный чат, либо
слабый анализ.

Правила:
- роль → модель задаётся в `config.json`, а не в коде;
- если модели из конфига нет в Ollama, система **не падает** и не выдумывает:
  берёт базовую модель и явно сообщает, что сработал резерв;
- список установленных моделей кэшируется на минуту, чтобы не дёргать Ollama
  на каждый вызов.

Роли: `coordinator`, `agent`, `analyst`, `code_expert`, `scada`.
"""
import json
import time
import urllib.request
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"

_CACHE_TTL = 60.0
_tags_cache = {"ts": 0.0, "names": set()}


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def installed_models(force: bool = False) -> set:
    """Имена моделей, реально доступных в Ollama. Пустое множество — Ollama молчит."""
    now = time.time()
    if not force and _tags_cache["names"] and now - _tags_cache["ts"] < _CACHE_TTL:
        return _tags_cache["names"]
    names = set()
    try:
        with urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for item in data.get("models", []):
            name = item.get("name")
            if name:
                names.add(name)
    except Exception:                                   # noqa: BLE001
        names = set()
    _tags_cache["names"] = names
    _tags_cache["ts"] = now
    return names


def role_model(role: str) -> tuple:
    """(имя модели, примечание). Примечание не пустое, если сработал резерв."""
    cfg = _load_config()
    base = cfg.get("model") or "qwen2.5:1.5b"
    roles = cfg.get("model_roles") or {}
    wanted = roles.get(role) or roles.get("agent") or base
    if not wanted or wanted == base:
        return base, ""
    available = installed_models()
    if not available:
        # Ollama недоступна: не притворяемся, что модель выбрана.
        return wanted, "Ollama не отвечает: доступность модели не проверена"
    if wanted in available:
        return wanted, ""
    return base, f"модель роли '{role}' ({wanted}) не установлена — используется {base}"


def describe() -> dict:
    """Карта ролей для печати в отчёте: что реально будет использоваться."""
    cfg = _load_config()
    return {role: role_model(role) for role in
            ("coordinator", "agent", "analyst", "code_expert", "scada")}


if __name__ == "__main__":
    for role, (name, note) in describe().items():
        print(f"{role:12} -> {name} {('(' + note + ')') if note else ''}")
