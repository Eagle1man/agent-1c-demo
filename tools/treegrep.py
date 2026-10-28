# -*- coding: utf-8 -*-
import json, glob, os
files = glob.glob(os.path.expandvars(r"C:\Users\diorl\.local\share\opencode\tool-output\tool_*"))
files.sort(key=os.path.getmtime)
d = json.load(open(files[-1], encoding="utf-8"))
t = d if isinstance(d, list) else d.get("tree", d)
for x in t:
    p = x["path"]
    if "/epf/" in p and x["type"] == "blob":
        print(p)
