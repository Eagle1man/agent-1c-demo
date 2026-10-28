# -*- coding: utf-8 -*-
"""
Готовый скрипт установки библиотек.
Запустите: python install_libraries.py
"""
import subprocess, sys
from pathlib import Path

print("=" * 60)
print("1С AI Ассистент: Установка библиотек")
print("=" * 60)

libs = ["datasets", "huggingface_hub", "sentence-transformers", "chromadb", "requests"]

for lib in libs:
    print(f"\nУстанавливаю {lib}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", lib],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        print(f"  ✅ {lib} установлен")
    else:
        print(f"  ⚠️  {lib} (попытка continued)")
        # Пробуем установить с --user
        result2 = subprocess.run(
            [sys.executable, "-m", "pip", "install", lib, "--user"],
            capture_output=True, text=True, timeout=120
        )
        if result2.returncode == 0:
            print(f"  ✅ {lib} установлен с --user")
        else:
            print(f"  ❌ {lib}: {result2.stderr[-200:]}")

# Проверяем
print("\n" + "=" * 60)
print("Проверяю импорты...")
try:
    import datasets, sentence_transformers, chromadb, requests
    print("  ✅ Все библиотеки загружены успешно!")
except Exception as e:
    print(f"  ❌ Ошибка импорта: {e}")
    print("   Попробуйте перезапустить PowerShell/CMD после установки")

print("=" * 60)