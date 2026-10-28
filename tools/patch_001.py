# -*- coding: utf-8 -*-
"""Патч генератора: Configuration -> InternalInfo первым с детьми (C4),
каталог 001 -> InternalInfo последним с записями (класс из argv),
остальное -> пустой последним."""
import sys
from pathlib import Path

cls = sys.argv[1]
P = "3b9b2a01-7c4e-4b1d-9f2a-"
kids = {"001": ["000000000002", "000000000003"]}


def entries(short_ids):
    out = ""
    for sh in short_ids:
        out += ("<xr:ContainedObject><xr:ClassId>" + cls + "</xr:ClassId>"
                + "<xr:ObjectId>" + P + sh + "</xr:ObjectId></xr:ContainedObject>")
    return out


p = Path(r"C:\1c_bases\cfg_src\Catalogs\3b9b2a01-7c4e-4b1d-9f2a-000000000001.xml")
x = p.read_text(encoding="utf-8")
x = x.replace("<InternalInfo/>", "<InternalInfo>" + entries(kids["001"]) + "</InternalInfo>")
p.write_text(x, encoding="utf-8")
print("001 patched with", cls)
