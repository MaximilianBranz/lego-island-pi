#!/usr/bin/env bash
# Koppelt einen oder mehrere Joy-Cons per Bluetooth mit dem Pi.
#
# Auf dem Pi ausfuehren: bash scripts/pair-joycons.sh
set -euo pipefail

if ! command -v bluetoothctl >/dev/null; then
  echo "bluetoothctl fehlt. Zuerst scripts/install.sh ausfuehren."
  exit 1
fi

echo "== Joy-Con Bluetooth-Kopplung =="
echo
echo "An jedem Joy-Con, den du koppeln willst: die kleine ovale Sync-Taste"
echo "neben der Metallschiene ca. 3 Sekunden gedrueckt halten, bis die vier"
echo "Spieler-LEDs hin- und herlaufen (Kopplungsmodus)."
echo
read -r -p "Enter druecken, wenn die Joy-Cons im Kopplungsmodus sind... " _

echo "-- Suche 15 Sekunden nach Geraeten..."
bluetoothctl power on
bluetoothctl agent on
bluetoothctl default-agent
timeout 15 bluetoothctl scan on || true

mapfile -t DEVICES < <(bluetoothctl devices | grep -i "Joy-Con" || true)

if [ ${#DEVICES[@]} -eq 0 ]; then
  echo
  echo "Keine Joy-Cons gefunden. Sync-Taste erneut druecken und Script"
  echo "neu starten. Falls das wiederholt nicht klappt: 'bluetoothctl scan on'"
  echo "manuell laufen lassen und pruefen, ob ueberhaupt Geraete auftauchen."
  exit 1
fi

for line in "${DEVICES[@]}"; do
  MAC=$(awk '{print $2}' <<<"$line")
  NAME=$(cut -d' ' -f3- <<<"$line")
  echo
  echo "-- Koppel mit: $NAME ($MAC)"
  bluetoothctl pair "$MAC" || true
  bluetoothctl trust "$MAC" || true
  bluetoothctl connect "$MAC" || true
done

echo
echo "== Fertig =="
echo "Verbundene Geraete pruefen:  bluetoothctl devices Connected"
echo "Gamepad testen:              bash scripts/test-gamepad.sh"
