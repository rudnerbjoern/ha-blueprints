# Smart Ventilation

Smart Ventilation ist ein modulares Home-Assistant-Projekt für raumbezogene
Lüftungsempfehlungen. Es vergleicht das Innen- und Außenklima und bewertet, ob
das Öffnen der Fenster aktuell sinnvoll ist.

Die Logik funktioniert ganzjährig und benötigt keinen festen Sommer- oder
Wintermodus.

## Komponenten

Das System besteht derzeit aus zwei Template-Blueprints:

- `smart_ventilation_sensor.yaml` bewertet einen einzelnen Raum.
- `smart_ventilation_floor.yaml` fasst mehrere Raumempfehlungen zu einer
  Etagenempfehlung zusammen.

Die Benutzeroberfläche wird separat als
[Smart Ventilation Card](https://github.com/rudnerbjoern/smart-ventilation-card)
entwickelt. Dieses Repository stellt die Sensor-API bereit; Installation,
Quellcode und Releases der Karte befinden sich im Card-Repository.

## Benötigte Sensoren

Für jeden Raum werden benötigt:

- Innentemperatur
- absolute Luftfeuchtigkeit beziehungsweise Wasserdampfkonzentration innen
- Außentemperatur
- absolute Luftfeuchtigkeit beziehungsweise Wasserdampfkonzentration außen

Optional kann die relative Luftfeuchtigkeit des Raums angegeben werden. Sie
ermöglicht einen genaueren Schutz vor zu trockener Raumluft.

Die Außensensoren können von allen Räumen gemeinsam verwendet werden:

```text
Außentemperatur ───────────────────┐
absolute Außenfeuchtigkeit ────────┤
                                   │
Wohnzimmer-Sensoren ───────────────┼─ Raumempfehlung
Schlafzimmer-Sensoren ─────────────┼─ Raumempfehlung
Bad-Sensoren ──────────────────────┼─ Raumempfehlung
Arbeitszimmer-Sensoren ────────────┘
```

## Zustände des Raumsensors

Die Zustände sind absichtlich sprachunabhängig, damit Dashboards und
Automationen unabhängig von der Home-Assistant-Sprache funktionieren.

| Zustand       | Bedeutung                                                   |
| ------------- | ----------------------------------------------------------- |
| `ventilate`   | Lüften wird empfohlen                                       |
| `conditional` | Lüften kann sinnvoll sein, die Bedingungen sind nicht ideal |
| `keep_closed` | Fenster sollten geschlossen bleiben                         |
| `neutral`     | Kein wesentlicher Vor- oder Nachteil                         |
| `unavailable` | Mindestens ein benötigter Sensor ist nicht verfügbar         |

## Trocknungspotenzial

Die zentrale Größe ist die Differenz der absoluten Feuchtigkeit:

```text
Trocknungspotenzial =
absolute Innenfeuchtigkeit - absolute Außenfeuchtigkeit
```

Beispiel:

```text
Innen:  9,2 g/m³
Außen:  5,1 g/m³

Trocknungspotenzial: 4,1 g/m³
```

Ein positiver Wert bedeutet, dass die Außenluft weniger Wasserdampf enthält
und beim Lüften Feuchtigkeit aus dem Raum aufnehmen kann.

Je höher der Wert ist, desto größer ist das Potenzial, durch Lüften
Feuchtigkeit aus dem Raum zu entfernen.

### Standardklassifizierung

| Trocknungspotenzial   | Stufe               |
| --------------------: | ------------------- |
| unter −2,0 g/m³       | `negative`          |
| −2,0 bis unter 0 g/m³ | `slightly_negative` |
| 0 bis unter 0,8 g/m³  | `low`               |
| 0,8–2,0 g/m³          | `moderate`          |
| 2,0–4,0 g/m³          | `high`              |
| ab 4,0 g/m³           | `very_high`         |

Die Öffnungs- und Schließgrenzen sind bewusst asymmetrisch. Ab +0,8 g/m³ wird
Lüften standardmäßig als nützlich bewertet. Eine feuchtigkeitsbedingte
Schließempfehlung entsteht dagegen erst unter −2,0 g/m³. Der Bereich
dazwischen bleibt neutral, damit frische Luft möglichst lange möglich bleibt.

Alle Grenzwerte können pro Blueprint-Instanz angepasst werden.

## Bestätigung einer Schließempfehlung

Ein Kandidat für `keep_closed` muss standardmäßig 15 Minuten ohne
Unterbrechung bestehen, bevor der öffentliche Sensorzustand zu `keep_closed`
wechselt.

Während dieser Wartezeit gilt:

```text
state: neutral
reason: keep_closed_pending
```

`ventilate`, `conditional` und gewöhnliche `neutral`-Kandidaten werden
sofort veröffentlicht. Fällt die Ursache einer bestätigten Schließempfehlung
weg, wird `keep_closed` ebenfalls sofort aufgehoben. Dadurch verhindert die
Bestätigungszeit ein Flattern, ohne das spätere Öffnen unnötig zu verzögern.

Diagnoseattribute:

```text
candidate_recommendation
candidate_reason
keep_closed_pending
keep_closed_pending_since
keep_closed_confirmation_minutes
maximum_acceptable_negative_drying_potential
```

## Verhalten bei kaltem Wetter

Kalte Außenluft ist nicht automatisch ungeeignet. Sie enthält häufig deutlich
weniger absolute Feuchtigkeit als warme Raumluft und kann deshalb im Winter
besonders wirksam trocknen.

Beispiel:

```text
Innentemperatur: 21 °C
Außentemperatur: −5 °C
Innenfeuchtigkeit: 10,0 g/m³
Außenfeuchtigkeit: 4,0 g/m³
Trocknungspotenzial: 6,0 g/m³
```

Ein mögliches Ergebnis ist:

```text
state: ventilate
reason: outdoor_air_much_drier_and_cold
recommended_duration_minutes: 3
```

Die kurze Dauer soll unnötigen Wärmeverlust begrenzen.

## Schutz vor zu trockener Raumluft

Ist ein Sensor für relative Innenfeuchtigkeit konfiguriert, wird er bevorzugt
für den Trockenschutz verwendet. Der Standardgrenzwert beträgt 35 %.

Unterhalb dieser Grenze wird weiteres trocknendes Lüften unterdrückt. Ohne
Sensor für relative Feuchtigkeit dient die absolute Innenfeuchtigkeit als
Ersatz; der Standardwert beträgt 5,5 g/m³.

Ein mögliches Ergebnis ist:

```text
state: keep_closed
reason: indoor_air_already_dry
```

Auch dieser Zustand durchläuft die 15-minütige Schließbestätigung.

## Verhalten bei warmem Wetter

Eine höhere Außentemperatur wird als thermischer Nachteil betrachtet, nicht als
absolutes Lüftungsverbot.

### Etwas wärmere Außenluft

Ist die Außenluft etwas wärmer, aber ausreichend trockener, lautet die
Empfehlung `conditional`. Die Feuchte kann dadurch sinken, allerdings mit
einem thermischen Nachteil.

### Deutlich wärmere Außenluft

Ist die Außenluft deutlich wärmer, entsteht normalerweise ein
`keep_closed`-Kandidat. Ein sehr hohes Trocknungspotenzial kann die Bewertung
zu `conditional` ändern und so in Ausnahmefällen eine kurze
Feuchteabfuhr ermöglichen.

## Standardgrenzen der Temperatur

Die Temperaturdifferenz wird so berechnet:

```text
Außentemperatur - Innentemperatur
```

Standardgrenzen:

```text
wärmere Außenluft:          +1,0 °C
deutlich wärmere Außenluft: +3,0 °C
```

## Empfohlene Lüftungsdauer

Für `ventilate` und `conditional` schätzt der Blueprint eine
Stoßlüftungsdauer. Für `neutral` und `keep_closed` bleibt die Dauer leer.

Die Schätzung kombiniert:

1. eine Grunddauer anhand der Außentemperatur,
2. eine Korrektur anhand des Trocknungspotenzials,
3. eine Korrektur für wärmere Außenluft.

### Grunddauern

| Außentemperatur | Grunddauer |
| --------------- | ---------: |
| unter 0 °C      |      4 min |
| 0–5 °C          |      5 min |
| 5–10 °C         |      7 min |
| 10–15 °C        |     10 min |
| 15–20 °C        |     15 min |
| über 20 °C      |     20 min |

Korrekturfaktoren:

### Korrektur des Trocknungspotenzials

Ein hohes Trocknungspotenzial verkürzt die empfohlene Dauer:

```text
sehr hohes Trocknungspotenzial: × 0,70
hohes Trocknungspotenzial:      × 0,85
moderates Trocknungspotenzial:  × 1,00
```

### Thermische Korrektur

Ist die Außenluft wärmer als die Raumluft, wird die Dauer ebenfalls verkürzt:

```text
wärmere Außenluft:              × 0,65
deutlich wärmere Außenluft:     × 0,50
```

Beispiel:

```text
Außentemperatur: 28 °C
Grunddauer: 20 min

sehr hohes Trocknungspotenzial:
20 × 0,70 = 14 min

deutlich wärmere Außenluft:
14 × 0,50 = 7 min
```

Ergebnis:

```text
recommended_duration_minutes: 7
```

Die Standardgrenzen der resultierenden Empfehlung liegen zwischen 2 und
30 Minuten.

## Wichtiger Hinweis zur Dauer

Die Dauer ist eine Orientierung für Stoßlüften und keine berechnete
Luftwechselzeit. Die tatsächliche Wirkung hängt von Größen ab, die der
Blueprint nicht kennt:

- Raumvolumen
- Fenstergröße
- Öffnungswinkel
- Wind
- Druckunterschiede
- Querlüftung
- Anzahl der geöffneten Fenster

Die Angabe ist daher als „empfohlene Stoßlüftungsdauer“ und nicht als
„optimale Lüftungsdauer“ zu verstehen. Zukünftige Versionen könnten Raum- und
Fenstereigenschaften optional berücksichtigen.

## Attribute des Raumsensors

Der erzeugte Sensor stellt folgende Attribute bereit.

### API

```text
api_version
```

### Empfehlung

```text
reason
```

### Temperatur

```text
indoor_temperature
outdoor_temperature
temperature_difference
thermal_condition
```

### Feuchtigkeit

```text
indoor_vapor_concentration
outdoor_vapor_concentration
drying_potential
drying_potential_level
```

### Trockenschutz

```text
indoor_relative_humidity
dry_air_protection_active
dry_air_protection_source
```

### Dauer

```text
recommended_duration_minutes
```

Eine Dauer wird nur bei `ventilate` und `conditional` ausgegeben. Bei
`neutral` und `keep_closed` bleibt sie leer.

## Begründungscodes

Das Attribut `reason` verwendet maschinenlesbare Werte. Aktuelle Werte sind:

```text
indoor_air_already_dry
outdoor_air_more_humid
strong_drying_benefit_but_much_warmer
outdoor_air_much_warmer
outdoor_air_drier_but_warmer
outdoor_air_much_drier_and_cold
outdoor_air_significantly_drier
outdoor_air_drier
conditions_similar
keep_closed_pending
```

Zukünftige Automationen können diese Codes in lokalisierte Meldungen
übersetzen.

## Architektur

Smart Ventilation ist als modulares System aufgebaut.

### Raumsensor

Der Raumsensor führt die physikalische Bewertung für einen Raum durch:

```text
Innenklima
    +
Außenklima
    ↓
Smart Ventilation Sensor
```

### Etagenempfehlung

Der Etagen-Blueprint fasst mehrere gültige Raumsensoren zusammen. Dabei gilt:

- `ventilate` bleibt als klare Lüftungsempfehlung sichtbar.
- `conditional` bleibt als bedingte Empfehlung sichtbar.
- Ein Konflikt zwischen `ventilate` und `keep_closed` wird nicht verborgen.
- Eine Mischung aus `keep_closed` und `neutral` ergibt `neutral` mit
  `reason: mixed_keep_closed_and_neutral`.
- `keep_closed` wird nur veröffentlicht, wenn alle gültigen Räume
  `keep_closed` melden.

Damit kann ein einzelner Raum nicht die ganze Etage schließen, solange andere
Räume noch mit frischer Luft vereinbar sind. Die frühere thermische
Etagenüberschreibung beeinflusst den Zustand nicht mehr; ein möglicher
thermischer Hinweis bleibt nur als Diagnoseattribut
`thermal_override_candidate` sichtbar.

### Smart Ventilation Control

Ein zukünftiger Automations-Blueprint soll folgende Aufgaben übernehmen:

- Fenster überwachen
- Beginn einer Lüftung erkennen
- empfohlene Dauer verfolgen
- an das Schließen der Fenster erinnern
- dauerhafte Benachrichtigungen ausgeben
- mobile Benachrichtigungen senden
- optional Sprachassistenten verwenden

Diese Trennung hält die physikalische Klimabewertung unabhängig von
Benachrichtigungen und Fenstersteuerung.

## Aktualisierung der Sensoren

Der Raumsensor wird bei Änderungen der primären Klimasensoren und zusätzlich
einmal pro Minute neu berechnet. Der Minutentakt sorgt außerdem dafür, dass:

- die 15-minütige Bestätigung zuverlässig fortschreitet,
- Sensoren nach einem Ausfall wieder berücksichtigt werden,
- Änderungen der optionalen relativen Luftfeuchtigkeit erfasst werden,
- Neustarts und Template-Neuladungen aufgefangen werden.

Die tatsächlichen Messwerte ändern sich nur so häufig, wie die jeweiligen
physischen Sensoren neue Werte liefern. Der Minutentakt erfindet keine neuen
Messdaten, sondern bewertet den zuletzt bekannten gültigen Stand erneut.

## Standardkonfiguration

```text
minimales Trocknungspotenzial:       0,8 g/m³
akzeptierter negativer Bereich:      2,0 g/m³
Bestätigung für keep_closed:        15 min
hohes Trocknungspotenzial:           2,0 g/m³
sehr hohes Trocknungspotenzial:      4,0 g/m³

wärmere Außenluft:                  +1,0 °C
deutlich wärmere Außenluft:         +3,0 °C

minimale relative Innenfeuchte:      35 %
Ersatzgrenze absolute Feuchtigkeit:  5,5 g/m³

minimale empfohlene Dauer:            2 min
maximale empfohlene Dauer:           30 min
```

Jeder Wert kann für jede Blueprint-Instanz unabhängig konfiguriert werden.

## Status

Smart Ventilation wird aktiv entwickelt. Der Raumsensor sollte als
experimentell betrachtet werden, bis sein Verhalten über verschiedene
Jahreszeiten hinweg mit realen Klimadaten validiert wurde.

## Autor

Björn Rudner (@rudnerbjoern), mit der Hilfe von KI 😉
