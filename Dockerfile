# Fenfa (Verteil-Server) und das App-Portal in einem Image.
# Fenfa wird aus dem Quellcode von https://github.com/openprx/fenfa gebaut (MIT-Lizenz).
# Fester Stand von Fenfa (Commit oder Tag). v0.1.2 hat die Admin-Oberflaeche noch nicht, daher der Commit vom 2026-04-07.
ARG FENFA_REF=e0fbb666d779274329091677e4d6218b15c6d81c

FROM node:20-alpine AS web
ARG FENFA_REF
RUN apk add --no-cache git
WORKDIR /src
RUN git init -q . \
    && git remote add origin https://github.com/openprx/fenfa.git \
    && git fetch -q --depth 1 origin "${FENFA_REF}" \
    && git checkout -q FETCH_HEAD
# Deutsche Uebersetzung (siehe overlay/): ergaenzt die Sprachdateien von Fenfa
COPY overlay/ /overlay/
RUN cp -r /overlay/web/. web/ \
    && test "$(grep -c "'zh' ? '更新说明' : 'Changelog'" web/front/src/main.ts)" = 1 \
    && sed -i "s/'zh' ? '更新说明' : 'Changelog'/'zh' ? '更新说明' : getLanguage() === 'de' ? 'Änderungen' : 'Changelog'/" web/front/src/main.ts
# Projektlogo in der Admin-Oberflaeche (Anmeldung, Seitenmenue)
RUN node /overlay/patch-admin.mjs
RUN cd web/front && npm install && npm run build
RUN cd web/admin && npm install && npm run build

FROM golang:1.25-alpine AS server
ARG FENFA_REF
RUN apk add --no-cache build-base sqlite-dev
ENV CGO_ENABLED=1
WORKDIR /src
COPY --from=web /src .
# Deutsche Texte im UDID-Profil, das auf dem iPhone angezeigt wird
RUN f=internal/server/handlers/udid.go \
    && test "$(grep -c ' - Device Registration"' $f)" = 1 \
    && test "$(grep -c 'Register your device to install: ' $f)" = 2 \
    && test "$(grep -c 'Install this profile to register your device for app installation. Your' $f)" = 1 \
    && sed -i \
        -e 's/ - Device Registration"/ - Geräteregistrierung"/' \
        -e 's/Register your device to install: /Gerät registrieren, um zu installieren: /' \
        -e 's/"Install this profile to register your device for app installation\. Your device information will be collected for authorization purposes\."/"Installiere dieses Profil, um dein Gerät für die App-Installation zu registrieren. Deine Geräteinformationen werden nur zur Autorisierung erfasst."/' \
        $f
# Seiten-Icon, Titel und Sprache der HTML-Vorlagen
RUN for f in internal/web/templates/admin.html internal/web/templates/app.html; do \
      ( test "$(grep -c '<html lang="zh-CN">' $f)" = 1 \
        && test "$(grep -c '<meta charset="utf-8" />' $f)" = 1 \
        && sed -i \
          -e 's|<html lang="zh-CN">|<html lang="de">|' \
          -e 's|<meta charset="utf-8" />|<meta charset="utf-8" /><link rel="icon" type="image/svg+xml" href="/portal/logo" /><link rel="apple-touch-icon" href="/portal/logo.png" />|' \
          $f ) || exit 1; \
    done \
    && test "$(grep -c '"Title": "Modern distribution"' internal/server/router.go)" = 1 \
    && sed -i 's|"Title": "Modern distribution"|"Title": "App-Verteilung"|' internal/server/router.go
RUN go build -ldflags="-s -w -X main.version=${FENFA_REF}" -o /out/fenfa ./cmd/server

FROM alpine:3.22
RUN apk add --no-cache ca-certificates sqlite-libs tzdata su-exec nginx python3 openssl \
    && adduser -D -H -u 10001 appuser
WORKDIR /app
COPY --from=server /out/fenfa /app/fenfa
COPY --from=web /src/LICENSE /licenses/fenfa-LICENSE
COPY portal/ /app/portal/
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/sync-settings.py /app/sync-settings.py
RUN chmod 755 /entrypoint.sh \
    && chmod 644 /app/sync-settings.py \
    && chmod -R a+rX /app/portal \
    && chmod 644 /etc/nginx/nginx.conf
ENV FENFA_DATA_DIR=/data \
    FENFA_PORT=8000
VOLUME ["/data", "/app/uploads"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
ENTRYPOINT ["/entrypoint.sh"]
