# -*- coding: utf-8 -*-
"""Служба диалога «окно в 1С <-> нейросеть» (локальный Qwen через Ollama).

Учебная 1С не даёт COM/HTTP, поэтому окно в 1С и модель общаются через папки:
    exchange/chat/requests/<id>.json    — фраза, набранная в окне 1С
    exchange/chat/responses/<id>.json   — готовый текстовый ответ для 1С
    exchange/chat/archive/              — обработанные запросы (история показа)
    exchange/chat/state.json            — незавершённое подтверждение («да/нет»)

Логика (по концепции): низкий риск — агент делает сам; высокий риск
(создание документа) — агент останавливается и ждёт слово «да» человека;
каждое решение пишется в журнал (journal.jsonl).

Запуск (живая 1С):
    py -3 agent\chat_service.py --exchange C:\1c_agent\exchange
Проверка без 1С (эмулятор):
    py -3 agent\chat_service.py --mock --phrase "остатки на складе"
"""
import argparse
import json
import sys
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import Bridge, BridgeTimeout                       # noqa: E402
from tools import RISK, format_response                        # noqa: E402
import agent as agent_mod                                      # noqa: E402
from web_app import (qwen_route, QWEN_MODEL, QWEN_URL,         # noqa: E402
                     QWEN_TIMEOUT, LIVE_SALES_Q, LIVE_PARTNERS_Q,
                     LIVE_DOCS_Q)
from event_logger import EventLogger                           # noqa: E402

CONFIRM_YES = ("да", "д", "yes", "y", "ок", "ok", "подтверждаю", "создавай", "верно")
CONFIRM_NO = ("нет", "н", "no", "n", "отмена", "отменить", "не надо")

# Шаблоны демо-режима смотрят в регистры, которых нет в учебной базе, —
# подменяем живыми запросами (в DemoAgentT 12 контрагентов, 385 документов).
LIVE = {agent_mod.STOCK_Q: LIVE_SALES_Q,
        agent_mod.DEBT_Q: LIVE_PARTNERS_Q,
        agent_mod.ORDERS_Q: LIVE_DOCS_Q}


def now_ts():
    return datetime.now().isoformat(timespec="seconds")


class ChatService:
    """Диалог с моделью: файлы из 1С -> Qwen -> текстовый ответ в 1С."""

    def __init__(self, exchange, profile="бухгалтер", use_mock=False):
        self.root = Path(exchange)
        self.chat = self.root / "chat"
        for sub in ("requests", "responses", "archive", "log"):
            (self.chat / sub).mkdir(parents=True, exist_ok=True)
        self.state_path = self.chat / "state.json"
        self.log_path = self.chat / "log" / "service.log"
        self.bridge = Bridge(self.root, user="окно 1С")
        self.profile = profile
        self.mock = None
        if use_mock:
            from mock_bridge import Mock1C
            self.mock = Mock1C(self.root).start()
        self.pending = self._load_state()
        self.event_logger = EventLogger(self.root)

    # ---------------------------------------------------------------- служебное
    def _load_state(self):
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def _save_state(self):
        try:
            self.state_path.write_text(
                json.dumps(self.pending, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception:
            pass

    def _log(self, line):
        try:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(now_ts() + " " + line + "\n")
        except Exception:
            pass

    def stop(self):
        if self.mock:
            self.mock.stop()

    # ---------------------------------------------------------------- действия
    def _run(self, action, params, risk=None):
        """Отправить команду в 1С и вернуть ответ (dict)."""
        risk = risk or RISK.get(action, "low")
        if action == "запрос_1с":
            params = dict(params)
            params["query"] = LIVE.get(params.get("query"), params.get("query", ""))
        try:
            return self.bridge.send(action, params, self.profile, risk, timeout=20.0)
        except BridgeTimeout as exc:
            return {"status": "error",
                    "error": {"code": "bridge_timeout", "message": str(exc)}}

    def _confirm_answer(self, phrase):
        """Ответ человека на запрос подтверждения: (текст, статус, pending) или None."""
        low = phrase.strip().lower()
        pend = self.pending.get("create")
        if not pend:
            return None
        params = pend.get("params") or {}
        if low in CONFIRM_NO:
            self.bridge.journal("создать_документ", "high", "human_rejected",
                                "cancelled",
                                "человек отклонил: " + str(params.get("counterparty")))
            self.pending.pop("create", None)
            self._save_state()
            return ("Отменено: документ в 1С НЕ создан. Решение записано в журнал.",
                    "cancelled", False)
        if low in CONFIRM_YES:
            resp = self.bridge.send("создать_документ", params, self.profile, "high",
                                    confirmed_by=self.bridge.confirmed_by(), timeout=20.0)
            self.pending.pop("create", None)
            self._save_state()
            self.bridge.journal("создать_документ", "high", "human_confirmed",
                                resp.get("status"),
                                "подтверждено человеком: " + str(params.get("counterparty")),
                                resp.get("id"))
            ok = resp.get("status") == "ok"
            return (format_response(resp), "ok" if ok else "error", False)
        return None

    # ------------------------------------------------------------ понимание фразы
    # Явные слова-подсказки: демо не должно зависеть от слабой модели.
    KEYWORDS = (("связ", "связь"), ("пинг", "связь"),
                ("остат", "остатки"), ("склад", "остатки"), ("продаж", "остатки"),
                ("задолж", "долг"), ("долг", "долг"), ("взаиморасч", "долг"),
                ("заказ", "док"), ("документ", "док"), ("реализац", "док"),
                ("контрагент", "контр"), ("реквизит", "контр"), ("инн", "контр"))

    def _route_keywords(self, phrase):
        """Детерминированные фразы — работают даже без модели."""
        t = phrase.lower()
        for word, kind in self.KEYWORDS:
            if word in t:
                if kind == "связь":
                    return "проверка_связи", {}
                if kind == "остатки":
                    return "запрос_1с", {"query": agent_mod.STOCK_Q}
                if kind == "долг":
                    return "запрос_1с", {"query": agent_mod.DEBT_Q}
                if kind == "док":
                    return "запрос_1с", {"query": agent_mod.ORDERS_Q}
                if kind == "контр":
                    return "запрос_1с", {"query": agent_mod.PARTY_Q}
        return None

    def _route(self, phrase):
        """(action, params), источник: правила демо или Qwen."""
        route = agent_mod.demo_route(phrase, self.profile)
        if route is not None:
            return route, "правила"
        route = self._route_keywords(phrase)
        if route is not None:
            return route, "правила"
        q = qwen_route(phrase)
        if not q:
            return None, None
        intent = q.get("intent")
        if intent == "check":
            return ("проверка_связи", {}), "Qwen"
        if intent == "query" and q.get("query"):
            return ("запрос_1с", {"query": str(q["query"])}), "Qwen"
        if intent == "stock":
            return ("запрос_1с", {"query": agent_mod.STOCK_Q}), "Qwen"
        if intent == "debt":
            return ("запрос_1с", {"query": agent_mod.DEBT_Q}), "Qwen"
        if intent == "orders":
            return ("запрос_1с", {"query": agent_mod.ORDERS_Q}), "Qwen"
        if intent == "party":
            return ("запрос_1с", {"query": agent_mod.PARTY_Q}), "Qwen"
        if intent == "create":
            from web_app import (FULL_PARTIES, FULL_ITEMS, _find_name,
                                 enrich_doc_params)
            t = (phrase + " " + str(q.get("counterparty") or "")).lower()
            party = _find_name(t, FULL_PARTIES) or "ООО Ромашка"
            t2 = (phrase + " " + str(q.get("item") or "")).lower()
            item = _find_name(t2, FULL_ITEMS) or "Товар А"
            try:
                qty = int(q.get("qty") or 0) or 10
            except Exception:
                qty = 10
            try:
                price = int(q.get("price") or 0) or 150
            except Exception:
                price = 150
            params = {"doc_type": "РеализацияТоваровУслуг", "counterparty": party,
                      "positions": [{"item": item, "qty": qty, "price": price}]}
            return ("создать_документ", enrich_doc_params(phrase, params)), "Qwen"
        return None, None

    def _smalltalk(self, phrase):
        """Свободный разговор с моделью (когда это не задача для 1С)."""
        system = ("Ты — ИИ-агент, встроенный в 1С:Предприятие (демонстрация). "
                  "Отвечай по-русски, кратко (3-5 предложений), по делу. "
                  "Ты умеешь читать данные 1С (остатки, задолженность, документы, "
                  "контрагенты) и готовить документы после подтверждения человека. "
                  "Если вопрос про данные предприятия — предложи сформулировать "
                  "задачу, например: «покажи задолженность контрагентов».")
        payload = json.dumps({"model": QWEN_MODEL, "stream": False,
                              "messages": [{"role": "system", "content": system},
                                           {"role": "user", "content": phrase[:500]}]}
                             ).encode("utf-8")
        try:
            req = urllib.request.Request(QWEN_URL, data=payload,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=QWEN_TIMEOUT) as r:
                data = json.loads(r.read().decode("utf-8"))
            text = ((data.get("message") or {}).get("content") or "").strip()
            return text or "Модель не дала ответа — переформулируйте, пожалуйста."
        except Exception as exc:
            return ("Нейросеть недоступна (" + str(exc)[:80] +
                    "). Проверьте: ollama serve и модель " + QWEN_MODEL + ".")

    # ------------------------------------------------------------------ обработка
    def process(self, request):
        """Фраза из 1С -> текст ответа (dict для responses/<id>.json)."""
        phrase = str(request.get("phrase") or "").strip()
        profile = str(request.get("profile") or "")
        if profile:
            self.profile = profile
        self._log("request " + str(request.get("id")) + ": " + phrase)

        # --- отслеживание события ---
        start_time = time.time()
        conversation_id = str(request.get("id") or str(uuid.uuid4()))
        user_raw = str(request.get("user") or "")
        # ----------------------------

        if not phrase:
            duration_ms = int((time.time() - start_time) * 1000)
            self.event_logger.log_event(
                conversation_id=conversation_id,
                operation_type="chat_query",
                request=phrase,
                user_raw_id=user_raw,
                operation_status="error",
                error={"code": "empty_phrase", "message": "пустая фраза"},
                duration_ms=duration_ms,
            )
            return {"status": "error", "answer": "Пустая фраза.",
                    "error": {"code": "empty_phrase", "message": "Нет текста"}}

        low = phrase.lower()
        if low in CONFIRM_YES or low in CONFIRM_NO:
            decided = self._confirm_answer(phrase)
            if decided is None:
                decided = ("Сейчас нечего подтверждать — нет подготовленного документа.",
                           "ok", False)
            text, status, pending = decided
            duration_ms = int((time.time() - start_time) * 1000)
            self.event_logger.log_event(
                conversation_id=conversation_id,
                operation_type="document_confirm",
                request=phrase,
                user_raw_id=user_raw,
                operation_status="ok" if status != "error" else "error",
                duration_ms=duration_ms,
            )
            return {"status": "ok" if status != "error" else "error",
                    "answer": text, "pending": False, "kind": "doc"}

        route, source = self._route(phrase)
        if route is None:
            duration_ms = int((time.time() - start_time) * 1000)
            self.event_logger.log_event(
                conversation_id=conversation_id,
                operation_type="chat_query",
                request=phrase,
                user_raw_id=user_raw,
                model_response=("smalltalk: " + self._smalltalk(phrase)),
                operation_status="ok",
                duration_ms=duration_ms,
            )
            return {"status": "ok", "answer": self._smalltalk(phrase),
                    "kind": "chat", "pending": False}

        action, params = route
        risk = RISK.get(action, "high")
        if action == "создать_документ":
            resp = self._run(action, params, risk)
            if resp.get("status") == "need_confirmation":
                echo = (resp.get("result") or {}).get("echo", params)
                self.pending["create"] = {"params": params, "ts": now_ts()}
                self._save_state()
                self.bridge.journal(action, risk, "awaiting_human", "need_confirmation",
                                    "запрошено подтверждение: "
                                    + str(echo.get("counterparty")), resp.get("id"))
                lines = ["Высокий риск — решает человек. Готов создать:",
                         "  " + str(echo.get("doc_type")) + " на "
                         + str(echo.get("counterparty"))]
                for pos in echo.get("positions", []):
                    try:
                        s = float(pos.get("qty") or 0) * float(pos.get("price") or 0)
                    except Exception:
                        s = 0
                    lines.append("    - " + str(pos.get("item")) + ": "
                                 + str(pos.get("qty")) + " x " + str(pos.get("price"))
                                 + " = " + format(s, "g"))
                lines.append("Документ в 1С НЕ создан. Напишите «да» — создам, "
                             "«нет» — отменю.")
                duration_ms = int((time.time() - start_time) * 1000)
                self.event_logger.log_event(
                    conversation_id=conversation_id,
                    operation_type="document_create",
                    request=phrase,
                    user_raw_id=user_raw,
                    tools_called=[{"action": action, "params": params}],
                    tool_results=[{"status": "need_confirmation", "echo": echo}],
                    operation_status="unconfirmed",
                    duration_ms=duration_ms,
                )
                return {"status": "ok", "answer": "\n".join(lines),
                        "kind": "confirm", "pending": True, "tool": action}
            self.bridge.journal(action, risk, "auto", resp.get("status"),
                                (resp.get("error") or {}).get("message", ""),
                                resp.get("id"))
            duration_ms = int((time.time() - start_time) * 1000)
            self.event_logger.log_event(
                conversation_id=conversation_id,
                operation_type="document_create",
                request=phrase,
                user_raw_id=user_raw,
                tools_called=[{"action": action, "params": params}],
                tool_results=[{"status": resp.get("status"), "error": resp.get("error")}],
                operation_status=resp.get("status", "error"),
                duration_ms=duration_ms,
            )
            return {"status": "ok", "answer": format_response(resp),
                    "kind": "doc", "pending": False, "tool": action}

        resp = self._run(action, params, risk)
        self.bridge.journal(action, risk, "auto", resp.get("status"),
                            ("строк: " + str((resp.get("result") or {}).get("row_count")))
                            if action == "запрос_1с" else "проверка связи",
                            resp.get("id"))
        duration_ms = int((time.time() - start_time) * 1000)
        self.event_logger.log_event(
            conversation_id=conversation_id,
            operation_type=action,
            request=phrase,
            user_raw_id=user_raw,
            tools_called=[{"action": action, "params": params}],
            tool_results=[{"status": resp.get("status"), "result": resp.get("result"), "error": resp.get("error")}],
            operation_status=resp.get("status", "error"),
            duration_ms=duration_ms,
        )
        prefix = "🧠 Qwen понял задачу как «" + action + "»\n" if source == "Qwen" else ""
        return {"status": "ok", "answer": prefix + format_response(resp),
                "kind": "data", "pending": False, "tool": action,
                "query": params.get("query"), "src": source}

    # ------------------------------------------------------- файлы: приём и ответ
    def handle_file(self, path):
        """Обработать один файл запроса: ответ записать, запрос — в архив."""
        try:
            request = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            self._log("parse_error " + path.name + ": " + str(exc))
            try:
                path.replace(self.chat / "archive" / (path.stem + "__error.json"))
            except Exception:
                pass
            return None
        rid = str(request.get("id") or path.stem)
        try:
            payload = self.process(request)
        except Exception as exc:
            payload = {"status": "error", "answer": "[сбой службы] " + str(exc),
                       "error": {"code": "execution_error", "message": str(exc)}}
        answer = {"protocol": "1.1", "id": rid, "ts": now_ts(),
                  "status": payload.get("status", "ok"),
                  "answer": payload.get("answer", ""),
                  "kind": payload.get("kind", "chat"),
                  "pending": bool(payload.get("pending")),
                  "tool": payload.get("tool"),
                  "query": payload.get("query"),
                  "executed_by": "chat_service 1.1"}
        tmp = self.chat / "responses" / (rid + ".json.tmp")
        tmp.write_text(json.dumps(answer, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.chat / "responses" / (rid + ".json"))
        try:
            path.replace(self.chat / "archive" / (rid + "__request.json"))
        except Exception:
            pass
        self._log("answered " + rid + ": " + repr(answer["answer"][:120]))
        return answer

    def tick(self):
        n = 0
        for path in sorted((self.chat / "requests").glob("*.json")):
            if path.name.endswith(".tmp"):
                continue
            self.handle_file(path)
            n += 1
        return n

    def watch(self, interval=1.0):
        print("Служба диалога: exchange=" + str(self.root) + " модель=" + QWEN_MODEL
              + " mock=" + str(bool(self.mock)))
        print("Жду фразы из окна 1С (папка chat/requests). Ctrl+C — выход.")
        while True:
            try:
                n = self.tick()
                if n:
                    print(now_ts() + " обработано запросов: " + str(n))
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                self._log("tick error: " + str(exc))
            time.sleep(interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exchange", default=r"C:\1c_agent\exchange")
    ap.add_argument("--profile", default="бухгалтер")
    ap.add_argument("--model", default=QWEN_MODEL,
                    help="модель Ollama, например qwen2.5:1.5b или qwen3:4b")
    ap.add_argument("--mock", action="store_true", help="эмулятор 1С (без 1С)")
    ap.add_argument("--once", action="store_true", help="обработать очередь и выйти")
    ap.add_argument("--phrase", default=None, help="проверка: обработать фразу напрямую")
    args = ap.parse_args()

    # модель можно переключить без правок кода: --model qwen3:4b
    import web_app as _web
    _web.QWEN_MODEL = args.model
    globals()["QWEN_MODEL"] = args.model
    svc = ChatService(args.exchange, args.profile, use_mock=args.mock)
    try:
        if args.phrase:
            req = {"id": str(uuid.uuid4()), "phrase": args.phrase,
                   "profile": args.profile}
            print(json.dumps(svc.process(req), ensure_ascii=False, indent=2))
        elif args.once:
            print("обработано запросов:", svc.tick())
        else:
            try:
                svc.watch()
            except KeyboardInterrupt:
                print("\nОстановлено.")
    finally:
        svc.stop()


if __name__ == "__main__":
    main()
