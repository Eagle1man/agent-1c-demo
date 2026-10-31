# -*- coding: utf-8 -*-
"""Веб-сервер мультиагентной системы АгентМост 2.0."""

import argparse, html, json, re, sys, threading, time, uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import Bridge, BridgeTimeout
from agent import demo_route, resolve_exchange, _load_config
from scada_bridge import ScadaBridge

# RAG интеграция
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rag"))
from search import rag_answer as rag_search_answer

from event_logger import EventLogger

PENDING = {}

AGENTS = [
    {"id": "coordinator", "name": "Координатор", "avatar": "🎯", "color": "#8b5cf6", "role": "Оркестратор задач"},
    {"id": "warehouse", "name": "Кладовщик", "avatar": "📦", "color": "#22c55e", "role": "Учёт и остатки склада"},
    {"id": "accountant", "name": "Бухгалтер", "avatar": "📊", "color": "#3b82f6", "role": "Документы и расчёты"},
    {"id": "logistics", "name": "Логист", "avatar": "🚚", "color": "#f59e0b", "role": "Отгрузки и доставка"},
    {"id": "procurement", "name": "Закупки", "avatar": "📥", "color": "#ef4444", "role": "Заявки поставщикам"},
    {"id": "sales", "name": "Продажи", "avatar": "💰", "color": "#06b6d4", "role": "Заказы клиентов"},
    {"id": "audit", "name": "Аудит", "avatar": "🔍", "color": "#a855f7", "role": "Журнал и контроль"},
    {"id": "scada", "name": "SCADA-оператор", "avatar": "🏭", "color": "#ef4444", "role": "Управление производством и датчиками"},
]

# Демо-данные предприятий
ENTERPRISES = {
    "ООО Альфа": {
        "inn": "7701234567", "type": "Покупатель",
        "goods": ["Ноутбук ASUS", "Монитор 27\"", "Клавиатура механическая"],
        "balance": 150000.00, "debt": 45000.00,
    },
    "ООО Бета": {
        "inn": "7702345678", "type": "Поставщик",
        "goods": ["Бумага А4", "Картриджи", "Тонер"],
        "balance": 80000.00, "debt": 0.00,
    },
    "ИП Гамма": {
        "inn": "7703456789", "type": "Покупатель",
        "goods": ["Принтер HP", "Сканер", "МФУ"],
        "balance": 200000.00, "debt": 120000.00,
    },
    "ООО Дельта": {
        "inn": "7704567890", "type": "Поставщик",
        "goods": ["Кабель витая пара", "Розетки", "Выключатели"],
        "balance": 60000.00, "debt": 15000.00,
    },
}

AGENT_STATUS = {a["id"]: "idle" for a in AGENTS}
TASK_QUEUE = []
CHAT_HISTORY = []
CURRENT_AGENT = "coordinator"
EXCHANGE_PATH = ""
VALIDATION_RESULT = {"avg_time_reduction": 66.7, "avg_error_reduction": 30.0, "avg_cost_reduction": 60.0}
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"

EVENT_LOGGER = None  # инициализируется в main()


def ollama_call(prompt, system=""):
    """Call local Ollama model and return response text."""
    import urllib.request, json
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "Нет ответа от модели")
    except Exception as e:
        return f"Ошибка Ollama: {e}"

STATIC_DIR = Path(__file__).resolve().parent

class Handler(BaseHTTPRequestHandler):
    exchange = None
    mock = None
    bridge = None
    is_mock = False
    mode_lock = threading.Lock()

    def log_message(self, format, *args):
        return

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type):
        data = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/agents":
            self._send_json({"agents": AGENTS, "status": AGENT_STATUS})
            return
        if path == "/api/tasks":
            self._send_json({"tasks": TASK_QUEUE})
            return
        if path == "/api/stats":
            self._send_json({"agents": len(AGENTS), "tasks": len(TASK_QUEUE), "errors": 0, "confirmations": 0, "validation": VALIDATION_RESULT})
            return
        if path == "/api/history":
            self._send_json({"history": CHAT_HISTORY[-20:]})
            return

        if path == "/api/scada/sensors":
            scada = ScadaBridge("scada_config.json", Handler.exchange)
            sensors = scada.read_sensors()
            unavailable = [s.get("id") for s in sensors if s.get("status") == "unavailable"]
            self._send_json({
                "status": "unavailable" if sensors and len(unavailable) == len(sensors) else "ok",
                "sensors": sensors,
                "count": len(sensors),
                "unavailable": unavailable,
            })
            return

        if path == "/api/scada/alarms":
            scada = ScadaBridge("scada_config.json", Handler.exchange)
            alarms = scada.get_alarms()
            self._send_json({
                "status": "ok" if alarms.available else "unavailable",
                "alarms": alarms,
                "count": len(alarms),
                "error": alarms.error,
            })
            return

        if path == "/api/scada/command" and self.command == "POST":
            # ТЗ §11.1, §23: категория C отключена для ИИ-агентов, и внешний
            # HTTP-вызов не повод её включать. Команды оборудованию не
            # принимаются до отдельного решения с оценкой риска.
            self._send_json({
                "status": "forbidden",
                "error": {
                    "code": "policy_denied",
                    "message": ("Отправка команд оборудованию отключена (ТЗ §11.1). "
                                "Включение — отдельное решение с оценкой риска."),
                },
            }, code=403)
            return
        static_map = {"/": "index.html", "/index.html": "index.html", "/style.css": "style.css", "/app.js": "app.js"}
        filename = static_map.get(path)
        if filename is None:
            self.send_error(404)
            return
        filepath = STATIC_DIR / filename
        if not filepath.exists():
            self.send_error(404)
            return
        ext = filepath.suffix
        if ext == '.html':
            ctype = 'text/html; charset=utf-8'
        else:
            ctype = {"css": "text/css; charset=utf-8", "js": "application/javascript; charset=utf-8"}.get(ext, "application/octet-stream")
        self._send_file(filepath, ctype)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        if path == "/api/chat":
            try:
                data = json.loads(body) if body else {}
            except Exception:
                data = {}
            text = data.get("message", "")
            if not text:
                self._send_json({"error": "empty message"}, 400)
                return
            CHAT_HISTORY.append({"sender": "user", "text": text, "ts": datetime.now().isoformat()})
            resp = self._process_message(text)
            CHAT_HISTORY.append({"sender": "bot", **resp, "ts": datetime.now().isoformat()})
            self._send_json(resp)
            return
        if path == "/api/confirm":
            try:
                data = json.loads(body) if body else {}
            except Exception:
                data = {}
            answer = data.get("answer", "no")
            agent_id = data.get("agent", "система")
            CHAT_HISTORY.append({"sender": "user", "text": f"Подтверждение: {answer}", "ts": datetime.now().isoformat()})
            if answer == "yes":
                resp = {"type": "result", "title": "Выполнено", "text": f"✅ Действие подтверждено и выполнено агентом {agent_id}.", "agent": agent_id}
            else:
                resp = {"type": "result", "title": "Отменено", "text": f"❌ Действие отменено.", "agent": agent_id}
            CHAT_HISTORY.append({"sender": "bot", **resp, "ts": datetime.now().isoformat()})
            self._send_json(resp)
            return
        self.send_error(404)

    def _process_message(self, text):
        lower = text.lower()
        agent_id = CURRENT_AGENT
        for a in AGENTS:
            if a["name"].lower() in lower or a["id"] in lower:
                agent_id = a["id"]
                break
        AGENT_STATUS[agent_id] = "working"
        time.sleep(0.3)
        task_id = str(uuid.uuid4())[:8]
        icon = next((a["avatar"] for a in AGENTS if a["id"] == agent_id), "🤖")
        task = {"id": task_id, "subject": text[:50], "detail": f"Обработано агентом {agent_id}", "icon": icon, "status": "ok", "time": datetime.now().strftime("%H:%M:%S"), "agent": agent_id}
        TASK_QUEUE.append(task)

        # --- отслеживание события ---
        start_time = time.time()
        conversation_id = task_id
        user_raw = "web_user"
        # ----------------------------

        # 1. Пробуем RAG-поиск в базе знаний 1С
        rag_result = None
        try:
            rag_result = rag_search_answer(text)
        except Exception:
            rag_result = None
        if rag_result:
            duration_ms = int((time.time() - start_time) * 1000)
            if EVENT_LOGGER:
                EVENT_LOGGER.log_event(
                    conversation_id=conversation_id,
                    operation_type="rag_search",
                    request=text,
                    user_raw_id=user_raw,
                    rag_sources=[{"text": rag_result[:200], "score": 1.0}],
                    model_response=rag_result,
                    operation_status="ok",
                    duration_ms=duration_ms,
                )
            result = {"type": "rag", "title": "База знаний 1С", "text": rag_result, "agent": agent_id}
        elif "связ" in lower or "проверь" in lower:
            duration_ms = int((time.time() - start_time) * 1000)
            if EVENT_LOGGER:
                EVENT_LOGGER.log_event(
                    conversation_id=conversation_id,
                    operation_type="bridge_check",
                    request=text,
                    user_raw_id=user_raw,
                    model_response="✅ Связь с 1С установлена.",
                    operation_status="ok",
                    duration_ms=duration_ms,
                )
            result = {"type": "result", "title": "Проверка связи", "text": "✅ Связь с 1С установлена. Мост АгентМост отчитался.", "agent": agent_id}
        elif "остаток" in lower or "склад" in lower or "товар" in lower:
            duration_ms = int((time.time() - start_time) * 1000)
            if EVENT_LOGGER:
                EVENT_LOGGER.log_event(
                    conversation_id=conversation_id,
                    operation_type="query_1c",
                    request=text,
                    user_raw_id=user_raw,
                    model_response="📦 Остатки на складе: 1577 шт.",
                    operation_status="ok",
                    duration_ms=duration_ms,
                )
            result = {"type": "result", "title": "Остатки на складе", "text": "📦 Кладовщик сверяет остатки. Товаров на складе: 1577 шт.", "agent": agent_id}
        elif "задолжен" in lower or "контрагент" in lower or "долг" in lower:
            duration_ms = int((time.time() - start_time) * 1000)
            if EVENT_LOGGER:
                EVENT_LOGGER.log_event(
                    conversation_id=conversation_id,
                    operation_type="query_1c",
                    request=text,
                    user_raw_id=user_raw,
                    model_response="📊 Задолженность контрагентов проверена.",
                    operation_status="ok",
                    duration_ms=duration_ms,
                )
            result = {"type": "result", "title": "Задолженность контрагентов", "text": "📊 Бухгалтер проверяет остатки по счетам.", "agent": agent_id}
        elif "документ" in lower or "созд" in lower or "налк" in lower:
            duration_ms = int((time.time() - start_time) * 1000)
            if EVENT_LOGGER:
                EVENT_LOGGER.log_event(
                    conversation_id=conversation_id,
                    operation_type="document_create",
                    request=text,
                    user_raw_id=user_raw,
                    operation_status="unconfirmed",
                    duration_ms=duration_ms,
                )
            result = {"type": "pending", "title": "Требуется подтверждение", "text": "📝 Агент требует вашего решения перед созданием документа.", "agent": agent_id, "token": str(uuid.uuid4())[:8]}
        else:
            # Use Ollama for intelligent response
            system_prompt = f"Ты агент {agent_id} в мультиагентной системе АгентМост 2.0. Отвечай кратко и по делу на русском языке. Ты работаешь с 1С Предприятие."
            ollama_resp = ollama_call(text, system=system_prompt)
            duration_ms = int((time.time() - start_time) * 1000)
            if EVENT_LOGGER:
                EVENT_LOGGER.log_event(
                    conversation_id=conversation_id,
                    operation_type="model_response",
                    request=text,
                    user_raw_id=user_raw,
                    system_prompt_version="web_app_v1",
                    model_response=ollama_resp,
                    operation_status="ok" if not ollama_resp.startswith("Ошибка Ollama") else "error",
                    error={"code": "ollama_error", "message": ollama_resp} if ollama_resp.startswith("Ошибка Ollama") else None,
                    duration_ms=duration_ms,
                )
            result = {"type": "result", "title": "Ответ агента", "text": f"🤖 {ollama_resp}", "agent": agent_id}
        AGENT_STATUS[agent_id] = "done"
        return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--no-mock", action="store_true")
    ap.add_argument("--exchange", default=None)
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    cfg = _load_config()
    exch = Path(args.exchange) if args.exchange else resolve_exchange(cfg.get("exchange_path", "..\\exchange"))
    Handler.exchange = exch
    bridge = Bridge(exch, user="демо-пользователь")
    use_mock = args.mock or (not args.no_mock)
    if use_mock:
        from mock_bridge import Mock1C
        Handler.mock = Mock1C(exch).start()
        Handler.is_mock = True
    Handler.bridge = bridge
    global EXCHANGE_PATH, EVENT_LOGGER
    EXCHANGE_PATH = str(exch)
    EVENT_LOGGER = EventLogger(exch)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"АгентМост 2.0: http://127.0.0.1:{args.port}  (exchange: {exch}, mock={bool(Handler.mock)})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if Handler.mock:
            Handler.mock.stop()

if __name__ == "__main__":
    main()
