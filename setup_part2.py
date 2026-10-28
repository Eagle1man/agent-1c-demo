# -*- coding: utf-8 -*-
"""Полная настройка 1С AI Ассистента — шаг 2: скачивание датасетов на D:\1c_ai_data\"""
import sys
from pathlib import Path

BASE = Path("D:/1c_ai_data")
BASE.mkdir(parents=True, exist_ok=True)

try:
    from huggingface_hub import snapshot_download
    from datasets import load_dataset
except ImportError:
    print("Сначала запустите setup_part1.py (установит библиотеки)")
    sys.exit(1)

DATASETS = {
    "arefaste/1C_Forums": BASE / "1c_forums",
    "PruhaNLP/1C-Ebench": BASE / "1c_ebench",
    "kavlab/Spider-1C": BASE / "spider1c",
}

for name, target in DATASETS.items():
    target.mkdir(parents=True, exist_ok=True)
    print(f"\n📥 {name} -> {target}")
    try:
        snapshot_download(repo_id=name, local_dir=str(target), local_dir_use_symlinks=False)
        print(f"   ✅ Готово")
    except Exception as e:
        print(f"   ⚠️  snapshot_download: {e}")
        try:
            ds = load_dataset(name, cache_dir=str(target))
            print(f"   ✅ Через load_dataset: {list(ds.keys())}")
        except Exception as e2:
            print(f"   ❌ Ошибка: {e2}")
            print(f"   Скачайте вручную: https://huggingface.co/datasets/{name}")

print("\n✅ Все датасеты обработаны. Запустите setup_part3.py для RAG-индекса.")