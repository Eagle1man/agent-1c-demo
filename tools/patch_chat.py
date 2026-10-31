# -*- coding: utf-8 -*-
"""Патч chat_service.py: явные слова-подсказки до вызова Qwen."""
from pathlib import Path

P = Path(r"D:\agent-1c-demo\agent\chat_service.py")
s = P.read_text(encoding="utf-8-sig")
if "_route_keywords" in s:
    print("уже пропатчено")
    raise SystemExit(0)

anchor = (
    '    def _route(self, phrase):\n'
    '        """(action, params), источник: правила демо или Qwen."""\n'
    '        route = agent_mod.demo_route(phrase, self.profile)\n'
    '        if route:\n'
    '            return route, "правила"\n'
    '        q = qwen_route(phrase)\n'
)
assert anchor in s, "не найден якорь _route"

new = (
    '    # Явные слова-подсказки: демо не должно зависеть от слабой модели.\n'
    '    KEYWORDS = (("связ", "связь"), ("пинг", "связь"),\n'
    '                ("остат", "остатки"), ("склад", "остатки"), ("продаж", "остатки"),\n'
    '                ("задолж", "долг"), ("долг", "долг"), ("взаиморасч", "долг"),\n'
    '                ("заказ", "док"), ("документ", "док"), ("реализац", "док"),\n'
    '                ("контрагент", "контр"), ("реквизит", "контр"), ("инн", "контр"))\n'
    '\n'
    '    def _route_keywords(self, phrase):\n'
    '        """Детерминированные фразы — работают даже без модели."""\n'
    '        t = phrase.lower()\n'
    '        for word, kind in self.KEYWORDS:\n'
    '            if word in t:\n'
    '                if kind == "связь":\n'
    '                    return "проверка_связи", {}\n'
    '                if kind == "остатки":\n'
    '                    return "запрос_1с", {"query": agent_mod.STOCK_Q}\n'
    '                if kind == "долг":\n'
    '                    return "запрос_1с", {"query": agent_mod.DEBT_Q}\n'
    '                if kind == "док":\n'
    '                    return "запрос_1с", {"query": agent_mod.ORDERS_Q}\n'
    '                if kind == "контр":\n'
    '                    return "запрос_1с", {"query": agent_mod.PARTY_Q}\n'
    '        return None\n'
    '\n'
    '    def _route(self, phrase):\n'
    '        """(action, params), источник: правила демо или Qwen."""\n'
    '        route = agent_mod.demo_route(phrase, self.profile)\n'
    '        if route is not None:\n'
    '            return route, "правила"\n'
    '        route = self._route_keywords(phrase)\n'
    '        if route is not None:\n'
    '            return route, "правила"\n'
    '        q = qwen_route(phrase)\n'
)

s = s.replace(anchor, new, 1)
P.write_text(s, encoding="utf-8")
print("патч применён; байт:", len(s.encode("utf-8")))
