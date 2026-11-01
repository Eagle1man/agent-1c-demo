#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Единый интерфейс: чат + панель предприятия на живых данных 1С.

Зачем отдельный сервер: `agent/web_app.py` — демонстрационная витрина на
демо-данных. Для шага 2 нужен экран, который показывает **только то, что
реально пришло из 1С**, с источником и временем получения, и честно говорит
«источник недоступен», когда мост молчит.

Что отдаёт:
    GET  /            — страница: чат + панель
    GET  /api/health  — состояние моста (проверка_связи)
    GET  /api/panel   — счётчики и последние документы из 1С
    POST /api/ask     — вопрос: данные 1С (детерминированный маршрут) или RAG

Запуск:
    py agent/panel_server.py --exchange D:\\agent-1c-demo\\exchange --port 8077
"""
import argparse
import json
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

# Последний удачный снимок панели: показываем его с временем, если 1С недоступна.
LAST_OK = {"ts": None, "data": None}
PROD_CACHE = {"ts": 0.0, "data": None}

COUNTS = {
    "counterparties": "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего ИЗ Справочник.Контрагенты",
    "nomenclature": "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего ИЗ Справочник.Номенклатура",
    "documents": "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего ИЗ Документ.РеализацияТоваровУслуг",
}
LAST_DOCS = ("ВЫБРАТЬ ПЕРВЫЕ 5 Номер, Дата, Контрагент "
             "ИЗ Документ.РеализацияТоваровУслуг УПОРЯДОЧИТЬ ПО Дата УБЫВ")
ITEM_QUERY = "ВЫБРАТЬ ПЕРВЫЕ 8 Наименование ИЗ Справочник.Номенклатура"

ORDER_HEADER = ('ВЫБРАТЬ ПЕРВЫЕ 1 Номер, Дата, Контрагент, Проведен '
                'ИЗ Документ.РеализацияТоваровУслуг ГДЕ Номер = "{number}"')
ORDER_LINES = ('ВЫБРАТЬ Номенклатура, Количество, Цена '
               'ИЗ Документ.РеализацияТоваровУслуг.Товары КАК Товары '
               'ГДЕ Товары.Ссылка В (ВЫБРАТЬ Ссылка '
               'ИЗ Документ.РеализацияТоваровУслуг ГДЕ Номер = "{number}")')


def now_ts():
    return datetime.now().isoformat(timespec="seconds")


def bridge():
    return Bridge(EXCHANGE, user="панель")


def ask_1c(query):
    """Один запрос через мост. Возвращает (ответ, ошибка|None)."""
    try:
        resp = bridge().send("запрос_1с", {"query": query}, PROFILE, "low")
    except (BridgeTimeout, BridgeError) as exc:
        return None, str(exc)
    if resp.get("status") != "ok":
        err = (resp.get("error") or {}).get("message") or resp.get("status")
        return None, err
    return resp.get("result") or {}, None


def health():
    try:
        resp = bridge().send("проверка_связи", {}, PROFILE, "low")
    except (BridgeTimeout, BridgeError) as exc:
        return {"status": "unavailable", "error": str(exc), "ts": now_ts()}
    return {
        "status": resp.get("status"),
        "platform": (resp.get("result") or {}).get("platform"),
        "bridge": (resp.get("result") or {}).get("bsl_version"),
        "ts": now_ts(),
        "id": resp.get("id"),
    }


def panel():
    counts, errors = {}, []
    for key, query in COUNTS.items():
        res, err = ask_1c(query)
        if err:
            errors.append({"query": key, "error": err})
            counts[key] = None
        else:
            rows = res.get("rows") or [[0]]
            counts[key] = rows[0][0]

    docs, err = ask_1c(LAST_DOCS)
    if err:
        errors.append({"query": "last_docs", "error": err})
    items, err2 = ask_1c(ITEM_QUERY)
    if err2:
        errors.append({"query": "items", "error": err2})

    data = {
        "source": "1С:Предприятие (живой мост)",
        "ts": now_ts(),
        "counts": counts,
        "documents": (docs or {}).get("rows") or [],
        "document_columns": (docs or {}).get("columns") or [],
        "items": [r[0] for r in ((items or {}).get("rows") or [])],
        "errors": errors,
    }
    if not errors:
        LAST_OK["ts"] = data["ts"]
        LAST_OK["data"] = data
    else:
        data["last_success"] = LAST_OK["ts"]
        if LAST_OK["data"]:
            data["stale"] = LAST_OK["data"]
    return data


DATA_WORDS = ("документ", "контрагент", "номенклатур", "реализац", "заказ",
              "сколько", "покажи", "список", "последн")


def ask_phrase(phrase):
    """Детерминированный маршрут: вопрос про данные → запрос в 1С, иначе RAG."""
    low = phrase.lower()
    if any(w in low for w in DATA_WORDS):
        if "контрагент" in low:
            query = COUNTS["counterparties"]
            res, err = ask_1c(query)
            if err:
                return {"kind": "data", "answer": f"1С не ответила: {err}",
                        "source": "1С", "ts": now_ts()}
            total = (res.get("rows") or [[0]])[0][0]
            return {"kind": "data", "answer": f"Контрагентов в базе: {total}",
                    "source": "1С", "ts": now_ts()}
        if "номенклатур" in low:
            res, err = ask_1c(ITEM_QUERY)
            if err:
                return {"kind": "data", "answer": f"1С не ответила: {err}",
                        "source": "1С", "ts": now_ts()}
            names = ", ".join(r[0] for r in (res.get("rows") or []))
            return {"kind": "data", "answer": f"Номенклатура: {names}",
                    "source": "1С", "ts": now_ts()}
        res, err = ask_1c(LAST_DOCS)
        if err:
            return {"kind": "data", "answer": f"1С не ответила: {err}",
                    "source": "1С", "ts": now_ts()}
        parts = [f"{r[1]} {r[2]}" for r in (res.get("rows") or [])]
        return {"kind": "data", "answer": "Последние документы: " + "; ".join(parts),
                "source": "1С", "ts": now_ts()}

    try:
        from search import search, status
        if not status()["ready"]:
            return {"kind": "rag", "answer": "База знаний недоступна",
                    "source": "RAG", "ts": now_ts()}
        hits = search(phrase, top_k=3)
    except Exception as exc:                        # noqa: BLE001
        return {"kind": "rag", "answer": f"Поиск недоступен: {exc}",
                "source": "RAG", "ts": now_ts()}
    if not hits:
        return {"kind": "rag", "answer": "В базе знаний ничего не найдено",
                "source": "RAG", "ts": now_ts()}
    best = hits[0]
    src = (best.get("metadata") or {}).get("file") or best.get("source")
    return {"kind": "rag", "answer": best.get("text", "")[:600],
            "source": f"RAG · {src}", "ts": now_ts()}


PAGE = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>Предприятие: панель и чат</title>
<style>
 body{font-family:Segoe UI,sans-serif;margin:0;background:#f4f6f8;color:#1c2733}
 header{background:#123a5e;color:#fff;padding:14px 22px}
 header small{opacity:.75}
 main{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px 22px}
 .card{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
 .card h2{margin:.2rem 0 .8rem;font-size:16px}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th,td{text-align:left;padding:5px 6px;border-bottom:1px solid #eef1f4}
 .num{font-size:26px;font-weight:600}
 .muted{color:#6b7a89;font-size:12px}
 .err{background:#fdecec;border-left:4px solid #d64545;padding:8px 10px;border-radius:6px;font-size:13px}
 .ok{background:#eef8f0;border-left:4px solid #2e9e4f;padding:8px 10px;border-radius:6px;font-size:13px}
 input,button{font-size:14px;padding:8px 10px}
 input{width:calc(100% - 92px);border:1px solid #cfd8e0;border-radius:6px}
 button{background:#123a5e;color:#fff;border:0;border-radius:6px;cursor:pointer}
 #log{margin-top:12px;font-size:14px}
 .msg{padding:8px 10px;border-radius:6px;margin:6px 0;background:#f7f9fb}
 .src{font-size:11px;color:#6b7a89;margin-top:4px}
</style></head><body>
<header><b>Единая панель предприятия</b><br><small id="src">источник: проверяется…</small></header>
<main>
 <section class="card">
  <h2>Состояние предприятия</h2>
  <div id="health" class="muted">проверка связи…</div>
  <div style="display:flex;gap:24px;margin:14px 0">
   <div><div class="num" id="c-docs">—</div><div class="muted">документов реализации</div></div>
   <div><div class="num" id="c-cp">—</div><div class="muted">контрагентов</div></div>
   <div><div class="num" id="c-nom">—</div><div class="muted">позиций номенклатуры</div></div>
  </div>
  <table id="docs"><thead><tr><th>Номер</th><th>Дата</th><th>Контрагент</th></tr></thead><tbody></tbody></table>
  <p class="muted" id="items"></p>
  <p class="muted">Нажмите на строку — откроется карточка документа.</p>
  <div id="order" style="display:none;margin-top:10px">
   <h2 id="order-title"></h2>
   <div class="muted" id="order-head"></div>
   <table id="order-lines"><thead><tr><th>Позиция</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr></thead><tbody></tbody></table>
   <p class="muted" id="order-total"></p>
  </div>
 </section>
 <section class="card">
  <h2>Производство · SCADA / OPC UA</h2>
  <div id="prod-state" class="muted">проверка источника…</div>
  <table id="prod"><thead><tr><th>Параметр</th><th>Значение</th><th>Ед.</th><th>Статус</th></tr></thead><tbody></tbody></table>
</section>
 <section class="card">
  <h2>Чат</h2>
  <input id="q" placeholder="например: покажи последние документы">
  <button onclick="ask()">Спросить</button>
  <div id="log"></div>
 </section>
</main>
<script>
async function refresh(){
  const h=await (await fetch('/api/health')).json();
  const el=document.getElementById('health');
  if(h.status==='ok'){ el.className='ok';
    el.textContent='1С доступна · мост '+h.bridge+' · '+h.ts; }
  else { el.className='err';
    el.textContent='1С НЕДОСТУПНА: '+(h.error||h.status)+' · '+h.ts; }
  const p=await (await fetch('/api/panel')).json();
  document.getElementById('src').textContent='источник: '+p.source+' · получено '+p.ts;
  document.getElementById('c-docs').textContent=p.counts.documents ?? '—';
  document.getElementById('c-cp').textContent=p.counts.counterparties ?? '—';
  document.getElementById('c-nom').textContent=p.counts.nomenclature ?? '—';
  const tb=document.querySelector('#docs tbody'); tb.innerHTML='';
  (p.documents||[]).forEach(r=>{ const tr=document.createElement('tr');
    tr.style.cursor='pointer'; tr.title='открыть карточку';
    tr.onclick=()=>loadOrder(r[0]);
    r.forEach(c=>{const td=document.createElement('td'); td.textContent=c; tr.appendChild(td);});
    tb.appendChild(tr); });
  document.getElementById('items').textContent='Номенклатура: '+(p.items||[]).join(', ');
  const pr=await (await fetch('/api/production')).json();
  const ps=document.getElementById('prod-state');
  const tb2=document.querySelector('#prod tbody'); tb2.innerHTML='';
  if(pr.available){
    ps.className='ok';
    ps.textContent='источник: '+pr.source+' · '+pr.ts+' · режим: '+pr.mode;
    (pr.values||[]).forEach(v=>{ const tr=document.createElement('tr');
      [v.name, v.value, v.unit, v.alarm||v.quality].forEach(x=>{
        const td=document.createElement('td'); td.textContent=x; tr.appendChild(td); });
      tb2.appendChild(tr); });
  } else {
    ps.className='err';
    ps.textContent='производственных данных нет: '+(pr.error||pr.mode);
  }
  if(p.errors && p.errors.length){
    const box=document.createElement('div'); box.className='err';
    box.textContent='Часть данных не получена: '+p.errors.map(e=>e.query+': '+e.error).join('; ');
    el.parentElement.appendChild(box);
  }
}
async function loadOrder(num){
 const d=await (await fetch('/api/order?number='+encodeURIComponent(num))).json();
 document.getElementById('order').style.display='block';
 document.getElementById('order-title').textContent =
   d.error ? 'Карточка недоступна' : ('Документ № '+d.number);
 document.getElementById('order-head').textContent = d.error ? d.error :
   (d.source+' · '+d.ts+' · контрагент: '+d.counterparty+' · '+(d.posted?'проведён':'не проведён'));
 const tb=document.querySelector('#order-lines tbody'); tb.innerHTML='';
 (d.positions||[]).forEach(p=>{ const tr=document.createElement('tr');
   [p.item,p.qty,p.price,p.amount].forEach(v=>{const td=document.createElement('td'); td.textContent=v; tr.appendChild(td);});
   tb.appendChild(tr); });
 document.getElementById('order-total').textContent = d.error ? '' :
   ('Итого: '+d.total+' · позиций: '+(d.positions||[]).length);
}
async function ask(){
  const q=document.getElementById('q').value.trim(); if(!q) return;
  const log=document.getElementById('log');
  const m=document.createElement('div'); m.className='msg'; m.textContent=q;
  m.style.background='#e8f0f8'; log.prepend(m);
  const r=await (await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phrase:q})})).json();
  const a=document.createElement('div'); a.className='msg';
  a.textContent=r.answer;
  const s=document.createElement('div'); s.className='src'; s.textContent='источник: '+r.source+' · '+r.ts;
  a.appendChild(s); log.prepend(a);
}
refresh(); setInterval(refresh, 15000);
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')ask();});
</script></body></html>"""


def production():
    """Производственные данные: кэш 5 секунд, чтобы не дёргать OPC UA на каждый запрос."""
    now = time.time()
    if PROD_CACHE["data"] is not None and now - PROD_CACHE["ts"] < 5:
        return PROD_CACHE["data"]
    try:
        from source_mode import current
        data = current()
    except Exception as exc:                        # noqa: BLE001
        data = {"mode": "unavailable", "available": False,
                "error": f"адаптер не загрузился: {exc}"}
    PROD_CACHE["ts"] = now
    PROD_CACHE["data"] = data
    return data


def order(number):
    """Карточка документа: шапка + позиции. Номер — только цифры."""
    digits = "".join(ch for ch in str(number or "") if ch.isdigit())
    if not digits:
        return {"error": "номер документа должен содержать цифры", "ts": now_ts()}
    head, err = ask_1c(ORDER_HEADER.format(number=digits))
    if err:
        return {"error": err, "ts": now_ts(), "number": digits}
    rows = head.get("rows") or []
    if not rows:
        return {"error": f"документ {digits} не найден", "ts": now_ts(), "number": digits}
    lines, err2 = ask_1c(ORDER_LINES.format(number=digits))
    positions = []
    total = 0.0
    for r in (lines or {}).get("rows") or []:
        item, qty, price = r[0], float(r[1]), float(r[2])
        amount = qty * price
        total += amount
        positions.append({"item": item, "qty": qty, "price": price,
                          "amount": round(amount, 2)})
    return {
        "source": "1С:Предприятие (живой мост)",
        "ts": now_ts(),
        "number": rows[0][0],
        "date": rows[0][1],
        "counterparty": rows[0][2],
        "posted": bool(rows[0][3]),
        "positions": positions,
        "total": round(total, 2),
        "error": err2,
    }


class Handler(BaseHTTPRequestHandler):
    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/health":
            self._json(health())
            return
        if path == "/api/panel":
            self._json(panel())
            return
        if path == "/api/order":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self._json(order((qs.get("number") or [""])[0]))
            return
        if path == "/api/production":
            self._json(production())
            return
        self.send_error(404)

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


def main():
    global EXCHANGE
    ap = argparse.ArgumentParser()
    ap.add_argument("--exchange", default=str(Path(__file__).resolve().parent.parent / "exchange"))
    ap.add_argument("--port", type=int, default=8077)
    args = ap.parse_args()
    EXCHANGE = Path(args.exchange)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"панель: http://127.0.0.1:{args.port}  exchange={EXCHANGE}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
