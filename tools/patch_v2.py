# -*- coding: utf-8 -*-
"""Замена SYS7 на verbatim-блок из выгрузки базы + чистка config-строки."""
import re
from pathlib import Path

p = Path(r"D:\agent-1c-demo\tools\gen_cfg_v2.py")
s = p.read_text(encoding="utf-8")

new_sys = ('\nimport re as _re\n'
           '_dump = Path(r"C:\\1c_bases\\empty_dump\\Configuration.xml").read_text(encoding="utf-8")\n'
           'SYS7 = _re.search("<InternalInfo>.*?</InternalInfo>", _dump, flags=_re.S).group(0)\n')


def _rep(m):
    return new_sys


s2, n = re.subn(r'\nSYS7 = """.*?"""\n', _rep, s, count=1, flags=re.S)
assert n == 1, "SYS7 not replaced"
s = s2

old_cfg = 'config = (DECL + NS + "\\n" + \'<Configuration uuid="\' + P + \'00000000cafe">\' if False else DECL + NS + "\\n"'
assert old_cfg in s, "config line not found"
s = s.replace(old_cfg, 'config = (DECL + NS + "\\n"')

p.write_text(s, encoding="utf-8")
print("gen v2 fixed")
