# LEGO Island Pi Kiosk 🍕🎮

Spaßprojekt: Raspberry Pi am Fernseher (HDMI), der im Kiosk-Modus
[island.pizza](https://island.pizza) (die Browser-Portierung von LEGO Island,
Projekt [isledecomp/isle.pizza](https://github.com/isledecomp/isle.pizza))
startet – gesteuert mit zwei zu einem Controller kombinierten
Nintendo-Switch-Joy-Cons.

**Status: läuft komplett.** Kiosk-Autostart, Controller-Kombinieren,
Steuerung (Pfeiltasten + Maus) und Ton über HDMI sind auf einem Raspberry
Pi 5 (Debian 13/trixie, labwc/Wayland) getestet und funktionieren.

## Wie die Steuerung funktioniert

- Zwei Joy-Cons werden unter Linux über
  [joycond](https://github.com/DanielOgorchock/joycond) zu **einem**
  virtuellen Controller ("Nintendo Switch Combined Joy-Cons")
  zusammengeführt. Das ist reine Software – das mechanische Zusammenstecken
  im Comfort/Charging Grip ist nur fürs Halten/Laden und hat mit der
  Kopplung nichts zu tun. Ein einzelner Joy-Con funktioniert auch alleine.
- Der Kernel-Treiber dafür heißt `hid_nintendo` (seit Kernel 5.16 in Linux
  enthalten, aktuelles Raspberry Pi OS bringt ihn mit).
- **island.pizza unterstützt zwar offiziell die Browser-Gamepad-API, aber
  Chromium erkennt joycond's virtuellen Controller nicht als "standard"
  Gamepad** (eigene, nicht offizielle Produkt-ID 057e:2008) – das Spiel
  ignoriert ihn dadurch stillschweigend. Die Lösung:
  [`scripts/joycon-to-keyboard.py`](scripts/joycon-to-keyboard.py) liest
  die Controller-Rohdaten direkt per `evdev` und erzeugt per `uinput` eine
  virtuelle Tastatur + Maus:
  - Linker Stick links/rechts + D-Pad → Pfeiltasten (Spielsteuerung, das
    Original-LEGO-Island wird mit Pfeiltasten gesteuert)
  - Rechter Stick vor/zurück → Pfeiltasten hoch/runter
  - Rechter Stick (beide Achsen) → zusätzlich Mauszeiger (das
    Modus-Auswahlmenü von island.pizza ist reine Maus-UI)
  - A → Enter + Linksklick, B → Escape, X → Leertaste, Y → Strg
  - Achtung: `hid_nintendo` benennt Tasten nach physischer Position
    (Xbox-Konvention), nicht nach Nintendo-Aufdruck – bei Nintendo sitzt
    A rechts, B unten (siehe Kommentare im Skript).

## Hardware-Checkliste

- Raspberry Pi mit Bluetooth (3B+/4/5 intern, sonst BT-USB-Dongle)
- HDMI-Kabel zum Fernseher
- 2 Nintendo Switch Joy-Cons
- Raspberry Pi OS mit Desktop (Bookworm/trixie mit labwc, getestet)

## Ablauf (Ersteinrichtung)

1. [`scripts/install.sh`](scripts/install.sh) auf dem Pi ausführen –
   installiert Chromium, Bluetooth-Tools, `joycond`, den
   Tastatur/Maus-Übersetzer und den Autoconnect-Dienst (siehe unten), und
   trägt den `JustWorksRepairing`-Bluetooth-Fix ein.
2. [`scripts/pair-joycons.sh`](scripts/pair-joycons.sh) ausführen, um die
   Joy-Cons initial per Bluetooth zu koppeln.
3. Am linken **und** rechten Joy-Con je eine Schultertaste (L bzw. R)
   **gleichzeitig** drücken – das kombiniert beide zu einem virtuellen
   Controller (`joycond`-Eigenheit, siehe unten).
4. [`scripts/test-gamepad.sh`](scripts/test-gamepad.sh) ausführen, um zu
   prüfen, ob der kombinierte Controller da ist.
5. Kiosk-Autostart einrichten, siehe
   [`autostart/README.md`](autostart/README.md) – Chromium startet dann
   beim Boot automatisch im Vollbild auf island.pizza.
6. Audio-Ausgabe ist per [`config/asoundrc-hdmi`](config/asoundrc-hdmi)
   fest auf HDMI gepinnt (relevant, falls neben diesem Projekt noch andere
   Audio-Hardware am Pi hängt).

## Nach jedem Neustart/Stromausfall

Das ist die einzige wiederkehrende manuelle Handarbeit, die sich nicht
wegautomatisieren lässt:

- **Bluetooth-Wiederverbindung**: läuft normalerweise automatisch über den
  [`joycon-autoconnect`](scripts/joycon-autoconnect.sh)-Dienst (versucht
  10 Minuten lang alle 5s, bekannte Joy-Cons zu verbinden) – meist reicht
  ein kurzer Tastendruck an eingeschlafenen Joy-Cons, damit sie erkannt
  werden. Falls das mal nicht klappt (Fehler
  `br-connection-create-socket`/`InProgress`): alte Bindung entfernen und
  mit `scripts/pair-joycons.sh` neu koppeln. Der `JustWorksRepairing`-Fix
  in `/etc/bluetooth/main.conf` (von `install.sh` gesetzt) behebt die
  Ursache dafür in den allermeisten Fällen.
- **Kombinieren zu einem Controller**: `joycond` merkt sich die Gruppierung
  nicht über eine Trennung hinweg – nach jeder Neuverbindung müssen L und R
  nochmal gleichzeitig gedrückt werden, damit "Nintendo Switch Combined
  Joy-Cons" wieder entsteht. Das lässt sich technisch nicht automatisieren.

## Bekannte Stolpersteine (bereits gelöst, hier dokumentiert)

- **Chromium crasht im Kiosk unter labwc**: `--ozone-platform=wayland`
  fehlte, Chromium fiel auf X11 zurück und fand kein `$DISPLAY`. Fix ist in
  [`scripts/start-kiosk.sh`](scripts/start-kiosk.sh) drin.
- **DevTools sind auf dem Pi-Chromium-Paket standardmäßig gesperrt** ("Your
  organisation has blocked..."). Diagnose lief stattdessen über eine
  eigene Testseite ([`config/gamepad-test.html`](config/gamepad-test.html))
  und über direkte `evtest`-Auswertung der virtuellen Geräte per SSH.
- **`pkill -f` tötet sich selbst**: Wenn das Suchmuster wörtlich im
  eigenen SSH-Kommando vorkommt, matcht `pkill -f` die eigene
  aufrufende Shell mit. Abhilfe: Bracket-Trick, z. B.
  `pkill -f "pytho[n]3 -m http.server"`.

## Falls der Browser die Buttons trotzdem falsch erkennt

Siehe [`controller-profiles/README.md`](controller-profiles/README.md) für
Diagnoseschritte und einen Notnagel-Plan (z. B. AntiMicroX).
