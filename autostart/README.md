# Kiosk-Autostart einrichten

Chromium soll nach dem Booten automatisch im Vollbild auf `island.pizza`
starten ([`../scripts/start-kiosk.sh`](../scripts/start-kiosk.sh)). Wie das
eingerichtet wird, haengt von der Desktop-Umgebung des Pi ab. Zuerst prüfen,
welche gerade läuft:

```bash
echo $XDG_SESSION_TYPE      # x11 oder wayland
echo $DESKTOP_SESSION
```

## Variante A: Raspberry Pi OS Bookworm (Wayland/labwc, Standard seit 2023)

Autostart-Datei fuer labwc anlegen:

```bash
mkdir -p ~/.config/labwc
echo 'lego-island-pi/scripts/start-kiosk.sh &' >> ~/.config/labwc/autostart
```

(Pfad im Befehl ggf. an den tatsaechlichen Ablageort des Projekts anpassen,
z. B. `/home/pi/lego-island-pi/scripts/start-kiosk.sh`.)

Bildschirmschoner/Energiesparen fuer labwc deaktivieren: in
`~/.config/labwc/rc.xml` gibt es dafuer keine zentrale Option wie bei X11 -
am einfachsten in den Raspberry Pi OS Einstellungen unter
"Bildschirm sperren" / Energieoptionen deaktivieren, oder testen ob es reicht,
dass ein Vollbild-Kiosk-Fenster laeuft.

## Variante B: Raspberry Pi OS Bullseye oder aelter (X11/LXDE)

```bash
mkdir -p ~/.config/lxsession/LXDE-pi
cat >> ~/.config/lxsession/LXDE-pi/autostart <<'EOF'
@xset s off
@xset -dpms
@xset s noblank
@/home/pi/lego-island-pi/scripts/start-kiosk.sh
EOF
```

(`/home/pi/...` an den tatsaechlichen Pfad anpassen.)

## Variante C: systemd-Service (fortgeschritten, X11)

Nur verwenden, wenn der Pi direkt in eine grafische Sitzung mit Auto-Login
bootet. `systemd/lego-island-kiosk.service` als Vorlage nehmen, Pfade/User
anpassen und dann:

```bash
sudo cp systemd/lego-island-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lego-island-kiosk.service
```

## Testen ohne Neustart

```bash
bash scripts/start-kiosk.sh
```

Mit `Alt+F4` bzw. `Strg+C` (im Terminal) wieder beenden.
