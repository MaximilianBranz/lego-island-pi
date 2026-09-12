#!/usr/bin/env bash
# Startet Chromium im Kiosk-Modus (Vollbild, ohne Bedienelemente) auf
# island.pizza. Wird von den Autostart-Mechanismen in autostart/README.md
# aufgerufen - kann aber auch manuell zum Testen laufen gelassen werden.
set -euo pipefail

URL="https://island.pizza"

CHROMIUM_BIN="chromium-browser"
if ! command -v "$CHROMIUM_BIN" >/dev/null; then
  CHROMIUM_BIN="chromium"
fi

# Mauszeiger nach kurzer Inaktivitaet ausblenden (fuer TV-Betrieb).
if command -v unclutter >/dev/null; then
  unclutter -idle 0.5 -root &
fi

exec "$CHROMIUM_BIN" \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=TranslateUI \
  --autoplay-policy=no-user-gesture-required \
  --check-for-update-interval=31536000 \
  --overscroll-history-navigation=0 \
  --start-fullscreen \
  --incognito \
  "$URL"
