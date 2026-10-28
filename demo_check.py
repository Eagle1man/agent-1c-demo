# -*- coding: utf-8 -*-
"""Валидация демосценария на dist\\demo_agent_1c.exe (флаг --demo).

Детерминированный режим: ключевые слова → инструменты, без обращений к
модели — каждый промпт отрабатывает одинаково. Кормит подготовленные фазы
(включая двойное подтверждение: «нет» → отмена, «да» → создание),
сохраняет протокол в demo_out.txt.
Запуск: py -3 demo_check.py"""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXE = ROOT / "dist" / "demo_agent_1c.exe"
OUT = ROOT / "demo_out.txt"

PHRASES = [
    "проверь связь",                                  # 1 диагностика
    "остатки на складе",                              # 2 таблица (low)
    "задолженность контрагентов",                     # 3 таблица (low)
    "сколько заказов за неделю",                      # 4 таблица (low)
    "создай накладную на ООО Ромашка 10 шт Товар А",  # 5 эхо + «нет»
    "нет",
    "создай накладную на ООО Ромашка 10 шт Товар А",  # 6 эхо + «да» → РН-
    "да",
    "выход",
]

env = dict(os.environ, PYTHONIOENCODING="utf-8")
try:
    r = subprocess.run(
        [str(EXE), "--demo"],
        input=("\n".join(PHRASES) + "\n").encode("utf-8"),
        capture_output=True, env=env, timeout=300, cwd=str(EXE.parent))
    OUT.write_bytes(r.stdout + b"\n---STDERR---\n" + r.stderr)
    print(f"exit={r.returncode}, записано {OUT.name}, байт: {len(r.stdout)}")
except subprocess.TimeoutExpired:
    print("TIMEOUT 300s — смотрите demo_out.txt")
except FileNotFoundError:
    print(f"не найден exe: {EXE}")
