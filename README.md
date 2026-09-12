# LEGO Island Pi Kiosk 🍕🎮

Spaßprojekt: Raspberry Pi am Fernseher (HDMI), der im Kiosk-Modus
[island.pizza](https://island.pizza) (die Browser-Portierung von LEGO Island,
Projekt [isledecomp/isle.pizza](https://github.com/isledecomp/isle.pizza))
startet – gesteuert mit einem oder zwei Nintendo-Switch-Joy-Cons.

## Wie die Steuerung funktioniert

- island.pizza unterstützt **Gamepads direkt über die Browser-Gamepad-API**
  (Tastatur/Maus, Gamepad und Touch werden alle nativ unterstützt). Es ist
  also **kein** Tasten-Remapping nötig, wenn Chromium den Controller als
  Gamepad erkennt.
- Zwei Joy-Cons werden unter Linux über
  [joycond](https://github.com/DanielOgorchock/joycond) zu **einem**
  virtuellen Controller ("Nintendo Switch Combined Joy-Cons")
  zusammengeführt. Das ist reine Software – das mechanische Zusammenstecken
  im Comfort/Charging Grip ist nur fürs Halten/Laden und hat mit der
  Kopplung nichts zu tun. Ein einzelner Joy-Con funktioniert auch alleine.
- Der Kernel-Treiber dafür heißt `hid_nintendo` (seit Kernel 5.16 in Linux
  enthalten, aktuelles Raspberry Pi OS bringt ihn mit).

## Hardware-Checkliste

- Raspberry Pi mit Bluetooth (3B+/4/5 intern, sonst BT-USB-Dongle)
- HDMI-Kabel zum Fernseher
- 1–2 Nintendo Switch Joy-Cons
- Raspberry Pi OS mit Desktop (Bookworm oder neuer empfohlen)

## Ablauf

1. [`scripts/install.sh`](scripts/install.sh) auf dem Pi ausführen –
   installiert Chromium, Bluetooth-Tools und joycond.
2. [`scripts/pair-joycons.sh`](scripts/pair-joycons.sh) ausführen, um die
   Joy-Cons per Bluetooth zu koppeln.
3. [`scripts/test-gamepad.sh`](scripts/test-gamepad.sh) ausführen, um zu
   prüfen, ob joycond die Joy-Cons zu einem Controller kombiniert hat.
4. Kiosk-Autostart einrichten, siehe
   [`autostart/README.md`](autostart/README.md) – Chromium startet dann
   beim Boot automatisch im Vollbild auf island.pizza.
5. Falls der Browser die Buttons falsch erkennt: siehe
   [`controller-profiles/README.md`](controller-profiles/README.md) für den
   Fallback-Plan.

## Status

🚧 Gerade im Aufbau. Als Nächstes: Skripte auf dem Pi testen (Bluetooth-
Kopplung und Kiosk-Autostart hängen vom konkreten Raspberry Pi OS ab –
Bullseye/LXDE vs. Bookworm/labwc unterscheiden sich beim Autostart).
