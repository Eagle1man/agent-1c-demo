# -*- coding: utf-8 -*-
"""Контроль: копия seed2, переименованная в M1. Если DefaultForm уцелеет — дело в содержимом M1."""
import shutil
from pathlib import Path

SRC = Path(r"C:\1c_bases\epf_seed2")
DST = Path(r"C:\1c_bases\epf_ctl")
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
            f.write_text(t.replace("SeedData", "M1ctl"), encoding="utf-8")
(DST / "SeedData.xml").rename(DST / "M1ctl.xml")
(DST / "SeedData").rename(DST / "M1ctl")
print("ctl ready")
