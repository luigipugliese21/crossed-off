#!/usr/bin/env python3
"""crossed off. — tiny sync server (Python stdlib only).

Serves the app and keeps ONE shared copy of your notebook in data/state.json,
so your computer and your iPhone (over Tailscale) see the same lists.

  python3 server.py                         # serve on 0.0.0.0:8787
  python3 server.py --port 9000
  python3 server.py --seed crossed-off.json # start from a "save a copy" file

Then on the iPhone (Tailscale on):  http://<your-computer>:8787
"""
import argparse, json, os, socket, sys, tempfile, threading, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
STATIC = {"/": "index.html", "/index.html": "index.html", "/manifest.webmanifest": "manifest.webmanifest",
          "/icon-180.png": "icon-180.png", "/icon-512.png": "icon-512.png"}
lock = threading.Lock()


def valid(s):
    return isinstance(s, dict) and all(isinstance(s.get(k), list) for k in ("todos", "chores", "deadlines"))


def read_store():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_store(state, rev):
    os.makedirs(DATA_DIR, exist_ok=True)
    doc = {"rev": rev, "updated": int(time.time() * 1000), "state": state}
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)  # atomic: never leaves a half-written file
    return doc


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            return  # keep the console quiet during background syncs
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/state":
            with lock:
                doc = read_store()
            return self.send_json(200, doc or {"rev": 0, "state": None})
        name = STATIC.get(path)
        if not name:
            return self.send_error(404)
        full = os.path.join(ROOT, name)
        try:
            with open(full, "rb") as f:
                body = f.read()
        except FileNotFoundError:
            return self.send_error(404)
        ctype = {"html": "text/html; charset=utf-8", "png": "image/png",
                 "webmanifest": "application/manifest+json"}[name.rsplit(".", 1)[1]]
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        if self.path.split("?", 1)[0] != "/api/state":
            return self.send_error(404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 20 * 1024 * 1024:
                return self.send_json(413, {"error": "too large"})
            msg = json.loads(self.rfile.read(n))
            base, state, force = int(msg.get("base", -1)), msg.get("state"), bool(msg.get("force"))
        except (ValueError, TypeError, AttributeError):
            return self.send_json(400, {"error": "bad json"})
        if not valid(state):
            return self.send_json(400, {"error": "not a crossed-off notebook"})
        with lock:
            cur = read_store() or {"rev": 0, "state": None}
            if not force and base != cur["rev"]:
                # someone else (the other device) saved first — hand back theirs
                return self.send_json(409, cur)
            doc = write_store(state, cur["rev"] + 1)
        return self.send_json(200, {"rev": doc["rev"], "updated": doc["updated"]})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--seed", metavar="FILE", help='load a "save a copy" JSON file into the server')
    a = ap.parse_args()

    if a.seed:
        with open(a.seed, encoding="utf-8") as f:
            s = json.load(f)
        if not valid(s):
            sys.exit("That file isn't a crossed-off notebook.")
        cur = read_store() or {"rev": 0}
        write_store(s, cur["rev"] + 1)
        print(f"Loaded {a.seed} into {os.path.relpath(STATE_FILE, ROOT)}")

    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    host = socket.gethostname()
    print(f"crossed off. is open on port {a.port}")
    print(f"  this computer:      http://localhost:{a.port}")
    print(f"  iPhone (Tailscale): http://{host}:{a.port}   (or http://<tailscale-ip>:{a.port})")
    print("Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
