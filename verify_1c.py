# -*- coding: utf-8 -*-
"""Приёмка части opencode (1c/АгентМост.bsl + 1c/ИНСТРУКЦИЯ_1С.md).

Проверяет маркеры протокола v1.0, запрет COM/HTTP (учебная версия 1С),
полноту фикстур. Запуск: py -3 verify_1c.py
Коды: 0 — пройдено (или файлов ещё нет), 1 — есть нарушения."""
import json
import sys
from pathlib import Path

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    # ввод/вывод единообразно UTF-8 (консоль и пайп), без UnicodeError
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
BSL = ROOT / "1c" / "АгентМост.bsl"
DOC = ROOT / "1c" / "ИНСТРУКЦИЯ_1С.md"

REQUIRED_BSL = [
    '"protocol"', '"1.0"', "need_confirmation", "confirmed_by",
    "ПЕРВЫЕ 50", "ПодключитьОбработчикОжидания", "invalid_query",
    "unsupported_doc_type", "КодировкаТекста.UTF8", ".tmp", "__done",
    "★ ЕДИНСТВЕННОЕ МЕСТО ДЛЯ ПРАВКИ ПУТИ",
    "=== МОДУЛЬ ОБЪЕКТА ===", "=== МОДУЛЬ ФОРМЫ ===",
    "parse_error", "execution_error", "io_error",
]
FORBIDDEN_BSL = [
    "COMОбъект", "ВнешнееСоединение", "HTTPСоединение", "HTTPСервис",
    "ЗапуститьПриложение", "ФоновыеЗадания", "WebService",
]
REQUIRED_DOC = [
    "online.1c.ru", "Учебная версия", "Управление торговлей",
    "конфигуратор", "Внешняя обработка", "exchange",
    "Запустить мост", "проверка_связи",
]
REQUIRED_FIELDS_CMD = {"protocol", "id", "ts", "action", "profile", "risk",
                       "params", "confirmed_by"}
REQUIRED_FIELDS_RESP = {"protocol", "id", "ts", "status", "result", "error",
                        "executed_by"}


def main():
    problems, checked = [], 0

    # --- фикстуры: полнота и согласованность id команд/ответов ---
    cmd_ids, resp_ids = set(), set()
    for path in sorted((ROOT / "fixtures").glob("*.json")):
        checked += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            problems.append(f"{path.name}: не разбирается — {exc}")
            continue
        is_cmd = path.name.startswith("cmd_")
        want = REQUIRED_FIELDS_CMD if is_cmd else REQUIRED_FIELDS_RESP
        missing = want - set(data)
        if missing:
            problems.append(f"{path.name}: нет полей {sorted(missing)}")
        if data.get("protocol") != "1.0":
            problems.append(f"{path.name}: protocol != 1.0")
        (cmd_ids if is_cmd else resp_ids).add(data.get("id"))
    if cmd_ids != resp_ids:
        problems.append(f"id команд без ответа: {sorted(cmd_ids - resp_ids)}; "
                        f"ответов без команды: {sorted(resp_ids - cmd_ids)}")
    print(f"Фикстуры: проверено файлов — {checked}")

    # --- .bsl ---
    if not BSL.exists():
        print("ПРИЁМКА ОТЛОЖЕНА: 1c/АгентМост.bsl ещё не создан (opencode).")
        return 0
    raw = BSL.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        problems.append("АгентМост.bsl: не UTF-8 (нужен UTF-8 с BOM)")
        text = ""
    if text:
        if "\r\n" not in text:
            problems.append("АгентМост.bsl: нет CRLF-переносов")
        for token in REQUIRED_BSL:
            if token not in text:
                problems.append(f"АгентМост.bsl: нет обязательного маркера «{token}»")
        for token in FORBIDDEN_BSL:
            if token in text:
                problems.append(f"АгентМост.bsl: ЗАПРЕЩЁННЫЙ код «{token}» "
                                "(учебная версия 1С не поддерживает)")
        # Экранирование кавычек: в 1С обратный слэш НЕ является escape-символом.
        # Запись "\"Имя\"" оставляет строку незакрытой, и модуль не компилируется.
        # Реальный случай: epf падал с «Ошибка инициализации модуля» на такой строке,
        # при этом проверка маркеров проходила — то есть файл никогда не собирался.
        import re as _re_esc
        for _m in _re_esc.finditer(r'\\"[A-Za-zА-Яа-я_0-9]', text):
            _line = text[: _m.start()].count("\n") + 1
            problems.append(
                f"АгентМост.bsl: строка {_line}: неверное экранирование \\\" — "
                'в 1С кавычка внутри строки удваивается (""); модуль не скомпилируется')

        # Объявления и возвраты: 1С не компилирует модуль, если Процедура
        # возвращает значение, если имя объявлено дважды или если написано
        # «Процедуру». Прежняя приёмка этого не ловила, и epf падал на запуске.
        _decl = _re_esc.compile(
            r"^\s*(Процедура|Функция|Процедуру|Функцию|КонецПроцедуры|КонецФункции)\b")
        _ret = _re_esc.compile(r"^\s*Возврат\s+(.+?);")
        _names, _stack = {}, []
        for _i, _ln in enumerate(text.splitlines(), 1):
            _m = _decl.match(_ln)
            if _m:
                _kind = _m.group(1)
                if _kind in ("Процедуру", "Функцию"):
                    problems.append(
                        f"АгентМост.bsl: строка {_i}: «{_kind}» — такого ключевого "
                        "слова в 1С нет")
                elif _kind in ("Процедура", "Функция"):
                    _nm = _re_esc.search(r"(?:Процедура|Функция)\s+([A-Za-zА-Яа-я_0-9]+)", _ln)
                    if _nm:
                        _n = _nm.group(1).lower()
                        if _n in _names:
                            problems.append(
                                f"АгентМост.bsl: строка {_i}: имя «{_nm.group(1)}» "
                                f"уже объявлено в строке {_names[_n]} — модуль не "
                                "скомпилируется")
                        else:
                            _names[_n] = _i
                    _stack.append((_kind, _i))
                elif _stack:
                    _stack.pop()
                continue
            _r = _ret.match(_ln)
            if _r and _stack and _stack[-1][0] == "Процедура" and _r.group(1).strip():
                problems.append(
                    f"АгентМост.bsl: строка {_i}: Процедура (с {_stack[-1][1]}) "
                    "возвращает значение через Возврат — 1С не компилирует модуль")
        if _stack:
            problems.append(
                f"АгентМост.bsl: не закрыто объявлений: {len(_stack)} "
                f"(последнее в строке {_stack[-1][1]})")
        # Функции, не объявленные в самом файле, — ошибка компиляции в 1С.
        if ("ВерсияПлатформы()" in text
                and "Функция ВерсияПлатформы" not in text):
            problems.append("АгентМост.bsl: вызов ВерсияПлатформы() — такой "
                            "глобальной функции в 1С нет, модуль не скомпилируется: "
                            "заменить на константу или Метаданные().Версия")
        # Модуль формы: обработчик ожидания должен быть ОБЪЯВЛЕН в модуле формы,
        # и переменные модуля формы — тоже (иначе ошибка компиляции в 1С).
        idx = text.find("=== МОДУЛЬ ФОРМЫ ===")
        form_part = text[idx:] if idx != -1 else ""
        if not form_part:
            problems.append("АгентМост.bsl: нет блока === МОДУЛЬ ФОРМЫ ===")
        else:
            if "Процедура ОпросОчереди" not in form_part:
                problems.append("АгентМост.bsl: в МОДУЛЕ ФОРМЫ нет «Процедура "
                                "ОпросОчереди» — ПодключитьОбработчикОжидания требует "
                                "процедуру в том же модуле (стандартный шаблон: форма "
                                "вызывает метод модуля объекта)")
            # Директивы контекста в модуле формы: каждая Процедура/Функция/Перем
            # обязана иметь явную &Директиву строкой выше (доказано практикой:
            # обработчики без &НаКлиенте молча не выполняются, форма падает).
            # Серверные (&НаСервере...) — валидны, ложных срабатываний нет.
            import re as _re
            _directive = _re.compile(
                r"^&(НаКлиенте|НаСервере|НаКлиентеНаСервере|НаСервереБезКонтекста)\b")
            _decl = _re.compile(r"^(Процедура|Функция|Перем)\b")
            _flines = form_part.splitlines()
            for _i, _ln in enumerate(_flines):
                _s = _ln.strip()
                _m = _decl.match(_s)
                if not _m:
                    continue
                _j = _i - 1
                _found = None
                while _j >= 0:
                    _p = _flines[_j].strip()
                    if not _p or _p.startswith("//"):
                        _j -= 1
                        continue
                    _dm = _directive.match(_p)
                    _found = _dm.group(1) if _dm else None
                    break
                if _found is None:
                    _name = _s.split("(")[0].strip()
                    problems.append(
                        f"АгентМост.bsl: в МОДУЛЕ ФОРМЫ «{_name}» без директивы "
                        f"контекста (строка {_i + 1} блока формы) — добавьте "
                        f"&НаКлиенте (или &НаСервере для серверной), иначе код "
                        f"не выполнится")
            if ("Перем ПутьКExchange" not in form_part
                    and "ПутьКExchange = Неопределено" in form_part):
                problems.append("АгентМост.bsl: модуль формы присваивает "
                                "ПутьКExchange, не объявленный в этом модуле "
                                "(ошибка компиляции в 1С) — путь читать из поля формы "
                                "Элементы.ПутьКExchange, объекту передавать через Объект.")
    print("АгентМост.bsl: разобран, маркеры проверены")

    # --- инструкция ---
    if not DOC.exists():
        problems.append("нет 1c/ИНСТРУКЦИЯ_1С.md")
    else:
        dtext = DOC.read_text(encoding="utf-8-sig")
        for token in REQUIRED_DOC:
            if token not in dtext:
                problems.append(f"ИНСТРУКЦИЯ_1С.md: нет «{token}»")
        print("ИНСТРУКЦИЯ_1С.md: проверена")

    if problems:
        print(f"\nНАРУШЕНИЙ: {len(problems)}")
        for p in problems:
            print("  x", p)
        return 1
    print("\nПРИЁМКА ПРОЙДЕНА: 1c/ соответствует протоколу v1.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
