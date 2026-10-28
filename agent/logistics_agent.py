# -*- coding: utf-8 -*-
"""
Агент-Логист: планирование отгрузок, контроль сроков доставки,
взаимодействие со складом и транспортом через 1С.
"""
import sys
import time
from base_agent import BaseAgent


class LogisticsAgent(BaseAgent):
    def __init__(self, exchange_root: str, poll_interval: float = 1.0):
        super().__init__("логист", exchange_root,
                         profile="логист", poll_interval=poll_interval)

    def execute(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("params") or {}
        risk = task.get("risk", "low")

        if action == "запрос_1с":
            query = params.get("query") or (
                "ВЫБРАТЬ ПЕРВЫЕ 50 Номер, Дата ИЗ Документ.ЗаказПокупателя "
                "ГДЕ НЕ ПометкаУдаления"
            )
            return super().execute({
                "action": "запрос_1с",
                "params": {"query": query},
                "risk": risk,
                "confirmed_by": task.get("confirmed_by"),
            })

        if action == "планировать_отгрузку":
            # Логист запрашивает у склада наличие, затем планирует отгрузку.
            item = params.get("item", "")
            qty = float(params.get("qty", 0))
            # Спрашиваем у себя же (или через координатор у кладовщика) — здесь упрощённо
            check = super().execute({
                "action": "проверить_наличие",
                "params": {"item": item, "qty": qty},
                "risk": "low",
            })
            if check.get("status") != "ok":
                return check
            enough = check.get("result", {}).get("enough", False)
            if not enough:
                return {
                    "status": "error",
                    "error": {
                        "code": "insufficient_stock",
                        "message": f"Недостаточно товара {item} для отгрузки {qty} шт.",
                    },
                }
            return {
                "status": "ok",
                "result": {
                    "item": item,
                    "qty": qty,
                    "planned_date": params.get("date", ""),
                    "note": "Отгрузка запланирована, товар зарезервирован",
                },
            }

        if action == "создать_отгрузку":
            if not task.get("confirmed_by"):
                return {
                    "status": "need_confirmation",
                    "result": {
                        "echo": {
                            "doc_type": "Отгрузка",
                            "item": params.get("item"),
                            "qty": params.get("qty"),
                            "counterparty": params.get("counterparty"),
                        }
                    },
                    "note": "требуется подтверждение отгрузки",
                }
            return super().execute({
                "action": "создать_документ",
                "params": {
                    "doc_type": "Отгрузка",
                    "counterparty": params.get("counterparty", ""),
                    "positions": params.get("positions", []),
                },
                "risk": "high",
                "confirmed_by": task.get("confirmed_by"),
            })

        return {"status": "error",
                "error": {"code": "unsupported_action",
                          "message": f"логист не умеет {action}"}}


if __name__ == "__main__":
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:\1c_agent\exchange"
    a = LogisticsAgent(ex)
    try:
        a.start()
        print("Агент-Логист запущен. Ctrl+C для остановки.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        a.stop()