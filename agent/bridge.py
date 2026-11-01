# -*- coding: utf-8 -*-
"""Файловый мост агента с 1С: команды/ответы через exchange/ (см. PROTOCOL.md)."""
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

PROTOCOL = "1.0"


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class BridgeError(Exception):
    """Базовая ошибка моста."""


class BridgeTimeout(BridgeError):
    """1С/мост не ответили за отведённое время."""


class Bridge:
    def __init__(self, exchange_path, user="демо-пользователь"):
        self.root = Path(exchange_path)
        self.user = user
        for sub in ("commands", "responses", "archive", "log"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        self.journal_path = self.root / "journal.jsonl"
        self.log_path = self.root / "log" / "agent.log"

    def send(self, action, params, profile="бухгалтер", risk="low",
             confirmed_by=None, timeout=15.0):
        """Писать команду (.tmp → атомарно) и ждать ответ с таймаутом."""
        cid = str(uuid.uuid4())
        cmd = {
            "protocol": PROTOCOL,
            "id": cid,
            "ts": now_ts(),
            "action": action,
            "profile": profile,
            "risk": risk,
            "params": params,
            "confirmed_by": confirmed_by,
        }
        tmp = self.root / "commands" / f"{cid}.json.tmp"
        cmd_path = self.root / "commands" / f"{cid}.json"
        tmp.write_text(json.dumps(cmd, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(cmd_path)

        resp_path = self.root / "responses" / f"{cid}.json"
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            if resp_path.exists():
                try:
                    data = json.loads(resp_path.read_text(encoding="utf-8-sig"))
                except json.JSONDecodeError:
                    time.sleep(0.2)  # дописывается — подождём
                    continue
                except PermissionError:
                    # 1С ещё держит файл (или антивирус): файл есть, но читать нельзя.
                    # Без этого панель падала с 500 при каждом таком совпадении.
                    time.sleep(0.1)
                    continue
                self._log(f"{action} {cid} -> {data.get('status')}")
                return data
            time.sleep(0.2)
        raise BridgeTimeout(
            "1С не отвечает: проверьте, что база открыта и в окне 1С запущен "
            "«АгентМост» (кнопка «Запустить мост»), а путь к exchange совпадает "
            "в config.json и в обработке."
        )

    def check(self, timeout=5.0):
        """Жив ли мост. None — таймаут (1С не запущена)."""
        try:
            return self.send("проверка_связи", {}, timeout=timeout)
        except BridgeTimeout:
            return None

    def confirmed_by(self, user=None):
        return {"user": user or self.user, "ts": now_ts()}

    def journal(self, action, risk, decision, status, summary, cid=None):
        """Журнал действий: каждое решение агента — с обоснованием (концепция)."""
        rec = {
            "ts": now_ts(),
            "id": cid or "-",
            "action": action,
            "risk": risk,
            "decision": decision,
            "status": status,
            "summary": summary,
        }
        with self.journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _log(self, line):
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{now_ts()} {line}\n")
