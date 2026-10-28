# -*- coding: utf-8 -*-
"""Полная настройка 1С AI Ассистента — шаг 1: проверка и установка"""
import os, sys, subprocess
from pathlib import Path

DISK_D = Path("D:/1c_ai_data")
DISK_D.mkdir(parents=True, exist_ok=True)

def step(msg):
    print(f"\n{'='*50}\n{msg}\n{'='*50}")

def run(cmd, desc=""):
    print(f"  ▶ {desc or cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.stdout: print(r.stdout[-1500:])
    if r.stderr: print("ERR:", r.stderr[-800:])
    return r.returncode == 0

if __name__ == "__main__":
    step("Шаг 1: Среда")
    print(f"  Python: {sys.version}")
    print(f"  Диск D: {DISK_D.resolve()}")
    import shutil
    free = shutil.disk_usage("D:\\").free // (1024**3)
    total = shutil.disk_usage("D:\\").total // (1024**3)
    print(f"  Свободно: {free} ГБ из {total} ГБ")

    step("Шаг 2: Библиотеки")
    run("pip install datasets huggingface_hub sentence-transformers chromadb requests", "Установка пакетов")

    print("\n✅ Шаги 1-2 готовы. Запустите setup_part2.py для скачивания датасетов.")