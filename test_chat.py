# -*- coding: utf-8 -*-
import urllib.request, json, time

BASE = "http://127.0.0.1:8080"

def chat(msg):
    req = urllib.request.Request(f"{BASE}/api/chat", data=json.dumps({"message": msg}).encode("utf-8"), headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req)
    return json.loads(r.read().decode("utf-8"))

tests = ["привет", "что умеет система?", "проверь связь"]

results = []
for t in tests:
    try:
        r = chat(t)
        results.append(f"Q: {t}")
        results.append(f"   TYPE: {r.get('type')}")
        results.append(f"   TITLE: {r.get('title')}")
        results.append(f"   TEXT: {r.get('text','')[:120]}")
        results.append(f"   AGENT: {r.get('agent')}")
        results.append("")
    except Exception as e:
        results.append(f"Q: {t}")
        results.append(f"   ERROR: {e}")
        results.append("")

out = "\n".join(results)
open("agent-1c-demo/test_results.txt", "w", encoding="utf-8").write(out)
print("Tests completed")
