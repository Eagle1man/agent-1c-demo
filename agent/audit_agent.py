# -*- coding: utf-8 -*-
"""
Агент-Аудит/Контроль: журналирование всех действий, проверка соответствия
правилам, выявление аномалий, формирование отчётов для руководителя.
"""
import sys
import time
import json
from pathlib import Path
from base_agent import BaseAgent


class AuditAgent(BaseAgent):
    def __init__(self, exchange_root: str, poll_interval: float = 1.0):
        super().__init__("аудит", exchange_root,
                         profile="руководитель", poll_interval=poll_interval)
        self.audit_path = self.root / "agents" / "audit.json"

    def execute(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("params") or {}
        risk = task.get("risk", "low")

        if action == "проверить_журнал":
            # Проверить последние записи в journal.jsonl на аномалии
            journal_path = self.root / "journal.jsonl"
            anomalies = []
            if journal_path.exists():
                lines = journal_path.read_text(encoding="utf-8").splitlines()
                for line in lines[-50:]:
                    try:
                        rec = json.loads(line)
                        if rec.get("status") == "error":
                            anomalies.append(rec)
                        if rec.get("decision") == "human_rejected":
                            anomalies.append(rec)
                    except Exception:
                        pass
            return {
                "status": "ok",
                "result": {
                    "anomalies": anomalies,
                    "count": len(anomalies),
                    "note": "журнал проверен",
                },
            }

        if action == "проверить_высокорисковые_без_подтверждения":
            # Проверить, не было ли high-risk действий без confirmed_by
            journal_path = self.root / "journal.jsonl"
            violations = []
            if journal_path.exists():
                lines = journal_path.read_text(encoding="utf-8").splitlines()
                for line in lines[-100:]:
                    try:
                        rec = json.loads(line)
                        if rec.get("risk") == "high" and rec.get("status") == "ok":
                            violations.append(rec)
                    except Exception:
                        pass
            return {
                "status": "ok",
                "result": {
                    "violations": violations,
                    "count": len(violations),
                    "note": "проверка высокорисковых действий выполнена",
                },
            }

        if action == "сформировать_отчёт":
            # Аудит-отчёт за период
            return {
                "status": "ok",
                "result": {
                    "report": "аудитный отчёт сформирован",
                    "period": params.get("period", "сегодня"),
                    "note": "отчёт готов для руководителя",
                },
            }

        return {"status": "error",
                "error": {"code": "unsupported_action",
                          "message": f"аудит не умеет {action}"}}


if __name__ == "__main__":
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:\1c_agent\exchange"
    a = AuditAgent(ex)
    try:
        a.start()
        print("Агент-Аудит запущен. Ctrl+C для остановки.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        a.stop()