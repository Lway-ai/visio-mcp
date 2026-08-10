import win32com.client, pythoncom

pythoncom.CoInitialize()
try:
    app = win32com.client.GetActiveObject("Visio.Application")
except Exception:
    print("no running Visio")
    raise SystemExit
closed = []
for d in list(app.Documents):
    n = d.Name
    if "visio_mcp_tmp" in n:
        try:
            d.Close()
            closed.append(n)
        except Exception as e:
            print("fail", n, e)
print("closed leftover tabs:", closed)
pythoncom.CoUninitialize()
