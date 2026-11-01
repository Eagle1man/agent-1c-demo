# -*- coding: utf-8 -*-
"""Проверка поведения панели при недоступной 1С.

    py tools/check_offline.py

Закрывает 1С, проверяет, что панель честно сообщает об отказе и не подставляет
числа, проверяет, что RAG продолжает работать, и НЕ открывает 1С обратно —
это отдельный шаг (`py tools/epf/test_epf_live.py`).
"""
import json
import subprocess
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8077"
FAILED = []


def check(name, cond, detail=""):
    print(("  [PASS] " if cond else "  [FAIL] ") + name + ("" if cond else " " + detail))
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


def main():
    print("закрываю 1С…")
    subprocess.run(["taskkill", "/IM", "1cv8t.exe", "/F"], capture_output=True)
    time.sleep(6)

    health = get("/api/health")
    check("health сообщает об отказе", health.get("status") != "ok", str(health)[:120])
    check("в отказе есть причина", bool(health.get("error")), str(health)[:120])

    panel = get("/api/panel")
    counts = panel.get("counts") or {}
    check("счётчики не подставляются",
          all(v is None for v in counts.values()), str(counts))
    check("ошибки перечислены", bool(panel.get("errors")))

    data = post("/api/ask", {"phrase": "сколько контрагентов"})
    check("вопрос про данные не выдумывает ответ",
          "не ответила" in (data.get("answer") or "").lower(), str(data)[:140])

    rag = post("/api/ask", {"phrase": "как создать внешнюю печатную форму"})
    check("RAG продолжает работать без 1С", rag.get("kind") == "rag", str(rag)[:120])

    print(f"\nИТОГ: {'OK' if not FAILED else 'ОШИБОК ' + str(len(FAILED))}")
    return 0 if not FAILED else 2


if __name__ == "__main__":
    sys.exit(main())
