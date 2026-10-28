#!/bin/zsh
# Baut eine Ad-hoc-IPA mit Xcode und laedt sie zu Fenfa hoch.
# Nutzung: ./release.sh <Scheme> <Version> <Build>
# Benoetigt: FENFA_URL, FENFA_TOKEN (Upload-Token), FENFA_VARIANT_ID in der Umgebung oder in ~/.fenfa.env
set -euo pipefail

[ -f "$HOME/.fenfa.env" ] && source "$HOME/.fenfa.env"
: "${FENFA_URL:?z.B. https://apps.deinname.duckdns.org}"
: "${FENFA_TOKEN:?API-Token aus Fenfa unter Settings}"
: "${FENFA_VARIANT_ID:?Variant-ID der App in Fenfa}"

SCHEME="${1:?Scheme}"
VERSION="${2:?Version, z.B. 1.0.0}"
BUILD="${3:?Build-Nummer, z.B. 1}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(mktemp -d)"

xcodebuild archive \
  -scheme "$SCHEME" \
  -destination 'generic/platform=iOS' \
  -archivePath "$OUT/app.xcarchive" \
  MARKETING_VERSION="$VERSION" CURRENT_PROJECT_VERSION="$BUILD" \
  -allowProvisioningUpdates

xcodebuild -exportArchive \
  -archivePath "$OUT/app.xcarchive" \
  -exportOptionsPlist "$HERE/ExportOptions.plist" \
  -exportPath "$OUT/export" \
  -allowProvisioningUpdates

IPA="$(ls "$OUT"/export/*.ipa | head -1)"

curl --fail -X POST "$FENFA_URL/upload" \
  -H "X-Auth-Token: $FENFA_TOKEN" \
  -F "variant_id=$FENFA_VARIANT_ID" \
  -F "app_file=@$IPA" \
  -F "version=$VERSION" \
  -F "build=$BUILD"

echo "Hochgeladen: $IPA"
