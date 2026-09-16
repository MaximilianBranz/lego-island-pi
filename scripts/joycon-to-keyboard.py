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
  - Linker + rechter Stick X       -> Pfeiltasten links/rechts (Drehen/Lenken,
                                       beide Sticks steuern das gleichzeitig)
  - Rechter Stick Y (vor/zurueck)  -> Pfeiltasten hoch/runter (Vorwaerts/Rueckwaerts)
  - D-Pad                          -> Pfeiltasten (alle 4 Richtungen)
  - Rechter Stick (beide Achsen)   -> zusaetzlich Mauszeiger (Menuenavigation,
                                       laeuft parallel zu den Pfeiltasten)
  - A                              -> Enter UND Linksklick
  - B                              -> Escape
  - X                              -> Leertaste
  - Y                              -> Linke Strg-Taste

Muss als root laufen (Zugriff auf /dev/uinput). Wird ueber
systemd/joycon-to-keyboard.service verwaltet.
"""
import select
import time
import evdev
from evdev import ecodes, UInput, InputDevice

DEVICE_NAME = "Nintendo Switch Combined Joy-Cons"
TICK_SECONDS = 1.0 / 60  # fuer die Mauszeiger-Bewegung (60 Hz)
MOUSE_MAX_SPEED = 18     # Pixel pro Tick bei voll ausgelenktem Stick (quadratische Kurve)
MOUSE_DEADZONE = 0.20

# Digitale Tasten-Zuordnung: Joy-Con-Button -> Liste virtueller Ausgaben
BUTTON_MAP = {
    ecodes.BTN_DPAD_UP: [(ecodes.EV_KEY, ecodes.KEY_UP)],
    ecodes.BTN_DPAD_DOWN: [(ecodes.EV_KEY, ecodes.KEY_DOWN)],
    ecodes.BTN_DPAD_LEFT: [(ecodes.EV_KEY, ecodes.KEY_LEFT)],
    ecodes.BTN_DPAD_RIGHT: [(ecodes.EV_KEY, ecodes.KEY_RIGHT)],
    # Achtung: hid_nintendo benennt Codes nach physischer Position
    # (Xbox-Konvention), nicht nach Nintendo-Aufdruck. Bei Nintendo sitzt
    # A rechts (=BTN_EAST), B unten (=BTN_SOUTH), X oben (=BTN_NORTH),
    # Y links (=BTN_WEST).
    ecodes.BTN_EAST: [(ecodes.EV_KEY, ecodes.KEY_ENTER), (ecodes.EV_KEY, ecodes.BTN_LEFT)],  # A
    ecodes.BTN_SOUTH: [(ecodes.EV_KEY, ecodes.KEY_ESC)],      # B
    ecodes.BTN_NORTH: [(ecodes.EV_KEY, ecodes.KEY_SPACE)],    # X
    ecodes.BTN_WEST: [(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL)],  # Y
    ecodes.BTN_START: [(ecodes.EV_KEY, ecodes.KEY_ENTER)],
    ecodes.BTN_SELECT: [(ecodes.EV_KEY, ecodes.KEY_ESC)],
}

# Beide Sticks X = links/rechts (Drehen), rechter Stick Y = vor/zurueck ->
# Pfeiltasten (digital, mit Hysterese gegen Flackern). Schwellwerte pro
# Achse einzeln einstellbar - links/rechts absichtlich unempfindlicher als
# vor/zurueck, damit man nicht schon bei leichtem Wackeln lenkt.
STICK_AXES = {
    # Achse: (negative Taste, positive Taste, Press-Schwelle, Release-Schwelle)
    ecodes.ABS_X: (ecodes.KEY_LEFT, ecodes.KEY_RIGHT, 0.75, 0.55),
    ecodes.ABS_RX: (ecodes.KEY_LEFT, ecodes.KEY_RIGHT, 0.75, 0.55),  # rechter Stick, auch links/rechts
    ecodes.ABS_RY: (ecodes.KEY_UP, ecodes.KEY_DOWN, 0.5, 0.3),
}

# Rechter Stick -> Mauszeiger (kontinuierlich)
MOUSE_AXES = {ecodes.ABS_RX: "x", ecodes.ABS_RY: "y"}

ALL_KEYS = sorted(
    {code for outs in BUTTON_MAP.values() for (typ, code) in outs if typ == ecodes.EV_KEY}
    | {key for cfg in STICK_AXES.values() for key in cfg[:2]}
)

# Mehrere Achsen koennen dieselbe Taste bedienen (z.B. beide Sticks ->
# links/rechts). Damit ein losgelassener Stick eine Taste nicht faelschlich
# loslaesst, die der ANDERE Stick noch haelt, wird der Zustand pro Achse
# getrennt verfolgt und die Taste erst dann losgelassen, wenn KEINE Achse
# mehr aktiv ist.
KEY_SOURCES = {}
for _axis, (_neg, _pos, *_th) in STICK_AXES.items():
    KEY_SOURCES.setdefault(_neg, []).append((_axis, False))
    KEY_SOURCES.setdefault(_pos, []).append((_axis, True))


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
    # Aktivierungs-Status je (Achse, Richtung) - siehe KEY_SOURCES oben.
    axis_dir_active = {(axis, is_pos): False for axis in STICK_AXES for is_pos in (False, True)}
    key_state = {key: False for cfg in STICK_AXES.values() for key in cfg[:2]}
    mouse_axis = {"x": 0.0, "y": 0.0}
    mouse_remainder = {"x": 0.0, "y": 0.0}  # Nachkommaanteil fuer feine Aufloesung

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

                        elif event.type == ecodes.EV_ABS:
                            # Kein elif zwischen STICK_AXES/MOUSE_AXES: ABS_RY
                            # speist beides gleichzeitig (Pfeiltaste UND Maus).
                            if event.code in STICK_AXES:
                                neg_key, pos_key, press_th, release_th = STICK_AXES[event.code]
                                val = normalize(dev, event.code, event.value)
                                released = -release_th < val < release_th
                                for key, is_pos, active_now in (
                                    (neg_key, False, val <= -press_th),
                                    (pos_key, True, val >= press_th),
                                ):
                                    axis_dir = (event.code, is_pos)
                                    if active_now:
                                        axis_dir_active[axis_dir] = True
                                    elif released:
                                        axis_dir_active[axis_dir] = False
                                    # sonst (zwischen Release- und Press-Schwelle):
                                    # vorherigen Zustand beibehalten (Hysterese)

                                    should_be = any(
                                        axis_dir_active[(a, p)] for a, p in KEY_SOURCES[key]
                                    )
                                    if should_be != key_state[key]:
                                        ui.write(ecodes.EV_KEY, key, 1 if should_be else 0)
                                        ui.syn()
                                        key_state[key] = should_be

                            if event.code in MOUSE_AXES:
                                mouse_axis[MOUSE_AXES[event.code]] = normalize(dev, event.code, event.value)

                now = time.monotonic()
                if now >= next_tick:
                    for axis_name in ("x", "y"):
                        v = apply_deadzone(mouse_axis[axis_name], MOUSE_DEADZONE)
                        # Quadratische Kurve: feine, praezise Bewegung bei
                        # leichtem Auslenken, volles Tempo erst bei starkem.
                        curved = (v * v) * (1.0 if v >= 0 else -1.0)
                        mouse_remainder[axis_name] += curved * MOUSE_MAX_SPEED

                    dx_int = int(mouse_remainder["x"])
                    dy_int = int(mouse_remainder["y"])
                    if dx_int or dy_int:
                        ui.write(ecodes.EV_REL, ecodes.REL_X, dx_int)
                        ui.write(ecodes.EV_REL, ecodes.REL_Y, dy_int)
                        ui.syn()
                        # Nachkommaanteil behalten statt zu verwerfen -
                        # sorgt fuer feine Aufloesung auch bei langsamer,
                        # gleichmaessiger Bewegung statt "Treppenstufen".
                        mouse_remainder["x"] -= dx_int
                        mouse_remainder["y"] -= dy_int
                    next_tick = now + TICK_SECONDS

        except OSError:
            print("joycon-to-keyboard: Geraet getrennt, warte auf Neuverbindung...", flush=True)
            for key in ALL_KEYS:
                ui.write(ecodes.EV_KEY, key, 0)
            ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
            ui.syn()
            for k in key_state:
                key_state[k] = False
            for k in axis_dir_active:
                axis_dir_active[k] = False
            mouse_axis["x"] = mouse_axis["y"] = 0.0
            mouse_remainder["x"] = mouse_remainder["y"] = 0.0
            time.sleep(1)


if __name__ == "__main__":
    run()
