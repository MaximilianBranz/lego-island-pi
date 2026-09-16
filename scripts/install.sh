#!/usr/bin/env bash
# Installiert alles, was fuer den LEGO Island Kiosk auf dem Raspberry Pi
# gebraucht wird: Chromium, Bluetooth-Tools und joycond (kombiniert zwei
# Joy-Cons zu einem virtuellen Gamepad).
#
# Auf dem Pi ausfuehren: bash scripts/install.sh
set -euo pipefail

echo "== LEGO Island Pi Kiosk - Setup =="

sudo apt update

# Paketname variiert je nach Raspberry Pi OS Version.
CHROMIUM_PKG="chromium-browser"
if ! apt-cache show "$CHROMIUM_PKG" >/dev/null 2>&1; then
  CHROMIUM_PKG="chromium"
fi

sudo apt install -y --no-install-recommends \
  "$CHROMIUM_PKG" \
  bluez bluez-tools \
  joystick evtest \
  unclutter \
  git build-essential cmake pkg-config \
  libevdev-dev libudev-dev \
  python3-evdev

echo "-- Chromium-Paket: $CHROMIUM_PKG"

# Kernel-Treiber fuer Joy-Cons pruefen
if ! lsmod | grep -q hid_nintendo; then
  echo "-- Versuche hid_nintendo Kernelmodul zu laden..."
  if sudo modprobe hid_nintendo 2>/dev/null; then
    echo "   OK."
  else
    echo "   WARNUNG: hid_nintendo konnte nicht geladen werden."
    echo "   Kernel-Version pruefen (>= 5.16 noetig): uname -r"
  fi
fi

# joycond bauen und installieren
JOYCOND_DIR="/opt/joycond"
if [ ! -d "$JOYCOND_DIR" ]; then
  echo "-- Klone joycond nach $JOYCOND_DIR"
  sudo git clone https://github.com/DanielOgorchock/joycond.git "$JOYCOND_DIR"
else
  echo "-- joycond bereits vorhanden, aktualisiere..."
  sudo git -C "$JOYCOND_DIR" pull
fi

echo "-- Baue joycond..."
(cd "$JOYCOND_DIR" && sudo cmake . && sudo make && sudo make install)

echo "-- Aktiviere joycond-Dienst..."
sudo systemctl enable --now joycond

# BlueZ-Fix: Joy-Cons (v.a. der rechte) haben ohne diese Einstellung nach
# Sleep/Reboot oft eine ungueltige Bonding-Info und scheitern beim
# Reconnect mit "br-connection-create-socket", obwohl sie noch als
# gekoppelt gelten. JustWorksRepairing erlaubt BlueZ, die Kopplung im
# Hintergrund automatisch zu erneuern, statt hart abzubrechen.
if ! grep -q "^JustWorksRepairing" /etc/bluetooth/main.conf 2>/dev/null; then
  echo "-- Aktiviere JustWorksRepairing in /etc/bluetooth/main.conf..."
  sudo sed -i '/^\[General\]/a JustWorksRepairing = always' /etc/bluetooth/main.conf
  sudo systemctl restart bluetooth
fi

# joycon-to-keyboard: uebersetzt den (von Chromium nicht als "standard"
# erkannten) kombinierten Joy-Con-Controller in virtuelle Tastatureingaben.
echo "-- Richte joycon-to-keyboard Dienst ein..."
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sudo mkdir -p /opt/lego-island-pi/scripts
sudo cp "$PROJECT_DIR/scripts/joycon-to-keyboard.py" /opt/lego-island-pi/scripts/
sudo cp "$PROJECT_DIR/systemd/joycon-to-keyboard.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now joycon-to-keyboard

# joycon-autoconnect: versucht nach jedem Boot eine Weile lang, bekannte
# Joy-Cons automatisch per Bluetooth wiederzuverbinden.
echo "-- Richte joycon-autoconnect Dienst ein..."
sudo cp "$PROJECT_DIR/scripts/joycon-autoconnect.sh" /opt/lego-island-pi/scripts/
sudo cp "$PROJECT_DIR/systemd/joycon-autoconnect.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now joycon-autoconnect

echo
echo "== Fertig =="
echo "Naechster Schritt: Joy-Cons koppeln mit scripts/pair-joycons.sh"
