# -*- coding: utf-8 -*-
"""Инвентаризация живой 1С через файловый мост.

Что делает: отправляет `проверка_связи`, затем минимальные запросы к объектам
демо-конфигурации, и записывает фактический результат в
`docs/live_1c_inventory.md`. Ошибка выполнения запроса — тоже результат: она
означает, что объекта или поля нет в этой конфигурации.

Запуск (мост должен быть запущен в 1С):
    py tools\\live_inventory.py
    py tools\\live_inventory.py --exchange D:\\agent-1c-demo\\exchange
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))

from bridge import Bridge, BridgeError, BridgeTimeout  # noqa: E402

QUERIES = [
    ("Справочник.Контрагенты",
     "ВЫБРАТЬ ПЕРВЫЕ 5 Ссылка, Наименование ИЗ Справочник.Контрагенты"),
    ("Справочник.Номенклатура",
     "ВЫБРАТЬ ПЕРВЫЕ 5 Ссылка, Наименование ИЗ Справочник.Номенклатура"),
    ("Документ.РеализацияТоваровУслуг",
     "ВЫБРАТЬ ПЕРВЫЕ 5 Ссылка, Номер, Дата, Контрагент "
     "ИЗ Документ.РеализацияТоваровУслуг"),
    ("КоличествоКонтрагентов",
     "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего ИЗ Справочник.Контрагенты"),
    ("КоличествоНоменклатуры",
     "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего ИЗ Справочник.Номенклатура"),
    ("КоличествоДокументов",
     "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего ИЗ Документ.РеализацияТоваровУслуг"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exchange", default=str(ROOT / "exchange"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "live_1c_inventory.md"))
    args = ap.parse_args()

    bridge = Bridge(args.exchange, user="аудит")
    lines = ["# Живая 1С: фактическая инвентаризация", "",
             f"Каталог обмена: `{args.exchange}`", ""]

    try:
        check = bridge.send("проверка_связи", {}, "бухгалтер", "low")
    except (BridgeTimeout, BridgeError) as exc:
        print(f"МОСТ НЕ ОТВЕТИЛ: {exc}")
        lines += ["## Мост", "", f"**НЕ ОТВЕТИЛ**: {exc}", ""]
        Path(args.out).write_text("\n".join(lines), encoding="utf-8")
        return 2

    status = check.get("status")
    result = check.get("result") or {}
    lines += ["## Мост", "",
              f"- статус: `{status}`",
              f"- платформа: `{result.get('platform')}`",
              f"- версия моста: `{result.get('bsl_version')}`",
              f"- id ответа: `{check.get('id')}`", ""]
    print(f"проверка_связи: {status}, платформа {result.get('platform')}, "
          f"мост {result.get('bsl_version')}")
    if status != "ok":
        lines += [f"Ошибка: `{check.get('error')}`", ""]
        Path(args.out).write_text("\n".join(lines), encoding="utf-8")
        return 3

    lines += ["## Объекты конфигурации", "",
              "| Проверка | Статус | Строк | Что вернула 1С |",
              "|---|---|---|---|"]

    for title, query in QUERIES:
        try:
            resp = bridge.send("запрос_1с", {"query": query}, "бухгалтер", "low")
        except (BridgeTimeout, BridgeError) as exc:
            lines.append(f"| {title} | сбой связи | — | {exc} |")
            print(f"{title}: сбой связи — {exc}")
            continue

        st = resp.get("status")
        res = resp.get("result") or {}
        err = (resp.get("error") or {}).get("message", "")
        rows = res.get("row_count")
        if st == "ok":
            cols = res.get("columns") or []
            first = (res.get("rows") or [[]])[0]
            sample = ", ".join(f"{c}={v}" for c, v in zip(cols, first))[:120]
            lines.append(f"| {title} | ok | {rows} | {sample} |")
            print(f"{title}: ok, строк {rows}, {sample}")
        else:
            code = (resp.get("error") or {}).get("code", "?")
            lines.append(f"| {title} | {code} | — | {err[:120]} |")
            print(f"{title}: ОШИБКА {code} — {err[:120]}")

    lines += ["", "## Вывод", "",
              "Строки со статусом `ok` — объекты, которые реально доступны мосту "
              "в этой конфигурации. Остальные либо отсутствуют, либо требуют "
              "других имён полей.", ""]
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"\nзаписано: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
