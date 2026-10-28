# -*- coding: utf-8 -*-
import os
path = os.path.join(os.path.dirname(__file__), "web_app.py")
src = open(path, "r", encoding="utf-8").read()

# 1. Add Ollama constants after VALIDATION_RESULT line
old_const = 'VALIDATION_RESULT = {"avg_time_reduction": 66.7, "avg_error_reduction": 30.0, "avg_cost_reduction": 60.0}'
new_const = old_const + '\nOLLAMA_URL = "http://localhost:11434/api/generate"\nOLLAMA_MODEL = "qwen2.5:1.5b"\n\n\ndef ollama_call(prompt, system=""):\n    """Call local Ollama model and return response text."""\n    import urllib.request, json\n    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}\n    if system:\n        payload["system"] = system\n    data = json.dumps(payload).encode("utf-8")\n    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})\n    try:\n        with urllib.request.urlopen(req, timeout=60) as resp:\n            result = json.loads(resp.read().decode("utf-8"))\n            return result.get("response", "Нет ответа от модели")\n    except Exception as e:\n        return f"Ошибка Ollama: {e}"'
src = src.replace(old_const, new_const)

# 2. Add enterprise demo data after AGENTS list (before AGENT_STATUS)
old_agents_end = ']\n\nAGENT_STATUS'
new_agents_end = ''']

# Демо-данные предприятий
ENTERPRISES = {
    "ООО Альфа": {
        "inn": "7701234567", "type": "Покупатель",
        "goods": ["Ноутбук ASUS", "Монитор 27\"", "Клавиатура механическая"],
        "balance": 150000.00, "debt": 45000.00,
    },
    "ООО Бета": {
        "inn": "7702345678", "type": "Поставщик",
        "goods": ["Бумага А4", "Картриджи", "Тонер"],
        "balance": 80000.00, "debt": 0.00,
    },
    "ИП Гамма": {
        "inn": "7703456789", "type": "Покупатель",
        "goods": ["Принтер HP", "Сканер", "МФУ"],
        "balance": 200000.00, "debt": 120000.00,
    },
    "ООО Дельта": {
        "inn": "7704567890", "type": "Поставщик",
        "goods": ["Кабель витая пара", "Розетки", "Выключатели"],
        "balance": 60000.00, "debt": 15000.00,
    },
}

AGENT_STATUS'''
src = src.replace(old_agents_end, new_agents_end, 1)

# 3. Modify _process_message to use Ollama for general queries
old_else = '''        else:
            result = {"type": "result", "title": "Запрос принят", "text": "🤖 Запрос обработан в системе мультиагентов.", "agent": agent_id}'''
new_else = '''        else:
            # Use Ollama for intelligent response
            system_prompt = f"Ты агент {agent_id} в мультиагентной системе АгентМост 2.0. Отвечай кратко и по делу на русском языке. Ты работаешь с 1С Предприятие."
            ollama_resp = ollama_call(text, system=system_prompt)
            result = {"type": "result", "title": "Ответ агента", "text": f"🤖 {ollama_resp}", "agent": agent_id}'''
src = src.replace(old_else, new_else)

open(path, "w", encoding="utf-8").write(src)
print("web_app.py updated with Ollama integration")
