---
name: wiki-artikel
description: >
  Erstellt hochwertige deutsche Wikipedia-Artikel aus anderssprachigem (meist englischem)
  Wikitext. Verwende diesen Skill immer, wenn der Nutzer einen Wikipedia-Artikel auf
  Deutsch erstellen, übersetzen oder aus einer anderssprachigen Vorlage ableiten möchte.
  Trigger-Phrasen: "Wikipedia-Artikel erstellen", "deutschen Artikel schreiben", "dewiki",
  "Artikel anlegen", "aus dem Englischen übernehmen", "Wikipedia übersetzen", oder wenn
  der Nutzer englischen Wikitext einfügt und einen deutschen Artikel daraus haben möchte.
  Auch bei Begriffen wie "Wikisyntax", "Wikicode", "Wikitext auf Deutsch" diesen Skill
  verwenden. Dieser Skill geht über reine Syntax-Konvertierung hinaus – er erzeugt einen
  eigenständigen, enzyklopädisch hochwertigen Artikel nach dewiki-Konventionen. Für reine
  Syntax-Konvertierung ohne redaktionelle Arbeit den wende-Skill verwenden.
---

# Wiki-Artikel – Deutsche Wikipedia-Artikel erstellen

Erzeuge vollwertige deutsche Wikipedia-Artikel aus anderssprachigem Quelltext. Das
Ergebnis ist kein Übersetzungsprodukt, sondern ein eigenständiger enzyklopädischer
Artikel, der den Konventionen der deutschsprachigen Wikipedia entspricht.

## Abgrenzung zum Wende-Skill

Der **Wende-Skill** ist ein Werkzeug für mechanische Syntax-Konvertierung (Templates,
Zitationen, Zahlenformate). Dieser Skill hier ist ein **redaktioneller Workflow**:
Er nutzt Wende als einen Schritt, trifft aber darüber hinaus redaktionelle
Entscheidungen über Struktur, Gewichtung, Stil und Vollständigkeit.

## Eingaben

1. **Anderssprachiger Wikitext** (Pflicht): Der Nutzer fügt den Quelltext ein.
2. **Zusätzliche Quellen** (optional): Weitere Texte, die einfließen sollen.

Keine automatische Web-Recherche durchführen, sofern der Nutzer es nicht
ausdrücklich verlangt. Nur das verwenden, was der Nutzer bereitstellt.

## Workflow

### Schritt 1: Analyse

Den Quelltext lesen und folgendes bestimmen:

- **Artikeltyp**: Person, Unternehmen, Ort, Film, Album, Software, Konzept, Ereignis?
- **Struktur**: Welche Abschnitte existieren, welche fehlen?
- **Infobox**: Welcher Typ, welche Parameter sind gefüllt?
- **Quellenqualität**: Wie viele Einzelnachweise, welche Qualität?
- **Lücken**: Was fehlt, was müsste ergänzt werden?

Den Nutzer kurz über den Plan informieren – besonders über erkannte Lücken.

### Schritt 2: Syntaktische Konvertierung (→ Wende)

Die Regeln aus `/mnt/skills/user/wende/references/rules.yaml` lesen und anwenden.
Dieser Schritt ist rein mechanisch und folgt dem Wende-Workflow:

- Templates konvertieren oder entfernen
- Zitationsvorlagen umschreiben (cite web → Internetquelle etc.)
- Zitationsparameter mappen (title → titel, access-date → abruf etc.)
- Zu entfernende Parameter streichen (archive-url, url-status etc.)
- `|sprache=en` bei englischsprachigen Quellen ergänzen
- Zahlenformate anpassen (Dezimaltrennzeichen, Tausendertrennzeichen, Skalenworte)
- Datumsformate umwandeln (MDY → DMY, Monatsnamen übersetzen)
- Namensräume anpassen (Category → Kategorie, File → Datei)
- Bildparameter konvertieren (thumb → mini, right → rechts)
- Magic Words anpassen (DEFAULTSORT → SORTIERUNG)
- Typografie korrigieren (Anführungszeichen, Gedankenstriche, geschützte Leerzeichen)

### Schritt 3: Artikelstruktur nach dewiki-Standards aufbauen

Jetzt beginnt die redaktionelle Arbeit. Die Struktur aus `references/dewiki-struktur.md`
als Referenz verwenden – dort sind Gliederungsvorlagen für verschiedene Artikeltypen
hinterlegt.

Zentrale Prinzipien:

**Einleitung**: Der erste Absatz steht ohne Überschrift direkt nach der Infobox.
Der erste Satz definiert den Artikelgegenstand mit fettem Lemma. Die Einleitung
fasst den Artikel eigenständig zusammen – sie soll auch ohne den Rest verständlich sein.

**Gliederung**: Logische Abschnitte mit `==`-Überschriften in dewiki-typischer
Reihenfolge. Die Reihenfolge am Artikelende ist fest:
`Literatur → Einzelnachweise → Weblinks → Normdaten → SORTIERUNG → Kategorien`

**Infobox**: Die passende deutsche Infobox-Vorlage verwenden. Die Parameter-Mappings
aus der rules.yaml im Wende-Skill nutzen. Nicht alle enwiki-Parameter haben ein
dewiki-Äquivalent – überflüssige weglassen statt raten.

**Einzelnachweise**: Abschnitt `== Einzelnachweise ==` mit `<references />`. Belege
stehen direkt nach dem Satz, den sie belegen – nicht gesammelt am Ende.

**Weblinks**: Maximal 5, nur hochwertige offizielle Links. Format: `* [URL Beschreibung]`

**Kategorien**: Mindestens eine. Von spezifisch zu allgemein sortieren. Typische
Muster sind in `references/dewiki-struktur.md` dokumentiert. Nur Kategorien verwenden,
bei denen hohe Sicherheit besteht, dass sie auf dewiki existieren. Im Zweifelsfall
einen Kommentar setzen: `<!-- TODO: Kategorie prüfen -->`.

**Wikilinks**: Bekannte Titel anpassen (rules.yaml → link_mappings). Bei unbekannten
Links: im Zweifelsfall den englischen Titel belassen und markieren:
`<!-- TODO: dewiki-Linkziel prüfen -->`. Das ist besser als einen falschen Link zu setzen.

### Schritt 4: Prosa neu schreiben

Die Prosa nicht wörtlich übersetzen, sondern als eigenständigen deutschen Text
verfassen. Die englische Version dient als inhaltliche Grundlage, nicht als
Satzvorlage.

Stilregeln:
- Enzyklopädischer, neutraler Ton (kein Journalismus, keine Wertungen)
- Natürliches Deutsch, deutsche Begriffe wo sie existieren (keine Anglizismen)
- Passive Konstruktionen und Nominalstil sind in dewiki üblich und angemessen
- Fachbegriffe konsistent verwenden
- Eigennamen, Markennamen, Werktitel in Originalsprache belassen
- Zitate im Original belassen, deutsche Übersetzung ergänzen:
  `{{Zitat|Originaltext|Sprache=en|Übersetzung=Deutscher Text}}`
- Deutsche Anführungszeichen: „..." statt "..."
- Halbgeviertstrich (–) als Gedankenstrich, nicht Geviertstrich (—)
- Geschütztes Leerzeichen zwischen Zahl und Einheit: `10&nbsp;km`

### Schritt 5: Qualitätskontrolle

Vor der Ausgabe diese Checkliste durchgehen:

**Struktur:**
- [ ] Einleitung vorhanden, erster Satz definierend mit fettem Lemma
- [ ] Infobox korrekt konvertiert (alle Parameter deutsch)
- [ ] Abschnitte in dewiki-typischer Reihenfolge
- [ ] Einzelnachweise-Abschnitt mit `<references />`

**Syntax:**
- [ ] Alle Templates konvertiert oder entfernt
- [ ] Einzelnachweise vollständig und korrekt formatiert
- [ ] Zahlen- und Datumsformate deutsch
- [ ] Keine englischen Namespace-Präfixe (`Category:`, `File:`)
- [ ] Klammern balanciert (`{{`/`}}`, `<ref>`/`</ref>`)
- [ ] URLs unverändert (kein Zahlenformat-Tausch in URLs)

**Inhalt:**
- [ ] Keine englischen Reste in der Prosa
- [ ] Kategorien vorhanden und plausibel
- [ ] SORTIERUNG gesetzt (bei Personen: Nachname, Vorname)
- [ ] Personendaten-Vorlage (bei Personenartikeln)
- [ ] Normdaten-Vorlage (mit passendem TYP)
- [ ] Unsichere Stellen mit `<!-- TODO: ... -->` markiert

### Schritt 6: Ausgabe

Den fertigen Artikel als vollständigen Wikitext ausgeben. Der Text soll direkt
in einen Wikipedia-Editor einfügbar sein. Als `.txt`-Datei bereitstellen.

Den Nutzer auf folgendes hinweisen:
- Welche Abschnitte noch Recherche benötigen (TODO-Kommentare)
- Welche Wikilinks und Kategorien manuell geprüft werden sollten
- Ob Informationen aus dem Quellartikel ausgelassen wurden (und warum)

## Besondere dewiki-Konventionen

Einige Konventionen, die sich von enwiki unterscheiden:

- **Keine Klappboxen im Artikeltext**: Collapsible sections werden in dewiki vermieden
- **Keine Flaggen-Icons**: `{{flag|...}}` nicht im Fließtext verwenden
- **Keine Interwiki-Links**: Wikidata übernimmt das, nicht manuell setzen
- **Belege im Fließtext**: Refs stehen direkt nach dem Satz, nicht gesammelt am Ende
- **Weblinks sparsam**: Maximal 5 hochwertige, offizielle Links
- **Kein „as of"-Konstrukt**: Stattdessen `Stand MONAT JAHR` in Klammern oder als Vorlage

## Umgang mit Lücken und Unsicherheiten

- Nichts erfinden oder spekulieren
- Fehlende Informationen als Kommentar markieren: `<!-- TODO: Abschnitt XY ergänzen -->`
- Lieber ein kürzerer korrekter Artikel als ein aufgeblähter unsicherer
- Dem Nutzer explizit mitteilen, welche Stellen Nacharbeit brauchen
- Kategorien und Wikilinks, bei denen Unsicherheit besteht, markieren

## Artikelstruktur-Referenz

Für detaillierte Gliederungsvorlagen nach Artikeltyp (Person, Unternehmen, Ort,
Film, Album, Software, Konzept) sowie Einleitungsmuster, Einzelnachweis-Formate
und Kategorienmuster: `references/dewiki-struktur.md` lesen.
