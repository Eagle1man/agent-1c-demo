# -*- coding: utf-8 -*-
"""Вариант m2: форма M1 (свободное поле) + модуль seed (без переменных)."""
import shutil
from pathlib import Path

SRC = Path(r"C:\1c_bases\epf_m1")
DST = Path(r"C:\1c_bases\epf_m2")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "M1" in t:
            f.write_text(t.replace("M1", "M2"), encoding="utf-8")
(DST / "M1.xml").rename(DST / "M2.xml")
(DST / "M1").rename(DST / "M2")
seed_mod = Path(r"C:\1c_bases\epf_seed2\SeedData\Forms\Форма\Ext\Form\Module.bsl")
dst_mod = DST / "M2" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
dst_mod.write_text(seed_mod.read_text(encoding="utf-8"), encoding="utf-8")
print("m2 ready")
