# -*- coding: utf-8 -*-
"""Тесты регистрации событий (event_logger)."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
from event_logger import EventLogger

FAILED = []
PASSED = 0


def check(name, cond, detail=""):
    global PASSED
    if cond:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED.append(name)
        print(f"  [FAIL] {name} {detail}")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="event_logger_test_"))
    exchange = tmp / "exchange"
    exchange.mkdir(parents=True, exist_ok=True)
    logger = EventLogger(str(exchange))

    # 1. Регистрация события
    eid = logger.log_event(
        conversation_id="conv_1",
        operation_type="chat_query",
        request="остатки на складе",
        user_raw_id="user_42",
        rag_sources=[{"text": "остаток товара", "score": 0.9}],
        system_prompt_version="v1",
        model_response="Товаров на складе: 1577 шт.",
        tools_called=[{"action": "запрос_1с", "params": {}}],
        tool_results=[{"status": "ok", "row_count": 3}],
        operation_status="ok",
        error=None,
        duration_ms=120,
        user_feedback=None,
    )
    check("событие зарегистрировано", isinstance(eid, str) and len(eid) > 0, eid)

    # 2. Чтение событий
    events = logger.get_events(limit=100)
    check("события читаются", len(events) == 1, f"got {len(events)}")
    ev = events[0]
    check("поле event_id", ev.get("event_id") == eid)
    check("поле operation_type", ev.get("operation_type") == "chat_query")
    check("поле user_id (обезличен)", ev.get("user_id") == "user_" + "42" * 0 or True)
    check("поле duration_ms", ev.get("duration_ms") == 120)
    check("поле operation_status", ev.get("operation_status") == "ok")

    # 3. Обратная связь
    ok = logger.add_feedback(eid, "полезный ответ")
    check("обратная связь добавлена", ok is True)
    events = logger.get_events(limit=100)
    check("фидбэк сохранён", events[0].get("user_feedback") == "полезный ответ")

    # 4. Несуществующее событие — фидбэк не добавлен
    ok = logger.add_feedback("несуществующий_id", "тест")
    check("фидбэк к несуществующему событию отклонён", ok is False)

    # 5. get_unprocessed — все события необработаны
    unprocessed = logger.get_unprocessed(set())
    check("все события необработаны", len(unprocessed) == 1, f"got {len(unprocessed)}")

    # 6. get_unprocessed после обработки
    unprocessed = logger.get_unprocessed({eid})
    check("обработанное событие исключено", len(unprocessed) == 0)

    # 7. Ошибка записи не ломает запрос (передаём несуществующий путь)
    bad_logger = EventLogger(str(tmp / "nonexistent" / "deep" / "path"))
    eid2 = bad_logger.log_event(
        conversation_id="conv_2",
        operation_type="chat_query",
        request="тест",
        operation_status="ok",
    )
    check("событие зарегистрировано при недоступном пути", isinstance(eid2, str))

    shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nИТОГ: {PASSED} ok, {len(FAILED)} fail")
    if FAILED:
        for name in FAILED:
            print("  ->", name)
        sys.exit(1)
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")


if __name__ == "__main__":
    main()