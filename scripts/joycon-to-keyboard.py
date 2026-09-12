#!/usr/bin/env python3
"""
Uebersetzt Eingaben vom joycond-kombinierten Joy-Con-Controller
("Nintendo Switch Combined Joy-Cons") in virtuelle Tastatureingaben.

Grund: Chromium erkennt joycond's virtuelles Geraet nicht als "standard"
Gamepad (eigene, nicht offizielle Produkt-ID), wodurch Web-Spiele wie
island.pizza den Controller stillschweigend ignorieren. Diese Uebersetzung
umgeht das Problem komplett, indem sie normale Tastatur-Events erzeugt -
die kann jede Webseite lesen.

Muss als root laufen (Zugriff auf /dev/uinput). Wird ueber
systemd/joycon-to-keyboard.service verwaltet.
"""
import time
import evdev
from evdev import ecodes, UInput, InputDevice

DEVICE_NAME = "Nintendo Switch Combined Joy-Cons"

# Digitale Tasten-Zuordnung: Joy-Con-Button -> Tastatur-Taste
BUTTON_MAP = {
    ecodes.BTN_DPAD_UP: ecodes.KEY_UP,
    ecodes.BTN_DPAD_DOWN: ecodes.KEY_DOWN,
    ecodes.BTN_DPAD_LEFT: ecodes.KEY_LEFT,
    ecodes.BTN_DPAD_RIGHT: ecodes.KEY_RIGHT,
    ecodes.BTN_SOUTH: ecodes.KEY_ENTER,      # A
    ecodes.BTN_EAST: ecodes.KEY_ESC,         # B
    ecodes.BTN_WEST: ecodes.KEY_SPACE,       # X
    ecodes.BTN_NORTH: ecodes.KEY_LEFTCTRL,   # Y
    ecodes.BTN_START: ecodes.KEY_ENTER,
    ecodes.BTN_SELECT: ecodes.KEY_ESC,
}

# Linker Stick -> Pfeiltasten (analog, mit Ein-/Ausschalt-Schwellwert)
STICK_AXES = {
    ecodes.ABS_X: (ecodes.KEY_LEFT, ecodes.KEY_RIGHT),
    ecodes.ABS_Y: (ecodes.KEY_UP, ecodes.KEY_DOWN),
}
PRESS_THRESHOLD = 0.5   # ab hier: Taste "gedrueckt"
RELEASE_THRESHOLD = 0.3  # darunter: Taste "losgelassen" (Hysterese gegen Flackern)

ALL_KEYS = sorted(set(BUTTON_MAP.values()) |
                   {k for pair in STICK_AXES.values() for k in pair})


def find_device():
    for path in evdev.list_devices():
        dev = InputDevice(path)
        if dev.name == DEVICE_NAME:
            return dev
    return None


def normalize(dev, code, value):
    info = dev.absinfo(code)
    span = (info.max - info.min) / 2.0
    mid = (info.max + info.min) / 2.0
    if span == 0:
        return 0.0
    return (value - mid) / span


def run():
    ui = UInput({ecodes.EV_KEY: ALL_KEYS}, name="joycon-virtual-keyboard")
    stick_state = {code: False for pair in STICK_AXES.values() for code in pair}
    button_state = {}

    print("joycon-to-keyboard: warte auf Geraet...", flush=True)
    while True:
        dev = find_device()
        if dev is None:
            time.sleep(2)
            continue

        print(f"joycon-to-keyboard: verbunden mit {dev.path}", flush=True)
        try:
            for event in dev.read_loop():
                if event.type == ecodes.EV_KEY and event.code in BUTTON_MAP:
                    key = BUTTON_MAP[event.code]
                    ui.write(ecodes.EV_KEY, key, event.value)  # 1=down, 0=up, 2=repeat->wird ignoriert unten
                    if event.value in (0, 1):
                        ui.syn()

                elif event.type == ecodes.EV_ABS and event.code in STICK_AXES:
                    neg_key, pos_key = STICK_AXES[event.code]
                    val = normalize(dev, event.code, event.value)

                    for key, active_now in (
                        (neg_key, val <= -PRESS_THRESHOLD),
                        (pos_key, val >= PRESS_THRESHOLD),
                    ):
                        released = -RELEASE_THRESHOLD < val < RELEASE_THRESHOLD
                        if active_now and not stick_state[key]:
                            ui.write(ecodes.EV_KEY, key, 1)
                            ui.syn()
                            stick_state[key] = True
                        elif released and stick_state[key]:
                            ui.write(ecodes.EV_KEY, key, 0)
                            ui.syn()
                            stick_state[key] = False
        except OSError:
            print("joycon-to-keyboard: Geraet getrennt, warte auf Neuverbindung...", flush=True)
            # Alle Tasten sicherheitshalber loslassen
            for key in ALL_KEYS:
                ui.write(ecodes.EV_KEY, key, 0)
            ui.syn()
            for k in stick_state:
                stick_state[k] = False
            time.sleep(1)


if __name__ == "__main__":
    run()
