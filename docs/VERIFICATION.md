# Verifikation der dekodierten Werte

Gegenprobe der Cloud-/REST-Dekodierung gegen die Judo-App.
Referenzgerät: **i-soft SAFE+ (Typ `0x33`)**, Gerätenummer 123456, Steuerung SW 3.02 / HW 5.10,
Connectivity-Modul SW 1.14. Stand: 2026-11-14.

Quellen im Code: `custom_components/judo_isoft/judo_client/` (`client.py`,
`protocol/families/isoft.py`).

Legende: ✅ bestätigt · 🟡 plausibel, aber nur eine Messung / geraten · ⬜ offen

## Bestätigt (App und Home Assistant stimmen überein)

- [x] ✅ Gesamtwasser `water_total_l` (Kommando `0x08`): 340,052 m³ (App 340,1)
- [x] ✅ Zielhärte `target_hardness`: 8 °dH
- [x] ✅ Regenerationen `regeneration_count` (Statusblock Offset 62): 728
- [x] ✅ Salzreichweite `salt_days_remaining` (Kommando `0x5E`): 227 d = 32 Wochen
- [x] ✅ Max. Entnahmedauer `leakage_max_duration_min` (Blockoffset 80): 120 min (2 h)
- [x] ✅ Max. Entnahmemenge `leakage_max_volume_l` (Blockoffset 78): 900 l, auch Wechsel auf 1000 l und zurück
- [x] ✅ Max. Durchfluss `leakage_max_flow_lph` (Blockoffset 76): 4000 l/h
- [x] ✅ Urlaubsmodus-Typ `vacation_mode_type` (Blockoffset 82, Rohwerte 0/3/5/9 = U0/U1/U2/U3): U1 und U2 getestet. Laut Judo-Handbuch schaltet der Leckageschutz nach 72 h ohne Verbrauch in den gewählten Modus: U1 = 6 min / 50 l / 500 l/h, U2 = 12 min / 100 l / 1000 l/h, U3 = Leckageschutz geschlossen.
- [x] ✅ Sleepmodusdauer `sleep_mode_duration_h` (Blockoffset 83): 2 h und 3 h getestet. Laut Judo-Handbuch einstellbar von 1 bis 10 h. Im Sleepmodus ist die Entnahme innerhalb der Dauer nicht überwacht und der Leckageschutz schließt bei Überschreitung der Grenzwerte nicht.
- [x] ✅ Wasserszene `water_scene`: normal
- [x] ✅ Szenenhärten Duschen 4 / Garten 10 / Heizung 1 / Waschen 1 / Normal 8 °dH
- [x] ✅ Gerätenummer `cloud_node_id` (Kommando `0x03`): 123456
- [x] ✅ Hardware 5.10 und Connectivity-Modul 1.14

- [x] ✅ Meldungen (`get error messages`): 22 Einträge seit 2023 gelesen. Zeitstempel sind deutsche Ortszeit (wird nach UTC umgerechnet). Meldung 251 „Urlaubsmodus: reduzierte Grenzwerte“ am 2026-11-15 02:27 passt zum aktiven Urlaubsmodus U1.

## Offen: ohne Eingriff, nur abwarten

| | Wert | Aktuell | Gegenprobe | Erwartung |
|---|---|---|---|---|
| ✅ | `maintenance_days_remaining` / `_hours_remaining` (`0x07`, erstes Wort); Stunden zählen 1 pro Stunde herunter (2403 → 2402 → 2390), abgerundet 99 d = App am 2026-11-15 | 99 d / 2390 h | erledigt | |
| ⬜ | `maintenance_count` (`0x07`, zweites Wort) | 3 | nach der nächsten Wartung | 4 |
| ⬜ | `regeneration_count` | 728 | nach der nächsten Regeneration | 729 |
| ⬜ | `salt_weight_g` / `salt_days_remaining` | 22 750 g / 227 d | in 1 bis 2 Wochen | Werte fallen, App zeigt dasselbe |
| 🟡 | `salt_level_pct`, Tankkapazität 50 kg angenommen (`SALT_TANK_CAPACITY_G`) | 45,5 % | genauen App-Prozentwert notieren und nach dem Nachfüllen vergleichen | App ≈ HA. Zeigt die App 50 %, wäre der Tank ca. 45 kg. |
| ⬜ | `soft_water_m3` | 202,309 | App-Wert Weichwasser notieren | gleicher Wert |
| 🟡 | `battery_runtime_min` (`0x5D`, Bytes 6 bis 7) | 2 min | beobachten, ob sich der Wert in der App ändert (z. B. nach einem Batterietest) | ändert sich nur die App, ist es Byte 0 statt Bytes 6 bis 7 |

## Offen: in der App umstellen, danach Rohdaten vergleichen

| | Wert | Aktuell | Umstellung | Erwartung |
|---|---|---|---|---|
| 🟡 | `vacation_mode_active` (Statusblock Offset 64) | False | Urlaubsmodus aktivieren | True (bei U1 mit offenem Ventil beobachtet). Offset 7 flippt gleichzeitig. Ein anderes Projekt nennt Byte 64 „Ventil geschlossen“: prüfen, ob es bei manuell geschlossenem Leckageschutz ebenfalls 1 wird. Mit U3 prüfen, welche Grenzwerte im aktiven Zustand gelten. |
| ⬜ | Szenendauer (Duschen 2 h, Garten 2 h, Heizung 2 h, Waschen 1 h) | nicht gefunden | Szene aktivieren und prüfen, welche Felder sich füllen (`waterscene_time*`) | Dauer in den Cloud-Metadaten |
| ⬜ | „Bedienung erlaubt" | nicht gefunden | Bedienung sperren, falls möglich | Kandidat: `disable_time` |

## Offen: nur mit anderem Gerät oder gar nicht prüfbar

- [ ] 🟡 `emergency_power_module` (`0x5D`, Byte 1): immer `01`. Ein Gerät ohne Notstrommodul fehlt zum Vergleich.
- [ ] 🟡 `battery_capacity_pct` (`0x5D`, Byte 3): konstant 100. Erst bei entladenem Akku zeigt sich, ob das Byte stimmt.
- [ ] 🟡 Firmware `3.02n`: die App zeigt laut Eingabe `3.02`. Der Buchstabe `n` bleibt, solange die App nicht ohne ihn bestätigt wird.

## Lokale Verbindung

- [ ] ⬜ Alle echten Prüfwerte stammen aus der Cloud. Die lokale REST-Dekodierung ist nur gegen die Doku-Beispiele (`docs/API-Kommandos.md`) und den Mock getestet.
      Vergleich Cloud gegen lokal ist der wichtigste noch offene Test.

## Bekannt ungeprüft, ohne App-Gegenwert

- [ ] Status-Flags `0x43` (Alarm, Wartung, Regeneration aktiv): Bit-Zuordnung unbelegt, die Cloud liefert dieses Kommando nicht.
- [ ] Statistik-Kommandos `F3` bis `FE`: werden nicht dekodiert.

## Rohdaten erneut abrufen

Das Statusblock-Layout (Kommandos 790 bis 792) lässt sich nur im Vergleich vorher/nachher prüfen:
Wert in der App ändern, Cloud-Payload abrufen, geänderte Bytes den Offsets zuordnen.
Aus dem Dev-Container, mit den Zugangsdaten des Config Entry, über `JudoiSoftAPI` mit `force_cloud=True`
und `api._client._transport.read_cloud_device_data()`.

## Wasserstatistik (Tagesverlauf, 3-h-Segmente)

- [ ] ⬜ Kommando `FB` (Doku: 8 × u32le Liter für 0:00, 3:00 … 21:00) wurde am 2026-11-15 über die Cloud
      (`set device data`, `cmd=FB`, `data=0E0B07EA` = 14.11.2026, Encoding `hex` und `rest_inline`) abgefragt.
      Antwort: HTTP 200, Wert `null`, im folgenden `get device data` kein neues Feld. Über diesen Weg liefert die Cloud keine Statistik.
      Offen: Abfrage über die lokale REST-Schnittstelle oder den Cloud-Befehl, den die App verwendet.
