# -*- coding: utf-8 -*-
"""Полная настройка 1С AI Ассистента — шаг 3: построение RAG-индекса"""
import json, sys
from pathlib import Path

BASE = Path("D:/1c_ai_data")
CHROMA_DIR = BASE / "chroma_db"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
except ImportError:
    print("Сначала запустите setup_part1.py")
    sys.exit(1)

def load_docs():
    docs = []
    forums_dir = BASE / "1c_forums"
    if not forums_dir.exists():
        print(f"⚠️  Не найдено: {forums_dir}")
        return docs
    count = 0
    for f in forums_dir.rglob("*.jsonl"):
        print(f"   Читаю: {f.name}")
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line: continue
                try:
                    rec = json.loads(line)
                    prompt = rec.get("prompt", "") or rec.get("question", "")
                    solution = rec.get("solution", "") or rec.get("answer", "")
                    think = rec.get("think_process", "")
                    if prompt:
                        text = f"ВОПРОС: {prompt}\n"
                        if think: text += f"ЛОГИКА: {think}\n"
                        if solution: text += f"РЕШЕНИЕ: {solution}"
                        docs.append({"id": f"forum_{count}", "text": text,
                                    "metadata": {"source": "1C_Forums", "prompt": prompt[:200]}})
                        count += 1
                except: continue
    print(f"   Всего документов: {count}")
    return docs

def build():
    print("🔄 Загружаю модель эмбеддингов...")
    model = SentenceTransformer("intembed/multilingual-e5-base")
    print("📂 Загружаю документы...")
    docs = load_docs()
    if not docs:
        print("❌ Нет документов. Сначала setup_part2.py")
        return
    texts = [d["text"] for d in docs]
    print("🧠 Создаю эмбеддинги...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    print("💾 Сохраняю в ChromaDB...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection("1c_knowledge")
    collection.add(documents=[d["text"] for d in docs],
                   embeddings=embeddings.tolist(),
                   metadatas=[d["metadata"] for d in docs],
                   ids=[d["id"] for d in docs])
    print(f"✅ Индекс готов: {collection.count()} документов")
    print(f"📁 {CHROMA_DIR.resolve()}")

if __name__ == "__main__":
    build()