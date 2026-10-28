# -*- coding: utf-8 -*-
"""Сквозная проверка агента через Mock1C — без 1С и без Ollama.

Запуск: py -3 agent\\test_demo.py"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bridge import Bridge, BridgeTimeout
from mock_bridge import Mock1C
from tools import execute_tool, format_response
import agent as agent_mod

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    # ввод/вывод единообразно UTF-8 (консоль и пайп), без UnicodeError
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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


def silent(_prompt=""):
    return "да"


def main():
    tmp = Path(tempfile.mkdtemp(prefix="agent1c_test_"))
    print(f"Exchange: {tmp}")
    mock = Mock1C(tmp).start()
    bridge = Bridge(tmp, user="тест")
    noreply = Bridge(tmp / "empty", user="тест")  # без моста — для таймаута
    quiet = lambda *a, **k: None  # noqa: E731

    try:
        print("— связь —")
        r = json.loads(execute_tool(bridge, "проверка_связи", {}, "бухгалтер",
                                    input_func=silent, print_func=quiet))
        check("связь: ok", r.get("status") == "ok", str(r))
        check("связь: мост отчитался", "АгентМост" in str(r.get("executed_by")))
        check("format_response связь", "Связь с 1С" in format_response(r))

        print("— запросы —")
        r = json.loads(execute_tool(
            bridge, "запрос_1с",
            {"query": "ВЫБРАТЬ Номенклатура ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки()"},
            "логист", input_func=silent, print_func=quiet))
        check("запрос: ok", r.get("status") == "ok", str(r))
        check("запрос: есть строки", (r.get("result") or {}).get("row_count", 0) > 0)
        check("format_response таблица", format_response(r).count("|") > 3)

        r = json.loads(execute_tool(
            bridge, "запрос_1с",
            {"query": "ВЫБРАТЬ * ИЗ Справочник.Контрагенты; УДАЛИТЬ ИЗ РегистрСведений.КурсыВалют"},
            "бухгалтер", input_func=silent, print_func=quiet))
        check("запрос злонамеренный: отклонён",
              r.get("status") == "error"
              and (r.get("error") or {}).get("code") == "invalid_query", str(r))

        print("— создание документа (высокий риск) —")
        args = {"counterparty": "ООО Ромашка",
                "positions": [{"item": "Товар А", "qty": 10, "price": 150}]}
        r = json.loads(execute_tool(bridge, "создать_документ", dict(args), "логист",
                                    input_func=lambda p: "нет", print_func=quiet))
        check("отказ человека -> cancelled", r.get("status") == "cancelled", str(r))

        r = json.loads(execute_tool(bridge, "создать_документ", dict(args), "логист",
                                    input_func=lambda p: "да", print_func=quiet))
        check("подтверждение -> ok с номером",
              r.get("status") == "ok"
              and str((r.get("result") or {}).get("number", "")).startswith("РН-"),
              str(r))

        print("— журнал и архив —")
        lines = [json.loads(x) for x in
                 bridge.journal_path.read_text(encoding="utf-8").splitlines()]
        decisions = {x["decision"] for x in lines}
        check("журнал: есть human_rejected", "human_rejected" in decisions)
        check("журнал: есть human_confirmed", "human_confirmed" in decisions)
        check("журнал: поля полные",
              all(set(x) >= {"ts", "id", "action", "risk", "decision", "status", "summary"}
                  for x in lines))
        check("команды убраны в архив",
              not list((tmp / "commands").glob("*.json"))
              and any((tmp / "archive").glob("*__done.json")))

        print("— таймаут (1С не запущена) —")
        try:
            noreply.send("проверка_связи", {}, timeout=1)
            check("таймаут: поднят BridgeTimeout", False)
        except BridgeTimeout:
            check("таймаут: поднят BridgeTimeout", True)

        print("— демо-маршрутизация фраз —")
        cases = [
            ("проверь связь", "проверка_связи"),
            ("остатки на складе", "запрос_1с"),
            ("задолженность контрагентов", "запрос_1с"),
            ("сколько заказов за неделю", "запрос_1с"),
            ("создай накладную на ООО Ромашка 10 шт", "создать_документ"),
            ("привет, как дела?", None),
        ]
        for phrase, expected in cases:
            route = agent_mod.demo_route(phrase, "логист")
            got = route[0] if route else None
            check(f"фраза «{phrase}» -> {expected}", got == expected, f"got={got}")
        route = agent_mod.demo_route("создай накладную на ИП Иванов", "логист")
        check("в фразе распознан контрагент",
              route is not None and route[1]["counterparty"] == "ИП Иванов")

        print("— фикстуры протокола —")
        fx = Path(__file__).resolve().parent.parent / "fixtures"
        for path in sorted(fx.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            ok = data.get("protocol") == "1.0" and isinstance(data.get("id"), str)
            if path.name.startswith("cmd_"):
                ok = ok and isinstance(data.get("action"), str) and "params" in data
            else:
                ok = ok and data.get("status") in ("ok", "error", "need_confirmation")
            check(f"фикстура {path.name}", ok)
            check(f"format_response не падает на {path.name}",
                  isinstance(format_response(data), str))

        print("— config/dataset —")
        cfg = json.loads((Path(__file__).resolve().parent / "config.json")
                         .read_text(encoding="utf-8"))
        check("config: профиль и модель",
              cfg.get("profile") in ("бухгалтер", "логист") and bool(cfg.get("model")))
        ds_lines = (Path(__file__).resolve().parent.parent / "dataset" / "dataset.jsonl"
                    ).read_text(encoding="utf-8").splitlines()
        rows = [json.loads(x) for x in ds_lines if x.strip()]
        check("dataset: 6 записей «ситуация → действие»",
              len(rows) == 6
              and all({"situation", "action", "risk"} <= set(r) for r in rows))
    finally:
        mock.stop()
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nИТОГ: {PASSED} ok, {len(FAILED)} fail")
    if FAILED:
        for name in FAILED:
            print("  -> ", name)
        sys.exit(1)
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")


if __name__ == "__main__":
    main()
