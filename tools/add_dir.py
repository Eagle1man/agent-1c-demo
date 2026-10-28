# -*- coding: utf-8 -*-
"""Добавить &НаКлиенте всем процедурам модуля seed."""
from pathlib import Path

p = Path(r"C:\1c_bases\epf_seed2\SeedData\Forms\Форма\Ext\Form\Module.bsl")
x = p.read_text(encoding="utf-8")
out = []
for line in x.splitlines(keepends=True):
    if line.startswith(("Процедура ", "Функция ")):
        out.append("&НаКлиенте\n")
    out.append(line)
p.write_text("".join(out), encoding="utf-8")
print("directives:", "".join(out).count("&НаКлиенте"))
