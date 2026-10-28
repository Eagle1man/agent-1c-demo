# -*- coding: utf-8 -*-
path = "agent-1c-demo/agent/web_app.py"
src = open(path, "r", encoding="utf-8").read()

# Fix the confirmation response in do_POST
old_confirm = '''            answer = data.get("answer", "no")
            CHAT_HISTORY.append({"sender": "user", "text": f"Подтверждение: {answer}", "ts": datetime.now().isoformat()})
            resp = {"type": "result", "title": "Подтверждение", "text": f"Действие {answer} для агента {data.get('agent', 'система')}."}
            CHAT_HISTORY.append({"sender": "bot", **resp, "ts": datetime.now().isoformat()})
            self._send_json(resp)'''
new_confirm = '''            answer = data.get("answer", "no")
            agent_id = data.get("agent", "система")
            CHAT_HISTORY.append({"sender": "user", "text": f"Подтверждение: {answer}", "ts": datetime.now().isoformat()})
            if answer == "yes":
                resp = {"type": "result", "title": "Выполнено", "text": f"✅ Действие подтверждено и выполнено агентом {agent_id}.", "agent": agent_id}
            else:
                resp = {"type": "result", "title": "Отменено", "text": f"❌ Действие отменено.", "agent": agent_id}
            CHAT_HISTORY.append({"sender": "bot", **resp, "ts": datetime.now().isoformat()})
            self._send_json(resp)'''
src = src.replace(old_confirm, new_confirm)

open(path, "w", encoding="utf-8").write(src)
print("Updated confirmation handler")
