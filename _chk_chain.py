d = open("rk3568_app/modules/web_ui.py", "rb").read()
keywords = [b'if path == "/"', b'elif path == "/api/health"', b'elif path == "/api/events"', b'elif path == "/api/decision"']
for kw in keywords:
    idx = d.find(kw)
    if idx > 0:
        print("OK pos=%d: %s" % (idx, d[idx:idx+60]))
    else:
        print("MISSING: %s" % kw)
