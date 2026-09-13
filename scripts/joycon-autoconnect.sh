#!/usr/bin/env bash
# Versucht wiederholt, bereits gekoppelte (bonded) Joy-Cons erneut per
# Bluetooth zu verbinden. Laeuft eine Weile nach dem Boot, damit man nicht
# jedes Mal manuell bluetoothctl bedienen muss - ein kurzer Tastendruck am
# Joy-Con (der ihn aus dem Schlaf weckt) reicht dann, der Pi greift sofort
# zu.
#
# Das Kombinieren zweier Joy-Cons zu einem virtuellen Controller (L+R
# gleichzeitig druecken) bleibt trotzdem ein manueller Schritt - das
# entscheidet joycond bei jeder Neuverbindung neu und laesst sich nicht
# automatisieren.
set -uo pipefail

DURATION_SECONDS="${1:-600}"
INTERVAL_SECONDS=5

echo "joycon-autoconnect: versuche ${DURATION_SECONDS}s lang, bekannte Joy-Cons zu verbinden..."
end=$((SECONDS + DURATION_SECONDS))
while [ "$SECONDS" -lt "$end" ]; do
  while read -r _ mac _; do
    [ -z "${mac:-}" ] && continue
    if ! bluetoothctl info "$mac" 2>/dev/null | grep -q "Connected: yes"; then
      bluetoothctl connect "$mac" >/dev/null 2>&1
    fi
  done < <(bluetoothctl devices Paired | grep -i "joy-con")
  sleep "$INTERVAL_SECONDS"
done
echo "joycon-autoconnect: Zeitfenster abgelaufen, beende mich."
