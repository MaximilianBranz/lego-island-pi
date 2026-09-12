#!/usr/bin/env python3
"""
Uebersetzt Eingaben vom joycond-kombinierten Joy-Con-Controller
("Nintendo Switch Combined Joy-Cons") in virtuelle Tastatur- UND
Maus-Eingaben.

Grund: Chromium erkennt joycond's virtuelles Geraet nicht als "standard"
Gamepad (eigene, nicht offizielle Produkt-ID), wodurch Web-Spiele wie
island.pizza den Controller stillschweigend ignorieren. Diese Uebersetzung
umgeht das Problem komplett, indem sie normale Tastatur-/Maus-Events
erzeugt - die kann jede Webseite lesen.

Aufteilung (passend zu island.pizza: Menue ist reine Maus-UI, das
eigentliche Spiel wird mit Pfeiltasten gesteuert):
  - Linker Stick + D-Pad -> Pfeiltasten (Spielsteuerung)
  - Rechter Stick        -> Mauszeiger bewegen (Menuenavigation)
  - A                    -> Enter UND Linksklick
  - B                    -> Escape
  - X                    -> Leertaste
  - Y                    -> Linke Strg-Taste

Muss als root laufen (Zugriff auf /dev/uinput). Wird ueber
systemd/joycon-to-keyboard.service verwaltet.
"""
import select
import time
import evdev
from evdev import ecodes, UInput, InputDevice

DEVICE_NAME = "Nintendo Switch Combined Joy-Cons"
TICK_SECONDS = 1.0 / 60  # fuer die Mauszeiger-Bewegung (60 Hz)
MOUSE_MAX_SPEED = 18     # Pixel pro Tick bei voll ausgelenktem Stick
MOUSE_DEADZONE = 0.20

# Digitale Tasten-Zuordnung: Joy-Con-Button -> Liste virtueller Ausgaben
BUTTON_MAP = {
    ecodes.BTN_DPAD_UP: [(ecodes.EV_KEY, ecodes.KEY_UP)],
    ecodes.BTN_DPAD_DOWN: [(ecodes.EV_KEY, ecodes.KEY_DOWN)],
    ecodes.BTN_DPAD_LEFT: [(ecodes.EV_KEY, ecodes.KEY_LEFT)],
    ecodes.BTN_DPAD_RIGHT: [(ecodes.EV_KEY, ecodes.KEY_RIGHT)],
    ecodes.BTN_SOUTH: [(ecodes.EV_KEY, ecodes.KEY_ENTER), (ecodes.EV_KEY, ecodes.BTN_LEFT)],  # A
    ecodes.BTN_EAST: [(ecodes.EV_KEY, ecodes.KEY_ESC)],       # B
    ecodes.BTN_WEST: [(ecodes.EV_KEY, ecodes.KEY_SPACE)],     # X
    ecodes.BTN_NORTH: [(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL)], # Y
    ecodes.BTN_START: [(ecodes.EV_KEY, ecodes.KEY_ENTER)],
    ecodes.BTN_SELECT: [(ecodes.EV_KEY, ecodes.KEY_ESC)],
}

# Linker Stick -> Pfeiltasten (digital, mit Hysterese gegen Flackern)
STICK_AXES = {
    ecodes.ABS_X: (ecodes.KEY_LEFT, ecodes.KEY_RIGHT),
    ecodes.ABS_Y: (ecodes.KEY_UP, ecodes.KEY_DOWN),
}
PRESS_THRESHOLD = 0.5
RELEASE_THRESHOLD = 0.3

# Rechter Stick -> Mauszeiger (kontinuierlich)
MOUSE_AXES = {ecodes.ABS_RX: "x", ecodes.ABS_RY: "y"}

ALL_KEYS = sorted(
    {code for outs in BUTTON_MAP.values() for (typ, code) in outs if typ == ecodes.EV_KEY}
    | {k for pair in STICK_AXES.values() for k in pair}
)


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


def apply_deadzone(val, deadzone):
    if abs(val) < deadzone:
        return 0.0
    sign = 1.0 if val > 0 else -1.0
    return sign * (abs(val) - deadzone) / (1.0 - deadzone)


def run():
    ui = UInput(
        {
            ecodes.EV_KEY: ALL_KEYS + [ecodes.BTN_LEFT, ecodes.BTN_RIGHT],
            ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y],
        },
        name="joycon-virtual-input",
    )
    stick_state = {code: False for pair in STICK_AXES.values() for code in pair}
    mouse_axis = {"x": 0.0, "y": 0.0}

    print("joycon-to-keyboard: warte auf Geraet...", flush=True)
    while True:
        dev = find_device()
        if dev is None:
            time.sleep(2)
            continue

        print(f"joycon-to-keyboard: verbunden mit {dev.path}", flush=True)
        try:
            next_tick = time.monotonic()
            while True:
                remaining = max(0.0, next_tick - time.monotonic())
                r, _, _ = select.select([dev.fd], [], [], remaining)

                if dev.fd in r:
                    for event in dev.read():
                        if event.type == ecodes.EV_KEY and event.code in BUTTON_MAP:
                            if event.value in (0, 1):
                                for typ, code in BUTTON_MAP[event.code]:
                                    ui.write(typ, code, event.value)
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

                        elif event.type == ecodes.EV_ABS and event.code in MOUSE_AXES:
                            mouse_axis[MOUSE_AXES[event.code]] = normalize(dev, event.code, event.value)

                now = time.monotonic()
                if now >= next_tick:
                    dx = apply_deadzone(mouse_axis["x"], MOUSE_DEADZONE) * MOUSE_MAX_SPEED
                    dy = apply_deadzone(mouse_axis["y"], MOUSE_DEADZONE) * MOUSE_MAX_SPEED
                    if dx or dy:
                        ui.write(ecodes.EV_REL, ecodes.REL_X, int(dx))
                        ui.write(ecodes.EV_REL, ecodes.REL_Y, int(dy))
                        ui.syn()
                    next_tick = now + TICK_SECONDS

        except OSError:
            print("joycon-to-keyboard: Geraet getrennt, warte auf Neuverbindung...", flush=True)
            for key in ALL_KEYS:
                ui.write(ecodes.EV_KEY, key, 0)
            ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
            ui.syn()
            for k in stick_state:
                stick_state[k] = False
            mouse_axis["x"] = mouse_axis["y"] = 0.0
            time.sleep(1)


if __name__ == "__main__":
    run()
