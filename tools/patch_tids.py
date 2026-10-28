# -*- coding: utf-8 -*-
"""Патч gen_cfg_v2: уникальные TypeId для всех GeneratedType."""
from pathlib import Path

TIDS = ["95c2ef3f-aa79-499d-9a4a-74ef4567fae0", "2a38f156-d8c3-4624-aced-df9108bb2716",
        "0b2adf99-81b4-406c-9640-2ecddd2641b4", "adfb401b-3f93-4b5d-b72e-10bf7b494f80",
        "4f0c8fb1-645a-4294-8332-8ec8df415384", "1c2e8be5-5a43-4150-a8a9-dde5c170303e",
        "55345caf-13a2-41c8-ac07-1dca38cd648b", "54463a95-bfcc-4b7f-9e14-fbe5a34019a0",
        "19c31f6f-4f23-4921-8a85-89e517028623", "97677835-6ea5-4e1c-86ff-6e1dcd734b6b",
        "7d144f12-4355-445e-9df5-a52a2da7b6c9", "e5176488-3434-459d-b071-2e47b7c35fb3",
        "a93da3c7-a886-4534-8bf2-6508b7356dfa", "e3a672c1-afa3-49aa-bacf-4008fb9caf47",
        "77873974-80d2-4605-9333-fbc1275ad711", "7cf02857-3e5c-4017-9dc4-cb292c6d440c",
        "a0d9c6b9-d6f5-43d1-a3af-5c1e4bb95491"]

p = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\tools\gen_cfg_v2.py")
s = p.read_text(encoding="utf-8")

new_fn = '''_TIDS = %s
_tid_i = [0]


def _tid():
    v = _TIDS[_tid_i[0] %% len(_TIDS)]
    _tid_i[0] += 1
    return v


ZERO = "00000000-0000-0000-0000-000000000000"
''' % (TIDS,)

old_zero = 'ZERO = "00000000-0000-0000-0000-000000000000"'
assert old_zero in s
s = s.replace(old_zero, new_fn)
s = s.replace('"<xr:TypeId>" + ZERO + "</xr:TypeId>"', '"<xr:TypeId>" + _tid() + "</xr:TypeId>"')
assert "_tid()" in s
p.write_text(s, encoding="utf-8")
print("unique tids in")
