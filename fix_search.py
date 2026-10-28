#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для исправления search.py"""
import os

PATH = r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\rag\search.py"

# Создаем исправленную версию файла целиком
FIXED_CODE = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RAG-поиск в базе знаний 1С (используется web_app.py)"""
from pathlib import Path

BASE = Path("D:/1c_ai_data")
CHROMA_DIR = BASE / "chroma_db"

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
except ImportError:
    SentenceTransformer = None
    chromadb = None

_model = _client = _collection = None

def _init():
    global _model, _client, _collection
    if _model is None and SentenceTransformer:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    if _client is None and chromadb and CHROMA_DIR.exists():
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            _collection = _client.get_collection("1c_knowledge")
        except Exception:
            _collection = None

def search(query, top_k=3):
    _init()
    if not _collection:
        return [{"text": "База знаний не построена. Запустите D:/1c_ai_data/setup_part3.py", "score": 0}]
    q_emb = _model.encode([query]).tolist()
    res = _collection.query(query_embeddings=q_emb, n_results=top_k,
                            include=["documents", "metadatas", "distances"])
    hits = []
    for i in range(len(res["documents"][0])):
        hits.append({"text": res["documents"][0][i],
                     "metadata": res["metadatas"][0][i],
                     "score": round(1 - res["distances"][0][i], 3)})
    return hits

def rag_answer(query):
    hits = search(query, top_k=3)
    if not hits:
        return "🤷 В базе знаний 1С не найдено подходящих ответов"
    print(f"✅ Найдено {len(hits)} документа в базе знаний")
    print(f"🏆 Лучшая релевантность: {hits[0]['score']:.2f}")
    ctx = "\\n\\n".join([f"---\\n{h['text'][:1000]}\\n(релевантность: {h['score']})" for h in hits])
    return f"""На основе базы знаний 1С (реальные обсуждения):

{ctx}"""

if __name__ == "__main__":
    print(rag_answer("как исправить синтаксическую ошибку в 1С"))
'''

with open(PATH, "w", encoding="utf-8") as f:
    f.write(FIXED_CODE)

print("✅ Файл search.py успешно перезаписан!")