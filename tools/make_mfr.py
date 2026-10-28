# -*- coding: utf-8 -*-
"""Вариант mfr: корень ctl (рабочий) + Form.xml из M1. Изоляция влияния тела формы."""
import shutil
from pathlib import Path

SRC_CTL = Path(r"C:\1c_bases\epf_ctl")
SRC_M1 = Path(r"C:\1c_bases\epf_m1")
DST = Path(r"C:\1c_bases\epf_mfr")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC_CTL, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "M1ctl" in t:
            f.write_text(t.replace("M1ctl", "Mfr"), encoding="utf-8")
(DST / "M1ctl.xml").rename(DST / "Mfr.xml")
(DST / "M1ctl").rename(DST / "Mfr")
# подменить тело формы на M1
src_body = SRC_M1 / "M1" / "Forms" / "Форма" / "Ext" / "Form.xml"
dst_body = DST / "Mfr" / "Forms" / "Форма" / "Ext" / "Form.xml"
dst_body.write_bytes(src_body.read_bytes())
print("mfr ready")
