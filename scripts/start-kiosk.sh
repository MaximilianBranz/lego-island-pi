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
# unclutter ist X11-only - unter Wayland (labwc) ueberspringen, sonst
# schlaegt es fehlerlos fehl ("could not open display").
if [ "${XDG_SESSION_TYPE:-}" != "wayland" ] && [ -z "${WAYLAND_DISPLAY:-}" ] \
   && command -v unclutter >/dev/null; then
  unclutter -idle 0.5 -root &
fi

# Unter Wayland muss Chromium explizit dazu gebracht werden, den
# Wayland-Backend zu nutzen - sonst faellt es auf X11 zurueck und findet
# kein $DISPLAY (Absturz beim Start).
OZONE_ARGS=()
if [ -n "${WAYLAND_DISPLAY:-}" ]; then
  OZONE_ARGS=(--ozone-platform=wayland --enable-features=UseOzonePlatform)
fi

# WICHTIG: kein --incognito! island.pizza speichert Spielstaende lokal im
# Browser (IndexedDB/localStorage) - Inkognito wuerde die bei jedem
# Neustart des Kiosks (Reboot, Absturz, manueller Neustart) verwerfen.
# Stattdessen ein eigenes, dauerhaftes Profil, getrennt von einer evtl.
# normalen Chromium-Nutzung auf dem Pi.
PROFILE_DIR="$HOME/.config/lego-island-kiosk-profile"

exec "$CHROMIUM_BIN" \
  "${OZONE_ARGS[@]}" \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=TranslateUI \
  --autoplay-policy=no-user-gesture-required \
  --check-for-update-interval=31536000 \
  --overscroll-history-navigation=0 \
  --start-fullscreen \
  "$URL"
