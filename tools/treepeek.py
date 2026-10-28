# -*- coding: utf-8 -*-
import json, collections, glob, os
files = glob.glob(os.path.expandvars(r"C:\Users\diorl\.local\share\opencode\tool-output\tool_*"))
d = json.load(open(files[-1], encoding="utf-8"))
t = d if isinstance(d, list) else d.get("tree", d)
for prefix in ("content", "tools", "plugins", "adapters", "openspec"):
    subs = collections.Counter(
        x["path"][len(prefix) + 1:].split("/")[0]
        for x in t if x["path"].startswith(prefix + "/") and "/" in x["path"][len(prefix) + 1:])
    print("==", prefix)
    for k, v in subs.most_common(30):
        print("  ", v, k)
# skills everywhere
print("== skills/rules hits")
for x in t:
    p = x["path"].lower()
    if "skill" in p or x["path"].endswith("SKILL.md"):
        print("  ", x["path"])
