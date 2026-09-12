#!/usr/bin/env bash
# Prueft, ob joycond die gekoppelten Joy-Cons als Gamepad(s) bereitstellt,
# und laesst Tasten/Sticks live testen.
#
# Auf dem Pi ausfuehren: bash scripts/test-gamepad.sh
set -euo pipefail

echo "== Gefundene Joystick-Geraete =="
shopt -s nullglob
JS_DEVICES=(/dev/input/js*)
shopt -u nullglob

if [ ${#JS_DEVICES[@]} -eq 0 ]; then
  echo "Keine /dev/input/js* Geraete gefunden."
  echo "- Sind die Joy-Cons verbunden? bluetoothctl devices Connected"
  echo "- Laeuft joycond?              systemctl status joycond"
  exit 1
fi

for js in "${JS_DEVICES[@]}"; do
  NAME=$(udevadm info -q property -n "$js" 2>/dev/null | grep '^NAME=' | cut -d= -f2- || echo "unbekannt")
  echo "$js  ->  $NAME"
done

echo
FIRST_JS="${JS_DEVICES[0]}"
echo "-- Starte jstest fuer $FIRST_JS (Sticks bewegen / Tasten druecken,"
echo "   Strg+C zum Beenden). Bei zwei gekoppelten Joy-Cons sollte hier"
echo "   'Nintendo Switch Combined Joy-Cons' auftauchen."
echo
jstest "$FIRST_JS"
