# -*- coding: utf-8 -*-
"""
Unified событийный лог взаимодействия пользователя с агентом.

Регистрирует для каждого обращения:
- event_id, conversation_id, timestamp
- operation_type, user_id (обезличенный)
- request (текст запроса)
- rag_sources (использованные документы RAG)
- system_prompt_version
- model_response (ответ Ollama)
- tools_called, tool_results
- operation_status (ok / error / cancelled / unconfirmed / model_unverified)
- error (код и сообщение)
- duration_ms
- user_feedback (оценка/комментарий, nullable)

Хранилище: JSONL в exchange/events.jsonl (рядом с существующим journal.jsonl).
Ошибка записи в журнал не должна прерывать пользовательский запрос.
"""

import json
import hashlib
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _anon_user_id(raw: str) -> str:
    """Обезличенный идентификатор пользователя (SHA-256 от исходного)."""
    if not raw:
        return "anonymous"
    return "user_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class EventLogger:
    def __init__(self, exchange_root: str):
        self.root = Path(exchange_root)
        self.events_path = self.root / "events.jsonl"
        self._enabled = True

    def log_event(
        self,
        conversation_id: str,
        operation_type: str,
        request: str,
        user_raw_id: str = "",
        *,
        rag_sources: Optional[list] = None,
        system_prompt_version: Optional[str] = None,
        model_response: Optional[str] = None,
        tools_called: Optional[list] = None,
        tool_results: Optional[list] = None,
        operation_status: str = "ok",
        error: Optional[dict] = None,
        duration_ms: Optional[int] = None,
        user_feedback: Optional[str] = None,
    ) -> str:
        """
        Записать событие в журнал. Возвращает event_id.
        Любая ошибка записи перехватывается — пользовательский запрос не прерывается.
        """
        event_id = str(uuid.uuid4())
        rec = {
            "event_id": event_id,
            "conversation_id": conversation_id,
            "ts": now_ts(),
            "operation_type": operation_type,
            "user_id": _anon_user_id(user_raw_id),
            "request": request,
            "rag_sources": rag_sources or [],
            "system_prompt_version": system_prompt_version,
            "model_response": model_response,
            "tools_called": tools_called or [],
            "tool_results": tool_results or [],
            "operation_status": operation_status,
            "error": error,
            "duration_ms": duration_ms,
            "user_feedback": user_feedback,
        }
        try:
            with self.events_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as exc:
            # Не ломаем пользовательский запрос из-за сбоя логирования
            import sys
            print(f"[event_logger] сбой записи события: {exc}", file=sys.stderr)
            self._enabled = False
        return event_id

    def add_feedback(self, event_id: str, feedback: str) -> bool:
        """Добавить обратную связь пользователя к существующему событию."""
        if not self.events_path.exists():
            return False
        try:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()
            updated = []
            found = False
            for line in lines:
                try:
                    rec = json.loads(line)
                    if rec.get("event_id") == event_id:
                        rec["user_feedback"] = feedback
                        found = True
                    updated.append(json.dumps(rec, ensure_ascii=False))
                except Exception:
                    updated.append(line)
            if found:
                self.events_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
            return found
        except Exception:
            return False

    def get_events(self, limit: int = 1000, offset: int = 0) -> list:
        """Получить события (последние limit с отступом offset)."""
        if not self.events_path.exists():
            return []
        try:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            events.reverse()  # последние первыми
            return events[offset:offset + limit]
        except Exception:
            return []

    def get_unprocessed(self, processed_ids: set) -> list:
        """Получить события, которые ещё не обработаны фоновым аналитиком."""
        if not self.events_path.exists():
            return []
        try:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            return [e for e in events if e.get("event_id") not in processed_ids]
        except Exception:
            return []