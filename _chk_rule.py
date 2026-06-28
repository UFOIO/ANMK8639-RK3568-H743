d = open("rk3568_app/modules/dashboard.html", "rb").read()
import re
# Find the rule rendering line
m = re.search(rb"event.*name.*description", d)
if m:
    print(m.group()[:150])
else:
    # Search for "event" near "r.name"
    idx = d.find(b"r.event")
    if idx > 0:
        print(d[idx:idx+120])
