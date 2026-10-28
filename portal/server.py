#!/usr/bin/env python3
"""App-Uebersicht fuer Fenfa im Stil des App Store, mit Passwort-Login.

Liest Produkte ueber die Admin-API, baut daraus eine Seite und aktualisiert sie
alle REFRESH Sekunden. Umgebung:
  FENFA_ADMIN_TOKEN      Admin-Token von Fenfa (Pflicht)
  PORTAL_PORT/PORTAL_BIND  Port und Adresse des Webservers (Standard 8080 / 0.0.0.0)
  PORTAL_PASSWORD        Passwort fuer die Seite (Pflicht)
  SESSION_SECRET         geheimer Schluessel fuer das Login-Cookie (Pflicht)
  FENFA_INTERNAL_URL     Adresse von Fenfa im LAN, z.B. http://127.0.0.1:8000
  FENFA_PRIMARY_DOMAIN   oeffentliche Adresse, z.B. https://apps.example.com
  ICON_DIR               beschreibbarer Ordner fuer hochgeladene Icons (<slug>.png)
Icons laden sich ueber /portal/settings hoch, ohne eigenes Icon wird eines erzeugt.
"""
import hashlib
import hmac
import html
import json
import os
import threading
import time
import urllib.request
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote

FENFA = os.environ.get("FENFA_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
PUBLIC = os.environ.get("FENFA_PRIMARY_DOMAIN", "https://apps.example.com").rstrip("/")
TOKEN = os.environ.get("FENFA_ADMIN_TOKEN", "")
PASSWORD = os.environ.get("PORTAL_PASSWORD", "")
SECRET = os.environ.get("SESSION_SECRET", "").encode()
HERE = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.environ.get("ICON_DIR", os.path.join(HERE, "icons"))
ICON_MAX = 3 * 1024 * 1024
REFRESH = 300
PORT = int(os.environ.get("PORTAL_PORT", "8080"))
BIND = os.environ.get("PORTAL_BIND", "0.0.0.0")
SESSION_DAYS = 30
COOKIE = "portal_session"
MAX_FAILS, FAIL_WINDOW = 5, 600

PLATFORMS = {
    "ios": "iPhone & iPad",
    "macos": "Mac",
    "android": "Android",
    "windows": "Windows",
    "linux": "Linux",
}
DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]

CSS = """
:root{--bg:#f2f2f7;--card:#fff;--text:#000;--muted:#8a8a8e;--line:#e5e5ea;--blue:#007aff;--pill:#eeeef3}
@media (prefers-color-scheme:dark){:root{--bg:#000;--card:#1c1c1e;--text:#fff;--muted:#8e8e93;--line:#2c2c2e;--blue:#0a84ff;--pill:#2c2c2e}}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:var(--bg);color:var(--text);font:17px/1.35 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
main{max-width:680px;margin:0 auto;padding:max(28px,env(safe-area-inset-top)) 16px 56px}
.date{color:var(--muted);font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.02em;margin:0}
h1{font-size:34px;line-height:1.15;font-weight:700;letter-spacing:-.01em;margin:2px 0 22px}
.card{background:var(--card);border-radius:20px;padding:18px 18px 4px;margin-bottom:18px}
.head{display:flex;gap:16px;align-items:center;padding-bottom:14px}
.icon{width:72px;height:72px;border-radius:16px;flex:none;box-shadow:0 0 0 .5px rgba(0,0,0,.12)}
.head h2{font-size:20px;line-height:1.2;font-weight:600;margin:0}
.head h2 a{color:inherit;text-decoration:none}
.desc{color:var(--muted);font-size:15px;margin:3px 0 0}
.row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 0;border-top:.5px solid var(--line)}
.plat{font-size:16px;font-weight:500}
.meta{color:var(--muted);font-size:13px;margin-top:1px}
.btn{display:inline-block;background:var(--pill);color:var(--blue);text-decoration:none;text-transform:uppercase;font-weight:700;font-size:15px;letter-spacing:.01em;padding:7px 20px;border-radius:999px;white-space:nowrap}
.btn:active{opacity:.6}
.empty,.err{color:var(--muted);padding:12px 0;font-size:15px}
.foot{color:var(--muted);font-size:12px;text-align:center;margin-top:28px}
.foot form{display:inline}
.foot a{color:var(--blue);text-decoration:none}
.sub{color:var(--muted);margin:-14px 0 20px;font-size:15px}
.date a{color:var(--blue);text-decoration:none;text-transform:none;font-size:17px;font-weight:400}
.acts{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
label.btn{cursor:pointer}
button.btn{border:0;font:inherit;font-weight:700;font-size:15px;text-transform:uppercase;cursor:pointer}
.msg{color:var(--muted);font-size:13px;margin-top:6px;min-height:1.3em}
.foot button{background:none;border:0;color:var(--blue);font:inherit;padding:0;cursor:pointer}
.login{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.box{width:100%;max-width:340px;text-align:center}
.box .icon{width:88px;height:88px;border-radius:20px;margin:0 auto 18px;display:block}
.box h1{font-size:26px;margin:0 0 4px}
.box p{color:var(--muted);margin:0 0 22px;font-size:15px}
.box input{width:100%;font:inherit;padding:13px 16px;border-radius:12px;border:0;background:var(--card);color:var(--text);margin-bottom:12px;outline:2px solid transparent}
.box input:focus{outline-color:var(--blue)}
.box .go{width:100%;border:0;background:var(--blue);color:#fff;font:inherit;font-weight:600;padding:13px;border-radius:12px;cursor:pointer}
.box .bad{color:#ff3b30;font-size:14px;margin:0 0 12px}
"""


def api(path):
    req = urllib.request.Request(FENFA + path, headers={"X-Auth-Token": TOKEN})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)["data"]


def fetch():
    apps = []
    for item in api("/admin/api/products")["items"]:
        if not item.get("published"):
            continue
        detail = api("/admin/api/products/" + item["id"])
        apps.append({"product": detail["product"], "variants": detail.get("variants") or []})
    return apps


def latest(variant):
    releases = variant.get("releases") or []
    return max(releases, key=lambda r: r.get("created_at", "")) if releases else None


def install_url(variant, release):
    if variant.get("platform") == "ios":
        return "itms-services://?action=download-manifest&url=%s/ios/%s/manifest.plist" % (PUBLIC, release["id"])
    return "%s/d/%s" % (PUBLIC, release["id"])


def date_de(iso):
    y, m, d = iso[:10].split("-")
    return "%s.%s.%s" % (d, m, y)


def generated_icon(name):
    hue = int(hashlib.sha256(name.encode()).hexdigest()[:4], 16) % 360
    letter = html.escape((name.strip()[:1] or "?").upper())
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="hsl(%d,75%%,62%%)"/><stop offset="1" stop-color="hsl(%d,80%%,45%%)"/>'
        '</linearGradient></defs><rect width="100" height="100" fill="url(#g)"/>'
        '<text x="50" y="50" text-anchor="middle" dominant-baseline="central" fill="#fff" '
        'font-family="-apple-system,Helvetica,Arial,sans-serif" font-size="52" font-weight="600">%s</text></svg>'
        % (hue, (hue + 30) % 360, letter)
    ).encode()


def icon_path(slug):
    return os.path.join(ICON_DIR, os.path.basename(slug) + ".png")


def icon_version(slug):
    try:
        return int(os.path.getmtime(icon_path(slug)))
    except OSError:
        return 0


def page(title, body):
    return (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="apple-mobile-web-app-title" content="Meine Apps">'
        '<meta name="color-scheme" content="light dark">'
        '<link rel="icon" type="image/svg+xml" href="/portal/logo">'
        '<link rel="apple-touch-icon" href="/portal/logo.png">'
        "<title>%s</title><style>%s</style></head><body>%s</body></html>" % (html.escape(title), CSS, body)
    )


def render(apps, error=None):
    e = html.escape
    t = time.localtime()
    today = "%s, %d. %s" % (DAYS[t.tm_wday], t.tm_mday, MONTHS[t.tm_mon - 1])
    cards = []
    for app in apps:
        p = app["product"]
        rows = []
        for v in app["variants"]:
            if not v.get("published", True):
                continue
            rel = latest(v)
            if not rel:
                continue
            name = PLATFORMS.get(v.get("platform"), v.get("display_name") or v.get("platform", ""))
            version = "Version " + str(rel.get("version", "?"))
            if rel.get("build"):
                version += " (%s)" % rel["build"]
            label = "Installieren" if v.get("platform") == "ios" else "Laden"
            rows.append(
                '<div class="row"><div><div class="plat">%s</div><div class="meta">%s<br>%s</div></div>'
                '<a class="btn" href="%s">%s</a></div>'
                % (e(name), e(version), e(date_de(rel.get("created_at", "0000-00-00"))),
                   e(install_url(v, rel)), label)
            )
        body = "".join(rows) or '<div class="empty">Noch keine Version hochgeladen.</div>'
        desc = '<p class="desc">%s</p>' % e(p["description"]) if p.get("description") else ""
        cards.append(
            '<section class="card"><div class="head"><img class="icon" src="/portal/icon/%s?v=%d" alt="">'
            '<div><h2><a href="%s/products/%s">%s</a></h2>%s</div></div>%s</section>'
            % (e(p["slug"]), icon_version(p["slug"]), e(PUBLIC), e(p["slug"]), e(p["name"]), desc, body)
        )
    if error:
        cards.insert(0, '<div class="err">Fenfa ist gerade nicht erreichbar (%s). Zeige den letzten Stand.</div>' % e(error))
    if not apps and not error:
        cards.append('<div class="empty">Noch keine Apps veröffentlicht.</div>')
    return page(
        "Meine Apps",
        '<main><p class="date">%s</p><h1>Apps</h1>%s'
        '<div class="foot">Auf dem iPhone bitte in Safari öffnen · Aktualisiert %s · '
        '<a href="/portal/settings">Einstellungen</a> · '
        '<form method="post" action="/portal/logout"><button>Abmelden</button></form></div></main>'
        % (e(today), "".join(cards), e(time.strftime("%H:%M")))
    )


def login_page(error=""):
    bad = '<p class="bad">%s</p>' % html.escape(error) if error else ""
    return page(
        "Anmelden",
        '<div class="login"><form class="box" method="post" action="/portal/login">'
        '<img class="icon" src="/portal/logo" alt=""><h1>Meine Apps</h1><p>Bitte Passwort eingeben.</p>%s'
        '<input type="password" name="password" placeholder="Passwort" autocomplete="current-password" autofocus required>'
        '<button class="go" type="submit">Anmelden</button></form></div>' % bad,
    )


SETTINGS_JS = """
const H = {"X-Requested-With": "portal"};
const show = (slug) => { document.getElementById("img-" + slug).src = "/portal/icon/" + slug + "?v=" + Date.now(); };
document.querySelectorAll('input[type=file]').forEach((inp) => inp.addEventListener("change", async () => {
  const file = inp.files[0];
  if (!file) return;
  const slug = inp.dataset.slug, msg = document.getElementById("msg-" + slug);
  msg.textContent = "Wird hochgeladen \\u2026";
  try {
    const bmp = await createImageBitmap(file);
    const s = Math.min(bmp.width, bmp.height), c = document.createElement("canvas");
    c.width = c.height = 512;
    c.getContext("2d").drawImage(bmp, (bmp.width - s) / 2, (bmp.height - s) / 2, s, s, 0, 0, 512, 512);
    const blob = await new Promise((r) => c.toBlob(r, "image/png"));
    const res = await fetch("/portal/icon/" + encodeURIComponent(slug), {method: "POST", headers: H, body: blob});
    if (!res.ok) throw new Error("Fehler " + res.status);
    show(slug);
    msg.textContent = "Gespeichert.";
  } catch (err) {
    msg.textContent = "Das hat nicht geklappt: " + err.message;
  }
  inp.value = "";
}));
document.querySelectorAll("button.reset").forEach((btn) => btn.addEventListener("click", async () => {
  const slug = btn.dataset.slug, msg = document.getElementById("msg-" + slug);
  const res = await fetch("/portal/icon-reset/" + encodeURIComponent(slug), {method: "POST", headers: H});
  if (res.ok) { show(slug); msg.textContent = "Zur\\u00fcckgesetzt."; } else { msg.textContent = "Fehler " + res.status; }
}));
"""


def settings_page(apps):
    e = html.escape
    cards = []
    for app in apps:
        p = app["product"]
        slug = e(p["slug"])
        cards.append(
            '<section class="card"><div class="head"><img class="icon" id="img-%s" src="/portal/icon/%s?v=%d" alt="">'
            '<div><h2>%s</h2><div class="acts">'
            '<label class="btn">Icon wählen<input type="file" accept="image/*" data-slug="%s" hidden></label>'
            '<button class="btn reset" data-slug="%s">Zurücksetzen</button></div>'
            '<div class="msg" id="msg-%s"></div></div></div></section>'
            % (slug, slug, icon_version(p["slug"]), e(p["name"]), slug, slug, slug)
        )
    if not cards:
        cards.append('<div class="empty">Noch keine Apps vorhanden.</div>')
    return page(
        "Einstellungen",
        '<main><p class="date"><a href="/">‹ Apps</a></p><h1>Einstellungen</h1>'
        '<p class="sub">Icon pro App auswählen. Ein quadratisches Bild passt am besten, '
        "sonst wird es mittig zugeschnitten.</p>" + "".join(cards) + "</main><script>" + SETTINGS_JS + "</script>",
    )


def sign(expiry):
    return hmac.new(SECRET, str(expiry).encode(), hashlib.sha256).hexdigest()


def make_session():
    expiry = int(time.time()) + SESSION_DAYS * 86400
    return "%d.%s" % (expiry, sign(expiry))


def valid_session(value):
    try:
        expiry, mac = value.split(".", 1)
        return int(expiry) > time.time() and hmac.compare_digest(mac, sign(int(expiry)))
    except (ValueError, AttributeError):
        return False


def password_ok(candidate):
    a = hashlib.sha256(candidate.encode()).digest()
    b = hashlib.sha256(PASSWORD.encode()).digest()
    return hmac.compare_digest(a, b)


cache = {"apps": [], "html": render([])}
fails = {}
fails_lock = threading.Lock()


def refresh_now():
    cache["apps"] = fetch()
    cache["html"] = render(cache["apps"])
    cache["ts"] = time.time()


def refresh_loop():
    while True:
        wait = REFRESH
        try:
            refresh_now()
        except Exception as exc:
            print("Aktualisierung fehlgeschlagen:", exc, flush=True)
            cache["html"] = render(cache["apps"], error=type(exc).__name__)
            if not cache["apps"]:
                wait = 10
        time.sleep(wait)


class Handler(BaseHTTPRequestHandler):
    def client_ip(self):
        return self.headers.get("X-Real-IP") or self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.client_address[0]

    def secure(self):
        return self.headers.get("X-Forwarded-Proto", "") == "https"

    def authed(self):
        jar = SimpleCookie(self.headers.get("Cookie", ""))
        return COOKIE in jar and valid_session(jar[COOKIE].value)

    def send(self, code, body, kind="text/html; charset=utf-8", headers=()):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, where, headers=()):
        self.send(303, b"", headers=[("Location", where)] + list(headers))

    def cookie(self, value, max_age):
        flags = "Path=/; HttpOnly; SameSite=Lax; Max-Age=%d" % max_age
        if self.secure():
            flags += "; Secure"
        return ("Set-Cookie", "%s=%s; %s" % (COOKIE, value, flags))

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/healthz":
            return self.send(200, b"ok", "text/plain")
        if path == "/portal/login":
            return self.redirect("/") if self.authed() else self.send(200, login_page())
        if path in ("/portal/logo", "/portal/logo.png"):
            name, kind = ("logo.svg", "image/svg+xml") if path == "/portal/logo" else ("logo.png", "image/png")
            with open(os.path.join(HERE, name), "rb") as fh:
                return self.send(200, fh.read(), kind)
        if not self.authed():
            return self.redirect("/portal/login")
        if path in ("/", "/index.html"):
            if time.time() - cache.get("ts", 0) > 30:
                try:
                    refresh_now()
                except Exception:
                    pass
            return self.send(200, cache["html"])
        if path == "/portal/settings":
            return self.send(200, settings_page(cache["apps"]))
        if path.startswith("/portal/icon/"):
            slug = unquote(path[len("/portal/icon/"):])
            custom = icon_path(slug)
            if os.path.isfile(custom):
                with open(custom, "rb") as fh:
                    return self.send(200, fh.read(), "image/png")
            name = next((a["product"]["name"] for a in cache["apps"] if a["product"]["slug"] == slug), slug)
            return self.send(200, generated_icon(name), "image/svg+xml")
        self.send(404, b"not found", "text/plain")

    def change_icon(self, path):
        if not self.authed():
            return self.send(401, b"login required", "text/plain")
        if self.headers.get("X-Requested-With") != "portal":
            return self.send(403, b"forbidden", "text/plain")
        reset = path.startswith("/portal/icon-reset/")
        slug = unquote(path.rsplit("/", 1)[1])
        if slug not in {a["product"]["slug"] for a in cache["apps"]}:
            return self.send(404, b"unknown app", "text/plain")
        if reset:
            try:
                os.remove(icon_path(slug))
            except FileNotFoundError:
                pass
        else:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > ICON_MAX:
                return self.send(413, b"file too large", "text/plain")
            data = self.rfile.read(length)
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                return self.send(415, b"png required", "text/plain")
            os.makedirs(ICON_DIR, exist_ok=True)
            tmp = icon_path(slug) + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, icon_path(slug))
        cache["html"] = render(cache["apps"])
        self.send(200, b"ok", "text/plain")

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/portal/logout":
            return self.redirect("/portal/login", [self.cookie("", 0)])
        if path.startswith(("/portal/icon/", "/portal/icon-reset/")):
            return self.change_icon(path)
        if path != "/portal/login":
            return self.send(404, b"not found", "text/plain")
        ip = self.client_ip()
        now = time.time()
        with fails_lock:
            recent = [ts for ts in fails.get(ip, []) if now - ts < FAIL_WINDOW]
            fails[ip] = recent
            locked = len(recent) >= MAX_FAILS
        if locked:
            return self.send(429, login_page("Zu viele Versuche. Bitte in 10 Minuten erneut versuchen."))
        length = min(int(self.headers.get("Content-Length") or 0), 1024)
        form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
        if password_ok((form.get("password") or [""])[0]):
            return self.redirect("/", [self.cookie(make_session(), SESSION_DAYS * 86400)])
        with fails_lock:
            fails.setdefault(ip, []).append(now)
        time.sleep(1)
        self.send(401, login_page("Falsches Passwort."))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    if not (TOKEN and PASSWORD and SECRET):
        raise SystemExit("FENFA_ADMIN_TOKEN, PORTAL_PASSWORD und SESSION_SECRET müssen gesetzt sein")
    os.makedirs(ICON_DIR, exist_ok=True)
    threading.Thread(target=refresh_loop, daemon=True).start()
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
