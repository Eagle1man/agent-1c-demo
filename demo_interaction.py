# -*- coding: utf-8 -*-
# Demo script: показывает взаимодействие агентов с 1С через файловый мост
import json, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "agent"))
from bridge import Bridge
from mock_bridge import Mock1C

exchange = Path(__file__).resolve().parent / "exchange_demo"
exchange.mkdir(exist_ok=True)

# Запускаем mock 1С
mock = Mock1C(exchange).start()
bridge = Bridge(exchange, user="демо-пользователь")

print("=" * 60)
print("ДЕМО: Взаимодействие агентов с 1С через файловый мост")
print("=" * 60)
print(f"Exchange path: {exchange}")
print()

# 1. Проверка связи
print("1. Проверка связи с 1С...")
resp = bridge.send("проверка_связи", {}, timeout=5)
print(f"   Ответ: {json.dumps(resp['result'], ensure_ascii=False)}")
print()

# 2. Запрос остатков
print("2. Запрос остатков на складе...")
resp = bridge.send("запрос_1с", {"query": "ВЫБРАТЬ Номенклатура, Остаток ИЗ РегистрНакопления.ОстаткиТоваров"}, timeout=5)
print(f"   Колонки: {resp['result']['columns']}")
for row in resp['result']['rows']:
    print(f"   - {row}")
print()

# 3. Запрос задолженности
print("3. Запрос задолженности контрагентов...")
resp = bridge.send("запрос_1с", {"query": "ВЫБРАТЬ Контрагент, Задолженность ИЗ РегистрНакопления.Взаиморасчеты"}, timeout=5)
print(f"   Колонки: {resp['result']['columns']}")
for row in resp['result']['rows']:
    print(f"   - {row}")
print()

# 4. Создание документа (двухэтапное подтверждение)
print("4. Создание документа реализации (двухэтапное)...")
resp = bridge.send("создать_документ", {
    "doc_type": "РеализацияТоваровУслуг",
    "counterparty": "ООО Ромашка",
    "positions": [{"item": "Товар А", "qty": 5, "price": 150}],
}, timeout=5)
print(f"   Этап 1 (без подтверждения): статус = {resp['status']}")
print(f"   Ответ: {json.dumps(resp, ensure_ascii=False)[:200]}")
print()

print("   Подтверждаем создание документа...")
resp = bridge.send("создать_документ", {
    "doc_type": "РеализацияТоваровУслуг",
    "counterparty": "ООО Ромашка",
    "positions": [{"item": "Товар А", "qty": 5, "price": 150}],
}, confirmed_by=bridge.confirmed_by("Администратор"), timeout=5)
print(f"   Этап 2 (с подтверждением): статус = {resp['status']}")
print(f"   Ответ: {json.dumps(resp['result'], ensure_ascii=False)}")
print()

# 5. Журнал
print("5. Журнал действий:")
bridge.journal("демо", "low", "тест", "ok", "Демо-запуск")
journal = (exchange / "journal.jsonl").read_text(encoding="utf-8")
print(journal.strip())

mock.stop()
print()
print("=" * 60)
print("ДЕМО ЗАВЕРШЕНО")
print("=" * 60)
print()
print("Как работает связь:")
print("1. Агент пишет JSON-файл в exchange/commands/{id}.json")
print("2. 1С (или Mock1C) читает файл, обрабатывает, пишет ответ в exchange/responses/{id}.json")
print("3. Агент ждёт ответ (polling каждые 0.2 сек)")
print("4. После получения ответа команда архивируется в exchange/archive/")
print()
print("Для реальной 1С:")
print("- Откройте базу 1С")
print("- Запустите обработку «АгентМост» (кнопка «Запустить мост»)")
print("- Укажите путь к exchange в config.json и в обработке 1С")
print("- Агент будет отправлять команды, 1С будет выполнять их и отвечать")
