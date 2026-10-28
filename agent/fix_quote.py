# -*- coding: utf-8 -*-
path = "agent-1c-demo/agent/web_app.py"
src = open(path, "r", encoding="utf-8").read()
src = src.replace('"Монитор 27""', '"Монитор 27\\"')
open(path, "w", encoding="utf-8").write(src)
print("done")
