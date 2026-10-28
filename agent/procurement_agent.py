# -*- coding: utf-8 -*-
"""
Агент-Менеджер по закупкам: формирование заявок на закупку при дефиците,
выбор поставщиков, контроль цен и сроков поставки через 1С.
"""
import sys
import time
from base_agent import BaseAgent


class ProcurementAgent(BaseAgent):
    def __init__(self, exchange_root: str, poll_interval: float = 1.0):
        super().__init__("закупки", exchange_root,
                         profile="логист", poll_interval=poll_interval)

    def execute(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("params") or {}
        risk = task.get("risk", "low")

        if action == "запрос_1с":
            query = params.get("query") or (
                "ВЫБРАТЬ ПЕРВЫЕ 50 Наименование, ИНН, КПП ИЗ Справочник.Контрагенты"
            )
            return super().execute({
                "action": "запрос_1с",
                "params": {"query": query},
                "risk": risk,
                "confirmed_by": task.get("confirmed_by"),
            })

        if action == "проверить_дефицит":
            item = params.get("item", "")
            min_qty = float(params.get("min_qty", 0))
            # Кладовщик уже проверил остаток — здесь принимаем решение о закупке
            current_qty = float(params.get("current_qty", 0))
            if current_qty < min_qty:
                return {
                    "status": "ok",
                    "result": {
                        "item": item,
                        "current_qty": current_qty,
                        "min_qty": min_qty,
                        "deficit": min_qty - current_qty,
                        "need_purchase": True,
                    },
                }
            return {
                "status": "ok",
                "result": {
                    "item": item,
                    "need_purchase": False,
                },
            }

        if action == "сформировать_заявку_закупку":
            if not task.get("confirmed_by"):
                return {
                    "status": "need_confirmation",
                    "result": {
                        "echo": {
                            "doc_type": "ЗаказПоставщику",
                            "counterparty": params.get("counterparty", ""),
                            "positions": params.get("positions", []),
                        }
                    },
                    "note": "требуется подтверждение заявки на закупку",
                }
            return super().execute({
                "action": "создать_документ",
                "params": {
                    "doc_type": "ЗаказПоставщику",
                    "counterparty": params.get("counterparty", ""),
                    "positions": params.get("positions", []),
                },
                "risk": "high",
                "confirmed_by": task.get("confirmed_by"),
            })

        return {"status": "error",
                "error": {"code": "unsupported_action",
                          "message": f"закупки не умеют {action}"}}


if __name__ == "__main__":
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:\1c_agent\exchange"
    a = ProcurementAgent(ex)
    try:
        a.start()
        print("Агент-Закупки запущен. Ctrl+C для остановки.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        a.stop()