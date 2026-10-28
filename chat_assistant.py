#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple Console Chat Interface for 1C AI Assistant RAG."""

import sys
from pathlib import Path
import time

# Add project paths
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rag"))

from search import rag_answer


def print_slow(text, delay=0.02):
    """Print text with a typewriter effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def main():
    print("\n" + "=" * 60)
    print("🤖  1C ИИ АССИСТЕНТ — Консольный режим")
    print("=" * 60)
    print("📚 База знаний: 15 600 документов")
    print("🧠 Модель: all-MiniLM-L6-v2 (MiniLM)")
    print("=" * 60)
    print("\n💡 Подсказки:")
    print("  • Задавайте вопросы о 1С, программировании, ошибках")
    print("  • Введите 'exit' или 'quit' для выхода")
    print("  • Введите 'help' для подсказок")
    print("=" * 60 + "\n")

    while True:
        try:
            text = input("\n👤 Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 До свидания!")
            break

        if not text:
            continue

        # Commands
        if text.lower() in ("exit", "quit", "/exit", "q"):
            print("\n👋 До свидания!")
            break

        if text.lower() == "help":
            print("\n📋 Доступные команды:")
            print("  help  — эта справка")
            print("  exit  — выход из программы")
            print("  clear — очистить консоль")
            print("  вопросик — пример вопроса")
            continue

        if text.lower() == "clear":
            import os
            os.system('cls' if os.name == 'nt' else 'clear')
            continue

        if text.lower() == "вопросик":
            text = "Как исправить ошибку синтаксиса в 1С:Предприятие 8.3?"
            print(f"\n👤 Вы (пример): {text}")

        if not text:
            continue

        # Thinking animation
        print("\n🤖 ИИ: ", end="", flush=True)
        print_slow("Думаю...", delay=0.05)

        # Get answer from RAG
        try:
            response = rag_answer(text)
            if response:
                # Print the answer with formatting
                print("\n" + "─" * 60)
                print("📚  Ответ из базы знаний 1С:")
                print("─" * 60)
                # Print in wrapped lines
                lines = response.split('\n')
                for line in lines:
                    print("  " + line)
                print("─" * 60)
            else:
                print("❌ В базе знаний не найдено подходящих ответов.")
                print("💡 Попробуйте перефразировать вопрос или спросите про:")
                print("   • Синтаксические ошибки 1С")
                print("   • Подключение к базе данных")
                print("   • Создание форм и отчетов")
        except Exception as e:
            print(f"\n❌ Произошла ошибка: {e}")
            print("🔧 Попробуйте снова или проверьте подключение к базе данных.")


if __name__ == "__main__":
    main()