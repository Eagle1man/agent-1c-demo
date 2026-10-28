# -*- coding: utf-8 -*-
import re
from pathlib import Path

a = Path(r"C:\1c_bases\epf_seed2\SeedData\Forms\Форма\Ext\Form.xml").read_bytes().decode("utf-8-sig")
b = Path(r"C:\1c_bases\epf_m1\M1\Forms\Форма\Ext\Form.xml").read_bytes().decode("utf-8-sig")


def strip(s):
    return re.sub(r"<Events>.*?</Events>|<Attributes>.*?</Attributes>|<Commands>.*?</Commands>|<ChildObjects>.*?</ChildObjects>|<ChildItems>.*?</ChildItems>", "[...]", s, flags=re.S)


out = ["SEED head: " + a[:400].replace("\n", "\\n")]
out.append("M1 head: " + b[:400].replace("\n", "\\n"))
out.append("SEED skel: " + strip(a).replace("\n", "\\n"))
out.append("M1 skel: " + strip(b).replace("\n", "\\n"))
Path(r"C:\1c_bases\skelcmp.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote skelcmp.txt")
