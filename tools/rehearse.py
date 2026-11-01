# -*- coding: utf-8 -*-
"""Репетиция показа: прогон сценария с замерами времени.

    py tools/rehearse.py --runs 3

Каждый шаг проверяется по факту ответа, а не по «выглядит нормально».
Результат пишется в docs/rehearsal.md: шаг, время, что вернулось.
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8077"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=180) as r:
        return json.loads(r.read())


def get_text(path):
    with urllib.request.urlopen(BASE + path, timeout=180) as r:
        return r.read().decode("utf-8-sig")


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


STEPS = [
    ("1С на связи", lambda: get("/api/health"), lambda d: d.get("status") == "ok"),
    ("панель: счётчики", lambda: get("/api/panel"),
     lambda d: (d.get("counts") or {}).get("documents", 0) > 0),
    ("KPI и график", lambda: get("/api/kpi"),
     lambda d: (d.get("total") or 0) > 0 and len(d.get("months") or []) > 0),
    ("топ контрагентов", lambda: get("/api/top"), lambda d: len(d.get("items") or []) > 0),
    ("поиск «Клевер»", lambda: get("/api/search?q=" + urllib.parse.quote("Клевер")),
     lambda d: len(d.get("rows") or []) > 0),
    ("отчёт за период", lambda: get("/api/report?from=2026-01-01&to=2026-09-30"),
     lambda d: (d.get("documents") or 0) > 0),
    ("CSV позиций", lambda: get_text(
        "/api/export?type=positions&from=2026-01-01&to=2026-09-30"),
     lambda d: d.startswith("Позиция;")),
    ("карточка документа", lambda: get("/api/order?number=000000385"),
     lambda d: not d.get("error") and len(d.get("positions") or []) > 0),
    ("чат: данные из 1С", lambda: post("/api/ask", {"phrase": "сколько контрагентов"}),
     lambda d: d.get("kind") == "data"),
    ("чат: ответ из RAG", lambda: post("/api/ask",
                                       {"phrase": "как создать внешнюю печатную форму"}),
     lambda d: d.get("kind") == "rag"),
]


def one_run(run_no):
    rows, ok = [], 0
    for name, fn, check in STEPS:
        started = time.time()
        try:
            data = fn()
            passed = bool(check(data))
            detail = "" if passed else str(data)[:120]
        except Exception as exc:                    # noqa: BLE001
            passed, detail = False, f"{type(exc).__name__}: {exc}"[:120]
        elapsed = (time.time() - started) * 1000
        ok += passed
        rows.append((name, elapsed, passed, detail))
        print(f"  [{'OK  ' if passed else 'FAIL'}] {name:24} {elapsed:7.0f} мс "
              + ("" if passed else detail))
    print(f"  прогон {run_no}: {ok}/{len(STEPS)} шагов\n")
    return rows, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()

    out = [f"# Репетиция показа — {datetime.now().isoformat(timespec='seconds')}", ""]
    total_ok = 0
    for i in range(1, args.runs + 1):
        print(f"прогон {i}")
        rows, ok = one_run(i)
        total_ok += ok
        out.append(f"## Прогон {i}: {ok}/{len(STEPS)}")
        out.append("")
        out.append("| Шаг | Время, мс | Результат |")
        out.append("|---|---|---|")
        for name, ms, passed, detail in rows:
            out.append(f"| {name} | {ms:.0f} | {'OK' if passed else 'FAIL ' + detail} |")
        out.append("")

    total = len(STEPS) * args.runs
    out.insert(1, f"Итог: {total_ok}/{total} шагов успешно за {args.runs} прогона")
    out.insert(2, "")
    path = ROOT / "docs" / "rehearsal.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"итого {total_ok}/{total}; записано: {path}")
    return 0 if total_ok == total else 2


if __name__ == "__main__":
    sys.exit(main())
