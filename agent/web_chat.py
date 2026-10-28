#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Веб-интерфейс RAG-ассистента 1С на Flask"""

import os
import sys

# Добавляем пути для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rag'))

from flask import Flask, request, jsonify, render_template_string
from search import rag_answer

app = Flask(__name__)

# Популярные вопросы для автодополнения
SUGGESTIONS = [
    "Как исправить синтаксическую ошибку в 1С?",
    "Как создать накладную в 1С:Предприятие?",
    "Остатки товара на складе — как посчитать?",
    "Как подключиться к базе данных 1С?",
    "Как очистить кэш 1С?",
    "Как восстановить убитую конфигурацию?",
    "Как настроить пользователей и права?",
    "Как выгрузить данные в Excel из 1С?",
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>RAG-ассистент 1С</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .chat-box { height: 400px; border: 1px solid #ccc; padding: 10px; overflow-y: auto; margin-bottom: 10px; }
        .message { margin: 10px 0; padding: 8px; border-radius: 5px; }
        .user { background-color: #e3f2fd; }
        .bot { background-color: #f5f5f5; }
        input[type="text"] { width: 80%; padding: 8px; }
        button { padding: 8px 15px; }
        .suggestions { margin: 10px 0; }
        .suggestions button { margin: 5px; }
    </style>
</head>
<body>
    <h1>🤖 RAG-ассистент 1С</h1>
    
    <div class="suggestions">
        <strong>Подсказки:</strong><br>
        {% for s in suggestions %}
        <button onclick="askQuestion('{{ s }}')">{{ s }}</button><br>
        {% endfor %}
    </div>
    
    <div class="chat-box" id="chatBox"></div>
    
    <input type="text" id="questionInput" placeholder="Введите ваш вопрос..." onkeypress="handleKeyPress(event)">
    <button onclick="askQuestion(document.getElementById('questionInput').value)">Отправить</button>

    <script>
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                askQuestion(document.getElementById('questionInput').value);
            }
        }
        function addMessage(text, isUser) {
            const chatBox = document.getElementById('chatBox');
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : 'bot');
            div.innerHTML = '<strong>' + (isUser ? '👤 Вы' : '🤖 Ассистент') + ':</strong><br>' + text;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        function askQuestion(question) {
            if (!question.trim()) return;
            addMessage(question, true);
            document.getElementById('questionInput').value = '';
            
            fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question })
            })
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    addMessage('⚠ ' + data.error, false);
                } else {
                    addMessage(data.answer, false);
                }
            })
            .catch(e => addMessage('⚠ Ошибка: ' + e, false));
        }
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, suggestions=SUGGESTIONS)

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        question = data.get("question", "").strip()
        
        if not question:
            return jsonify({"error": "Введите вопрос!"})

        print(f"📥 Вопрос: {question}")
        result = rag_answer(question)
        
        if result:
            return jsonify({"answer": result})
        else:
            return jsonify({"answer": "🤷 Извините, не могу ответить на этот вопрос."})
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    print("Запуск веб-интерфейса: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)