import re
path = "agent-1c-demo/agent/web_app.py"
src = open(path, "r", encoding="utf-8").read()
lines = src.split("\n")
lines[29] = '        "goods": ["Ноутбук ASUS", "Монитор 27\\"", "Клавиатура механическая"],'
src = "\n".join(lines)
open(path, "w", encoding="utf-8").write(src)
print("done")
print(repr(lines[29]))
