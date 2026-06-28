with open("rk3568_app/modules/dashboard.html", "rb") as f:
    d = f.read()

# Find the loadDecisionRules JS and update the display format
# Add event name after the rule name
old_format = b"(r.name || \"\xe8\xa7\x84\xe5\x88\x99\"+(i+1)) + '</b>: ' + (r.description"
new_format = b"(r.name || \"\xe8\xa7\x84\xe5\x88\x99\"+(i+1)) + ' [' + (r.event||\"\") + ']</b>: ' + (r.description"

d = d.replace(old_format, new_format)

d = d.replace(b"\r\n", b"\n")
with open("rk3568_app/modules/dashboard.html", "wb") as f:
    f.write(d)

# Verify
if new_format in d:
    print("OK: rule name format updated to include event")
else:
    print("FAIL: replacement not found")
    idx = d.find(b"r.name")
    if idx > 0:
        print("Context:", d[idx:idx+100])
