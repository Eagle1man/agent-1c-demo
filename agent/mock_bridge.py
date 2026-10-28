# -*- coding: utf-8 -*-
"""Эмулятор 1С-моста (Mock1C) для проверки агента без установленной 1С.

Повторяет протокол v1.0 (PROTOCOL.md): валидацию запросов, ПЕРВЫЕ 50,
двухподтверждение создания документа, архивацию команд."""
import json
import threading
import time
from datetime import datetime
from pathlib import Path

FORBIDDEN = ("ИЗМЕНИТЬ", "УДАЛИТЬ", "ЗАПИСАТЬ", "ВЫЗВАТЬ", "ДОБАВИТЬ",
             "DELETE", "UPDATE", "INSERT", "DROP", "ТРАНЗАКЦИЯ")
DEMO_COUNTERPARTIES = ("ООО Ромашка", "ООО Ветка", "ИП Иванов")
DEMO_ITEMS = ("Товар А", "Товар Б", "Услуга монтажа")


def now_ts():
    return datetime.now().isoformat(timespec="seconds")


class Mock1C:
    def __init__(self, exchange_path, delay=0.15):
        self.root = Path(exchange_path)
        for sub in ("commands", "responses", "archive", "log"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self._stop = threading.Event()
        self._thread = None
        self._doc_seq = 122

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    # --- цикл опроса (как ПодключитьОбработчикОжидания в 1С) ---
    def _loop(self):
        while not self._stop.is_set():
            busy = False
            for path in sorted((self.root / "commands").glob("*.json")):
                self._handle(path)
                busy = True
            if not busy:
                time.sleep(0.1)

    def _handle(self, path):
        time.sleep(self.delay)
        try:
            cmd = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(cmd.get("id"), str):
                raise ValueError("нет id")
            resp = self._route(cmd)
        except Exception as exc:  # parse_error
            cid = path.stem
            resp = self._resp(cid, "error", None,
                              {"code": "parse_error", "message": str(exc)})
            self._write(cid, resp)
            self._archive(path, "error")
            return
        self._write(cmd["id"], resp)
        self._archive(path, "done" if resp["status"] != "error" else "error")

    def _write(self, cid, resp):
        tmp = self.root / "responses" / f"{cid}.json.tmp"
        final = self.root / "responses" / f"{cid}.json"
        tmp.write_text(json.dumps(resp, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(final)

    def _archive(self, path, verdict):
        target = self.root / "archive" / f"{path.stem}__{verdict}.json"
        path.replace(target)

    def _resp(self, cid, status, result, error):
        return {"protocol": "1.0", "id": cid, "ts": now_ts(), "status": status,
                "result": result, "error": error, "executed_by": "АгентМост 1.0 (mock)"}

    # --- маршрутизация действий (зеркалит .bsl) ---
    def _route(self, cmd):
        cid = cmd.get("id")
        action = cmd.get("action")
        if action == "проверка_связи":
            return self._resp(cid, "ok",
                              {"platform": "8.3.27.1508 (mock)", "bsl_version": "1.0"},
                              None)
        if action == "запрос_1с":
            return self._query(cid, (cmd.get("params") or {}).get("query", ""))
        if action == "создать_документ":
            return self._document(cid, cmd)
        return self._resp(cid, "error", None,
                          {"code": "unsupported_action", "message": str(action)})

    def _query(self, cid, query):
        q = (query or "").replace("\ufeff", "").strip()
        for line in list(q.splitlines()):
            if line.strip().startswith("//"):
                q = q.replace(line, "")
        upper = " ".join(q.upper().split())
        hits = [w for w in FORBIDDEN if w in upper] + ([";"] if ";" in q else [])
        if hits:
            return self._resp(cid, "error", None, {
                "code": "invalid_query",
                "message": "Запрос содержит запрещённые операции: "
                           + ", ".join(f"«{h}»" for h in hits)})
        if not upper.startswith("ВЫБРАТЬ"):
            return self._resp(cid, "error", None, {
                "code": "invalid_query",
                "message": "Запрос должен начинаться с ВЫБРАТЬ (только чтение)"})
        if "ПЕРВЫЕ" not in upper:
            q = q.replace("ВЫБРАТЬ", "ВЫБРАТЬ ПЕРВЫЕ 50", 1)  # лимит учебной 1С
        if "ОСТАТОК" in upper or "СКЛАД" in upper or "ТОВАР" in upper:
            cols = ["Номенклатура", "Остаток"]
            rows = [["Товар А", 120], ["Товар Б", 45], ["Услуга монтажа", None]]
        elif "КОНТРАГЕНТ" in upper or "ЗАДОЛЖ" in upper or "САЛЬДО" in upper:
            cols = ["Контрагент", "Задолженность"]
            rows = [["ООО Ромашка", 15000], ["ООО Ветка", 0], ["ИП Иванов", -2300]]
        elif "ЗАКАЗ" in upper:
            cols = ["Номер", "Дата"]
            rows = [["ЗП-0001", "2026-09-15"], ["ЗП-0002", "2026-09-18"]]
        else:
            cols = ["Параметр", "Значение"]
            rows = [[upper[:40], "демо-ответ mock 1С"]]
        return self._resp(cid, "ok",
                          {"columns": cols, "rows": rows,
                           "row_count": len(rows), "truncated": False},
                          None)

    def _document(self, cid, cmd):
        params = cmd.get("params") or {}
        if not cmd.get("confirmed_by"):
            return self._resp(cid, "need_confirmation", {"echo": params}, None)
        if params.get("doc_type") != "РеализацияТоваровУслуг":
            return self._resp(cid, "error", None, {
                "code": "unsupported_doc_type",
                "message": f"Вид документа «{params.get('doc_type')}» в демо-базе нет"})
        party = params.get("counterparty")
        if party not in DEMO_COUNTERPARTIES:
            return self._resp(cid, "error", None, {
                "code": "execution_error",
                "message": f"Контрагент «{party}» не найден. В демо есть: "
                           + ", ".join(DEMO_COUNTERPARTIES)})
        for pos in params.get("positions", []):
            if pos.get("item") not in DEMO_ITEMS:
                return self._resp(cid, "error", None, {
                    "code": "execution_error",
                    "message": f"Номенклатура «{pos.get('item')}» не найдена. "
                               "В демо есть: " + ", ".join(DEMO_ITEMS)})
        self._doc_seq += 1
        return self._resp(cid, "ok", {
            "number": f"РН-{self._doc_seq:06d}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "posted": True}, None)
