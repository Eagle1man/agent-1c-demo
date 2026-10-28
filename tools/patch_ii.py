# -*- coding: utf-8 -*-
"""Патч InternalInfo: расставить разные кандидаты ClassId по контекстам."""
from pathlib import Path

p = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\tools\gen_cfg_v1.py")
s = p.read_text(encoding="utf-8")

C1 = "9cd510cd-abfc-11d4-9434-004095e12fc7"
C2 = "9fcd25a0-4822-11d4-9414-008048da11f9"
C3 = "e3687481-0a87-462c-a166-9f34594f9bba"
C4 = "9de14907-ec23-4a07-96f0-85521cb6b53b"
C5 = "51f2d5d8-ea4d-4064-8892-82951750031e"

old_ii = '''def ii(*short_ids):
    items = ""
    for sh in short_ids:
        items += ("<xr:ContainedObject><xr:ClassId>00000000-0000-0000-0000-000000000000</xr:ClassId>"
                  + "<xr:ObjectId>" + P + sh + "</xr:ObjectId></xr:ContainedObject>")
    return "<InternalInfo>" + items + "</InternalInfo>"'''

new_ii = '''CLASS_BY_CTX = {"catalog_attr": "C1", "ts_attr": "C2", "doc": "C3", "config": "C4", "self": "C5"}
CLASSES = {"C1": "C1V", "C2": "C2V", "C3": "C3V", "C4": "C4V", "C5": "C5V"}


def ii(ctx, *short_ids):
    cls = CLASSES[CLASS_BY_CTX[ctx]]
    items = ""
    for sh in short_ids:
        items += ("<xr:ContainedObject><xr:ClassId>" + cls + "</xr:ClassId>"
                  + "<xr:ObjectId>" + P + sh + "</xr:ObjectId></xr:ContainedObject>")
    return "<InternalInfo>" + items + "</InternalInfo>"'''

assert old_ii in s
s = s.replace(old_ii, new_ii)
s = s.replace('"C1V"', f'"{C1}"').replace('"C2V"', f'"{C2}"').replace('"C3V"',
            f'"{C3}"').replace('"C4V"', f'"{C4}"').replace('"C5V"', f'"{C5}"')

s = s.replace('ii("000000000002", "000000000003")', 'ii("catalog_attr", "000000000002", "000000000003")')
s = s.replace('+ ii() +', '+ ii("self", "000000000004") +')
s = s.replace('ii("000000000006", "000000000007")', 'ii("doc", "000000000006", "000000000007")')
s = s.replace('ii("000000000008", "000000000009", "000000000010")',
              'ii("ts_attr", "000000000008", "000000000009", "000000000010")')
s = s.replace('ii("000000000001", "000000000004", "000000000005")',
              'ii("config", "000000000001", "000000000004", "000000000005")')

p.write_text(s, encoding="utf-8")
print("patched")
