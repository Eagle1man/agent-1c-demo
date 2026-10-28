# -*- coding: utf-8 -*-
"""Чат-агент для 1С: профили бухгалтер/логист (демо по концепции).

Режимы:
  * ollama — официальный SDK, tool calling (Qwen локально, данные не уходят);
  * demo   — разбор по ключевым словам, работает без установленной модели.
Автономность: low — агент делает сам; high — только с подтверждением человека.
"""
import json
import re
import sys
import threading
from pathlib import Path

from bridge import Bridge, BridgeTimeout
from tools import execute_tool, format_response

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    # ввод/вывод единообразно UTF-8 (консоль и пайп), без UnicodeError
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FROZEN = getattr(sys, "frozen", False)  # собрано PyInstaller в .exe
if FROZEN:
    ROOT = Path(sys.executable).resolve().parent
    _BUNDLE = Path(getattr(sys, "_MEIPASS", ROOT))
else:
    ROOT = Path(__file__).resolve().parent
    _BUNDLE = ROOT


def _load_config():
    external = ROOT / "config.json"  # рядом с exe (правится пользователем)
    if external.exists():
        return json.loads(external.read_text(encoding="utf-8"))
    bundled = _BUNDLE / "config.json"
    cfg = json.loads(bundled.read_text(encoding="utf-8")) if bundled.exists() else {}
    if FROZEN:
        cfg["exchange_path"] = "exchange"  # папка обмена — в одной папке с exe
    return cfg


CONFIG = _load_config()

BANNER = """
 Гуманистический ИИ-агент для 1С (демо)
 Агент выполняет работу — человек принимает решения.
 Профили: /бухгалтер | /логист   справка: /помощь   выход: /выход
"""

HELP = """Команды:
  /бухгалтер, /логист — сменить профиль
  /режим   — перепроверить наличие Ollama
  /помощь  — эта справка
  /выход   — выйти
Фразы демо-режима: «проверь связь», «остатки на складе»,
«задолженность контрагентов», «сколько заказов», «реквизиты контрагентов»,
«создай накладную на ООО Ромашка 10 шт».
Высокорисковые действия агент не выполнит без вашего «да»."""

# Демо-запросы без параметров «&» — выполняются в любой типовой конфигурации.
STOCK_Q = ("ВЫБРАТЬ ПЕРВЫЕ 50 Номенклатура, КоличествоОстаток КАК Остаток "
           "ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки()")
DEBT_Q = ("ВЫБРАТЬ ПЕРВЫЕ 50 Контрагент, СуммаОстаток КАК Задолженность "
          "ИЗ РегистрБухгалтерии.Хозрасчетный.Остатки()")
ORDERS_Q = ("ВЫБРАТЬ ПЕРВЫЕ 50 Номер, Дата ИЗ Документ.ЗаказПокупателя "
            "ГДЕ НЕ ПометкаУдаления")
PARTY_Q = "ВЫБРАТЬ ПЕРВЫЕ 50 Наименование, ИНН, КПП ИЗ Справочник.Контрагенты"

DEMO_PARTIES = ("ООО Ромашка", "ООО Ветка", "ИП Иванов")
DEMO_ITEMS = ("Товар А", "Товар Б", "Услуга монтажа")

CREATE_WORDS = ("создай", "создать", "оформи", "оформить",
                "выпусти", "выпустить", "проведи")
DOC_WORDS = ("накладн", "документ", "реализац")


def resolve_exchange(path_str):
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p).resolve()


def demo_route(text, profile):
    """(action, params) по фразе пользователя демо-режима, либо None."""
    t = text.lower()

    if any(w in t for w in CREATE_WORDS) and any(w in t for w in DOC_WORDS):
        party = next((n for n in DEMO_PARTIES if n.lower() in t), "ООО Ромашка")
        item = next((n for n in DEMO_ITEMS if n.lower() in t), "Товар А")
        m_qty = re.search(r"(\d+)\s*(?:шт|штук)", t)
        m_price = re.search(r"(?:по|цен[аы])\s*(\d+)", t)
        qty = int(m_qty.group(1)) if m_qty else 10
        price = int(m_price.group(1)) if m_price else 150
        return "создать_документ", {
            "doc_type": "РеализацияТоваровУслуг",
            "counterparty": party,
            "positions": [{"item": item, "qty": qty, "price": price}]}

    if any(k in t for k in ("связь", "пинг", "видит ли", "запущен", "соединен")):
        return "проверка_связи", {}
    if any(k in t for k in ("остатк", "склад", "сколько товар")):
        return "запрос_1с", {"query": STOCK_Q}
    if any(k in t for k in ("задолжен", "сальдо", "долг")):
        return "запрос_1с", {"query": DEBT_Q}
    if "заказ" in t:
        return "запрос_1с", {"query": ORDERS_Q}
    if any(k in t for k in ("контрагент", "реквизит", "инн")):
        return "запрос_1с", {"query": PARTY_Q}
    if any(k in t for k in ("сколько", "покажи", "выбери", "отчёт", "отчет", "дай")):
        return "запрос_1с", {"query": STOCK_Q if profile == "логист" else PARTY_Q}
    return None

# ---------------- режимы и запуск ----------------

def detect_mode():
    """ollama — если SDK есть, сервер отвечает и модель скачана; иначе demo."""
    if CONFIG.get("mode") == "demo":
        return "demo"
    try:
        import ollama
        resp = ollama.list()
        names = []
        for m in getattr(resp, "models", []) or []:
            name = (getattr(m, "model", None) or getattr(m, "name", None)
                    or (m.get("model") if isinstance(m, dict) else None)
                    or (m.get("name") if isinstance(m, dict) else None))
            if name:
                names.append(name)
        want = CONFIG.get("model", "")
        base = want.split(":")[0]
        if want and names and not any(
                n == want or n.split(":")[0] == base for n in names):
            print(f"[модель] «{want}» не найдена в Ollama — скачайте: "
                  f"ollama pull {want} (установлены: {', '.join(names)})")
            return "demo"
        return "ollama"
    except Exception:
        return "demo"


def ollama_turn(bridge, history, profile, model, input_func=input, print_func=print):
    """Цикл tool calling по официальной документации Ollama (до 6 шагов)."""
    from tools import TOOLS

    for _ in range(6):
        import ollama
        resp = ollama.chat(model=model, messages=history, tools=TOOLS)
        msg = resp.message
        history.append(msg)
        if not msg.tool_calls:
            print_func(msg.content or "")
            return
        for call in msg.tool_calls:
            fn = call.function
            args = dict(fn.arguments or {})
            print_func(f"  > инструмент: {fn.name}")
            result_json = execute_tool(bridge, fn.name, args, profile,
                                       input_func=input_func, print_func=print_func)
            print_func(format_response(json.loads(result_json)))
            history.append({"role": "tool", "tool_name": fn.name,
                            "content": result_json})


def main():
    # Веб-режим: в собранном exe по умолчанию (двойной клик по ярлыку)
    # открывается наглядный веб-интерфейс; консоль — только с флагом --cli.
    if "--web" in sys.argv or (FROZEN and "--cli" not in sys.argv):
        import webbrowser
        import web_app
        port = 8000
        for i, a in enumerate(sys.argv):
            if a == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    pass
        if "--no-mock" not in sys.argv and "--mock" not in sys.argv:
            sys.argv.append("--mock")  # как раньше: exe сам поднимает эмулятор 1С
        if "--port" not in sys.argv:
            sys.argv += ["--port", str(port)]
        sys.argv = [a for a in sys.argv if a not in ("--web", "--cli")]
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
        print(f"Открываю веб-интерфейс: http://127.0.0.1:{port}")
        print("(консольный режим: demo_agent_1c.exe --cli)")
        web_app.main()
        return
    print(BANNER)
    exchange = resolve_exchange(CONFIG["exchange_path"])
    bridge = Bridge(exchange, user=CONFIG.get("user", "демо-пользователь"))
    profile = CONFIG.get("profile", "бухгалтер")

    mock = None
    want_mock = "--mock" in sys.argv or (FROZEN and "--no-mock" not in sys.argv)
    if want_mock:
        from mock_bridge import Mock1C
        mock = Mock1C(exchange).start()
        print("Эмулятор 1С запущен — демонстрация работает без установленной 1С.")

    mode = detect_mode()
    if "--demo" in sys.argv:
        mode = "demo"  # детерминированный показ: без обращений к модели
    model = CONFIG.get("model", "qwen3:1.7b")
    print(f"Режим: {'Ollama + ' + model if mode == 'ollama' else 'демо (без модели)'}")
    print(f"Exchange: {exchange}")
    chk = bridge.check(timeout=4)
    print("1С: " + (format_response(chk) if chk else
                    "не отвечает — запустите «АгентМост» в 1С или перезапустите с --mock"))

    keep_history = bool(CONFIG.get("keep_history", False))

    def build_system():
        # Пересобирается на каждом ходу — профиль мог смениться (/логист)
        return (
            "Ты — агент для работы с 1С. Профиль: " + profile + ". "
            "Отвечай по-русски и кратко. Для действий в 1С вызывай инструменты. "
            "Запросы формируй только на встроенном языке 1С: начинаются с ВЫБРАТЬ, "
            "без «;», без параметров «&», всегда с ПЕРВЫЕ 50; английский SQL "
            "(SELECT/FROM/WHERE) не используй — только ВЫБРАТЬ/ИЗ/ГДЕ. "
            "Если инструмент вернул status=error — это ответ самой 1С: НЕ придумывай "
            "причины и не упоминай лицензии/доступы; назови код и текст ошибки, "
            "а при invalid_query — исправь запрос и вызови инструмент повторно. "
            "Создание документа возможно только после явного подтверждения "
            "пользователя — не считай его данным заранее.\n"
            "Примеры правильных запросов для типовых вопросов:\n"
            "остатки товара: " + STOCK_Q + "\n"
            "задолженность: " + DEBT_Q + "\n"
            "заказы: " + ORDERS_Q + "\n"
            "реквизиты контрагентов: " + PARTY_Q
        )

    history = []  # заполняется только при keep_history=true
    try:
        while True:
            try:
                text = input(f"\n{profile}> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nВыход.")
                break
            if not text:
                continue
            low = text.lower()
            if low in ("/выход", "выход", "exit", "quit", "/q"):
                break
            if low in ("/помощь", "/help"):
                print(HELP)
                continue
            if low in ("/бухгалтер", "/логист"):
                profile = low.lstrip("/")
                print(f"Профиль: {profile}")
                continue
            if low == "/режим":
                mode = detect_mode()
                print(f"Режим: {mode}")
                continue
            try:
                if mode == "ollama":
                    user_msg = {"role": "user", "content": text}
                    if keep_history:
                        history.append(user_msg)
                        msgs = history
                    else:
                        # Каждый вопрос — свежий контекст: малая модель
                        # деградирует в длинной истории (проверено на демо-сценарии)
                        msgs = [{"role": "system", "content": build_system()},
                                user_msg]
                    ollama_turn(bridge, msgs, profile, model,
                                input_func=input, print_func=print)
                    if keep_history:
                        history = msgs  # с tool-раундами текущего хода
                else:
                    route = demo_route(text, profile)
                    if route is None:
                        print(HELP)
                        continue
                    action, params = route
                    print(f"  > инструмент: {action}")
                    out = execute_tool(bridge, action, params, profile)
                    print(format_response(json.loads(out)))
            except BridgeTimeout as exc:
                print(f"[1С не отвечает] {exc}")
            except Exception as exc:
                print(f"[сбой] {exc}")
                if mode == "ollama":
                    mode = "demo"
                    print("Переключился в демо-режим (без модели).")
    finally:
        if mock:
            mock.stop()


if __name__ == "__main__":
    main()
