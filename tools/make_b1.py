# -*- coding: utf-8 -*-
"""Вариант b1: скелет seed2 + модуль моста (с директивами). Изоляция модуля."""
import re
import shutil
from pathlib import Path

PROJ = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo")
SRC = Path(r"C:\1c_bases\epf_seed2")
DST = Path(r"C:\1c_bases\epf_b1")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "SeedData" in t:
            f.write_text(t.replace("SeedData", "B1"), encoding="utf-8")
(DST / "SeedData.xml").rename(DST / "B1.xml")
(DST / "SeedData").rename(DST / "B1")

bsl = (PROJ / "1c" / "АгентМост.bsl").read_bytes().decode("utf-8-sig")
i_form = bsl.index("// === МОДУЛЬ ФОРМЫ ===")
form_code = bsl[i_form:].strip() + "\n"


def add_client(code):
    out = []
    for line in code.splitlines(keepends=True):
        if line.startswith(("Процедура ", "Функция ")):
            out.append("&НаКлиенте\n")
        out.append(line)
    return "".join(out)


mod = DST / "B1" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
mod.write_text(add_client(form_code), encoding="utf-8")
n = add_client(form_code).count("&НаКлиенте")
print("b1 ready, directives:", n)
