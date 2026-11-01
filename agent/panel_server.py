#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Единый интерфейс предприятия: панель, аналитика, карточка, чат.

Данные — из живой 1С через файловый мост. Графики рисуются SVG на клиенте без
внешних библиотек: страница работает офлайн и не требует сборки (ТЗ §40.7 —
никаких фреймворков ради моды).

Запуск:
    py agent/panel_server.py --port 8077
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "rag"))

from bridge import Bridge, BridgeError, BridgeTimeout      # noqa: E402

EXCHANGE = None
PROFILE = "бухгалтер"
CACHE = {}


def now_ts():
    return datetime.now().isoformat(timespec="seconds")


def bridge():
    return Bridge(EXCHANGE, user="панель")


# ---------------------------------------------------------------- запросы к 1С
JOIN = ("ИЗ Документ.РеализацияТоваровУслуг КАК Док "
        "ЛЕВОЕ СОЕДИНЕНИЕ Документ.РеализацияТоваровУслуг.Товары КАК ТЧ "
        "ПО ТЧ.Ссылка = Док.Ссылка")

Q_COUNTS = {
    "documents": "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего ИЗ Документ.РеализацияТоваровУслуг",
    "counterparties": "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего ИЗ Справочник.Контрагенты",
    "nomenclature": "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего ИЗ Справочник.Номенклатура",
}
Q_LAST_DOCS = ("ВЫБРАТЬ ПЕРВЫЕ 8 Номер, Дата, Контрагент "
               "ИЗ Документ.РеализацияТоваровУслуг УПОРЯДОЧИТЬ ПО Дата УБЫВ")
Q_ITEMS = "ВЫБРАТЬ ПЕРВЫЕ 8 Наименование ИЗ Справочник.Номенклатура"
Q_MONTHLY = (f"ВЫБРАТЬ ГОД(Док.Дата) КАК Год, МЕСЯЦ(Док.Дата) КАК Месяц, "
             f"СУММА(ТЧ.Количество * ТЧ.Цена) КАК Сумма {JOIN} "
             f"СГРУППИРОВАТЬ ПО ГОД(Док.Дата), МЕСЯЦ(Док.Дата) "
             f"УПОРЯДОЧИТЬ ПО Год, Месяц")
Q_TOP = (f"ВЫБРАТЬ Док.Контрагент КАК Контрагент, "
         f"СУММА(ТЧ.Количество * ТЧ.Цена) КАК Сумма {JOIN} "
         f"СГРУППИРОВАТЬ ПО Док.Контрагент УПОРЯДОЧИТЬ ПО Сумма УБЫВ")
Q_PERIOD_SUM = (f"ВЫБРАТЬ КОЛИЧЕСТВО(РАЗЛИЧНЫЕ Док.Ссылка) КАК Документов, "
                f"СУММА(ТЧ.Количество * ТЧ.Цена) КАК Сумма {JOIN} "
                f"ГДЕ Док.Дата >= ДАТАВРЕМЯ({{y1}},{{m1}},{{d1}}) "
                f"И Док.Дата <= ДАТАВРЕМЯ({{y2}},{{m2}},{{d2}},23,59,59)")
Q_PERIOD_TOP = (f"ВЫБРАТЬ ПЕРВЫЕ 10 ТЧ.Номенклатура КАК Позиция, "
                f"СУММА(ТЧ.Количество) КАК Количество, "
                f"СУММА(ТЧ.Количество * ТЧ.Цена) КАК Сумма {JOIN} "
                f"ГДЕ Док.Дата >= ДАТАВРЕМЯ({{y1}},{{m1}},{{d1}}) "
                f"И Док.Дата <= ДАТАВРЕМЯ({{y2}},{{m2}},{{d2}},23,59,59) "
                f"СГРУППИРОВАТЬ ПО ТЧ.Номенклатура УПОРЯДОЧИТЬ ПО Сумма УБЫВ")
Q_PERIOD_DOCS = ('ВЫБРАТЬ ПЕРВЫЕ 50 Номер, Дата, Контрагент '
                 'ИЗ Документ.РеализацияТоваровУслуг '
                 'ГДЕ Дата >= ДАТАВРЕМЯ({y1},{m1},{d1}) '
                 'И Дата <= ДАТАВРЕМЯ({y2},{m2},{d2},23,59,59) '
                 'УПОРЯДОЧИТЬ ПО Дата УБЫВ')
Q_HEADER = ('ВЫБРАТЬ ПЕРВЫЕ 1 Номер, Дата, Контрагент, Проведен '
            'ИЗ Документ.РеализацияТоваровУслуг ГДЕ Номер = "{number}"')
Q_LINES = ('ВЫБРАТЬ Номенклатура, Количество, Цена '
           'ИЗ Документ.РеализацияТоваровУслуг.Товары КАК Товары '
           'ГДЕ Товары.Ссылка В (ВЫБРАТЬ Ссылка '
           'ИЗ Документ.РеализацияТоваровУслуг ГДЕ Номер = "{number}")')


def ask_1c(query):
    try:
        resp = bridge().send("запрос_1с", {"query": query}, PROFILE, "low")
    except (BridgeTimeout, BridgeError) as exc:
        return None, str(exc)
    except Exception as exc:                        # noqa: BLE001
        return None, f"сбой обмена: {type(exc).__name__}: {exc}"
    if resp.get("status") != "ok":
        return None, (resp.get("error") or {}).get("message") or resp.get("status")
    return resp.get("result") or {}, None


def cached(key, ttl, producer):
    item = CACHE.get(key)
    if item and time.time() - item[0] < ttl:
        return item[1]
    value = producer()
    CACHE[key] = (time.time(), value)
    return value


def health():
    try:
        resp = bridge().send("проверка_связи", {}, PROFILE, "low")
    except (BridgeTimeout, BridgeError) as exc:
        return {"status": "unavailable", "error": str(exc), "ts": now_ts()}
    return {"status": resp.get("status"),
            "platform": (resp.get("result") or {}).get("platform"),
            "bridge": (resp.get("result") or {}).get("bsl_version"),
            "ts": now_ts()}


def panel():
    def build():
        from concurrent.futures import ThreadPoolExecutor
        counts, errors = {}, []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {key: pool.submit(ask_1c, query) for key, query in Q_COUNTS.items()}
            f_docs = pool.submit(ask_1c, Q_LAST_DOCS)
            f_items = pool.submit(ask_1c, Q_ITEMS)
            for key, fut in futures.items():
                res, err = fut.result()
                counts[key] = None if err else ((res.get("rows") or [[0]])[0][0])
                if err:
                    errors.append({"query": key, "error": err})
            docs, err = f_docs.result()
            if err:
                errors.append({"query": "docs", "error": err})
            items, err2 = f_items.result()
            if err2:
                errors.append({"query": "items", "error": err2})
        data = {"source": "1С:Предприятие (живой мост)", "ts": now_ts(),
                "counts": counts,
                "documents": (docs or {}).get("rows") or [],
                "items": [r[0] for r in ((items or {}).get("rows") or [])],
                "errors": errors}
        if not errors:
            CACHE["last_ok"] = (time.time(), data)
        else:
            last = CACHE.get("last_ok")
            data["last_success"] = (datetime.fromtimestamp(last[0])
                                    .isoformat(timespec="seconds") if last else None)
        return data
    # кэш 3 с: страница обновляется каждые 15 с, но переходы по карточкам и
    # повторные открытия не должны каждый раз ждать 1С
    return cached("panel", 3, build)


def kpi():
    def build():
        months, err = ask_1c(Q_MONTHLY)
        if err:
            return {"error": err, "ts": now_ts()}
        series, total = [], 0.0
        for year, month, amount in (months.get("rows") or []):
            amount = float(amount or 0)
            total += amount
            series.append({"label": f"{int(month):02d}.{str(int(year))[2:]}",
                           "year": int(year), "month": int(month),
                           "sum": round(amount, 2)})
        return {"source": "1С", "ts": now_ts(), "months": series,
                "total": round(total, 2),
                "average": round(total / len(series), 2) if series else 0}
    return cached("kpi", 30, build)


def top():
    def build():
        res, err = ask_1c(Q_TOP)
        if err:
            return {"error": err, "ts": now_ts()}
        rows = [{"name": r[0], "sum": round(float(r[1] or 0), 2)}
                for r in (res.get("rows") or [])][:6]
        return {"source": "1С", "ts": now_ts(), "items": rows}
    return cached("top", 30, build)


def search(query):
    q = (query or "").strip()
    if not q:
        return {"error": "пустой запрос", "ts": now_ts()}
    safe = re.sub(r'[^0-9A-Za-zА-Яа-яЁё _.-]', '', q)[:40]
    if not safe:
        return {"error": "в запросе нет допустимых символов", "ts": now_ts()}
    pattern = f"%{safe}%"
    query_text = ('ВЫБРАТЬ ПЕРВЫЕ 20 Номер, Дата, Контрагент '
                  'ИЗ Документ.РеализацияТоваровУслуг КАК Док '
                  'ГДЕ Док.Контрагент.Наименование ПОДОБНО "{p}" '
                  'ИЛИ Док.Номер ПОДОБНО "{p}" '
                  'УПОРЯДОЧИТЬ ПО Дата УБЫВ').format(p=pattern)
    res, err = ask_1c(query_text)
    if err:
        return {"error": err, "ts": now_ts()}
    return {"source": "1С", "ts": now_ts(), "query": safe,
            "rows": res.get("rows") or []}


def parse_day(value, fallback):
    """Дата из строки YYYY-MM-DD. Только цифры попадают в текст запроса к 1С."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", (value or "").strip())
    if not m:
        return fallback
    y, mo, d = (int(x) for x in m.groups())
    if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
        return (y, mo, d)
    return fallback


def period(date_from, date_to):
    start = parse_day(date_from, (2026, 1, 1))
    end = parse_day(date_to, (2026, 9, 30))
    if start > end:
        start, end = end, start
    params = {"y1": start[0], "m1": start[1], "d1": start[2],
              "y2": end[0], "m2": end[1], "d2": end[2]}
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_sum = pool.submit(ask_1c, Q_PERIOD_SUM.format(**params))
        f_top = pool.submit(ask_1c, Q_PERIOD_TOP.format(**params))
        summary, err = f_sum.result()
        positions, err2 = f_top.result()
    if err:
        return {"error": err, "ts": now_ts()}
    row = (summary.get("rows") or [[0, 0]])[0]
    return {
        "source": "1С", "ts": now_ts(),
        "period": {"from": "%04d-%02d-%02d" % start, "to": "%04d-%02d-%02d" % end},
        "documents": int(row[0] or 0),
        "total": round(float(row[1] or 0), 2),
        "positions": [{"item": r[0], "qty": r[1], "sum": round(float(r[2] or 0), 2)}
                      for r in (positions or {}).get("rows") or []],
        "error": err2,
    }


def export_csv(kind, date_from, date_to):
    """CSV с BOM и «;» — открывается в Excel без настроек."""
    start = parse_day(date_from, (2026, 1, 1))
    end = parse_day(date_to, (2026, 9, 30))
    params = {"y1": start[0], "m1": start[1], "d1": start[2],
              "y2": end[0], "m2": end[1], "d2": end[2]}
    if kind == "positions":
        query = Q_PERIOD_TOP.format(**params)
        header = ["Позиция", "Количество", "Сумма"]
    else:
        query = Q_PERIOD_DOCS.format(**params)
        header = ["Номер", "Дата", "Контрагент"]
    res, err = ask_1c(query)
    if err:
        return None, err
    rows = res.get("rows") or []
    truncated = bool(res.get("truncated")) or len(rows) >= 50
    lines = [";".join(header)]
    for r in rows:
        lines.append(";".join(str(x).replace(";", ",") for x in r))
    if truncated:
        lines.append("# показаны первые 50 строк (ограничение моста 1С)")
    return "\r\n".join(lines) + "\r\n", None


def order(number):
    digits = "".join(ch for ch in str(number or "") if ch.isdigit())
    if not digits:
        return {"error": "номер документа должен содержать цифры", "ts": now_ts()}
    head, err = ask_1c(Q_HEADER.format(number=digits))
    if err:
        return {"error": err, "ts": now_ts(), "number": digits}
    rows = head.get("rows") or []
    if not rows:
        return {"error": f"документ {digits} не найден", "ts": now_ts(), "number": digits}
    lines, err2 = ask_1c(Q_LINES.format(number=digits))
    positions, total = [], 0.0
    for item, qty, price in (lines or {}).get("rows") or []:
        amount = float(qty) * float(price)
        total += amount
        positions.append({"item": item, "qty": qty, "price": price,
                          "amount": round(amount, 2)})
    return {"source": "1С:Предприятие (живой мост)", "ts": now_ts(),
            "number": rows[0][0], "date": rows[0][1], "counterparty": rows[0][2],
            "posted": bool(rows[0][3]), "positions": positions,
            "total": round(total, 2), "error": err2}


def production():
    def build():
        try:
            from source_mode import current
            return current()
        except Exception as exc:                    # noqa: BLE001
            return {"mode": "unavailable", "available": False,
                    "error": f"адаптер не загрузился: {exc}"}
    return cached("prod", 5, build)


DATA_WORDS = ("документ", "контрагент", "номенклатур", "реализац", "заказ",
              "сколько", "покажи", "список", "последн", "выручк")


def ask_phrase(phrase):
    low = (phrase or "").lower()
    if any(w in low for w in DATA_WORDS):
        if "контрагент" in low:
            res, err = ask_1c(Q_COUNTS["counterparties"])
            if err:
                return {"kind": "data", "answer": f"1С не ответила: {err}",
                        "source": "1С", "ts": now_ts()}
            return {"kind": "data",
                    "answer": f"Контрагентов в базе: {(res.get('rows') or [[0]])[0][0]}",
                    "source": "1С", "ts": now_ts()}
        if "выручк" in low:
            data = kpi()
            if data.get("error"):
                return {"kind": "data", "answer": f"1С не ответила: {data['error']}",
                        "source": "1С", "ts": now_ts()}
            return {"kind": "data",
                    "answer": f"Выручка по документам реализации: {data['total']:,.0f} ₽ "
                              f"(среднее за месяц {data['average']:,.0f} ₽)",
                    "source": "1С", "ts": now_ts()}
        if "номенклатур" in low:
            res, err = ask_1c(Q_ITEMS)
            if err:
                return {"kind": "data", "answer": f"1С не ответила: {err}",
                        "source": "1С", "ts": now_ts()}
            return {"kind": "data",
                    "answer": "Номенклатура: " + ", ".join(r[0] for r in (res.get("rows") or [])),
                    "source": "1С", "ts": now_ts()}
        res, err = ask_1c(Q_LAST_DOCS)
        if err:
            return {"kind": "data", "answer": f"1С не ответила: {err}",
                    "source": "1С", "ts": now_ts()}
        parts = [f"{r[1]} {r[2]}" for r in (res.get("rows") or [])]
        return {"kind": "data", "answer": "Последние документы: " + "; ".join(parts),
                "source": "1С", "ts": now_ts()}

    try:
        from search import search as rag_search, status
        if not status()["ready"]:
            return {"kind": "rag", "answer": "База знаний недоступна",
                    "source": "RAG", "ts": now_ts()}
        hits = rag_search(phrase, top_k=3)
    except Exception as exc:                        # noqa: BLE001
        return {"kind": "rag", "answer": f"Поиск недоступен: {exc}",
                "source": "RAG", "ts": now_ts()}
    if not hits:
        return {"kind": "rag", "answer": "В базе знаний ничего не найдено",
                "source": "RAG", "ts": now_ts()}
    best = hits[0]
    src = (best.get("metadata") or {}).get("file") or best.get("source")
    return {"kind": "rag", "answer": best.get("text", "")[:700],
            "source": f"RAG · {src}", "ts": now_ts()}


PAGE = r"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Единая панель предприятия</title>
<style>
:root{--bg:#0f1720;--panel:#17222e;--panel2:#1d2b39;--line:#27374a;--txt:#e8eef4;--muted:#93a4b5;--accent:#3ea6ff;--ok:#33c47a;--bad:#e05c5c;--warn:#e0b34d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.45 "Segoe UI",system-ui,sans-serif}
header{display:flex;align-items:center;gap:16px;padding:14px 22px;background:linear-gradient(90deg,#14202b,#1a2c3d);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
header h1{font-size:17px;margin:0;font-weight:600;letter-spacing:.2px}
header .sub{color:var(--muted);font-size:12px}
.chips{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
.chip{padding:5px 10px;border-radius:20px;font-size:12px;border:1px solid var(--line);background:#101a24}
.chip.ok{border-color:#2b6b4a;color:#b9f0d1;background:#12251c}
.chip.bad{border-color:#6b2b2b;color:#f3c3c3;background:#241414}
.chip.warn{border-color:#6b5a2b;color:#f0e2b9;background:#241f12}
main{display:grid;grid-template-columns:2fr 1fr;gap:16px;padding:16px 22px 28px;max-width:1680px;margin:0 auto}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.card h2{margin:0 0 12px;font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.kpi{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi .v{font-size:24px;font-weight:650;letter-spacing:.3px}
.kpi .l{color:var(--muted);font-size:12px;margin-top:2px}
.kpi .m{color:#6f8296;font-size:11px;margin-top:6px}
.grid2{display:grid;grid-template-columns:1.6fr 1fr;gap:16px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--muted);font-weight:500;text-align:left;padding:6px;border-bottom:1px solid var(--line);font-size:12px}
td{padding:7px 6px;border-bottom:1px solid #1e2b3a}
tr.row:hover td{background:#1b2836;cursor:pointer}
.right{text-align:right}
.search{display:flex;gap:8px;margin-bottom:10px}
input{flex:1;background:#101a24;border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:9px 11px;font-size:13px}
input:focus{outline:none;border-color:var(--accent)}
button{background:var(--accent);color:#06121c;border:0;border-radius:8px;padding:9px 14px;font-weight:600;cursor:pointer}
button.ghost{background:#182635;color:var(--txt);border:1px solid var(--line)}
.err{background:#241414;border-left:3px solid var(--bad);padding:9px 11px;border-radius:8px;font-size:13px;color:#f3c3c3}
.okbox{background:#12251c;border-left:3px solid var(--ok);padding:9px 11px;border-radius:8px;font-size:13px;color:#b9f0d1}
.muted{color:var(--muted);font-size:12px}
#chat{display:flex;flex-direction:column;height:calc(100vh - 150px);min-height:420px}
#log{flex:1;overflow:auto;padding-right:4px}
.msg{background:#132030;border:1px solid #1e2b3a;border-radius:10px;padding:9px 11px;margin-bottom:8px;font-size:13px}
.msg.me{background:#16283a;border-color:#24415c}
.src{color:#6f8296;font-size:11px;margin-top:5px}
.bar{height:26px;background:#132030;border-radius:6px;overflow:hidden;margin:3px 0 9px}
.bar>div{height:100%;background:linear-gradient(90deg,#2b6fb0,#3ea6ff)}
.bar span{position:absolute;margin:-21px 0 0 8px;font-size:11px;color:#cfe3f5}
.hbars{display:grid;gap:2px}
.drawer{position:fixed;inset:0;background:rgba(6,10,14,.6);display:none;align-items:center;justify-content:center;z-index:20}
.drawer.open{display:flex}
.sheet{background:var(--panel);border:1px solid var(--line);border-radius:14px;width:min(760px,94vw);max-height:86vh;overflow:auto;padding:18px}
.sheet h3{margin:0 0 4px;font-size:16px}
.sheet .close{float:right;background:#182635;border:1px solid var(--line);color:var(--txt)}
.pos{border-top:1px solid var(--line);margin-top:12px}
.total{font-size:16px;margin-top:10px}
.dim{opacity:.55}
@media(max-width:1100px){main{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}}
</style></head><body>
<header>
 <div><h1>Единая панель предприятия</h1><div class="sub" id="src">источник: проверяется…</div></div>
 <div class="chips">
  <span class="chip" id="chip-1c">1С: проверка…</span>
  <span class="chip" id="chip-prod">SCADA/OPC UA: проверка…</span>
  <span class="chip" id="chip-time">—</span>
 </div>
</header>

<main>
 <div>
  <div class="kpis">
   <div class="kpi"><div class="v" id="k-revenue">—</div><div class="l">выручка, ₽</div><div class="m" id="k-revenue-m">из документов реализации</div></div>
   <div class="kpi"><div class="v" id="k-docs">—</div><div class="l">документов</div><div class="m">в базе 1С</div></div>
   <div class="kpi"><div class="v" id="k-cp">—</div><div class="l">контрагентов</div><div class="m">справочник 1С</div></div>
   <div class="kpi"><div class="v" id="k-avg">—</div><div class="l">средний чек, ₽</div><div class="m">выручка / документы</div></div>
  </div>

  <div class="card" style="margin-bottom:16px">
   <h2>Выручка по месяцам</h2>
   <svg id="chart" width="100%" height="190" preserveAspectRatio="none"></svg>
   <div class="muted" id="chart-note"></div>
  </div>

  <div class="card" style="margin-bottom:16px">
   <h2>Отчёт за период</h2>
   <div class="search">
    <input type="date" id="from" value="2026-01-01" style="max-width:170px">
    <input type="date" id="to" value="2026-09-30" style="max-width:170px">
    <button onclick="loadReport()">Показать</button>
    <button class="ghost" onclick="exportCsv('documents')">CSV документов</button>
    <button class="ghost" onclick="exportCsv('positions')">CSV позиций</button>
   </div>
   <div id="rep-sum" class="muted">выберите период и нажмите «Показать»</div>
   <table id="rep" style="margin-top:10px"><thead><tr><th>Позиция</th><th class="right">Кол-во</th><th class="right">Сумма, ₽</th></tr></thead><tbody></tbody></table>
  </div>

  <div class="grid2">
   <div class="card">
    <h2>Документы реализации</h2>
    <div class="search">
     <input id="q" placeholder="номер документа или контрагент, например 000000385 или Клевер">
     <button onclick="doSearch()">Найти</button>
     <button class="ghost" onclick="resetDocs()">Сбросить</button>
    </div>
    <table id="docs"><thead><tr><th>Номер</th><th>Дата</th><th>Контрагент</th></tr></thead><tbody></tbody></table>
    <div class="muted" id="docs-note">нажмите на строку — откроется карточка</div>
   </div>
   <div class="card">
    <h2>Топ контрагентов по сумме</h2>
    <div class="hbars" id="top"></div>
   </div>
  </div>

  <div class="card" style="margin-top:16px">
   <h2>Производство · SCADA / OPC UA</h2>
   <div id="prod-state" class="muted">проверка источника…</div>
   <table id="prod"><thead><tr><th>Параметр</th><th class="right">Значение</th><th>Ед.</th><th>Статус</th></tr></thead><tbody></tbody></table>
  </div>
 </div>

 <div class="card" id="chatcard">
  <h2>Чат с системой</h2>
  <div id="chat">
   <div id="log"><div class="msg">Спросите про данные: «сколько контрагентов», «покажи последние документы», «какая выручка». Или про 1С: «как создать внешнюю печатную форму».</div></div>
   <div class="search" style="margin:8px 0 0">
    <input id="phrase" placeholder="вопрос…">
    <button onclick="ask()">Спросить</button>
   </div>
  </div>
 </div>
</main>

<div class="drawer" id="drawer" onclick="if(event.target===this)closeCard()">
 <div class="sheet">
  <button class="close" onclick="closeCard()">Закрыть</button>
  <h3 id="card-title">Документ</h3>
  <div class="muted" id="card-head"></div>
  <div class="pos"><table id="card-lines"><thead><tr><th>Позиция</th><th class="right">Кол-во</th><th class="right">Цена</th><th class="right">Сумма</th></tr></thead><tbody></tbody></table></div>
  <div class="total" id="card-total"></div>
  <div class="muted" id="card-src"></div>
 </div>
</div>

<script>
const fmt=n=>new Intl.NumberFormat('ru-RU').format(Math.round(n));
async function j(u,opt){const r=await fetch(u,opt);return r.json()}

function drawChart(months){
  const svg=document.getElementById('chart'); svg.innerHTML='';
  if(!months||!months.length){document.getElementById('chart-note').textContent='нет данных';return}
  const W=svg.clientWidth||900,H=190,pad=26;
  const max=Math.max(...months.map(m=>m.sum))||1;
  const bw=(W-pad*2)/months.length;
  months.forEach((m,i)=>{
    const h=(H-pad-16)*m.sum/max;
    const x=pad+i*bw+bw*0.15, y=H-pad-h, w=bw*0.7;
    const r=document.createElementNS('http://www.w3.org/2000/svg','rect');
    r.setAttribute('x',x);r.setAttribute('y',y);r.setAttribute('width',w);r.setAttribute('height',h);
    r.setAttribute('rx',3);r.setAttribute('fill','#2f7fbe');
    const t=document.createElementNS('http://www.w3.org/2000/svg','title');
    t.textContent=m.label+': '+fmt(m.sum)+' ₽';r.appendChild(t);svg.appendChild(r);
    if(i%3===0||months.length<=12){
      const lb=document.createElementNS('http://www.w3.org/2000/svg','text');
      lb.setAttribute('x',x+w/2);lb.setAttribute('y',H-8);lb.setAttribute('fill','#7f93a6');
      lb.setAttribute('font-size','10');lb.setAttribute('text-anchor','middle');lb.textContent=m.label;
      svg.appendChild(lb);
    }
  });
  document.getElementById('chart-note').textContent='месяцев: '+months.length+' · максимум '+fmt(max)+' ₽';
}

async function refresh(){
  const h=await j('/api/health');
  const c1=document.getElementById('chip-1c');
  if(h.status==='ok'){c1.className='chip ok';c1.textContent='1С: связь есть · мост '+h.bridge}
  else{c1.className='chip bad';c1.textContent='1С: НЕТ СВЯЗИ'}
  document.getElementById('chip-time').textContent=h.ts||'—';

  const p=await j('/api/panel');
  document.getElementById('src').textContent='источник: '+p.source+' · получено '+p.ts;
  document.getElementById('k-docs').textContent=p.counts.documents??'—';
  document.getElementById('k-cp').textContent=p.counts.counterparties??'—';
  const docs=p.documents||[];
  const tbody=document.querySelector('#docs tbody'); tbody.innerHTML='';
  docs.forEach(r=>{const tr=document.createElement('tr');tr.className='row';
    tr.onclick=()=>openCard(r[0]);
    r.forEach(c=>{const td=document.createElement('td');td.textContent=c;tr.appendChild(td)});
    tbody.appendChild(tr)});
  document.getElementById('docs-note').textContent=
    p.errors&&p.errors.length?('часть данных не получена: '+p.errors.map(e=>e.query).join(', ')):
    'нажмите на строку — откроется карточка';

  const k=await j('/api/kpi');
  if(!k.error){document.getElementById('k-revenue').textContent=fmt(k.total);
    document.getElementById('k-revenue-m').textContent='среднее за месяц '+fmt(k.average)+' ₽';
    const dn=p.counts.documents;
    document.getElementById('k-avg').textContent=dn?fmt(k.total/dn):'—';
    drawChart(k.months);}
  else {document.getElementById('k-revenue').textContent='—';
    document.getElementById('chart-note').textContent='1С не ответила: '+k.error}

  const t=await j('/api/top');
  const box=document.getElementById('top'); box.innerHTML='';
  if(t.error){box.innerHTML='<div class="err">'+t.error+'</div>'}
  else{const max=t.items.length?t.items[0].sum:1;
    t.items.forEach(it=>{const d=document.createElement('div');
      d.innerHTML='<div class="muted">'+it.name+' · '+fmt(it.sum)+' ₽</div>'+
        '<div class="bar"><div style="width:'+Math.max(4,(it.sum/max*100))+'%"></div></div>';
      box.appendChild(d)})}

  const pr=await j('/api/production');
  const ps=document.getElementById('prod-state'), chip=document.getElementById('chip-prod');
  const tb=document.querySelector('#prod tbody'); tb.innerHTML='';
  if(pr.available){chip.className='chip ok';chip.textContent='OPC UA: есть данные';
    ps.className='okbox';ps.textContent='источник: '+pr.source+' · '+pr.ts+' · режим '+pr.mode;
    (pr.values||[]).forEach(v=>{const tr=document.createElement('tr');
      [v.name,(typeof v.value==='number'?v.value.toFixed(1):String(v.value)),v.unit||'',v.alarm||v.quality||'']
        .forEach((x,i)=>{const td=document.createElement('td');td.textContent=x;if(i===1)td.className='right';tr.appendChild(td)});
      tb.appendChild(tr)})}
  else{chip.className='chip warn';chip.textContent='OPC UA: не подключён';
    ps.className='err';ps.textContent=pr.error||('режим: '+pr.mode)}
}

async function loadReport(){
  const f=document.getElementById('from').value, t=document.getElementById('to').value;
  const d=await j('/api/report?from='+encodeURIComponent(f)+'&to='+encodeURIComponent(t));
  const s=document.getElementById('rep-sum');
  const tb=document.querySelector('#rep tbody'); tb.innerHTML='';
  if(d.error){s.className='err';s.textContent='1С не ответила: '+d.error;return}
  s.className='okbox';
  s.textContent='период '+d.period.from+' — '+d.period.to+' · документов: '+d.documents+
    ' · сумма: '+fmt(d.total)+' ₽ · источник 1С · '+d.ts;
  (d.positions||[]).forEach(p=>{const tr=document.createElement('tr');
    [p.item,p.qty,fmt(p.sum)].forEach((v,i)=>{const td=document.createElement('td');
      td.textContent=v; if(i>0)td.className='right'; tr.appendChild(td)});
    tb.appendChild(tr)});
}
function exportCsv(kind){
  const f=document.getElementById('from').value, t=document.getElementById('to').value;
  window.location='/api/export?type='+kind+'&from='+encodeURIComponent(f)+'&to='+encodeURIComponent(t);
}

async function openCard(num){
  const d=await j('/api/order?number='+encodeURIComponent(num));
  document.getElementById('drawer').classList.add('open');
  document.getElementById('card-title').textContent=d.error?'Карточка недоступна':('Документ № '+d.number);
  document.getElementById('card-head').textContent=d.error?d.error:
    (d.date+' · '+d.counterparty+' · '+(d.posted?'проведён':'не проведён'));
  const tb=document.querySelector('#card-lines tbody'); tb.innerHTML='';
  (d.positions||[]).forEach(p=>{const tr=document.createElement('tr');
    [[p.item,'left'],[p.qty,'right'],[fmt(p.price),'right'],[fmt(p.amount),'right']]
      .forEach(([v,c])=>{const td=document.createElement('td');td.textContent=v;td.className=c;tr.appendChild(td)});
    tb.appendChild(tr)});
  document.getElementById('card-total').textContent=d.error?'':'Итого: '+fmt(d.total)+' ₽ · позиций: '+(d.positions||[]).length;
  document.getElementById('card-src').textContent=d.error?'':(d.source+' · '+d.ts);
}
function closeCard(){document.getElementById('drawer').classList.remove('open')}

async function doSearch(){
  const q=document.getElementById('q').value.trim(); if(!q)return resetDocs();
  const d=await j('/api/search?q='+encodeURIComponent(q));
  const tb=document.querySelector('#docs tbody'); tb.innerHTML='';
  if(d.error){document.getElementById('docs-note').textContent=d.error;return}
  (d.rows||[]).forEach(r=>{const tr=document.createElement('tr');tr.className='row';
    tr.onclick=()=>openCard(r[0]);
    r.forEach(c=>{const td=document.createElement('td');td.textContent=c;tr.appendChild(td)});
    tb.appendChild(tr)});
  document.getElementById('docs-note').textContent='найдено: '+(d.rows||[]).length+' · запрос «'+d.query+'» · '+d.ts;
}
function resetDocs(){document.getElementById('q').value='';refresh()}

async function ask(){
  const el=document.getElementById('phrase'), q=el.value.trim(); if(!q)return;
  const log=document.getElementById('log');
  log.insertAdjacentHTML('afterbegin','<div class="msg me">'+q+'</div>');
  el.value='';
  const r=await j('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phrase:q})});
  log.insertAdjacentHTML('afterbegin','<div class="msg">'+r.answer.replace(/</g,'&lt;')+
    '<div class="src">источник: '+r.source+' · '+r.ts+'</div></div>');
}
document.getElementById('phrase').addEventListener('keydown',e=>{if(e.key==='Enter')ask()});
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')doSearch()});
refresh(); setInterval(refresh,15000); loadReport();
window.addEventListener('resize',()=>j('/api/kpi').then(k=>{if(!k.error)drawChart(k.months)}));
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path, qs = parsed.path, urllib.parse.parse_qs(parsed.query)
        if path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/export":
            kind = (qs.get("type") or ["documents"])[0]
            text, err = export_csv(kind, (qs.get("from") or [""])[0],
                                   (qs.get("to") or [""])[0])
            if err:
                self._json({"error": err}, 500)
                return
            body = ("\ufeff" + text).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="{kind}.csv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        routes = {
            "/api/health": health,
            "/api/panel": panel,
            "/api/kpi": kpi,
            "/api/top": top,
            "/api/production": production,
            "/api/order": lambda: order((qs.get("number") or [""])[0]),
            "/api/search": lambda: search((qs.get("q") or [""])[0]),
            "/api/report": lambda: period((qs.get("from") or [""])[0],
                                          (qs.get("to") or [""])[0]),
        }
        fn = routes.get(path)
        if not fn:
            self.send_error(404)
            return
        self._json(fn())

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/api/ask":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:                           # noqa: BLE001
            self._json({"answer": "некорректный запрос"}, 400)
            return
        self._json(ask_phrase(str(data.get("phrase") or "")))

    def log_message(self, *args):
        pass


def warmup():
    """Прогрев: модель эмбеддингов и первый обмен с 1С.

    Без этого первый вопрос к RAG на демо занимает ~90 секунд (загрузка модели),
    а первый запрос к 1С — до 8 секунд.
    """
    try:
        from search import search as rag_search, status
        status()
        rag_search("проверка", top_k=1)
    except Exception:                               # noqa: BLE001
        pass
    try:
        health()
    except Exception:                               # noqa: BLE001
        pass


def main():
    global EXCHANGE
    ap = argparse.ArgumentParser()
    ap.add_argument("--exchange", default=str(Path(__file__).resolve().parent.parent / "exchange"))
    ap.add_argument("--port", type=int, default=8077)
    args = ap.parse_args()
    EXCHANGE = Path(args.exchange)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    import threading
    threading.Thread(target=warmup, daemon=True).start()
    print(f"панель: http://127.0.0.1:{args.port}  exchange={EXCHANGE}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
