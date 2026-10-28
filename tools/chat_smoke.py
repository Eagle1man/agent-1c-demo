# -*- coding: utf-8 -*-
"""Дым-тест службы диалога: типовые фразы из окна 1С (эмулятор 1С)."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from chat_service import ChatService

EXCH = r"C:\1c_agent\exchange"
PHRASES = [
    "проверка связи",
    "покажи остатки на складе",
    "покажи задолженность контрагентов",
    "создай накладную на ООО Ромашка 5 шт по 200",
    "да",
]

svc = ChatService(EXCH, use_mock=True)
try:
    for phrase in PHRASES:
        req = {"id": str(uuid.uuid4()), "phrase": phrase, "profile": "бухгалтер"}
        out = svc.process(req)
        print("=" * 66)
        print("ФРАЗА:", phrase)
        print("СТАТУС:", out.get("status"), "| вид:", out.get("kind"),
              "| ждёт подтверждения:", out.get("pending"))
        print(out.get("answer"))
finally:
    svc.stop()
