# Fallback: falls Chromium die Joy-Cons nicht richtig erkennt

island.pizza liest Controller ueber die Standard-Browser-Gamepad-API.
Normalerweise reicht es, dass joycond den/die Joy-Con(s) als Gamepad(s)
bereitstellt (siehe [`../scripts/test-gamepad.sh`](../scripts/test-gamepad.sh))
- dann sollte der Browser sie automatisch erkennen, sobald man im Spiel
  eine Taste drueckt.

Moegliche Probleme und Loesungen, falls es nicht auf Anhieb klappt:

## 1. Gamepad wird gar nicht erkannt

- `chrome://gpu` bzw. `chrome://device-log` (in Chromium eingeben) pruefen,
  ob ueberhaupt ein Gamepad-Event ankommt.
- Testseite https://hardwaretester.com/gamepad im Kiosk-Chromium oeffnen und
  Tasten druecken - zeigt, ob der Browser das Geraet ueberhaupt sieht.
- `journalctl -u joycond -f` waehrend des Testens beobachten.

## 2. Gamepad wird erkannt, aber Tasten/Sticks sind falsch belegt

Chromium ordnet ein Geraet nur dann dem "Standard-Gamepad-Layout" zu, wenn
Vendor/Product-ID in seiner internen Datenbank hinterlegt sind. Bei den
kombinierten Joy-Cons kann das je nach Chromium-Version variieren. Optionen:

- Pruefen, ob ein Chromium-/Chrome-Update das Mapping verbessert.
- In den Einstellungen auf island.pizza (Configure-Menue im Spiel) selbst
  eine Zuordnung vornehmen, falls das Spiel eigene Tastenzuordnung anbietet.
- Als letzter Ausweg: mit [AntiMicroX](https://github.com/AntiMicroX/antimicrox)
  den Controller-Input auf Tastatureingaben (Pfeiltasten/Leertaste etc.)
  umleiten und im Spiel die Tastatursteuerung nutzen. Das ist aber nur der
  Notnagel, kein sauberer Gamepad-Support mehr.

## Referenz

- SDL-Community-Datenbank kennt die kombinierten Joy-Cons unter dem Namen
  "Nintendo Switch Combined Joy-Cons" - falls irgendein Tool eine
  SDL_GameControllerDB-Datei braucht, dort nachschauen:
  https://github.com/mdqinc/SDL_GameControllerDB
