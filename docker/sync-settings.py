#!/usr/bin/env python3
"""Uebernimmt FENFA_PRIMARY_DOMAIN in die Fenfa-Einstellungen.

Fenfa legt die oeffentliche Adresse beim ersten Start fest in seiner Datenbank ab
(http://localhost:8000) und bevorzugt sie vor der Umgebungsvariable. Dieses Skript
setzt sie nach dem Start auf den gewuenschten Wert und laesst alles andere unveraendert.
"""
import json
import os
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000"
TOKEN = os.environ["FENFA_ADMIN_TOKEN"]
WANT = os.environ["FENFA_PRIMARY_DOMAIN"].rstrip("/")


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"X-Auth-Token": TOKEN, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


for _ in range(90):
    try:
        current = call("GET", "/admin/api/settings")["data"]
        break
    except Exception:
        time.sleep(1)
else:
    sys.exit("Fenfa ist nicht erreichbar, die oeffentliche Adresse wurde nicht gesetzt.")

if current.get("primary_domain") != WANT:
    call("PUT", "/admin/api/settings", {
        "primary_domain": WANT,
        "secondary_domains": current.get("secondary_domains") or [],
        "organization": current.get("organization") or "Fenfa Distribution",
    })
    print("Oeffentliche Adresse gesetzt: " + WANT, flush=True)
