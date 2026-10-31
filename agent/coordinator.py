# -*- coding: utf-8 -*-
"""
Координатор (Оркестратор) мультиагентной системы.

Читает цели из blackboard, декомпозирует их на подзадачи,
назначает конкретным агентам через их inbox, собирает результаты
из outbox и разрешает конфликты.
"""
import json
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path

from base_agent import BaseAgent


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Coordinator(BaseAgent):
    def __init__(self, exchange_root: str, poll_interval: float = 1.0):
        super().__init__("координатор", exchange_root,
                         profile="руководитель", poll_interval=poll_interval)
        self.tasks = {}          # id задачи -> состояние
        self.task_goal = {}      # id задачи (inbox) -> id цели (blackboard)
        self.agent_status = {}   # agent_id -> busy/free

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._tick()
                self._collect_results()
                self._resolve_conflicts()
            except Exception as exc:
                self._journal("tick_error", "high", "auto", "error",
                              f"сбой координатора: {exc}")
            time.sleep(self.poll_interval)

    # ----------------------------- 목표 -----------------------------
    def accept_goal(self, goal_text: str, profile: str = "бухгалтер") -> str:
        """Принять цель от пользователя и опубликовать на blackboard."""
        gid = str(uuid.uuid4())
        goal = {
            "id": gid, "ts": now_ts(),
            "text": goal_text, "profile": profile,
            "status": "accepted",
        }
        self.publish("цели", goal)
        self.tasks[gid] = {"status": "accepted", "steps": [],
                           "results": {}, "profile": profile}
        self._journal("accept_goal", "low", "auto", "accepted",
                      f"цель: {goal_text}", gid)
        return gid
    # ----------------------------- декомпозиция -----------------------------
    def _tick(self):
        # Прочитать новые цели с доски
        for msg in self.read_blackboard("цели"):
            goal = msg.get("payload", msg)
            gid = goal["id"]
            if gid in self.tasks and self.tasks[gid].get("status") != "accepted":
                continue  # уже обрабатывается или завершена
            self._decompose(goal)

        # Координатор не исполняет задачи агентов — только распределяет цели.

    def _decompose(self, goal: dict):
        """Разбить цель на шаги и назначить агентам."""
        gid = goal["id"]
        text = goal["text"].lower()
        steps = []

        if any(w in text for w in ("датчик", "температур", "давлен", "уровн",
                                   "авари", "оборудован", "лини", "станк")):
            steps.append(("scada", "прочитать_датчики", {}, "low"))
            self.tasks[gid]["steps"] = steps
            self.tasks[gid]["status"] = "в работе"
            for agent_id, action, params, risk in steps:
                self._assign(agent_id, action, params, risk, gid)
            return

        if any(w in text for w in ("остат", "склад", "товар")):
            steps.append(("кладовщик", "запрос_1с",
                          {"query": "ВЫБРАТЬ ПЕРВЫЕ 50 Номенклатура, КоличествоОстаток КАК Остаток ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки()"},
                          "low"))
            self.tasks[gid]["steps"] = steps
            self.tasks[gid]["status"] = "в работе"
            for agent_id, action, params, risk in steps:
                self._assign(agent_id, action, params, risk, gid)
            return

        if any(w in text for w in ("задолжен", "контрагент", "долг")):
            steps.append(("бухгалтер", "запрос_1с",
                          {"query": "ВЫБРАТЬ ПЕРВЫЕ 50 Контрагент, СуммаОстаток КАК Задолженность ИЗ РегистрБухгалтерии.Хозрасчетный.Остатки()"},
                          "low"))
            self.tasks[gid]["steps"] = steps
            self.tasks[gid]["status"] = "в работе"
            for agent_id, action, params, risk in steps:
                self._assign(agent_id, action, params, risk, gid)
            return

        if any(w in text for w in ("накладн", "созда", "документ", "реализац")):
            steps.append(("кладовщик", "запрос_1с",
                          {"query": "ВЫБРАТЬ ПЕРВЫЕ 50 Номенклатура, КоличествоОстаток КАК Остаток ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки()"},
                          "low"))
            steps.append(("бухгалтер", "создать_документ",
                          {"doc_type": "РеализацияТоваровУслуг",
                           "counterparty": "ООО Ромашка",
                           "positions": [{"item": "Товар А", "qty": 5, "price": 200}]},
                          "high"))
            self.tasks[gid]["steps"] = steps
            self.tasks[gid]["status"] = "в работе"
            for agent_id, action, params, risk in steps:
                self._assign(agent_id, action, params, risk, gid)
            return

        if any(w in text for w in ("закуп", "поставщик", "заказ поставщику")):
            steps.append(("закупки", "запрос_1с",
                          {"query": "ВЫБРАТЬ ПЕРВЫЕ 50 Наименование, ИНН, КПП ИЗ Справочник.Контрагенты"},
                          "low"))
            self.tasks[gid]["steps"] = steps
            self.tasks[gid]["status"] = "в работе"
            for agent_id, action, params, risk in steps:
                self._assign(agent_id, action, params, risk, gid)
            return

        if any(w in text for w in ("продаж", "заказ клиента", "клиент")):
            steps.append(("продажи", "запрос_1с",
                          {"query": "ВЫБРАТЬ ПЕРВЫЕ 50 Номер, Дата ИЗ Документ.ЗаказПокупателя ГДЕ НЕ ПометкаУдаления"},
                          "low"))
            self.tasks[gid]["steps"] = steps
            self.tasks[gid]["status"] = "в работе"
            for agent_id, action, params, risk in steps:
                self._assign(agent_id, action, params, risk, gid)
            return

        if any(w in text for w in ("аудит", "журнал", "контроль", "нарушен")):
            steps.append(("аудит", "проверить_журнал",
                          {}, "low"))
            self.tasks[gid]["steps"] = steps
            self.tasks[gid]["status"] = "в работе"
            for agent_id, action, params, risk in steps:
                self._assign(agent_id, action, params, risk, gid)
            return

        # Неизвестная цель — фиксируем и ждём человека
        self.tasks[gid]["status"] = "неизвестная_цель"
        self._journal("accept_goal", "medium", "auto", "unknown",
                      f"цель не распознана: {goal['text']}", gid)

    def _assign(self, agent_id: str, action: str, params: dict,
                risk: str, goal_id: str):
        """Назначить задачу агенту через его inbox."""
        tid = str(uuid.uuid4())
        task = {
            "id": tid, "ts": now_ts(),
            "from": self.agent_id,
            "to": agent_id,
            "action": action,
            "profile": self.tasks[goal_id]["profile"],
            "risk": risk,
            "params": params,
            "confirmed_by": None,
            "goal_id": goal_id,
        }
        path = self.agents_dir / "inbox" / f"{agent_id}_{tid}.json"
        path.write_text(json.dumps(task, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        self.task_goal[tid] = goal_id
        self.tasks[goal_id]["results"][tid] = {"agent": agent_id,
                                                "status": "отправлено"}
        self._journal("assign_task", risk, "auto", "отправлено",
                      f"{action} → {agent_id} (цель {goal_id})", tid)
    # ----------------------------- сбор результатов -----------------------------
    def _collect_results(self):
        for path in sorted(self.outbox.glob("*.json")):
            if path.name.endswith(".tmp") or "__processed" in path.name:
                continue
            try:
                resp = json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue

            resp_tid = resp.get("in_response_to") or resp.get("goal_id")
            gid = self.task_goal.get(resp_tid)
            if gid and gid in self.tasks:
                tid = resp_tid
                if tid in self.tasks[gid]["results"]:
                    # Обновить existing запись (было «отправлено», стало фактический статус)
                    self.tasks[gid]["results"][tid].update({
                        "agent": resp.get("from"),
                        "status": resp.get("status"),
                        "result": resp.get("result"),
                        "error": resp.get("error"),
                    })
                else:
                    self.tasks[gid]["results"][tid] = {
                        "agent": resp.get("from"),
                        "status": resp.get("status"),
                        "result": resp.get("result"),
                        "error": resp.get("error"),
                    }
                # Если всё шаги цели завершены — фиксируем
                self._try_finalize_goal(gid)

            try:
                path.replace(path.parent / f"{path.stem}__processed.json")
            except Exception:
                pass

    def _try_finalize_goal(self, gid: str):
        task = self.tasks[gid]
        step_statuses = [v["status"] for v in task["results"].values()]
        if step_statuses and all(s in ("ok", "cancelled", "error")
                               for s in step_statuses):
            task["status"] = "завершено"
            self._journal("finalize_goal", "low", "auto", "завершено",
                          f"цель {gid} выполнена всеми шагами", gid)

    # ----------------------------- конфликты -----------------------------
    def _resolve_conflicts(self):
        for path in sorted(self.conflicts.glob("*.json")):
            try:
                rec = json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            if rec.get("status") != "open":
                continue
            # Координатор принимает решение: приоритет у агента с меньшим риском,
            # или эскалация к человеку при high risk.
            desc = rec.get("description", "")
            self._journal("resolve_conflict", "high", "координатор",
                          "разрешено",
                          f"конфликт {rec['id']}: {desc}", rec["id"])
            try:
                rec["status"] = "разрешено координатором"
                rec["resolved_ts"] = now_ts()
                path.write_text(json.dumps(rec, ensure_ascii=False, indent=2),
                                encoding="utf-8")
            except Exception:
                pass

    def run_goal(self, goal_text: str, profile: str = "бухгалтер",
                 wait_sec: int = 20) -> dict:
        """Принять цель и подождать выполнения (для CLI проверки)."""
        gid = self.accept_goal(goal_text, profile)
        deadline = time.time() + wait_sec
        while time.time() < deadline:
            self._tick()
            self._collect_results()
            if self.tasks[gid]["status"] == "завершено":
                break
            time.sleep(0.5)
        return self.tasks[gid]


if __name__ == "__main__":
    import sys
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:\1c_agent\exchange"
    c = Coordinator(ex)
    try:
        c.start()
        print("Координатор запущен. Введите цель (или Enter для демо):")
        text = input("> ").strip() or "покажи остатки на складе"
        res = c.run_goal(text, profile="бухгалтер", wait_sec=15)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    except KeyboardInterrupt:
        pass
    finally:
        c.stop()