#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RAG-ассистент для 1С — интеграция поиска знаний"""

import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, 'rag'))
sys.path.insert(0, os.path.join(_BASE, 'agent'))

try:
    from search import rag_answer, search as rag_search
    _RAG_AVAILABLE = True
except Exception as e:
    print(f"RAG не доступен: {e}")
    _RAG_AVAILABLE = False

try:
    from bridge import Bridge, BridgeTimeout
    _BRIDGE_AVAILABLE = True
except Exception as e:
    print(f"Bridge не доступен: {e}")
    _BRIDGE_AVAILABLE = False
def get_rag_answer(query):
    if not _RAG_AVAILABLE: return 'База знаний недоступна.'
    result = rag_answer(query)
    if result: return result
    return 'В базе знаний 1С нет подходящих ответов.'

def search_knowledge(query, top_k=5):
    if not _RAG_AVAILABLE: return []
    return rag_search(query, top_k=top_k)
