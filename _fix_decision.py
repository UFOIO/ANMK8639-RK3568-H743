with open("rk3568_app/modules/dashboard.html", "rb") as f:
    d = f.read()

# Fix JS: r.desc -> r.description, r.active -> r.enabled
d = d.replace(b"r.desc ", b"r.description ")
d = d.replace(b"r.active ?", b"r.enabled ?")

d = d.replace(b"\r\n", b"\n")
with open("rk3568_app/modules/dashboard.html", "wb") as f:
    f.write(d)

# Verify
for tag in [b"r.desc", b"r.active", b"r.description", b"r.enabled"]:
    print("found" if tag in d else "MISSING", ":", tag.decode())
