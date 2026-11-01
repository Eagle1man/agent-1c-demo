# -*- coding: utf-8 -*-
"""Проверка панели: живая 1С и честный отказ без неё.

Запуск с работающим мостом:
    py tools/check_panel.py
Коды: 0 — всё сходится, 2 — расхождение.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8077"
FAILED = []


def check(name, cond, detail=""):
    print(("  [PASS] " if cond else "  [FAIL] ") + name + ((" " + detail) if not cond else ""))
    if not cond:
        FAILED.append(name)


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=180) as r:
        return json.loads(r.read())


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def get_text(path):
    with urllib.request.urlopen(BASE + path, timeout=180) as r:
        return r.read().decode("utf-8-sig")


def main():
    health = get("/api/health")
    check("мост отвечает", health.get("status") == "ok", str(health))
    check("в ответе есть версия моста", bool(health.get("bridge")))

    panel = get("/api/panel")
    check("панель без ошибок", not panel.get("errors"), str(panel.get("errors")))
    counts = panel.get("counts") or {}
    check("документы > 0", (counts.get("documents") or 0) > 0, str(counts))
    check("контрагенты > 0", (counts.get("counterparties") or 0) > 0, str(counts))
    check("у панели есть источник и время",
          bool(panel.get("source")) and bool(panel.get("ts")))
    check("есть последние документы", len(panel.get("documents") or []) > 0)

    ans = post("/api/ask", {"phrase": "покажи последние документы"})
    check("вопрос про данные идёт в 1С", ans.get("kind") == "data", str(ans)[:200])
    check("в ответе указан источник", "1С" in (ans.get("source") or ""))

    rag = post("/api/ask", {"phrase": "как создать внешнюю печатную форму"})
    check("вопрос по знаниям идёт в RAG", rag.get("kind") == "rag", str(rag)[:200])
    check("у RAG-ответа есть источник", "RAG" in (rag.get("source") or ""))

    prod = get("/api/production")
    check("производственный блок отвечает", "mode" in prod, str(prod)[:150])
    check("без OPC UA данные не выдумываются",
          prod.get("available") is False and bool(prod.get("error")), str(prod)[:200])

    k = get("/api/kpi")
    check("график: есть месяцы", len(k.get("months") or []) > 0, str(k)[:150])
    check("график: сумма больше нуля", (k.get("total") or 0) > 0)
    top = get("/api/top")
    check("топ контрагентов заполнен", len(top.get("items") or []) > 0)
    found = get("/api/search?q=" + urllib.parse.quote("Клевер"))
    check("поиск по контрагенту работает", len(found.get("rows") or []) > 0,
          str(found.get("error")))
    by_num = get("/api/search?q=000000385")
    check("поиск по номеру документа работает",
          len(by_num.get("rows") or []) == 1, str(by_num)[:150])

    rep = get("/api/report?from=2026-01-01&to=2026-09-30")
    check("отчёт за период считается",
          (rep.get("documents") or 0) > 0 and (rep.get("total") or 0) > 0,
          str(rep)[:150])
    check("в отчёте есть топ позиций", len(rep.get("positions") or []) > 0)
    csv_text = get_text("/api/export?type=positions&from=2026-01-01&to=2026-09-30")
    check("CSV позиций отдаётся", csv_text.startswith("Позиция;"),
          csv_text[:80])

    card = get("/api/order?number=000000001")
    check("карточка документа открывается", not card.get("error"), str(card)[:200])
    check("в карточке есть позиции", len(card.get("positions") or []) > 0)
    check("у карточки есть источник и время",
          bool(card.get("source")) and bool(card.get("ts")))
    check("в карточке посчитана сумма", (card.get("total") or 0) > 0)
    missing = get("/api/order?number=999999999")
    check("несуществующий документ — понятная ошибка",
          "не найден" in (missing.get("error") or ""), str(missing)[:150])

    # Честный отказ: смотрим, что панель не выдумывает числа без 1С.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
    import panel_server
    saved = panel_server.EXCHANGE
    panel_server.EXCHANGE = Path(r"D:\agent-1c-demo\_нет_такого_exchange")
    try:
        broken = panel_server.panel()
        check("без 1С панель сообщает ошибку", bool(broken.get("errors")))
        check("без 1С числа не подставляются",
              all(v is None for v in (broken.get("counts") or {}).values()),
              str(broken.get("counts")))
    finally:
        panel_server.EXCHANGE = saved

    print(f"\nИТОГ: {'OK' if not FAILED else 'ОШИБОК ' + str(len(FAILED))}")
    return 0 if not FAILED else 2


if __name__ == "__main__":
    sys.exit(main())
