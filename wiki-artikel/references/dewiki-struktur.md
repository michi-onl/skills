# Artikelstruktur der deutschsprachigen Wikipedia

Referenz für die korrekte Gliederung und Reihenfolge von Abschnitten in dewiki-Artikeln.
Dieses Dokument deckt die häufigsten Artikeltypen ab und gibt Muster für Einleitungen,
Kategorien und Vorlagen.

## Inhaltsverzeichnis

1. [Allgemeine Artikelstruktur](#allgemeine-artikelstruktur)
2. [Personenartikel](#personenartikel)
3. [Unternehmensartikel](#unternehmensartikel)
4. [Ortsartikel](#ortsartikel)
5. [Filmartikel](#filmartikel)
6. [Albumartikel](#albumartikel)
7. [Softwareartikel](#softwareartikel)
8. [Konzept- und Sachartikel](#konzept--und-sachartikel)
9. [Einleitungsregeln](#einleitungsregeln)
10. [Einzelnachweise und Belege](#einzelnachweise-und-belege)
11. [Kategorien](#kategorien)
12. [Typische Vorlagen](#typische-vorlagen)
13. [Tabellen](#tabellen)

---

## Allgemeine Artikelstruktur

Die Reihenfolge der Bestandteile eines dewiki-Artikels:

```
{{Infobox ...}}                    ← Infobox (wenn passend)

Einleitungsabschnitt               ← Kein == Überschrift ==, direkt nach Infobox
(Definition, Kurzüberblick)

== Inhaltliche Abschnitte ==       ← Hauptteil, themenabhängig gegliedert

== Rezeption ==                    ← Optional
== Auszeichnungen ==               ← Optional
== Siehe auch ==                   ← Optional, sparsam verwenden
== Literatur ==                    ← Optional
== Einzelnachweise ==              ← Fast immer vorhanden
<references />
== Weblinks ==                     ← Optional, max. 5 hochwertige Links

{{Normdaten|...}}                  ← Optional
{{SORTIERUNG:...}}                 ← Bei Bedarf (Personen, Sonderzeichen)
[[Kategorie:...]]                  ← Mindestens eine Kategorie
```

Die Reihenfolge **Literatur → Einzelnachweise → Weblinks** ist fest und darf nicht
verändert werden. Danach kommen Vorlagen (Normdaten, Personendaten), dann SORTIERUNG,
dann Kategorien.

---

## Personenartikel

### Gliederung

```
{{Infobox Person}}

'''Vorname Nachname''' (* Geburtsdatum in Geburtsort; † Sterbedatum in Sterbeort)
ist/war ein/eine NATIONALITÄT BERUF.

== Leben ==
=== Kindheit und Ausbildung ===
=== Karriere ===
=== Privatleben ===

== Werk / Schaffen ==              ← bei Künstlern, Autoren etc.

== Diskografie / Filmografie ==    ← je nach Typ

== Auszeichnungen ==

== Einzelnachweise ==
<references />

== Weblinks ==
* [URL Offizielle Website]

{{Normdaten|TYP=p}}
{{Personendaten
|NAME=Nachname, Vorname
|ALTERNATIVNAMEN=
|KURZBESCHREIBUNG=nationalität Beruf
|GEBURTSDATUM=Tag. Monat Jahr
|GEBURTSORT=[[Ort]]
|STERBEDATUM=
|STERBEORT=
}}
{{SORTIERUNG:Nachname, Vorname}}
[[Kategorie:...]]
```

### Einleitung

Format: `'''Vorname Nachname''' (* Datum in Ort) ist ein deutscher Beruf.`

- Nur der Name fett
- Lebensdaten in Klammern mit Stern (*) und ggf. Kreuz (†)
- Nationalität + Beruf/Tätigkeit
- Geburts-/Sterbedaten nicht verlinken (dewiki-Konvention seit 2016)
- Orte verlinken: `[[Berlin]]`

### Typische Kategorien

```
[[Kategorie:BERUF]]                        z.B. [[Kategorie:Filmschauspieler]]
[[Kategorie:NATIONALITÄT]]                 z.B. [[Kategorie:US-Amerikaner]]
[[Kategorie:Geboren JJJJ]]                 z.B. [[Kategorie:Geboren 1985]]
[[Kategorie:Gestorben JJJJ]]               nur bei Verstorbenen
[[Kategorie:Mann]] / [[Kategorie:Frau]]
```

Häufige sichere Nationalitäts-Kategorien:
`US-Amerikaner`, `Brite`, `Deutscher`, `Franzose`, `Kanadier`, `Australier`,
`Japaner`, `Südkoreaner`, `Inder`, `Brasilianer`, `Schwede`, `Norweger`

Häufige sichere Berufs-Kategorien:
`Filmschauspieler`, `Filmregisseur`, `Popsänger`, `Rapsänger`, `Songwriter`,
`Gitarrist`, `Unternehmer`, `Informatiker`, `Physiker`, `Autor`,
`Fußballspieler`, `Tennisspieler`

---

## Unternehmensartikel

### Gliederung

```
{{Infobox Unternehmen
| Name =
| Logo =
| Rechtsform =
| ISIN =
| Gründungsdatum =
| Gründer =
| Sitz =
| Leitung =
| Mitarbeiterzahl =
| Umsatz =
| Branche =
| Homepage =
}}

Die '''Firmenname''' ist ein BRANCHE-Unternehmen mit Sitz in ORT.

== Geschichte ==
== Geschäftstätigkeit ==
=== Produkte / Dienstleistungen ===
== Unternehmensstruktur ==         ← Optional
== Kritik ==                       ← Optional, neutral formulieren
== Einzelnachweise ==
<references />
== Weblinks ==
* [URL Offizielle Website]

{{SORTIERUNG:Firmenname}}
[[Kategorie:...]]
```

### Einleitung

Format: `Die '''Firma''' (ehem. ''Altname'') ist ein BRANCHE-Unternehmen mit Sitz in ORT.`

Optionale Ergänzungen: Gründungsjahr, börsennotiert, Konzernzugehörigkeit.

### Typische Kategorien

```
[[Kategorie:BRANCHE]]                      z.B. [[Kategorie:Softwarehersteller]]
[[Kategorie:Unternehmen (ORT)]]            z.B. [[Kategorie:Unternehmen (San Francisco)]]
[[Kategorie:Gegründet JJJJ]]               z.B. [[Kategorie:Gegründet 2015]]
```

Häufige sichere Branchen-Kategorien:
`Softwarehersteller`, `Technologieunternehmen`, `Automobilhersteller`,
`Medienunternehmen`, `Pharmaunternehmen`, `Finanzdienstleistungsunternehmen`,
`Handelsunternehmen`, `Lebensmittelhersteller`, `Telekommunikationsunternehmen`

Hinweis: Unternehmens-Orts-Kategorien folgen dem Schema `Unternehmen (Stadtname)`.
US-amerikanische Städte ohne Bundesstaat: `Unternehmen (San Francisco)`, nicht
`Unternehmen (San Francisco, Kalifornien)`.

---

## Ortsartikel

### Gliederung

```
{{Infobox Ort}}

'''Ortsname''' ist eine Stadt/Gemeinde in REGION/LAND.

== Geografie ==
=== Lage ===
=== Klima ===
== Geschichte ==
== Politik ==
=== Gemeinderat ===
=== Bürgermeister ===
=== Wappen ===
== Kultur und Sehenswürdigkeiten ==
== Wirtschaft und Infrastruktur ==
=== Verkehr ===
== Persönlichkeiten ==
=== Söhne und Töchter der Stadt ===
== Einzelnachweise ==
<references />
== Weblinks ==
{{Commonscat|Ortsname}}

[[Kategorie:...]]
```

### Typische Kategorien

```
[[Kategorie:Ort im Landkreis X]]
[[Kategorie:Gemeinde in BUNDESLAND]]
[[Kategorie:Ort in LAND]]                  für nicht-deutsche Orte
```

---

## Filmartikel

### Gliederung

```
{{Infobox Film
| Deutscher Titel =
| Originaltitel =
| Produktionsland =
| Originalsprache =
| Erscheinungsjahr =
| Länge =
| Regie =
| Drehbuch =
| Produktion =
| Musik =
| Kamera =
| Schnitt =
| Besetzung =
}}

'''Filmtitel''' (Originaltitel: ''Original Title'') ist ein LAND GENRE aus dem Jahr JJJJ
von REGISSEUR.

== Handlung ==

== Produktion ==
=== Entstehungsgeschichte ===
=== Besetzung ===
=== Dreharbeiten ===

== Veröffentlichung ==

== Rezeption ==
=== Kritiken ===
=== Einspielergebnis ===

== Auszeichnungen ==

== Einzelnachweise ==
<references />

== Weblinks ==
* {{Internetquelle |url=... |titel=Filmtitel |werk=[[Internet Movie Database]]}}

{{SORTIERUNG:Filmtitel}}
[[Kategorie:...]]
```

### Einleitung

Format: `'''Filmtitel''' (Originaltitel: ''Original Title'') ist ein LAND GENRE aus dem Jahr JJJJ von REGISSEUR.`

Bei deutschsprachigen Filmen entfällt der Originaltitel.

### Typische Kategorien

```
[[Kategorie:Filmtitel JJJJ]]               z.B. [[Kategorie:Filmtitel 2024]]
[[Kategorie:LAND Film]]                    z.B. [[Kategorie:US-amerikanischer Film]]
[[Kategorie:GENRE]]                        z.B. [[Kategorie:Actionfilm]]
```

Häufige sichere Genre-Kategorien:
`Actionfilm`, `Komödie`, `Drama`, `Thriller`, `Horrorfilm`, `Science-Fiction-Film`,
`Animationsfilm`, `Dokumentarfilm`, `Abenteuerfilm`, `Fantasyfilm`, `Kriegsfilm`,
`Kriminalfilm`, `Liebesfilm`, `Musikfilm`

Länder-Kategorien: `US-amerikanischer Film`, `Britischer Film`, `Deutscher Film`,
`Französischer Film`, `Japanischer Film`, `Südkoreanischer Film`

### Besonderheiten

- Die **Handlung** wird im Präsens erzählt
- Das **Einspielergebnis** mit Quelle belegen, Beträge in US-Dollar belassen
- Die **Besetzungsliste** als Tabelle oder Aufzählung, nicht als Fließtext
- **IMDb-Link** in den Weblinks, nicht als Einzelnachweis verwenden

---

## Albumartikel

### Gliederung

```
{{Infobox Album
| Titel =
| Künstler =
| Genre =
| Jahr =
| Label =
| Produzent =
| Vorgänger =
| Nachfolger =
}}

'''Albumtitel''' ist das X. Studioalbum der/des KÜNSTLER. Es erschien am DATUM
über das Label LABEL.

== Hintergrund und Produktion ==

== Titelliste ==

== Rezeption ==
=== Kritiken ===
=== Chartplatzierungen ===

== Einzelnachweise ==
<references />

== Weblinks ==

{{SORTIERUNG:Albumtitel}}
[[Kategorie:...]]
```

### Einleitung

Format: `'''Albumtitel''' ist das X. Studioalbum der/des KÜNSTLER. Es erschien am DATUM.`

### Typische Kategorien

```
[[Kategorie:Album JJJJ]]
[[Kategorie:Album (GENRE)]]                z.B. [[Kategorie:Album (Pop)]]
[[Kategorie:KÜNSTLER-Album]]               z.B. [[Kategorie:Taylor-Swift-Album]]
```

Häufige sichere Genre-Kategorien für Alben:
`Album (Pop)`, `Album (Rock)`, `Album (Hip-Hop)`, `Album (R&B)`,
`Album (Electronic)`, `Album (Country)`, `Album (Metal)`, `Album (Jazz)`

### Titelliste

Die Titelliste als Wikitable formatieren:

```
{| class="wikitable"
! Nr.
! Titel
! Autor(en)
! Länge
|-
| 1 || „Songtitel" || Autor1, Autor2 || 3:42
|-
| 2 || „Songtitel" || Autor1 || 4:15
|}
```

---

## Softwareartikel

### Gliederung

```
{{Infobox Software
| Name =
| Logo =
| Entwickler =
| AktuelleVersion =
| AktuelleVersionFreigworddatum =
| Betriebssystem =
| Programmiersprache =
| Kategorie =
| Lizenz =
| Website =
}}

'''Name''' ist eine KATEGORIE-Software, die von ENTWICKLER entwickelt wird.

== Geschichte ==

== Funktionen ==

== Technik ==
=== Architektur ===

== Rezeption ==

== Einzelnachweise ==
<references />

== Weblinks ==
* [URL Offizielle Website]

{{SORTIERUNG:Name}}
[[Kategorie:...]]
```

### Einleitung

Format: `'''Name''' ist eine KATEGORIE, die von ENTWICKLER entwickelt wird.`

Optionale Ergänzungen: Lizenz (freie Software?), Plattformen, Erstveröffentlichung.

### Typische Kategorien

```
[[Kategorie:KATEGORIE-Software]]           z.B. [[Kategorie:Webbrowser]]
[[Kategorie:Freie Software]]               wenn zutreffend
[[Kategorie:Linux-Software]]               je nach Plattform
[[Kategorie:Windows-Software]]
[[Kategorie:MacOS-Software]]
[[Kategorie:Android-Software]]
[[Kategorie:IOS-Software]]
```

---

## Konzept- und Sachartikel

Für abstrakte Konzepte, wissenschaftliche Themen, Ereignisse, Bewegungen etc.

### Gliederung

```
'''Lemma''' (auch ''Alternativbezeichnung'') bezeichnet DEFINITION.

== Überblick / Definition ==               ← optional, wenn Einleitung nicht reicht

== Geschichte ==
=== Ursprünge ===
=== Entwicklung ===

== Merkmale / Eigenschaften ==

== Bedeutung / Anwendung ==

== Rezeption / Kritik ==

== Siehe auch ==                           ← hier eher sinnvoll als bei anderen Typen

== Literatur ==                            ← bei wissenschaftlichen Themen oft wichtig

== Einzelnachweise ==
<references />

== Weblinks ==

{{Normdaten|TYP=s}}
{{SORTIERUNG:Lemma}}
[[Kategorie:...]]
```

### Einleitung

Format variiert je nach Gegenstand:
- Konzept: `'''Lemma''' bezeichnet DEFINITION.`
- Ereignis: `Der/Die/Das '''Ereignis''' war ein KATEGORIE, das am DATUM in ORT stattfand.`
- Bewegung: `'''Lemma''' ist eine KATEGORIE, die MERKMAL.`

### Typische Kategorien

Stark themenabhängig. Allgemeine Muster:
```
[[Kategorie:FACHGEBIET]]                   z.B. [[Kategorie:Künstliche Intelligenz]]
[[Kategorie:Wissenschaftliche Methode]]
[[Kategorie:Politische Bewegung]]
[[Kategorie:Ereignis JJJJ]]
```

---

## Einleitungsregeln

Die Einleitung ist der wichtigste Teil des Artikels.

1. **Erster Satz**: Definiert den Artikelgegenstand. Lemma **fett**.
2. **Keine Überschrift**: Die Einleitung hat keine `==`-Überschrift.
3. **Eigenständig verständlich**: Soll den Artikel auch ohne den Rest zusammenfassen.
4. **Länge**: Proportional zum Artikel. Kurze Artikel: 1–2 Sätze. Lange: 1–3 Absätze.
5. **Belege**: In der Einleitung nur bei strittigen oder überraschenden Aussagen.

### Einleitungsmuster nach Typ

| Typ | Muster |
|-----|--------|
| Person | `'''Name''' (* Datum in Ort) ist ein/e NATIONALITÄT BERUF.` |
| Unternehmen | `Die '''Firma''' ist ein BRANCHE-Unternehmen mit Sitz in ORT.` |
| Ort | `'''Ortsname''' ist eine Stadt/Gemeinde im LANDKREIS in BUNDESLAND.` |
| Film | `'''Titel''' ist ein LAND GENRE aus dem Jahr JJJJ von REGISSEUR.` |
| Album | `'''Titel''' ist das X. Studioalbum der/des KÜNSTLER.` |
| Software | `'''Name''' ist eine KATEGORIE, die von ENTWICKLER entwickelt wird.` |
| Konzept | `'''Lemma''' bezeichnet DEFINITION.` |
| Ereignis | `Das '''Ereignis''' war ein KATEGORIE, das am DATUM stattfand.` |

---

## Einzelnachweise und Belege

### Internetquelle (häufigste Vorlage)

```
<ref>{{Internetquelle
|url=https://example.com/artikel
|titel=Titel des Artikels
|werk=Name der Website/Zeitung
|datum=2024-01-15
|abruf=2025-01-20
|sprache=en
}}</ref>
```

Wichtige Parameter:
- `url` (Pflicht)
- `titel` (Pflicht)
- `werk` – Name der Publikation
- `hrsg` – Herausgeber (wenn kein Werk angegeben)
- `autor` – Autor des Artikels
- `datum` – Publikationsdatum im ISO-Format (JJJJ-MM-TT)
- `abruf` – Abrufdatum im ISO-Format
- `sprache` – Sprachcode bei nicht-deutschsprachigen Quellen (z.B. `en`)

### Benannte Referenzen

Wenn dieselbe Quelle mehrfach verwendet wird:
```
<ref name="quelle1">{{Internetquelle |...}}</ref>

Spätere Verwendung:
<ref name="quelle1" />
```

### Literaturbelege

```
<ref>{{Literatur
|Autor=Vorname Nachname
|Titel=Buchtitel
|Verlag=Verlag
|Jahr=2023
|ISBN=978-3-...
|Seiten=42–45
}}</ref>
```

---

## Kategorien

### Allgemeine Regeln

- Mindestens eine Kategorie pro Artikel
- Von spezifisch zu allgemein sortieren
- Nur Kategorien verwenden, bei denen Sicherheit besteht, dass sie existieren
- Im Zweifelsfall markieren: `<!-- TODO: Kategorie prüfen -->`

### Häufige Muster nach Artikeltyp

| Typ | Kategorien |
|-----|-----------|
| Person | Beruf, Nationalität, Geboren JJJJ, Mann/Frau |
| Unternehmen | Branche, Unternehmen (Ort), Gegründet JJJJ |
| Ort | Ort in Region/Land |
| Film | Filmtitel JJJJ, Land Film, Genre |
| Album | Album JJJJ, Album (Genre), Künstler-Album |
| Software | Softwaretyp, Plattform, ggf. Freie Software |
| Konzept | Fachgebiet |

### Hinweise zur Kategorienwahl

Auf dewiki gibt es einige Besonderheiten:
- Personen-Kategorien nutzen die männliche Form für den Beruf, unabhängig vom
  Geschlecht der Person (umstritten, aber aktuell Konvention)
- Unternehmens-Orts-Kategorien: nur Stadtname, kein Bundesstaat/Land
- Bei Filmen: `Filmtitel JJJJ` (mit Jahreszahl, nicht `Film JJJJ`)
- Nationalitäts-Adjektive in Kategorien: `US-amerikanischer Film` (nicht `Amerikanischer Film`)

---

## Typische Vorlagen

### Normdaten

```
{{Normdaten|TYP=p|GND=|VIAF=|LCCN=}}   ← Personen (TYP=p)
{{Normdaten|TYP=k|GND=|VIAF=}}          ← Körperschaften/Unternehmen (TYP=k)
{{Normdaten|TYP=g|GND=}}                ← Geografika (TYP=g)
{{Normdaten|TYP=w|GND=}}                ← Werke (TYP=w)
{{Normdaten|TYP=s|GND=}}                ← Sachbegriffe (TYP=s)
```

Ohne bekannte IDs die leere Vorlage setzen: `{{Normdaten|TYP=p}}`

### Personendaten

```
{{Personendaten
|NAME=Nachname, Vorname
|ALTERNATIVNAMEN=
|KURZBESCHREIBUNG=nationalität Beruf
|GEBURTSDATUM=Tag. Monat Jahr
|GEBURTSORT=[[Ort]], [[Land]]
|STERBEDATUM=
|STERBEORT=
}}
```

### Commonscat

```
{{Commonscat|Artikelname}}
```

Im Weblinks-Abschnitt platzieren.

---

## Tabellen

### Allgemeine dewiki-Tabellenkonventionen

- Klasse `wikitable` verwenden: `{| class="wikitable"`
- Bei sortierbaren Tabellen: `{| class="wikitable sortable"`
- Bei nummerierten Zeilen: Klasse `tabelle-zaehler` ergänzen
- Keine Rank-Spalte verwenden (enwiki-Konvention, nicht dewiki)
- Kopfzeilen mit `!` statt `|`

### Diskografie-Tabellen

Enwiki nutzt oft komplexe Charttabellen mit vielen Spalten. Für dewiki vereinfachen:

```
{| class="wikitable"
! Jahr
! Titel
! Album
! Chartplatzierungen
|-
| 2023 || „Songtitel" || ''Albumname'' || DE: 5, AT: 8, CH: 12
|}
```

Alternativ die Vorlage `{{Charttabelle}}` verwenden, wenn sie zum Format passt.

### Filmografie-Tabellen

```
{| class="wikitable"
! Jahr
! Titel
! Rolle
! Anmerkungen
|-
| 2024 || ''[[Filmtitel]]'' || Rollenname || Hauptrolle
|}
```

### Allgemeiner Hinweis

Große enwiki-Tabellen (>30 Zeilen) kritisch prüfen: Enthalten sie relevante
Informationen für den dewiki-Artikel, oder sind sie besser als Liste oder
Fließtext darstellbar? Im Zweifelsfall kürzen und auf die wichtigsten Einträge
beschränken.
