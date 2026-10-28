# -*- coding: utf-8 -*-
"""Убрать из .bsl объявление Перем Фраза (конфликт с реквизитом формы)."""
from pathlib import Path

P = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\1c\АгентМост.bsl")
t = P.read_text(encoding="utf-8-sig")
bad_crlf = "&НаКлиенте\r\nПерем Фраза;\r\n"
bad_lf = "&НаКлиенте\nПерем Фраза;\n"
n = 0
for bad in (bad_crlf, bad_lf):
    if bad in t:
        t = t.replace(bad, "", 1)
        n += 1
print("удалено объявлений:", n)
t = t.replace("\r\n", "\n").replace("\n", "\r\n")
P.write_bytes(b"\xef\xbb\xbf" + t.encode("utf-8"))
print("осталось 'Перем Фраза':", "Перем Фраза" in t, "| байт:", P.stat().st_size)
