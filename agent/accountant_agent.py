# -*- coding: utf-8 -*-
"""
Агент-Бухгалтер: документы реализации/прихода, расчёты с контрагентами,
сверка остатков, формирование проводок через 1С.
"""
import time
from base_agent import BaseAgent


class AccountantAgent(BaseAgent):
    def __init__(self, exchange_root: str, poll_interval: float = 1.0):
        super().__init__("бухгалтер", exchange_root,
                         profile="бухгалтер", poll_interval=poll_interval)

    def execute(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("params") or {}
        risk = task.get("risk", "low")

        if action == "запрос_1с":
            query = params.get("query") or (
                "ВЫБРАТЬ ПЕРВЫЕ 50 Контрагент, СуммаОстаток КАК Задолженность "
                "ИЗ РегистрБухгалтерии.Хозрасчетный.Остатки()"
            )
            return super().execute({
                "action": "запрос_1с",
                "params": {"query": query},
                "risk": risk,
                "confirmed_by": task.get("confirmed_by"),
            })

        if action == "создать_документ":
            # Бухгалтер проводит документ — высокий риск, нужен confirmed_by
            if not task.get("confirmed_by"):
                return {
                    "status": "need_confirmation",
                    "result": {
                        "echo": {
                            "doc_type": params.get("doc_type"),
                            "counterparty": params.get("counterparty"),
                            "positions": params.get("positions", []),
                        }
                    },
                    "note": "требуется подтверждение создания документа бухгалтерией",
                }
            return super().execute({
                "action": "создать_документ",
                "params": {
                    "doc_type": params.get("doc_type", "РеализацияТоваровУслуг"),
                    "counterparty": params.get("counterparty", ""),
                    "positions": params.get("positions", []),
                },
                "risk": "high",
                "confirmed_by": task.get("confirmed_by"),
            })

        if action == "сверка_расчётов":
            counterparty = params.get("counterparty", "")
            query = (
                f"ВЫБРАТЬ ПЕРВЫЕ 50 Контрагент, СуммаОстаток КАК Задолженность "
                f"ИЗ РегистрБухгалтерии.Хозрасчетный.Остатки() "
                f"ГДЕ Контрагент = \"{counterparty}\""
            )
            res = super().execute({
                "action": "запрос_1с",
                "params": {"query": query},
                "risk": "low",
            })
            if res.get("status") != "ok":
                return res
            return {
                "status": "ok",
                "result": {
                    "counterparty": counterparty,
                    "debt": res.get("result"),
                    "note": "сверка расчётов выполнена",
                },
            }

        return {"status": "error",
                "error": {"code": "unsupported_action",
                          "message": f"бухгалтер не умеет {action}"}}


if __name__ == "__main__":
    import sys
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:\1c_agent\exchange"
    a = AccountantAgent(ex)
    try:
        a.start()
        print("Агент-Бухгалтер запущен. Ctrl+C для остановки.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        a.stop()