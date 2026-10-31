# -*- coding: utf-8 -*-
"""Спринт 0: регрессия на исправления, без которых проверки врут.

Проверяем ровно то, что было сломано:
- схема инструментов LLM валидна и не содержит категорию C;
- отправка команд оборудованию отклоняется политикой, а не выполняется;
- недоступная SCADA не подменяется случайными значениями и не выглядит
  как «аварий нет»;
- цель про датчики не падает в координаторе и доходит до SCADA-агента.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from tools import TOOLS, execute_tool, SCADA_WRITE_ENABLED
from scada_bridge import ScadaBridge
from coordinator import Coordinator

FAILED = []
PASSED = 0


def check(name, cond, detail=""):
    global PASSED
    if cond:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED.append(name)
        print(f"  [FAIL] {name} {detail}")


class FakeBridge:
    """Мост-заглушка: журналирует вызовы, в 1С не ходит."""

    def __init__(self, root):
        self.root = Path(root)
        self.journaled = []

    def journal(self, *args, **kwargs):
        self.journaled.append(args)

    def confirmed_by(self):
        return {"user": "тест", "ts": "2026-10-31T00:00:00"}

    def send(self, *args, **kwargs):
        return {"status": "ok", "result": {}, "id": "fake"}


def main():
    tmp = Path(tempfile.mkdtemp(prefix="sprint0_test_"))
    try:
        # ---------------------------------------------------------- инструменты
        names = [t["function"]["name"] for t in TOOLS]
        check("инструменты описаны", len(names) >= 4)
        check("категория C отсутствует в списке инструментов",
              "отправить_команду" not in names, str(names))
        check("флаг записи в SCADA выключен", SCADA_WRITE_ENABLED is False)

        for tool in TOOLS:
            fn = tool["function"]
            params = fn.get("parameters", {})
            check(f"схема {fn['name']}: type=object", params.get("type") == "object")
            check(f"схема {fn['name']}: required не внутри properties",
                  "required" not in params.get("properties", {}))
            for req in params.get("required", []):
                check(f"схема {fn['name']}: required '{req}' есть в properties",
                      req in params.get("properties", {}))

        # сериализуемость схемы — то, что уходит в Ollama
        try:
            json.dumps(TOOLS, ensure_ascii=False)
            check("схемы сериализуются в JSON", True)
        except (TypeError, ValueError) as exc:
            check("схемы сериализуются в JSON", False, str(exc))

        # ---------------------------------------------------------- политика C
        bridge = FakeBridge(tmp)
        raw = execute_tool(bridge, "отправить_команду",
                           {"tag": "T1", "value": 42}, "бухгалтер",
                           input_func=lambda _: "да", print_func=lambda *_: None)
        resp = json.loads(raw)
        check("команда оборудованию отклонена", resp.get("status") == "forbidden", raw)
        check("код отказа policy_denied",
              (resp.get("error") or {}).get("code") == "policy_denied")
        check("отказ записан в журнал",
              any("policy_denied" in str(entry) for entry in bridge.journaled))

        # ---------------------------------------------------------- SCADA: отказ
        cfg = tmp / "scada_config.json"
        cfg.write_text(json.dumps({
            "scada_url": "http://127.0.0.1:9",   # заведомо закрытый порт
            "integration_1c": False,
            "sensors": [{"id": "s1", "name": "Температура", "tag": "T1",
                         "unit": "C", "min": 0, "max": 100}],
        }, ensure_ascii=False), encoding="utf-8")

        scada = ScadaBridge(str(cfg), str(tmp / "exchange"))
        sensors = scada.read_sensors()
        check("датчик вернулся", len(sensors) == 1)
        s = sensors[0]
        check("значение не выдумано", s.get("value") is None, str(s.get("value")))
        check("статус unavailable", s.get("status") == "unavailable", str(s.get("status")))
        check("причина отказа указана", bool(s.get("error")))

        alarms = scada.get_alarms()
        check("список аварий пуст", len(alarms) == 0)
        check("но источник помечен недоступным", alarms.available is False)
        check("ошибка аварий сохранена", bool(alarms.error))

        # ---------------------------------------------------------- координатор
        c = Coordinator.__new__(Coordinator)
        c.agent_id = "координатор"
        c.journal_path = Path(tmp) / "journal.jsonl"
        c.tasks = {}
        c.task_goal = {}
        c.assigned = []
        c._assign = lambda agent_id, action, params, risk, gid: c.assigned.append(
            (agent_id, action, gid))

        gid = "goal-scada"
        c.tasks[gid] = {"status": "accepted", "steps": [], "results": {},
                        "profile": "бухгалтер"}
        try:
            c._decompose({"id": gid, "text": "покажи температуру на линии"})
            check("цель про датчики не падает", True)
        except Exception as exc:                       # noqa: BLE001
            check("цель про датчики не падает", False, f"{type(exc).__name__}: {exc}")

        check("цель ушла SCADA-агенту",
              bool(c.assigned) and c.assigned[0][0] == "scada", str(c.assigned))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nИТОГ: {PASSED} ok, {len(FAILED)} fail")
    if FAILED:
        for name in FAILED:
            print(f"  -> {name}")
        sys.exit(1)
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")


if __name__ == "__main__":
    main()
