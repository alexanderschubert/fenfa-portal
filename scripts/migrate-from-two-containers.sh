#!/bin/bash
# Zieht eine Installation aus zwei Containern (Fenfa + Portal, siehe start-fenfa.sh / start-portal.sh)
# auf das kombinierte Image fenfa-portal um. Auf dem Unraid als root ausfuehren:
#   bash /mnt/user/appdata/fenfa-portal/scripts/migrate-from-two-containers.sh
#
# Was passiert (in dieser Reihenfolge):
#   1. Das neue Image wird gebaut (die alten Container laufen dabei weiter).
#   2. Die Fenfa-Datenbank wird gesichert.
#   3. Admin-/Upload-Token, Passwort und Icons werden uebernommen.
#   4. Ein vorausgefuelltes Unraid-Template wird angelegt.
#   5. Die alten Container werden gestoppt und in *-old umbenannt (nicht geloescht).
# Danach installierst du den neuen Container ueber das Template (Docker, Add Container).
set -euo pipefail

OLD_DIR="${OLD_DIR:-/mnt/user/appdata/fenfa}"           # Daten der alten Installation
SRC_DIR="${SRC_DIR:-/mnt/user/appdata/fenfa-portal}"    # dieses Projekt
TEMPLATES="${TEMPLATES:-/boot/config/plugins/dockerMan/templates-user}"
OLD_FENFA="${OLD_FENFA:-fenfa}"
OLD_PORTAL="${OLD_PORTAL:-fenfa-portal}"

say() { printf '\n== %s\n' "$*"; }
die() { printf 'FEHLER: %s\n' "$*" >&2; exit 1; }

[ -d "$OLD_DIR/data" ] || die "$OLD_DIR/data nicht gefunden"
[ -f "$OLD_DIR/.env" ] || die "$OLD_DIR/.env nicht gefunden (Admin- und Upload-Token)"
[ -f "$SRC_DIR/Dockerfile" ] || die "$SRC_DIR/Dockerfile nicht gefunden"

DOMAIN="${FENFA_PRIMARY_DOMAIN:-}"
if [ -z "$DOMAIN" ]; then
  DOMAIN="$(docker inspect "$OLD_PORTAL" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null \
    | sed -n 's/^FENFA_PRIMARY_DOMAIN=//p' | head -n 1)"
fi
[ -n "$DOMAIN" ] || die "Oeffentliche Adresse unbekannt. Starte mit: FENFA_PRIMARY_DOMAIN=https://apps.example.com bash $0"

say "1/5 Image bauen (dauert beim ersten Mal einige Minuten)"
docker build -t fenfa-portal:local "$SRC_DIR"

say "2/5 Datenbank sichern"
BACKUP="$OLD_DIR/backup-data-$(date +%F-%H%M)"
cp -a "$OLD_DIR/data" "$BACKUP"
echo "Sicherung: $BACKUP"

say "3/5 Zugangsdaten und Icons uebernehmen"
CRED="$OLD_DIR/data/credentials.env"
{
  grep -E '^(FENFA_ADMIN_TOKEN|FENFA_UPLOAD_TOKEN)=' "$OLD_DIR/.env" || true
  if [ -f "$OLD_DIR/portal.env" ]; then
    grep -E '^(PORTAL_PASSWORD|SESSION_SECRET)=' "$OLD_DIR/portal.env" || true
  fi
} > "$CRED"
chmod 600 "$CRED"
echo "Gespeichert in $CRED ($(wc -l < "$CRED" | tr -d ' ') Werte)"
if [ -d "$OLD_DIR/portal-icons" ]; then
  mkdir -p "$OLD_DIR/data/portal-icons"
  cp -a "$OLD_DIR/portal-icons/." "$OLD_DIR/data/portal-icons/"
  chown -R 10001:10001 "$OLD_DIR/data/portal-icons" || echo "WARNUNG: chown fehlgeschlagen"
  echo "Icons kopiert"
fi

say "4/5 Template anlegen"
mkdir -p "$TEMPLATES"
OUT="$TEMPLATES/my-fenfa-portal.xml"
sed \
  -e "s|/mnt/user/appdata/fenfa-portal/data|$OLD_DIR/data|g" \
  -e "s|/mnt/user/appdata/fenfa-portal/uploads|$OLD_DIR/uploads|g" \
  -e "/Name=\"Oeffentliche URL\"/ s|/>\$|>$DOMAIN</Config>|" \
  "$SRC_DIR/unraid/fenfa-portal-local.xml" > "$OUT"
echo "Template: $OUT"

say "5/5 Alte Container stoppen"
for c in "$OLD_FENFA" "$OLD_PORTAL"; do
  if docker inspect "$c" >/dev/null 2>&1; then
    docker update --restart=no "$c" >/dev/null
    docker stop "$c" >/dev/null
    docker rename "$c" "$c-old"
    echo "$c gestoppt und in $c-old umbenannt"
  else
    echo "$c nicht gefunden, uebersprungen"
  fi
done

cat <<EOF

Fertig. Weiter in der Unraid-Oberflaeche:
  1. Docker, Add Container, Template "my-fenfa-portal" waehlen.
     Pfade und Adresse ($DOMAIN) sind schon eingetragen. Token-Felder leer lassen,
     sie werden aus $CRED gelesen. Apply.
  2. Im Nginx Proxy Manager beim Proxy Host im Tab Advanced alles ausser
       client_max_body_size 1g;
     entfernen (die zwei location-Zeilen mit Port 7012 werden nicht mehr gebraucht).
     Der Proxy zeigt weiter auf Port 7011.
  3. Pruefen: Startseite, /admin, ein Install-Button.

Zurueck zum alten Stand, falls etwas nicht stimmt:
  docker rm -f fenfa-portal
  docker rename $OLD_FENFA-old $OLD_FENFA && docker rename $OLD_PORTAL-old $OLD_PORTAL
  docker update --restart=unless-stopped $OLD_FENFA $OLD_PORTAL
  docker start $OLD_FENFA $OLD_PORTAL
EOF
