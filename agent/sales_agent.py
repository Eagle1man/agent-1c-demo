# -*- coding: utf-8 -*-
"""
Агент-Менеджер по продажам: обработка клиентских заказов, контроль оплат,
информирование клиентов о статусах через 1С.
"""
import sys
import time
from base_agent import BaseAgent


class SalesAgent(BaseAgent):
    def __init__(self, exchange_root: str, poll_interval: float = 1.0):
        super().__init__("продажи", exchange_root,
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

        if action == "обработать_заказ_клиента":
            order_id = params.get("order_id", "")
            counterparty = params.get("counterparty", "")
            # Проверить оплату (упрощённо)
            return {
                "status": "ok",
                "result": {
                    "order_id": order_id,
                    "counterparty": counterparty,
                    "status": "принят_в_работу",
                    "note": "Заказ клиента передан логисту на отгрузку",
                },
            }

        if action == "проверить_оплату":
            order_id = params.get("order_id", "")
            paid = params.get("paid", False)
            if not paid:
                return {
                    "status": "need_confirmation",
                    "result": {
                        "echo": {
                            "order_id": order_id,
                            "note": "Оплата не поступила — требуется решение",
                        }
                    },
                    "note": "требуется подтверждение отгрузки без оплаты",
                }
            return {
                "status": "ok",
                "result": {
                    "order_id": order_id,
                    "paid": True,
                    "note": "Оплата подтверждена",
                },
            }

        if action == "создать_документ":
            if not task.get("confirmed_by"):
                return {
                    "status": "need_confirmation",
                    "result": {
                        "echo": {
                            "doc_type": params.get("doc_type"),
                            "counterparty": params.get("counterparty"),
                        }
                    },
                    "note": "требуется подтверждение создания документа продажами",
                }
            return super().execute({
                "action": "создать_документ",
                "params": {
                    "doc_type": params.get("doc_type", "ЗаказКлиента"),
                    "counterparty": params.get("counterparty", ""),
                    "positions": params.get("positions", []),
                },
                "risk": "high",
                "confirmed_by": task.get("confirmed_by"),
            })

        return {"status": "error",
                "error": {"code": "unsupported_action",
                          "message": f"продажи не умеют {action}"}}


if __name__ == "__main__":
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:\1c_agent\exchange"
    a = SalesAgent(ex)
    try:
        a.start()
        print("Агент-Продажи запущен. Ctrl+C для остановки.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        a.stop()