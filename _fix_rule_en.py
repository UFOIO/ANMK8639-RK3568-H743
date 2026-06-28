with open("rk3568_app/modules/dashboard.html", "rb") as f:
    d = f.read()

# Current format: name [event]: description
# New format: event: name - description
old = b"(r.name || \"\xe8\xa7\x84\xe5\x88\x99\"+(i+1)) + ' [' + (r.event||\"\") + ']</b>: ' + (r.description"
new = b"(r.event||\"\") + ': ' + (r.name||\"\xe8\xa7\x84\xe5\x88\x99\"+(i+1)) + '</b> - ' + (r.description"

d = d.replace(old, new)

d = d.replace(b"\r\n", b"\n")
with open("rk3568_app/modules/dashboard.html", "wb") as f:
    f.write(d)
print("OK" if new in d else "FAIL")
