# -*- coding: utf-8 -*-
"""
Базовый класс мультиагента для системы на базе 1С:Предприятие.

Агент работает через файловые почтовые ящики:
  agents/inbox/<agent_id>.json    — входящие задачи
  agents/outbox/<agent_id>.json   — исходящие результаты
  agents/blackboard/<topic>.json  — общая доска объявлений

Каждый агент autonomously опрашивает свой inbox, выполняет задачу
через chat_service.py (шлюз к 1С) и пишет результат в outbox.
"""
import json
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path

from bridge import Bridge, BridgeTimeout
from chat_service import ChatService


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class BaseAgent:
    def __init__(self, agent_id: str, exchange_root: str,
                 profile: str = "бухгалтер", poll_interval: float = 1.0):
        self.agent_id = agent_id
        self.root = Path(exchange_root)
        self.profile = profile
        self.poll_interval = poll_interval

        self.agents_dir = self.root / "agents"
        self.inbox = self.agents_dir / "inbox"
        self.outbox = self.agents_dir / "outbox"
        self.blackboard = self.agents_dir / "blackboard"
        self.conflicts = self.agents_dir / "conflicts"
        self.human_confirm = self.agents_dir / "human_confirm"

        for d in (self.inbox, self.outbox, self.blackboard,
                  self.conflicts, self.human_confirm):
            d.mkdir(parents=True, exist_ok=True)

        self.chat = ChatService(self.root, profile=profile, use_mock=True)
        self._stop = threading.Event()
        self._thread = None
        self.journal_path = self.root / "journal.jsonl"

    # ----------------------------- lifecycle -----------------------------
    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[agent {self.agent_id}] запущен")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.chat.stop()
        print(f"[agent {self.agent_id}] остановлен")

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:
                self._journal("tick_error", "high", "auto", "error",
                              f"сбой тика агента {self.agent_id}: {exc}")
            time.sleep(self.poll_interval)

    # ----------------------------- inbox -----------------------------
    def _tick(self):
        for path in sorted(self.inbox.glob("*.json")):
            if path.name.endswith(".tmp") or "__processed" in path.name:
                continue
            self._handle(path)
    def _handle(self, path: Path):
        try:
            task = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            self._archive(path, "parse_error")
            self._journal("parse_error", "high", "auto", "error",
                          f"некорректная задача {path.name}: {exc}")
            return

        to = task.get("to")
        if to and to != self.agent_id:
            # не наше задание — пропускаем, не трогая
            try:
                path.replace(self.inbox / f"{path.stem}__skipped.json")
            except Exception:
                pass
            return

        task_id = str(task.get("id") or path.stem)
        result = self.execute(task)

        resp = {
            "protocol": "1.1",
            "id": str(uuid.uuid4()),
            "ts": now_ts(),
            "from": self.agent_id,
            "to": task.get("from", "координатор"),
            "in_response_to": task_id,
            "status": result.get("status", "ok"),
            "result": result.get("result"),
            "error": result.get("error"),
            "executed_by": f"{self.agent_id} 1.1",
        }
        out_path = self.outbox / f"{resp['id']}.json"
        tmp = self.outbox / f"{resp['id']}.json.tmp"
        tmp.write_text(json.dumps(resp, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(out_path)

        try:
            path.replace(self.inbox / f"{path.stem}__processed.json")
        except Exception:
            pass

        self._journal(task.get("action", "неизвестно"),
                      task.get("risk", "low"), "auto",
                      resp["status"],
                      f"задача {task_id} выполнена агентом {self.agent_id}",
                      task_id)
    # ----------------------------- execute -----------------------------
    def execute(self, task: dict) -> dict:
        """
        Точка переопределения в конкретных агентах.
        task — словарь из inbox. Должен вернуть dict со статусом.
        """
        action = task.get("action")
        params = task.get("params") or {}
        risk = task.get("risk", "low")

        if action == "проверка_связи":
            try:
                self.chat.process({
                    "id": str(uuid.uuid4()),
                    "phrase": "проверка связи",
                    "profile": self.profile,
                })
                return {"status": "ok", "result": "связь есть"}
            except Exception as exc:
                return {"status": "error", "error": {"code": "tick_error", "message": str(exc)}}

        if action == "запрос_1с":
            try:
                out = self.chat.process({
                    "id": str(uuid.uuid4()),
                    "phrase": params.get("query", ""),
                    "profile": self.profile,
                })
                return {"status": out.get("status", "ok"),
                        "result": out.get("answer"),
                        "query": out.get("query")}
            except Exception as exc:
                return {"status": "error", "error": {"code": "query_error", "message": str(exc)}}

        if action == "создать_документ":
            # high risk: требуется подтверждение координатора / человека
            if not task.get("confirmed_by"):
                return {
                    "status": "need_confirmation",
                    "result": {"echo": params},
                    "note": "требуется подтверждение человека",
                }
            try:
                out = self.chat.process({
                    "id": str(uuid.uuid4()),
                    "phrase": f"создай документ {params.get('doc_type')} на {params.get('counterparty')}",
                    "profile": self.profile,
                })
                return {"status": out.get("status", "ok"),
                        "result": out.get("answer")}
            except Exception as exc:
                return {"status": "error", "error": {"code": "doc_error", "message": str(exc)}}

        return {"status": "error",
                "error": {"code": "unsupported_action",
                          "message": f"агент {self.agent_id} не умеет {action}"}}
    # ----------------------------- blackboard / journal -----------------------------
    def publish(self, topic: str, payload: dict) -> str:
        """Опубликовать объявление на чёрную доску."""
        msg_id = str(uuid.uuid4())
        msg = {"id": msg_id, "ts": now_ts(), "from": self.agent_id,
               "topic": topic, "payload": payload}
        path = self.blackboard / f"{topic}_{msg_id}.json"
        path.write_text(json.dumps(msg, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return msg_id

    def read_blackboard(self, topic: str):
        """Прочитать все объявления по теме."""
        return [json.loads(p.read_text(encoding="utf-8-sig"))
                for p in sorted(self.blackboard.glob(f"{topic}_*.json"))]

    def register_conflict(self, description: str, participants: list) -> str:
        """Зарегистрировать конфликт целей агентов."""
        cid = str(uuid.uuid4())
        rec = {"id": cid, "ts": now_ts(),
               "description": description,
               "participants": participants,
               "status": "open"}
        path = self.conflicts / f"{cid}.json"
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        self._journal("conflict", "high", "auto", "open",
                      f"конфликт: {description} ({', '.join(participants)})",
                      cid)
        return cid

    def request_human_confirm(self, task_summary: str, task_id: str) -> str:
        """Запросить подтверждение человека (High Risk)."""
        cid = str(uuid.uuid4())
        rec = {"id": cid, "ts": now_ts(),
               "task_id": task_id,
               "summary": task_summary,
               "status": "awaiting"}
        path = self.human_confirm / f"{cid}.json"
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        self._journal("human_confirm", "high", "auto", "awaiting",
                      f"запрос подтверждения: {task_summary}", cid)
        return cid

    def _journal(self, action, risk, decision, status, summary, cid=None):
        rec = {"ts": now_ts(), "id": cid or "-",
               "agent": self.agent_id,
               "action": action, "risk": risk,
               "decision": decision, "status": status,
               "summary": summary}
        with self.journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _archive(self, path: Path, verdict: str):
        target = self.inbox / f"{path.stem}__{verdict}.json"
        try:
            path.replace(target)
        except Exception:
            pass


if __name__ == "__main__":
    # Быстрая проверка базового агента
    import sys
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:\1c_agent\exchange"
    a = BaseAgent("тестовый_агент", ex, profile="бухгалтер")
    try:
        a.start()
        print("Работает 10 секунд... (Ctrl+C для остановки)")
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        a.stop()