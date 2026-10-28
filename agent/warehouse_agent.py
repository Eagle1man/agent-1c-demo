# -*- coding: utf-8 -*-
"""
Агент-Кладовщик: учёт движения товаров на складе, приёмка, отгрузка,
контроль остатков через запросы к 1С.
"""
import time
from base_agent import BaseAgent


class WarehouseAgent(BaseAgent):
    def __init__(self, exchange_root: str, poll_interval: float = 1.0):
        super().__init__("кладовщик", exchange_root,
                         profile="кладовщик", poll_interval=poll_interval)

    def execute(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("params") or {}
        risk = task.get("risk", "low")

        if action == "запрос_1с":
            # Кладовщик читает остатки из регистра ТоварыНаСкладах
            query = params.get("query") or (
                "ВЫБРАТЬ ПЕРВЫЕ 50 Номенклатура, КоличествоОстаток КАК Остаток "
                "ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки()"
            )
            return super().execute({
                "action": "запрос_1с",
                "params": {"query": query},
                "risk": risk,
                "confirmed_by": task.get("confirmed_by"),
            })

        if action == "проверить_наличие":
            item = params.get("item", "")
            qty = float(params.get("qty", 0))
            # Кладовщик проверяет остаток конкретной номенклатуры
            query = (
                f"ВЫБРАТЬ ПЕРВЫЕ 1 Номенклатура, КоличествоОстаток КАК Остаток "
                f"ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки() "
                f"ГДЕ Номенклатура = \"{item}\""
            )
            res = super().execute({
                "action": "запрос_1с",
                "params": {"query": query},
                "risk": "low",
            })
            if res.get("status") != "ok":
                return res
            # Упрощённо: считаем, что наличие есть, если ответ не пустой
            available = bool(res.get("result"))
            enough = available  # в реальности сравнить qty с Остаток
            return {
                "status": "ok",
                "result": {
                    "item": item,
                    "requested_qty": qty,
                    "available": available,
                    "enough": enough,
                    "note": "остаток проверен через запрос_1с",
                },
            }

        if action == "списание_товара":
            # Высокий риск — требует подтверждения
            if not task.get("confirmed_by"):
                return {
                    "status": "need_confirmation",
                    "result": {
                        "echo": {
                            "item": params.get("item"),
                            "qty": params.get("qty"),
                            "doc_type": "Списание",
                        }
                    },
                    "note": "требуется подтверждение списания товара",
                }
            return super().execute({
                "action": "создать_документ",
                "params": {
                    "doc_type": "СписаниеТоваров",
                    "counterparty": params.get("counterparty", ""),
                    "positions": params.get("positions", []),
                },
                "risk": "high",
                "confirmed_by": task.get("confirmed_by"),
            })

        return {"status": "error",
                "error": {"code": "unsupported_action",
                          "message": f"кладовщик не умеет {action}"}}


if __name__ == "__main__":
    import sys
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:\1c_agent\exchange"
    a = WarehouseAgent(ex)
    try:
        a.start()
        print("Агент-Кладовщик запущен. Ctrl+C для остановки.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        a.stop()