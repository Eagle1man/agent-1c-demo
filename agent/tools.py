# -*- coding: utf-8 -*-
"""Инструменты агента: схемы для LLM, уровни риска, human-in-the-loop.

Адаптивная автономность (из концепции): low — агент делает сам и пишет в
журнал; high — человек подтверждает в консоли, и только тогда уходит
confirmed_by в 1С."""
import json
import re

RISK = {
    "проверка_связи": "low",
    "запрос_1с": "low",
    "создать_документ": "high",
}

CONFIRM_YES = ("да", "д", "yes", "y", "ок", "ok", "согласен", "подтверждаю")

TOOLS = [
    {"type": "function", "function": {
        "name": "проверка_связи",
        "description": "Проверить, что мост 1С запущен и отвечает.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "запрос_1с",
        "description": "Выполнить SELECT-запрос к 1С и вернуть таблицу. Только чтение данных.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string",
                      "description": "Запрос на встроенном языке 1С: начинается с ВЫБРАТЬ, без «;», без параметров «&» и без изменения данных. Добавляй ПЕРВЫЕ 50."}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "создать_документ",
        "description": "Создать и провести документ в 1С. ВЫСОКИЙ РИСК: потребуется подтверждение человека в консоли.",
        "parameters": {"type": "object", "properties": {
            "doc_type": {"type": "string", "description": "Вид документа, обычно РеализацияТоваровУслуг"},
            "counterparty": {"type": "string", "description": "Наименование контрагента точно как в 1С"},
            "positions": {"type": "array", "description": "Товарные позиции", "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "Номенклатура"},
                    "qty": {"type": "number", "description": "Количество"},
                    "price": {"type": "number", "description": "Цена"},
                },
                "required": ["item", "qty", "price"]}}},
            "required": ["counterparty", "positions"]}}},
]

def _echo_block(echo):
    lines = ["", "=" * 56, "СОЗДАНИЕ ДОКУМЕНТА — ВЫСОКИЙ РИСК",
             "=" * 56,
             f"  Вид:         {echo.get('doc_type')}",
             f"  Контрагент:  {echo.get('counterparty')}", "  Позиции:"]
    total = 0.0
    for pos in echo.get("positions", []):
        amount = float(pos.get("qty", 0)) * float(pos.get("price", 0))
        total += amount
        lines.append(f"    - {pos.get('item')}: {pos.get('qty')} x {pos.get('price')} = {amount:g}")
    lines.append(f"  Итого:       {total:g}")
    lines.append("=" * 56)
    return "\n".join(lines)


def execute_tool(bridge, name, arguments, profile, input_func=input, print_func=print):
    """Исполнение инструмента. Возвращает JSON-строку для модели.

    Подтверждение человека проверяется здесь (кодом), а не на слово модели:
    тот же принцип двухзащиты дублирован на стороне 1С."""
    risk = RISK.get(name, "high")

    if name == "проверка_связи":
        resp = bridge.send("проверка_связи", {}, profile, risk)
        bridge.journal(name, risk, "auto", resp.get("status"),
                       "проверка связи с 1С", resp.get("id"))
        return json.dumps(resp, ensure_ascii=False)

    if name == "запрос_1с":
        # Нормализация ответов маленькой модели: срезаем завершающую «;» и,
        # если запрос пришёл английским SQL, переводим базовые ключевые слова
        # на встроенный язык. «;» ВНУТРИ и деструктивные слова не трогаем —
        # их отсекает мост (invalid_query).
        q = (arguments.get("query") or "").strip().rstrip(";").strip()
        if re.match(r"select\b", q, flags=re.IGNORECASE):
            for pat, rep in ((r"select\b", "ВЫБРАТЬ"), (r"top\s+(\d+)\b", r"ПЕРВЫЕ \1"),
                             (r"from\b", "ИЗ"), (r"where\b", "ГДЕ")):
                q = re.sub(pat, rep, q, flags=re.IGNORECASE)
        resp = bridge.send("запрос_1с", {"query": q},
                           profile, risk)
        rows = (resp.get("result") or {}).get("row_count")
        bridge.journal(name, risk, "auto", resp.get("status"),
                       f"строк: {rows}" if rows is not None
                       else (resp.get("error") or {}).get("message", ""),
                       resp.get("id"))
        return json.dumps(resp, ensure_ascii=False)

    if name == "создать_документ":
        params = {
            "doc_type": arguments.get("doc_type") or "РеализацияТоваровУслуг",
            "counterparty": arguments.get("counterparty", ""),
            "positions": arguments.get("positions", []),
        }
        resp = bridge.send("создать_документ", params, profile, risk)
        if resp.get("status") == "need_confirmation":
            echo = (resp.get("result") or {}).get("echo", params)
            print_func(_echo_block(echo))
            answer = input_func("Подтвердить создание (да/нет): ").strip().lower()
            if answer not in CONFIRM_YES:
                bridge.journal(name, risk, "human_rejected", "cancelled",
                               f"человек отклонил: {echo.get('counterparty')}",
                               resp.get("id"))
                return json.dumps(
                    {"status": "cancelled",
                     "note": "Человек отклонил создание документа — ничего не создано."},
                    ensure_ascii=False)
            resp = bridge.send("создать_документ", params, profile, risk,
                               confirmed_by=bridge.confirmed_by())
            bridge.journal(name, risk, "human_confirmed", resp.get("status"),
                           f"подтверждено человеком: {echo.get('counterparty')}",
                           resp.get("id"))
        elif resp.get("status") == "ok":
            # 1С не запросила подтверждения — нарушение протокола, фиксируем.
            bridge.journal(name, risk, "protocol_violation", "ok",
                           "мост выполнил создание без confirmed_by", resp.get("id"))
        else:
            bridge.journal(name, risk, "auto", resp.get("status"),
                           (resp.get("error") or {}).get("message", ""),
                           resp.get("id"))
        return json.dumps(resp, ensure_ascii=False)

    err = {"status": "error",
           "error": {"code": "unsupported_action", "message": f"нет инструмента {name}"}}
    return json.dumps(err, ensure_ascii=False)


def format_response(resp):
    """Человекочитаемый вывод ответа 1С в консоль."""
    status = resp.get("status")
    if status == "cancelled":
        return "[отменено] " + resp.get("note", "")
    if status == "need_confirmation":
        return "[ожидает подтверждения]"
    if status == "error":
        err = resp.get("error") or {}
        return f"[ошибка {err.get('code')}] {err.get('message')}"
    result = resp.get("result") or {}
    if "columns" in result:
        cols = result["columns"]
        rows = result.get("rows", [])
        widths = [len(str(c)) for c in cols]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
        out = [" | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cols)),
               "-+-".join("-" * w for w in widths)]
        for row in rows:
            out.append(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
        note = f"  (строк: {result.get('row_count')}" + \
               (", прервано лимитом" if result.get("truncated") else "") + ")"
        return "\n".join(out) + "\n" + note
    if "number" in result:
        return (f"Документ создан: {result.get('number')} от {result.get('date')}"
                f" (проведён: {'да' if result.get('posted') else 'нет'})")
    if "platform" in result:
        return (f"Связь с 1С есть: платформа {result.get('platform')}, "
                f"мост {result.get('bsl_version')}")
    return json.dumps(result, ensure_ascii=False)
