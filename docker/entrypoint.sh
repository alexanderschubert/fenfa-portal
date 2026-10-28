#!/bin/sh
# Startet nginx (Port 8080), Fenfa (8000) und das Portal (8081) in einem Container.
set -e

DATA=/data
CRED="$DATA/credentials.env"

mkdir -p "$DATA/portal-icons" /app/uploads /tmp/nginx
for dir in "$DATA" /app/uploads; do
  if [ "$(stat -c %u "$dir")" != "10001" ]; then
    chown -R 10001:10001 "$dir" 2>/dev/null || true
  fi
done
# Das Portal laeuft als appuser und muss hier schreiben koennen (auch wenn /data schon appuser gehoert).
chown -R 10001:10001 "$DATA/portal-icons"
touch "$CRED"
chmod 600 "$CRED"

saved() { sed -n "s/^$1=//p" "$CRED" | tail -n 1; }

# ensure NAME KIND: nimmt den Wert aus der Umgebung, sonst aus credentials.env,
# sonst wird er einmalig erzeugt und dort gespeichert.
NEW=""
ensure() {
  eval "val=\${$1:-}"
  [ -n "$val" ] || val="$(saved "$1")"
  if [ -z "$val" ]; then
    case "$2" in
      password) val="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-14)" ;;
      secret)   val="$(openssl rand -hex 32)" ;;
      *)        val="$(openssl rand -hex 16)" ;;
    esac
    echo "$1=$val" >> "$CRED"
    NEW="$NEW $1"
  fi
  export "$1=$val"
}

ensure FENFA_ADMIN_TOKEN token
ensure FENFA_UPLOAD_TOKEN token
ensure PORTAL_PASSWORD password
ensure SESSION_SECRET secret

DOMAIN_SET="${FENFA_PRIMARY_DOMAIN:-}"
if [ -z "${FENFA_PRIMARY_DOMAIN:-}" ]; then
  FENFA_PRIMARY_DOMAIN="http://localhost:8080"
  echo "HINWEIS: FENFA_PRIMARY_DOMAIN ist nicht gesetzt. Fuer die iOS-Installation wird eine oeffentliche https-Adresse gebraucht."
fi
export FENFA_PRIMARY_DOMAIN

if [ -n "$NEW" ]; then
  echo "=============================================================="
  echo " Zugangsdaten wurden erzeugt (gespeichert in /data/credentials.env)"
  echo "   Admin-Token (Anmeldung unter /admin): $FENFA_ADMIN_TOKEN"
  echo "   Upload-Token (fuer release.sh):       $FENFA_UPLOAD_TOKEN"
  echo "   Passwort der Startseite:               $PORTAL_PASSWORD"
  echo "=============================================================="
fi

export FENFA_INTERNAL_URL="http://127.0.0.1:8000"
export PORTAL_PORT=8081
export PORTAL_BIND=127.0.0.1
export ICON_DIR="$DATA/portal-icons"

pids=""
start() { "$@" & pids="$pids $!"; }
trap 'kill $pids 2>/dev/null; exit 0' TERM INT

start su-exec appuser /app/fenfa
start su-exec appuser python3 -u /app/portal/server.py
start nginx -g 'daemon off;'

# Oeffentliche Adresse in Fenfas Datenbank uebernehmen (laeuft einmalig im Hintergrund)
if [ -n "$DOMAIN_SET" ]; then
  su-exec appuser python3 -u /app/sync-settings.py &
fi

while :; do
  for p in $pids; do
    if ! kill -0 "$p" 2>/dev/null; then
      echo "Ein Prozess ($p) wurde beendet, stoppe den Container."
      kill $pids 2>/dev/null
      exit 1
    fi
  done
  sleep 2
done
