# API-KOMMANDOZEILEN – Table Export

Source: API-KOMMANDOZEILEN.pdf


## Dosierpumpe i-dos eco Gerätetyp 0x41


### Betriebsdaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Gesamtwassermenge lesen | 28 | 4 | 4 byte Wasserverbrauch in L<br>4 byte unbenutzt |  | 8 |

### Betriebsstatus

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Statusdaten abfragen | 43 | 29 | 1 byte Schaltungstyp<br>1 byte Betriebsmodus<br>1 byte unbenutzt<br>1 byte Konzentration (min, Norm, max)<br>1 byte unbenutzt<br>2 byte Fehlercode<br>2 byte Warnmeldungen<br>6 byte unbenutzt<br>2 byte Dosiermenge<br>2 byte akt. Wasserdurchfluss in l/h<br>2byte Restmenge im Behälter<br>4 byte Wasserverbrauch in L<br>4 byte unbenutzt | /api/rest/4300<br>data=020001020000000000000000000000000000<br>002f000d0000004dae0200 | 8 |
| Datum und Uhrzeit lesen | 61 | 6 | Je ein Byte: Tag, Monat, Jahr, Stunde, Minute, Sekunde --> Jahr<br>00 .. 99 | /api/rest/6100<br>data=0507170a1b1b 05.07.23 10:27:27 | 8 |
| Datum und Uhrzeit schreiben | 71 | 6 | Je ein Byte: Tag, Monat, Jahr, Stunde, Minute, Sekunde --> Jahr<br>00 .. 99 | /api/rest/71000507170B2727 05.07.23 11:27:27 | 8 |

### Einstellungen

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Dosierung schreiben | 52 | 2 | 1 byte unbenutzt<br>1 byte Konzentration: 1-min 2-norm 3-max | /api/rest/52000002 Konz. norm | 8 |
| Pumpenbetriebsart einstellen | 53 | 3 | 1 byte Pumpenmodus: 0-aus 1-automatik 2-manuell 3-"ein"<br>bis 5ml dosiert.<br>2 byte Pumpendrehzahl bei man. Betrieb in U/min. | /api/rest/5300010000 auto, 0U/min manuell | 8 |
| Dosierung lesen | 63 | 6 | 1 byte Typ: 1- JUL-W<br>2- JUL-C<br>3- JUL-H<br>4- JUL-S<br>5- JUL-SW<br>1 byte Inhalt: 1-3 ltr<br>2-6 ltr<br>3-25 ltr<br>4-60 ltr | data=0102 JUL-W, 6ltr | 8 |

### Infodaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| SW-Version Gerätesteuerung lesen | 1 | 3 | 3 byte SW-Version | /api/rest/0100<br>data=661301 entspricht 1.19f | 8 |
| Gerätenummer lesen | 6 | 4 | 4 byte Gerätenummer | /api/rest/0600<br>data=0774ed0b entspricht 200111111 | 8 |
| Inbetriebnahmedatum lesen | E | 4 |  | /api/rest/0E00<br>data=6414CB7B UNIX Timestamp:<br>1679084411dez = 17.3.2023 21:20 GMT+1 | 8 |
| Gerätetyp lesen | FF | 1 | 1 byte Gerätetyp | /api/rest/FF00<br>data="44" | 8 |

### Wasserverbrauch

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | FB | 4 | 32 byte:Es werden die Gesamttageswerte für den angefragten<br>Tag zurückgeliefert:<br>1-4 Byte: 0:00<br>5-8 Byte: 3:00<br>9-12 Byte: 6:00<br>13-16 Byte: 9:00<br>17-20 Byte: 12:00<br>21-24 Byte: 15:00<br>25-28 Byte: 18:00<br>29-32 Byte: 21:00 | /api/rest/FB000D0807E7<br>Tagesdaten vom 13.08.2023 | 8 |
| Wochenstatistik | FC | 3 | 28 byte:<br>Es werden alle Gesamtwerte der Tage der angefragten Woche<br>zurückgeliefert:<br>1-4 Byte: Montag<br>5-8 Byte: Dienstag<br>9-12 Byte: Mittwoch<br>13-16 Byte: Donnerstag<br>17-20 Byte: Freitag<br>21-24 Byte: Samstag<br>25-28 Byte: Sonntag | /api/rest/FC002007E7<br>Wochendaten aus KW32 2023 | 8 |
| Monatsstatistik | FD | 3 | 124 byte:<br>Es werden alle Tage des angefragten Montats zurück geliefert<br>max 31 Tage<br>Byte 1-4: Tag1<br>Byte 5-8: Tag2<br>…..<br>Byte 121-124: Tag 31 | /api/rest/FD000807E7<br>Monatsdaten aus August 2023 | 8 |
| Jahresstatistik | FE | 2 | 48 byte:<br>Es wird die Gesamtsumme des Verbrauchs jedes Monats des<br>angefragen Jahres zurück geliefert<br>1-4 Byte: Januar<br>5-8 Byte: Februar<br>9-12 Byte: März<br>13-16 Byte: April<br>17-20 Byte: Mai<br>21-24 Byte: Juni<br>25-28 Byte: Juli<br>29-32 Byte: August<br>33-36 Byte: September<br>37-40 Byte: Oktober<br>41-44 Byte: November<br>45-48 Byte: Dezember | /api/rest/FE0007E7<br>Jahresdaten aus 2023 | 9 |

## Enthärter SOFTwell P Gerätetyp 0x34 (52 dez) und Gerätetyp 0x59 (dez 89) ohne Leckageschutz SOFTwell S Gerätetyp 0x35 (53 dez) und Gerätetyp 0x63 (dez 99) SOFTwell K Gerätetyp 0x36 (54 dez) und Gerätetyp 0x5A (dez 90) SOFTwell KP Gerätetyp 0x47 (71 dez) und Gerätetyp 0x62 (dez 98) SOFTwell KS Gerätetyp 0x48 (72 dez) und Gerätetyp 0x64 (dez 100)


### Betriebsdaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Weichwassermenge lesen | 29 | 4 | Weichwassermenge in liter lsb first | /api/rest/2900<br>data=2EDC0000 56,366 m³ | 5 |

### Infodaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| SW-Version Gerätesteuerung lesen | 1 | 3 | 3 byte SW-Version | /api/rest/0100<br>data=670102 entspricht 2.01d | 5 |
| Betriebsstundenzähler | 25 | 4 | 4 byte Betriebsstunden<br>1 byte Minuten<br>1 byte Stunden<br>2 byte Tage | /api/rest/2500<br>data=060c7500 117Tage, 12h, 6 min. | 5 |
| Gerätenummer lesen | 6 | 4 | 4 byte Gerätenummer | /api/rest/0600<br>data=64d90100 entspricht 121188 | 5 |
| Inbetriebnahmedatum lesen | E | 4 |  |  | 5 |
| Gerätetyp lesen | FF | 1 | 1 byte Gerätetyp | /api/rest/FF00<br>data="34" | 5 |

### Wasserstatistik

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | FB | 4 | 32 byte:Es werden die Gesamttageswerte für den<br>angefragten Tag zurückgeliefert:<br>1-4 Byte: 0:00<br>5-8 Byte: 3:00<br>9-12 Byte: 6:00<br>13-16 Byte: 9:00<br>17-20 Byte: 12:00<br>21-24 Byte: 15:00<br>25-28 Byte: 18:00<br>29-32 Byte: 21:00 | /api/rest/FB000D0807E7<br>Tagesdaten vom 13.08.2023 | 5 |
| Wochenstatistik | FC | 3 | 28 byte:<br>Es werden alle Gesamtwerte der Tage der<br>angefragten Woche zurückgeliefert:<br>1-4 Byte: Montag<br>5-8 Byte: Dienstag<br>9-12 Byte: Mittwoch<br>13-16 Byte: Donnerstag<br>17-20 Byte: Freitag<br>21-24 Byte: Samstag<br>25-28 Byte: Sonntag | /api/rest/FC002007E7<br>Wochendaten aus KW32 2023 | 5 |
| Monatsstatistik | FD | 3 | 124 byte:<br>Es werden alle Tage des angefragten Montats<br>zurück geliefert max 31 Tage<br>Byte 1-4: Tag1<br>Byte 5-8: Tag2<br>…..<br>Byte 121-124: Tag 31 | /api/rest/FD000807E7<br>Monatsdaten aus August 2023 | 5 |
| Jahresstatistik | FE | 2 | 48 byte:<br>Es wird die Gesamtsumme des Verbrauchs jedes<br>Monats des angefragen Jahres zurück geliefert<br>1-4 Byte: Januar<br>5-8 Byte: Februar<br>9-12 Byte: März<br>13-16 Byte: April | /api/rest/FE0007E7<br>Jahresdaten aus 2023 | 5 |

## Enthärter i-soft Gerätetyp 0x32 (50 dez) und Gerätetyp 0x53 (83 dez) mit Leckagealarm i-soft K Gerätetyp 0x43 (67 dez) und Gerätetyp 0x54 (84 dez)


### Bedienung

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Regeneration starten | 35 | 1 | Start = 00 | /api/rest/350000 | 4 |

### Betriebsdaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Gesamtwassermenge lesen | 28 | 4 | Wassermenge in liter lsb first | /api/rest/2800<br>data=EC221000 1057,516 m³ | 4 |
| Weichwassermenge lesen | 29 | 4 | Weichwassermenge in liter lsb first | /api/rest/2900<br>data=2EDC0000 56,366 m³ | 4 |

### Betriebsstatus

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Wunschwasserhärte lesen | 51 | 2 | 2 byte Antwort Wunschwasserhärte | /api/rest/5100 data="0600" 6°dH | 4 |

### Einstellungen

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Härteeinheit lesen | 23 | 1 | 0 °dH , 1 °eH , 2 °fH , 3 gpg , 4 ppm , 5 mmol , 6 mval | data=00 Einheit °dH | 4 |
| Härteeinheit schreiben | 24 | 1 | 0 °dH , 1 °eH , 2 °fH , 3 gpg , 4 ppm , 5 mmol , 6 mval | /api/rest/240004 Einheit ppm | 4 |
| Wunschwasserhärte schreiben | 30 | 1/ 2 | 1 byte: Härte in °dH wird in Geräteeinheit umgerechnet ODER<br>2 byte: Härte in Geräteeinheit ohne Komma (also 17,8 --> 178) | /api/rest/300007 7°dH<br>/api/rest/30000A00 10°dH | 4 |
| Leckagealarm setzen | 3C | 0 |  | /api/rest/3C00 | 4 |
| Leckagealarm zurücksetzen | 3D | 0 |  | /api/rest/3D00 | 4 |
| Max. Entnahmdauer schreiben | 3E | 1 | max. Entnahmezeit in Minuten 1-255 Minuten, 0 deaktiviert überwachung | /api/rest/3E0028 Entnahmedauer max. 40min | 4 |
| Max. Entnahmemenge schreiben | 3F | 2 | max. Durchfluss in Liter/Stunde 1- 65535 l/h, 0 deaktiviert überwachung | /api/rest/3F00C409 2500ltr/h | 4 |
| Max. Volumenstrom schreiben | 40 | 2 | max. Wassermenge am Stück in Liter 1- 65535 l , 0 deaktiviert überwachung | /api/rest/4000F401 500ltr | 4 |
| Salzvorrat lesen oder schreiben | 56 | 2 | ohne Data:<br>4 byte antwort:<br>2byte Salzgewicht<br>2byte Salzreichweite in Tagen<br>mit 2 byte Data:<br>absolutes Salzgewicht in gramm | /api/rest/5600<br>data=f6541100 f654 = 21750g, 1100 = 17 Tage<br>schreiben:<br>/api/rest/56004448 = 18500g | 4 |
| Salzreichweitenmangelwarnung lesen<br>und schreiben | 57 |  | ohne Data:<br>Salzreichweitenmangelwarnung in Tagen<br>Mit Data:<br>1 byte: Setzt Reichweitenmangelwarnung auf x Tage | /api/rest/570014 Setzt Reichweitenmangel auf<br>20 Tage | 4 |

### Infodaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| SW-Version Gerätesteuerung lesen | 1 | 3 | 3 byte SW-Version | /api/rest/0100<br>data=6b1502 entspricht 2.21k | 4 |
| Betriebsstundenzähler | 25 | 4 | 4 byte Betriebsstunden<br>1 byte Minuten<br>1 byte Stunden<br>2 byte Tage | data=060c7500 117Tage, 12h, 6 min. | 4 |
| Kundendienst/Serviceadresse | 58 | 16 | Servicetelefonnummer ASCII, ohne datenbytes = lesen, 16 bytes data schreiben. | data=2b343920373139352036393235313720<br>ASCII umsetzung: +49 7195 692517 | 4 |
| Gerätenummer lesen | 6 | 4 | 4 byte Gerätenummer | /api/rest/0600<br>data=64d90100 entspricht 121188 | 4 |
| Inbetriebnahmedatum lesen | E | 4 |  |  | 4 |
| Gerätetyp lesen | FF | 1 | 1 byte Gerätetyp | /api/rest/FF00<br>data="32" | 4 |

### Wasserstatistik

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | FB | 4 | 32 byte:Es werden die Gesamttageswerte für den angefragten Tag zurückgeliefert:<br>1-4 Byte: 0:00<br>5-8 Byte: 3:00<br>9-12 Byte: 6:00<br>13-16 Byte: 9:00<br>17-20 Byte: 12:00<br>21-24 Byte: 15:00<br>25-28 Byte: 18:00<br>29-32 Byte: 21:00 | /api/rest/FB000D0807E7<br>Tagesdaten vom 13.08.2023 | 4 |
| Wochenstatistik | FC | 3 | 28 byte:<br>Es werden alle Gesamtwerte der Tage der angefragten Woche zurückgeliefert:<br>1-4 Byte: Montag<br>5-8 Byte: Dienstag<br>9-12 Byte: Mittwoch<br>13-16 Byte: Donnerstag<br>17-20 Byte: Freitag<br>21-24 Byte: Samstag<br>25-28 Byte: Sonntag | /api/rest/FC002007E7<br>Wochendaten aus KW32 2023 | 4 |
| Monatsstatistik | FD | 3 | 124 byte:<br>Es werden alle Tage des angefragten Montats zurück geliefert max 31 Tage<br>Byte 1-4: Tag1<br>Byte 5-8: Tag2<br>…..<br>Byte 121-124: Tag 31 | /api/rest/FD000807E7<br>Monatsdaten aus August 2023 | 4 |
| Jahresstatistik | FE | 2 | 48 byte:<br>Es wird die Gesamtsumme des Verbrauchs jedes Monats des angefragen Jahres zurück<br>geliefert<br>1-4 Byte: Januar<br>5-8 Byte: Februar<br>9-12 Byte: März<br>13-16 Byte: April<br>17-20 Byte: Mai<br>21-24 Byte: Juni<br>25-28 Byte: Juli<br>29-32 Byte: August<br>33-36 Byte: September<br>37-40 Byte: Oktober<br>41-44 Byte: November<br>45-48 Byte: Dezember | /api/rest/FE0007E7<br>Jahresdaten aus 2023 | 4 |

## Enthärter i-soft PRO Gerätetyp 0x58 (88 dez) mit Leckageschutz i-soft PRO Gerätetyp 0x4b (75 dez) i-soft PRO L Gerätetyp 0x4c (76 dez)


### Bedienung

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Regeneration starten | 35 | 1 | Start = 00 | /api/rest/350000 | 2 |
| Szene Sofortaktivierung | 36 |  | 1 byte szenennummer 1..9 + A<br>2 byte Dauer in HH:MM<br>'Dauer: 000F, 001E, 002D, 0100, 0200,0600,0C00, FFFF - unendlich | /api/rest/36000200200 Szene2 für 2:00 Stunden aktivieren<br>Szene 0: Alltag meistern<br>Szene 1: Körper pflegen<br>Szene 2: Garten Bewässern<br>Szene 3: Urlaub geniessen<br>Szene 4: Wäsche waschen<br>Szene 5: Hochdruckreinigen<br>Szene 6: Pool befüllen<br>Szene 7: Heizung befüllen<br>Szene 8: Custom Szene 1<br>Szene 9: Custom Szene 2<br>Szene A: Custom Szene 3 | 2 |
| Szene einstellen / editieren | 37 |  | 1 byte Szenennummer 1..10<br>1 byte Wasserhärte in °dH<br>1 byte Wasserhärte in °f, mmol*10, ppm/10<br>1 byte Leckageschutz (0 = deaktiviert, 1 = aktiv)<br>1 byte Leckageschutz Entnahmemenge (0 = deaktiviert, 1 = aktiv)<br>1 byte Leckageschutz Durchflussmenge (0 = deaktiviert, 1 = aktiv)<br>1 byte Leckageschutz Entnahmezeit (0 = deaktiviert, 1 = aktiv)<br>1 byte Favoritenauswahl (0 = deaktiviert, 1 = aktiv)<br>1 byte Zeitsteuerung an/aus<br>Für normale Szene: {<br>1 byte akPve Tage ( je Tag Sa..So 1 bit 1,2,4,8,16,32,64)<br>2 byte Startzeit in HH:MM<br>2 byte Endzeite in HH:MM<br>}<br>Für Szene "Urlaub genießen": {<br>2 byte Startdatum Jahr<br>1 byte Startdatum Monat<br>1 byte Startdatum Tag<br>2 byte Stopdatum Jahr<br>1 byte Stopdatum Monat<br>1 byte Stopdatum Tag<br>}<br>oder<br>1 Byte Szenennummer: liefert aktuelle Einstellung der Szene wie oben<br>Kodiert zurück | Beispiel reguläre Szene:<br>/api/rest/370001060B01010001010107080F0E1E<br>Szene 1 auf 6°dH, Leckageschutz an für Entnahmemenge und -<br>zeit, als Favorit anzeigen und am Mo,Di und Mi von 8:15 bis<br>14:30 aktivieren.<br>Es können nur bestehende Szenen eingestellt werden. Es ist<br>nicht möglich, neue Szenen zu erstellen! Dies muss einmalig am<br>Gerät durchgeführt werden.<br>Beispiel Urlaubsmodus:<br>/api/rest/37000308010001000101E8070601E8070704<br>Szene Urlaubsmodus auf 8°dH, Leckageschutz für<br>Volumenstrombegrenzung an, als Favorit markieren, Start am<br>1.6.2024 bis 4.7.2024 | 2 |
| Szene zurücksetzen | 38 |  | 1 byte szenennummer 1..10 auf Grundeinstellung setzen | /api/rest/380001 Szene 1 zurücksetzen | 2 |

### Betriebsdaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Gesamtwassermenge lesen | 28 | 4 | Wassermenge in liter lsb first | /api/rest/2800<br>data=EC221000 1057,516 m³ | 3 |
| Weichwassermenge lesen | 29 | 4 | Weichwassermenge in liter lsb first | /api/rest/2900<br>data=2EDC0000 56,366 m³ | 3 |

### Betriebsstatus

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Wunschwasserhärte lesen | 51 | 2 | 2 byte Antwort Wunschwasserhärte | /api/rest/5100 data="0600" 6°dH | 2 |

### Einstellungen

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Härteeinheit lesen | 23 | 1 | 0 °dH , 2 °fH | data=00 Einheit °dH | 2 |
| Härteeinheit schreiben | 24 | 1 | 0 °dH , 2 °fH | /api/rest/240001 Einheit °dH | 2 |
| Wunschwasserhärte schreiben | 30 | 1/ 2 | 1 byte: Härte in °dH wird in Geräteeinheit umgerechnet | /api/rest/300007 7°dH | 2 |
| Leckageschutz schliessen | 3C | 0 |  | /api/rest/3C00 | 2 |
| Leckageschutz öffnen | 3D | 0 |  | /api/rest/3D00 | 2 |
| Max. Entnahmdauer schreiben | 3E | 1 | max. Entnahmezeit in Minuten 1-255 Minuten, 0 deaktiviert<br>überwachung<br>ohne Data liefert aktuellen Wert des Gerätes zurück | /api/rest/3E0028 Entnahmedauer max. 40min | 2 |
| Max. Entnahmemenge schreiben | 3F | 2 | max. Wassermenge in Liter 1- 3000 l, 0 deaktiviert überwachung<br>ohne Data liefert aktuellen Wert des Gerätes zurück | /api/rest/3F00C409 2500ltr | 2 |
| Max. Volumenstrom schreiben | 40 | 2 | max. Durchfluss am Stück in Liter/Stunde 1- 5000 l/h, 0 deaktiviert<br>überwachung<br>ohne Data liefert aktuellen Wert des Gerätes zurück | /api/rest/4000F401 500ltr/h | 2 |
| Urlaubsmodus schreiben | 41 | 0/1 | Start Urlaubsmodus<br>1 byte:<br>Bit 0 = 1 Urlaubsmodus aktiv<br>Bit 1 = unused<br>Bit 2 = unused<br>Bit 3 = unused<br>Bit 4 = unused<br>Bit 5 = 1 Mikroleckage (0 = Nur Melden , 1 = Melden und schliessen)<br>Bit 6 = 1 Automatischer Mikroleckagetest (1= Aktiv)<br>Bit 7 = 1 Leckagealarm/schutz global AUS (1=AUS)<br>1 byte:<br>Urlaubsdauer in Tagen | /api/rest/41000105 Urlaubsmodus aktivieren 5Tage | 2 |
| Salzvorrat lesen oder schreiben | 56 | 2 | ohne Data:<br>4 byte antwort:<br>2byte Salzgewicht<br>2byte Salzreichweite in Tagen | /api/rest/5600<br>data=f6541100 f654 = 21750g, 1100 = 17 Tage | 2 |
| Salzreichweitenmangelwarnung lesen und<br>schreiben | 57 |  | Ohne Data:<br>Salzreichweitenmangelwarnung in Tagen<br>Mit Data:<br>1 byte: Setzt Reichweitenmangelwarnung auf x Tage | /api/rest/570014 Setzt Reichweitenmangel auf 20 Tage | 2 |

### Infodaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| SW-Version Gerätesteuerung lesen | 1 | 3 | 3 byte SW-Version | /api/rest/0100<br>data=0C0001 entspricht 1.0.12 | 2 |
| Betriebsstundenzähler | 25 | 4 | 4 byte Betriebsstunden<br>1 byte Minuten<br>1 byte Stunden<br>2 byte Tage | data=060c7500 117Tage, 12h, 6 min. | 2 |
| Kundendienst/Serviceadresse | 58 | 16 | Servicetelefonnummer ASCII, ohne datenbytes = lesen, 16 bytes data<br>schreiben. | data=2b343920373139352036393235313720<br>ASCII umsetzung: +49 7195 692517 | 2 |
| Gerätenummer lesen | 6 | 4 | 4 byte Gerätenummer | /api/rest/0600<br>data=10D36F28 entspricht 282292008 | 2 |
| Inbetriebnahmedatum lesen | E | 4 | 4 byte<br>1 byte Tag<br>1 byte Monat<br>2 byte Jahr |  | 2 |
| Gerätetyp lesen | FF | 1 | 1 byte Gerätetyp | /api/rest/FF00<br>data="58" | 2 |

### Salzverbrauchsstatistik

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | F3 | 4 | Es werden die Gesamttageswerte für den angefragten Tag<br>zurückgeliefert, sofern Daten vorhanden je 4 byte:<br>1 Byte Stunde, 3 byte Menge<br>z.B.:<br>"data":<br>"0100000002000000030000000400000005000000060000000700000017<br>000000"<br>Stundenwerte für Stunde 01, 02,03,04,05,06,07 und 23 | /api/rest/F3001306E807<br>Tagesdaten vom 19.6.2024 | 3 |
| Wochenstatistik | F4 | 3 | Es werden alle Gesamtwerte der Tage der angefragten Woche<br>zurückgeliefert, sofern Daten vorhanden je 4 byte:<br>1Byte Wochentag (00-Montag), 3 Byte Menge<br>z.B.:<br>"data": "000000000200000004000000"<br>Tageswerte der Woche für Montag, Mittwoch und Freitag | /api/rest/F40019E807<br>Wochendaten aus KW25 2024 | 3 |
| Monatsstatistik | F5 | 3 | Es werden Tageswerte des angefragten Montats zurück geliefert,<br>sofern Daten vorhanden immer 4 byte:<br>1 byte Tag, 3 bytes Menge<br>z.B.<br>"data": "03000000060000000B000000110000001300000015000000"<br>für Tageswerte von Tag 3, 6, 11, 17, 19 und 21 | /api/rest/F50006E807<br>Monatsdaten aus Juni 2024 | 3 |
| Jahresstatistik | F6 | 2 | Es wird die Gesamtsumme des Verbrauchs jedes Monats des<br>angefragen Jahres zurück geliefert, sofern Daten vorhanden<br>immer 4 byte:<br>1 byte Monat, 3 bytes Menge<br>z.B. "data": "0400000006000000" für Monat April und Juni | /api/rest/F600E807<br>Jahresdaten aus 2024 | 3 |

### Volumenstromstatistik

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | F7 | 4 | Es werden die Gesamttageswerte für den angefragten Tag<br>zurückgeliefert, sofern Daten vorhanden je 4 byte:<br>1 byte Stunde, 3 Byte Daten<br>"data":<br>"0000067201000000020000000300000004000672050006A406000000"<br>00:00 672 - 1650ltr/h<br>01:00 0<br>02:00 0<br>03:00 0<br>04:00 672 - 1650ltr/h<br>05:00 6A4 - 1700 ltr/h<br>06:00 0 | /api/rest/F7001506E807<br>Tagesdaten vom 21.06.2024 | 3 |
| Wochenstatistik | F8 | 3 | Es werden alle Gesamtwerte der Tage der angefragten Woche<br>zurückgeliefert, sofern Daten vorhanden je 4 byte:<br>1 byte Tag (Mo=00), 3 byte Menge<br>"data": "0000000002000000040006A4"<br>Montag 0, Mittwoch 0, Freitag 6A4 - 1700Ltr/h | /api/rest/F80019E807<br>Wochendaten aus KW25 2024 | 3 |
| Monatsstatistik | F9 | 3 | Es werden alle Tage des angefragten Montats zurück geliefert<br>sofoern Daten vorhanden, max 31 Tage je 4 byte:<br>1 byte Monat, 3 Byte Menge<br>"data": "03000000060000000B0000001100000013000000150006A4"<br>Tageswerte für Tag 3,6,11,17,19 und 21 | /api/rest/F90006E807<br>Monatsdaten aus Juni 2024 | 3 |
| Jahresstatistik | FA | 2 | Es wird die Gesamtsumme des Verbrauchs des angefragen Jahres zurück<br>geliefert sofern Daten vorhanden je 4 byte:<br>1 byte Monat, 3 bytes Menge<br>z.B.:<br>"data": "04008CA0060006A4"<br>Monat April 8CA = 2250 liter/h, Juni 19= 1700liter/h | /api/rest/FA00E807<br>Jahresdaten aus 2024 | 3 |

### Wasserstatistik

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | FB | 4 | Es werden die Gesamttageswerte für den angefragten Tag<br>zurückgeliefert, sofern Daten vorhanden je 4 byte:<br>1 byte Stunde, 3 byte Menge<br>z.B.<br>"data":<br>"000000050100000002000000030000000400000A0500000F06000000"<br>00:00 5liter<br>01:00 0<br>02:00 0<br>03:00 0<br>04:00 10liter<br>05:00 15liter<br>06:00 0 Liter | /api/rest/FB001506E807<br>Tagesdaten vom 21.06.2024 | 3 |
| Wochenstatistik | FC | 3 | Es werden die Gesamtwerte der Tage der angefragten Woche<br>zurückgeliefert, sofern Daten vorhanden je 4 byte:<br>1 byte Tag (Mo=00), 3 byte Werte<br>z.B.:<br>"data": "000000000200000004000019"<br>Montag 0, Mittwoch 0, Freitag 19hex = 25liter | /api/rest/FC0019E807<br>Wochendaten aus KW25 2024 | 3 |
| Monatsstatistik | FD | 3 | Es werden die Tageswerte des angefragten Montats zurück geliefert<br>sofoern Daten vorhanden, max 31 Tage je 4 byte:<br>1 byte Tag, 3 bytes Menge<br>z.B.:<br>"data": "03000000060000000B000000110000001300000015000019"<br>Tage 3,6,11,15 = 0, Tag 21 19hex = 25liter | /api/rest/FD0006E807<br>Monatsdaten aus Juni 2024 | 3 |
| Jahresstatistik | FE | 2 | Es wird die Gesamtsumme des Verbrauchs des angefragen Jahres zurück<br>geliefert, sofern Daten vorhanden je 4 byte:<br>1 byte Monat, 3 bytes Menge<br>z.B.:<br>"data": "040000AA06000019"<br>Monat April AA = 170liter, Juni 19= 25liter | /api/rest/FE00E807<br>Jahresdaten aus 2024 | 3 |

## Enthärter i-soft SAFE+ Gerätetyp 0x33 (51 dez) und Gerätetyp 0x57 (87 dez) mit Leckageschutz i-soft K SAFE+ Gerätetyp 0x42 (66 dez) und Gerätetyp 0x67 (103 dez)


### Bedienung

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Regeneration starten | 35 | 1 | Start = 00 | /api/rest/350000 | 1 |

### Betriebsdaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Gesamtwassermenge lesen | 28 | 4 | Wassermenge in liter lsb first | /api/rest/2800<br>data=EC221000 1057,516 m³ | 1 |
| Weichwassermenge lesen | 29 | 4 | Weichwassermenge in liter lsb first | /api/rest/2900<br>data=2EDC0000 56,366 m³ | 1 |

### Betriebsstatus

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Wunschwasserhärte lesen | 51 | 2 | 2 byte Antwort Wunschwasserhärte | /api/rest/5100 data="0600" 6°dH | 1 |

### Einstellungen

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Härteeinheit lesen | 23 | 1 | 0 °dH , 1 °eH , 2 °fH , 3 gpg , 4 ppm , 5 mmol , 6 mval | data=00 Einheit °dH | 1 |
| Härteeinheit schreiben | 24 | 1 | 0 °dH , 1 °eH , 2 °fH , 3 gpg , 4 ppm , 5 mmol , 6 mval | /api/rest/240004 Einheit ppm | 1 |
| Wunschwasserhärte schreiben | 30 | 1/ 2 | 1 byte: Härte in °dH wird in Geräteeinheit umgerechnet ODER<br>2 byte: Härte in Geräteeinheit ohne Komma (also 17,8 --> 178) | /api/rest/300007 7°dH<br>/api/rest/30000A00 10°dH | 1 |
| Leckageschutz schliessen | 3C | 0 |  | /api/rest/3C00 | 1 |
| Leckageschutz öffnen | 3D | 0 |  | /api/rest/3D00 | 1 |
| Max. Entnahmdauer schreiben | 3E | 1 | max. Entnahmezeit in Minuten 1-255 Minuten, 0 deaktiviert<br>überwachung | /api/rest/3E0028 Entnahmedauer max. 40min | 1 |
| Max. Entnahmemenge schreiben | 3F | 2 | max. Durchfluss in Liter/Stunde 1- 65535 l/h, 0 deaktiviert<br>überwachung | /api/rest/3F00C409 2500ltr/h | 1 |
| Max. Volumenstrom schreiben | 40 | 2 | max. Wassermenge am Stück in Liter 1- 65535 l , 0 deaktiviert<br>überwachung | /api/rest/4000F401 500ltr | 1 |
| Urlaubsmodus schreiben | 41 | 0/1 | Start Urlaubsmodus<br>1 byte:<br>Bit 0 = 1 Urlaubsmodus aktiv<br>Bit 1 = 1 U1<br>Bit 2 = 1 U2<br>Bit 3 = 1 U3<br>Bit 4 = unused<br>Bit 5 = 1 Mikroleckage (0 = Nur Melden , 1 = Melden und schliessen)<br>Bit 6 = 1 Automatischer Mikroleckagetest (1= Aktiv)<br>Bit 7 = 1 Leckagealarm/schutz global AUS (1=AUS) | /api/rest/410003 U1 aktivieren | 1 |
| Salzvorrat lesen oder schreiben | 56 | 2 | ohne Data:<br>4 byte antwort:<br>2byte Salzgewicht<br>2byte Salzreichweite in Tagen<br>mit 2 byte Data:<br>absolutes Salzgewicht in gramm | /api/rest/5600<br>data=f6541100 f654 = 21750g, 1100 = 17 Tage<br>schreiben:<br>/api/rest/56004448 = 18500g | 1 |
| Salzreichweitenmangelwarnung lesen und<br>schreiben | 57 |  | Ohne Data:<br>Salzreichweitenmangelwarnung in Tagen<br>Mit Data:<br>1 byte: Setzt Reichweitenmangelwarnung auf x Tage | /api/rest/570014 Setzt Reichweitenmangel auf 20 Tage | 1 |

### Infodaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| SW-Version Gerätesteuerung lesen | 1 | 3 | 3 byte SW-Version | /api/rest/0100<br>data=6b1502 entspricht 2.21k | 1 |
| Betriebsstundenzähler | 25 | 4 | 4 byte Betriebsstunden<br>1 byte Minuten<br>1 byte Stunden<br>2 byte Tage | data=060c7500 117Tage, 12h, 6 min. | 1 |
| Kundendienst/Serviceadresse | 58 | 16 | Servicetelefonnummer ASCII, ohne datenbytes = lesen, 16 bytes data<br>schreiben. | data=2b343920373139352036393235313720<br>ASCII umsetzung: +49 7195 692517 | 1 |
| Gerätenummer lesen | 6 | 4 | 4 byte Gerätenummer | /api/rest/0600<br>data=64d90100 entspricht 121188 | 1 |
| Inbetriebnahmedatum lesen | E | 4 |  |  | 1 |
| Gerätetyp lesen | FF | 1 | 1 byte Gerätetyp | /api/rest/FF00<br>data="33" | 1 |

### Wasserstatistik

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | FB | 4 | 32 byte:Es werden die Gesamttageswerte für den angefragten Tag<br>zurückgeliefert:<br>1-4 Byte: 0:00<br>5-8 Byte: 3:00<br>9-12 Byte: 6:00<br>13-16 Byte: 9:00<br>17-20 Byte: 12:00<br>21-24 Byte: 15:00<br>25-28 Byte: 18:00<br>29-32 Byte: 21:00 | /api/rest/FB000D0807E7<br>Tagesdaten vom 13.08.2023 | 1 |
| Wochenstatistik | FC | 3 | 28 byte:<br>Es werden alle Gesamtwerte der Tage der angefragten Woche<br>zurückgeliefert:<br>1-4 Byte: Montag<br>5-8 Byte: Dienstag<br>9-12 Byte: Mittwoch<br>13-16 Byte: Donnerstag<br>17-20 Byte: Freitag<br>21-24 Byte: Samstag<br>25-28 Byte: Sonntag | /api/rest/FC002007E7<br>Wochendaten aus KW32 2023 | 1 |
| Monatsstatistik | FD | 3 | 124 byte:<br>Es werden alle Tage des angefragten Montats zurück geliefert max 31<br>Tage<br>Byte 1-4: Tag1<br>Byte 5-8: Tag2<br>…..<br>Byte 121-124: Tag 31 | /api/rest/FD000807E7<br>Monatsdaten aus August 2023 | 1 |
| Jahresstatistik | FE | 2 | 48 byte:<br>Es wird die Gesamtsumme des Verbrauchs jedes Monats des<br>angefragen Jahres zurück geliefert<br>1-4 Byte: Januar<br>5-8 Byte: Februar<br>9-12 Byte: März<br>13-16 Byte: April<br>17-20 Byte: Mai<br>21-24 Byte: Juni<br>25-28 Byte: Juli<br>29-32 Byte: August<br>33-36 Byte: September<br>37-40 Byte: Oktober<br>41-44 Byte: November<br>45-48 Byte: Dezember | /api/rest/FE0007E7<br>Jahresdaten aus 2023 | 1 |

## Heizungsbefüllung i-fill 60 Gerätetyp 0x3C


### Bedienung

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Leckageschutz schliessen | 51 |  |  | /api/rest/5100 | 10 |
| Leckageschutz öffnen | 52 |  |  | /api/rest/5200 | 10 |
| Störmelderelais EIN/AUS | 54 | 1 byte | 1 byte Störmelderelais ein/aus<br>0-automatikbetrieb<br>128-manuell aus<br>129-manuell ein | /api/rest/5400F0 Störmelderelais manuell einschalten | 10 |

### Betriebsdaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Gesamtwassermenge lesen | 28 | 4 | Wassermenge in liter |  | 10 |

### Betriebsstatus

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Grenzwertdaten abfragen | 42 | (22 bytes<br>response) | 22 byte antwort:<br>1 byte Sprache: 0-DE, 1-EN, 2-FR, 3-NL, 4-IT<br>1 byte Einheit: 0-°dH, 1-°e, 2-°fH, 3-gpg, 4-ppm, 5-mmol, 6-mval/l<br>1 byte Korrektur Rohwasserhärte<br>1 byte Patronentyp siehe rechts<br>1 byte unused<br>1 byte Max. Anzahl Füllzyklen<br>1 byte Max. Fülldruck *10<br>1 byte Hysteres Fülldruck *10<br>2 byte Rohwasserhärte<br>2 byte Max Füllzeit in minuten<br>2 byte Max Füllmenge in Liter<br>2 byte Heizungsinhalt<br>2 byte max. Leitwert<br>4 byte Patronenkapazität | data=00000000000514011400050014000500c80064004c1d0000<br>00 - DE<br>00 - °dH<br>00<br>00 - PURE7500<br>00<br>51<br>40<br>11<br>0040<br>0105<br>0040<br>0C50<br>0680<br>00001D4C | 10 |
| Modus Füllventil einstellen | 53 | 1 byte | 1 byte Modus Füllventil:<br>0-automatik<br>1-manuell öffnen<br>2-manuell schliessen | /api/rest/530001 Füllventil manuell öffnen | 10 |

### Einstellungen

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Grenzwerte einstellen | 50 | 22 byte | 22 byte:<br>1 byte Sprache: 0-DE, 1-EN, 2-FR, 3-NL, 4-IT<br>1 byte Einheit: 0-°dH, 1-°e, 2-°fH, 3-gpg, 4-ppm, 5-mmol, 6-mval/l<br>1 byte Korrektur Rohwasserhärte<br>1 byte Patronentyp siehe rechts<br>1 byte unused<br>1 byte Max. Anzahl Füllzyklen<br>1 byte Max. Fülldruck *10<br>1 byte Hysteres Fülldruck *10<br>2 byte Rohwasserhärte<br>2 byte Max Füllzeit in minuten<br>2 byte Max Füllmenge in Liter<br>2 byte Heizungsinhalt<br>2 byte max. Leitwert<br>4 byte Patronenkapazität | /api/rest/500000000000000514011400050014000500c80064004<br>c1d0000<br>Patronentypen:<br>0 - PURE 7500<br>1 - PURE 25000<br>2- SOFT 12000<br>3 - SOFT 60000<br>4 - PURE frei<br>5 - SOFT frei<br>10 - JP17<br>11 - JP26<br>12 - JP46<br>13 - JP100 | 10 |

### Infodaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| SW-Version Gerätesteuerung lesen | 1 | 3 | 3 byte SW-Version | /api/rest/0100<br>data=661301 entspricht 1.19f | 10 |
| Gerätenummer lesen | 6 | 4 | 4 byte Gerätenummer | /api/rest/0600<br>data=0774ed0b entspricht 200111111 | 10 |
| Inbetriebnahmedatum lesen | E | 4 |  |  | 10 |
| Gerätetyp lesen | FF | 1 | 1 byte Gerätetyp | /api/rest/FF00<br>data="3C" | 10 |

### Wasserverbrauch

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | FB | 4 | 32 byte:Es werden die Gesamttageswerte für den angefragten Tag<br>zurückgeliefert:<br>1-4 Byte: 0:00<br>5-8 Byte: 3:00<br>9-12 Byte: 6:00<br>13-16 Byte: 9:00<br>17-20 Byte: 12:00<br>21-24 Byte: 15:00<br>25-28 Byte: 18:00<br>29-32 Byte: 21:00 | /api/rest/FB000D0807E7<br>Tagesdaten vom 13.08.2023 | 10 |
| Wochenstatistik | FC | 3 | 28 byte:<br>Es werden alle Gesamtwerte der Tage der angefragten Woche<br>zurückgeliefert:<br>1-4 Byte: Montag<br>5-8 Byte: Dienstag<br>9-12 Byte: Mittwoch<br>13-16 Byte: Donnerstag<br>17-20 Byte: Freitag<br>21-24 Byte: Samstag<br>25-28 Byte: Sonntag | /api/rest/FC002007E7<br>Wochendaten aus KW32 2023 | 10 |
| Monatsstatistik | FD | 3 | 124 byte:<br>Es werden alle Tage des angefragten Montats zurück geliefert max 31<br>Tage<br>Byte 1-4: Tag1<br>Byte 5-8: Tag2<br>…..<br>Byte 121-124: Tag 31 | /api/rest/FD000807E7<br>Monatsdaten aus August 2023 | 10 |
| Jahresstatistik | FE | 2 | 48 byte:<br>Es wird die Gesamtsumme des Verbrauchs jedes Monats des<br>angefragen Jahres zurück geliefert<br>1-4 Byte: Januar<br>5-8 Byte: Februar<br>9-12 Byte: März<br>13-16 Byte: April<br>17-20 Byte: Mai<br>21-24 Byte: Juni<br>25-28 Byte: Juli<br>29-32 Byte: August<br>33-36 Byte: September<br>37-40 Byte: Oktober<br>41-44 Byte: November<br>45-48 Byte: Dezember | /api/rest/FE0007E7<br>Jahresdaten aus 2023 | 10 |

## Leckageschutz + Filter ZEWA i-SAFE FILT Gerätetyp 0x44 PROM-i-SAFE Gerätetyp 0x44


### Bedienung

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Leckageschutz schließen | 51 | 0 |  | /api/rest/5100 | 7 |
| Leckageschutz öffnen | 52 | 0 |  | /api/rest/5200 | 7 |
| Sleepmodus starten | 54 | 0 |  | /api/rest/5400 | 7 |
| Sleepmodus beenden | 55 | 0 |  | /api/rest/5500 | 7 |
| Urlaubsmodus starten | 57 | 0 |  | /api/rest/5700 | 7 |
| Urlaubsmodus beenden | 58 | 0 |  | /api/rest/5800 | 7 |
| Mikroleckageprüfung starten | 5C | 0 |  | /api/rest/5C00 | 7 |
| Lernmodus starten | 5D | 0 |  | /api/rest/5D00 | 7 |
| Abwesenheitslimits lesen | 5E | 6 | je 2 byte: Grenzwert Durchfluss in l/h<br>Grenzwert Wassermenge in l<br>Grenzwert Entnahmezeit in min | /api/rest/5E00<br>data=640005000500 100, 5, 5 | 7 |

### Betriebsdaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Gesamtwassermenge lesen | 28 | 4 | Wassermenge in liter |  | 7 |

### Betriebsstatus

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Meldung zurücksetzen | 63 | 0 |  | /api/rest/6300 | 7 |

### Einstellungen

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Leckageeinstellungen schreiben | 50 | 7 | Byte 1: Urlaubsmodus, 0 = aus, 1 = U1, 2 = U2, 3 = U3<br>Byte 2+3: Max. Volumenstrom, Einheit Liter/ Stunde<br>Byte 4+5, Max. Entnahmemenge; ganzzahlig, Einheit: Liter<br>Byte 6+7, Max. Entnahmedauer, ganzzahlig, Einheit: Minute | /api/rest/500002D007FA000A00 U2,<br>2000ltr/h, 250ltr, 10min | 7 |
| Sleepmodusdauer schreiben | 53 | 1 | 1, 2, 3 … 10 (ganzzahlig), Einheit Stunde | /api/rest/530008 8h Sleepmodus,<br>Achtung: Starten des Sleepmodus mit<br>Kommando 54 | 7 |
| Urlaubsmodus typ schreiben | 56 | 1 | Url Modus byte 0-Aus, 1-U1, 2-U2, 3-U3 |  | 7 |
| Datum und Uhrzeit lesen | 59 | 6 | Je ein Byte: Tag, Monat, Jahr, Stunde, Minute, Sekunde | data=1c04170e041e 28.4.23, | 7 |
| Datum und Uhrzeit schreiben | 5A | 6 | Je ein Byte: Tag, Monat, Jahr, Stunde, Minute, Sekunde | 14:04:30 | 7 |
| Mikroleckage Einstellen | 5B | 1 | 0 - keine Aut. Prüfung, 1 - mit Meldung, 2 - mit Meldung und<br>Schliessen | /api/rest/5B0001 Prüfung nur mit<br>Meldung | 7 |
| Abwesenheitslimits schreiben | 5F | 6 | je 2 byte: Grenzwert Durchfluss in l/h<br>Grenzwert Wassermenge in l<br>Grenzwert Entnahmezeit in min | /api/rest/5F009C04F4010A00<br>2500l/h 500ltr 10min | 7 |
| Abwesenheitszeit lesen | 60 | 1/6 | Senden: 1 byte Abwesenheitszeitraum 0..6<br>Empfang: 1 byte Starttag (0..6 = So - Sa)<br>1 byte Startzeit h 0..23<br>1 byte Startzeit min 0..59<br>1 byte Stoptag (0..6 = So-Sa)<br>1 byte Stopzeit h 0..23<br>1 byte Stopzeit min (0..59) | data=020400030700 Di, 4:00 bis Mi<br>7:00 | 7 |
| Abwesenheitszeit schreiben | 61 | 7 | 1 byte Abwesenheitszeitraum 0..6<br>1 byte Starttag (0..6 = So - Sa)<br>1 byte Startzeit h 0..23<br>1 byte Startzeit min 0..59<br>1 byte Stoptag (0..6 = So-Sa)<br>1 byte Stopzeit h 0..23<br>1 byte Stopzeit min (0..59) | /api/rest/610003040200060800<br>Zeitraum 3 Do 02:00 bis Sa 08:00 | 7 |
| Abwesenheitszeit löschen | 62 | 1 | 1 byte Abwesenheitszeitraum 0..6 | Rücklesewert mit Kommando 60 ergibt<br>dann data = 000000000000 | 7 |
| Lernmodus status lesen | 64 |  | 1 byte Lernmodus aktiv: 0-deaktiviert 1-aktiviert<br>2 byte Rest-Lernwassermenge in l | /api/rest/6400 data=011027<br>Lernmodus aktiv, Restwasser 10m³ | 7 |
| Mikroleckageprüfung lesen | 65 |  | 0 - keine Aut. Prüfung, 1 - mit Meldung, 2 - mit Meldung und<br>Schliessen | /api/rest/6500 data=00 keine<br>auto. Prüfung | 7 |
| Sleepmodusdauer lesen | 66 | 1 | 1, 2, 3 … 10 (ganzzahlig), Einheit Stunde | /api/rest/6600 data="06"<br>6h Sleepmodus ist eingestellt | 7 |

### Infodaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| SW-Version Gerätesteuerung lesen | 1 | 3 | 3 byte SW-Version | /api/rest/0100<br>data=661301 entspricht 1.19f | 7 |
| Gerätenummer lesen | 6 | 4 | 4 byte Gerätenummer | /api/rest/0600<br>data=0774ed0b entspricht 200111111 | 7 |
| Inbetriebnahmedatum lesen | E | 4 |  | /api/rest/0E00<br>data=6414CB7B UNIX Timestamp:<br>1679084411dez = 17.3.2023 21:20<br>GMT+1 | 7 |
| Gerätetyp lesen | FF | 1 | 1 byte Gerätetyp | /api/rest/FF00<br>data="44" | 7 |

### Wasserverbrauch

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | FB | 4 | 32 byte:Es werden die Gesamttageswerte für den angefragten Tag<br>zurückgeliefert:<br>1-4 Byte: 0:00<br>5-8 Byte: 3:00<br>9-12 Byte: 6:00<br>13-16 Byte: 9:00<br>17-20 Byte: 12:00<br>21-24 Byte: 15:00<br>25-28 Byte: 18:00<br>29-32 Byte: 21:00 | /api/rest/FB000D0807E7<br>Tagesdaten vom 13.08.2023 | 7 |
| Wochenstatistik | FC | 3 | 28 byte:<br>Es werden alle Gesamtwerte der Tage der angefragten Woche<br>zurückgeliefert:<br>1-4 Byte: Montag<br>5-8 Byte: Dienstag<br>9-12 Byte: Mittwoch<br>13-16 Byte: Donnerstag<br>17-20 Byte: Freitag<br>21-24 Byte: Samstag<br>25-28 Byte: Sonntag | /api/rest/FC002007E7<br>Wochendaten aus KW32 2023 | 7 |
| Monatsstatistik | FD | 3 | 124 byte:<br>Es werden alle Tage des angefragten Montats zurück geliefert max<br>31 Tage<br>Byte 1-4: Tag1<br>Byte 5-8: Tag2<br>…..<br>Byte 121-124: Tag 31 | /api/rest/FD000807E7<br>Monatsdaten aus August 2023 | 7 |
| Jahresstatistik | FE | 2 | 48 byte:<br>Es wird die Gesamtsumme des Verbrauchs jedes Monats des<br>angefragen Jahres zurück geliefert<br>1-4 Byte: Januar<br>5-8 Byte: Februar<br>9-12 Byte: März<br>13-16 Byte: April<br>17-20 Byte: Mai<br>21-24 Byte: Juni<br>25-28 Byte: Juli<br>29-32 Byte: August<br>33-36 Byte: September<br>37-40 Byte: Oktober<br>41-44 Byte: November<br>45-48 Byte: Dezember | /api/rest/FE0007E7<br>Jahresdaten aus 2023 | 7 |

## Leckageschutzgerät ZEWA i-SAFE Gerätetyp 0x44


### Bedienung

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Leckageschutz schließen | 51 | 0 |  | /api/rest/5100 | 6 |
| Leckageschutz öffnen | 52 | 0 |  | /api/rest/5200 | 6 |
| Sleepmodus starten | 54 | 0 |  | /api/rest/5400 | 6 |
| Sleepmodus beenden | 55 | 0 |  | /api/rest/5500 | 6 |
| Urlaubsmodus starten | 57 | 0 |  | /api/rest/5700 | 6 |
| Urlaubsmodus beenden | 58 | 0 |  | /api/rest/5800 | 6 |
| Mikroleckageprüfung starten | 5C | 0 |  | /api/rest/5C00 | 6 |
| Lernmodus starten | 5D | 0 |  | /api/rest/5D00 | 6 |
| Abwesenheitslimits lesen | 5E | 6 | je 2 byte: Grenzwert Durchfluss in l/h<br>Grenzwert Wassermenge in l<br>Grenzwert Entnahmezeit in min | /api/rest/5E00<br>data=640005000500 100, 5, 5 | 6 |

### Betriebsdaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Gesamtwassermenge lesen | 28 | 4 | Wassermenge in liter |  | 6 |

### Betriebsstatus

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Meldung zurücksetzen | 63 | 0 |  | /api/rest/6300 | 6 |

### Einstellungen

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Leckageeinstellungen schreiben | 50 | 7 | Byte 1: Urlaubsmodus, 0 = aus, 1 = U1, 2 = U2, 3 = U3<br>Byte 2+3: Max. Volumenstrom, Einheit Liter/ Stunde<br>Byte 4+5, Max. Entnahmemenge; ganzzahlig, Einheit: Liter<br>Byte 6+7, Max. Entnahmedauer, ganzzahlig, Einheit: Minute | /api/rest/500002D007FA000A00 U2, 2000ltr/h, 250ltr, 10min | 6 |
| Sleepmodusdauer schreiben | 53 | 1 | 1, 2, 3 … 10 (ganzzahlig), Einheit Stunde | /api/rest/530008 8h Sleepmodus, Achtung: Starten des Sleepmodus mit 54 | 6 |
| Urlaubsmodus typ schreiben | 56 | 1 | Url Modus byte 0-Aus, 1-U1, 2-U2, 3-U3 |  | 6 |
| Datum und Uhrzeit lesen | 59 | 6 | Je ein Byte: Tag, Monat, Jahr, Stunde, Minute, Sekunde | data=1c04170e041e 28.4.23, 14:04:30 | 6 |
| Datum und Uhrzeit schreiben | 5A | 6 | Je ein Byte: Tag, Monat, Jahr, Stunde, Minute, Sekunde |  | 6 |
| Mikroleckage Einstellen | 5B | 1 | 0 - keine Aut. Prüfung, 1 - mit Meldung, 2 - mit Meldung und Schliessen | /api/rest/5B0001 Prüfung nur mit Meldung | 6 |
| Abwesenheitslimits schreiben | 5F | 6 | je 2 byte: Grenzwert Durchfluss in l/h<br>Grenzwert Wassermenge in l<br>Grenzwert Entnahmezeit in min | /api/rest/5F009C04F4010A00 2500l/h 500ltr 10min | 6 |
| Abwesenheitszeit lesen | 60 | 1/6 | Senden: 1 byte Abwesenheitszeitraum 0..6<br>Empfang: 1 byte Starttag (0..6 = So - Sa)<br>1 byte Startzeit h 0..23<br>1 byte Startzeit min 0..59<br>1 byte Stoptag (0..6 = So-Sa)<br>1 byte Stopzeit h 0..23<br>1 byte Stopzeit min (0..59) | data=020400030700 Di, 4:00 bis Mi 7:00 | 6 |
| Abwesenheitszeit schreiben | 61 | 7 | 1 byte Abwesenheitszeitraum 0..6<br>1 byte Starttag (0..6 = So - Sa)<br>1 byte Startzeit h 0..23<br>1 byte Startzeit min 0..59<br>1 byte Stoptag (0..6 = So-Sa)<br>1 byte Stopzeit h 0..23<br>1 byte Stopzeit min (0..59) | /api/rest/610003040200060800 Zeitraum 3 Do 02:00 bis Sa 08:00 | 6 |
| Abwesenheitszeit löschen | 62 | 1 | 1 byte Abwesenheitszeitraum 0..6 | Rücklesewert mit Kommando 60 ergibt dann data = 000000000000 | 6 |
| Lernmodus status lesen | 64 |  | 1 byte Lernmodus aktiv: 0-deaktiviert 1-aktiviert<br>2 byte Rest-Lernwassermenge in l | /api/rest/6400 data=011027 Lernmodus aktiv, Restwasser 10m³ | 6 |
| Mikroleckageprüfung lesen | 65 |  | 0 - keine Aut. Prüfung, 1 - mit Meldung, 2 - mit Meldung und Schliessen | /api/rest/6500 data=00 keine auto. Prüfung | 6 |
| Sleepmodusdauer lesen | 66 | 1 | 1, 2, 3 … 10 (ganzzahlig), Einheit Stunde | /api/rest/6600 data = "06" | 6 |

### Infodaten

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| SW-Version Gerätesteuerung lesen | 1 | 3 | 3 byte SW-Version | /api/rest/0100<br>data=661301 entspricht 1.19f | 6 |
| Gerätenummer lesen | 6 | 4 | 4 byte Gerätenummer | /api/rest/0600<br>data=0774ed0b entspricht 200111111 | 6 |
| Inbetriebnahmedatum lesen | E | 4 |  | /api/rest/0E00<br>data=6414CB7B UNIX Timestamp:<br>1679084411dez = 17.3.2023 21:20 GMT+1 | 6 |
| Gerätetyp lesen | FF | 1 | 1 byte Gerätetyp | /api/rest/FF00<br>data="44" | 6 |

### Wasserstatistik

| Parameter | Kommando (hex) | Länge (byte) | Anmerkungen | Beispielkommando | Page |
| --- | --- | --- | --- | --- | --- |
| Tagesstatistik | FB | 4 | 32 byte:Es werden die Gesamttageswerte für den angefragten Tag<br>zurückgeliefert:<br>1-4 Byte: 0:00<br>5-8 Byte: 3:00<br>9-12 Byte: 6:00<br>13-16 Byte: 9:00<br>17-20 Byte: 12:00<br>21-24 Byte: 15:00<br>25-28 Byte: 18:00<br>29-32 Byte: 21:00 | /api/rest/FB000D0807E7<br>Tagesdaten vom 13.08.2023 | 6 |
| Wochenstatistik | FC | 3 | 28 byte:<br>Es werden alle Gesamtwerte der Tage der angefragten Woche zurückgeliefert:<br>1-4 Byte: Montag<br>5-8 Byte: Dienstag<br>9-12 Byte: Mittwoch<br>13-16 Byte: Donnerstag<br>17-20 Byte: Freitag<br>21-24 Byte: Samstag<br>25-28 Byte: Sonntag | /api/rest/FC002007E7<br>Wochendaten aus KW32 2023 | 6 |
| Monatsstatistik | FD | 3 | 124 byte:<br>Es werden alle Tage des angefragten Montats zurück geliefert max 31 Tage<br>Byte 1-4: Tag1<br>Byte 5-8: Tag2<br>…..<br>Byte 121-124: Tag 31 | /api/rest/FD000807E7<br>Monatsdaten aus August 2023 | 6 |
| Jahresstatistik | FE | 2 | 48 byte:<br>Es wird die Gesamtsumme des Verbrauchs jedes Monats des angefragen<br>Jahres zurück geliefert<br>1-4 Byte: Januar<br>5-8 Byte: Februar<br>9-12 Byte: März<br>13-16 Byte: April<br>17-20 Byte: Mai<br>21-24 Byte: Juni<br>25-28 Byte: Juli<br>29-32 Byte: August<br>33-36 Byte: September<br>37-40 Byte: Oktober<br>41-44 Byte: November<br>45-48 Byte: Dezember | /api/rest/FE0007E7<br>Jahresdaten aus 2023 | 6 |