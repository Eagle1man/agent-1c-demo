# -*- coding: utf-8 -*-
"""Быстрый запрос к живой 1С через мост: удобно смотреть структуру объектов.

    py tools/probe_1c.py "ВЫБРАТЬ ПЕРВЫЕ 1 * ИЗ Документ.РеализацияТоваровУслуг"
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))

from bridge import Bridge  # noqa: E402


def main():
    query = " ".join(sys.argv[1:])
    if not query:
        print("нужен текст запроса")
        return 2
    bridge = Bridge(ROOT / "exchange", user="проба")
    resp = bridge.send("запрос_1с", {"query": query}, "бухгалтер", "low")
    status = resp.get("status")
    if status != "ok":
        print("статус:", status, "ошибка:", resp.get("error"))
        return 1
    res = resp.get("result") or {}
    print("колонки:", res.get("columns"))
    print("строк:", res.get("row_count"))
    for row in (res.get("rows") or [])[:5]:
        print(" ", row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
