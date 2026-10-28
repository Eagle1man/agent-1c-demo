with open('C:\\Users\\diorl\\.cline\\data\\workspaces\\chat\\agent-1c-demo\\agent\\web_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '        AGENT_STATUS[agent_id] = "working"\n        time.sleep(0.3)\n        task_id = str(uuid.uuid4())[:8]\n        icon = next((a["avatar"] for a in AGENTS if a["id"] == agent_id), "🤖")\n        task = {"id": task_id, "subject": text[:50], "detail": f"Обработано агентом {agent_id}", "icon": icon, "status": "ok", "time": datetime.now().strftime("%H:%M:%S"), "agent": agent_id}\n        TASK_QUEUE.append(task)\n\n        # 1. Пробуем RAG-поиск в базе знаний 1С'

new = '        AGENT_STATUS[agent_id] = "working"\n        time.sleep(0.3)\n        task_id = str(uuid.uuid4())[:8]\n        icon = next((a["avatar"] for a in AGENTS if a["id"] == agent_id), "🤖")\n        task = {"id": task_id, "subject": text[:50], "detail": f"Обработано агентом {agent_id}", "icon": icon, "status": "ok", "time": datetime.now().strftime("%H:%M:%S"), "agent": agent_id}\n        TASK_QUEUE.append(task)\n\n        # --- отслеживание события ---\n        start_time = time.time()\n        conversation_id = task_id\n        user_raw = "web_user"\n        # ----------------------------\n\n        # 1. Пробуем RAG-поиск в базе знаний 1С'

if old in content:
    content = content.replace(old, new, 1)
    with open('C:\\Users\\diorl\\.cline\\data\\workspaces\\chat\\agent-1c-demo\\agent\\web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: replaced event tracking header')
else:
    print('FAIL: old text not found')
    idx = content.find('time.sleep(0.3)')
    if idx >= 0:
        print(repr(content[idx:idx+400]))