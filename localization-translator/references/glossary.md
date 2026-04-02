# Software Localization Glossary (EN → DE)

Quick reference for common terms. Context matters — these are defaults, not rules.

## Keep in English (established loanwords)

App, Badge, Branch, Browser, Bug, Button, Cache, Checkbox, Commit, Cookie, Dashboard, Dropdown, E-Mail, Emoji, Feedback, Fork, Framework, Hashtag, Icon, Layout, Link, Login, Logout, Merge, Newsletter, Notification, Podcast, Popup, Proxy, Pull-Request, Radio Button, Repository, Screenshot, Server, Slider, Smartphone, Snippet, Tab, Tag, Thread (Chat/Forum), Toggle, Token, Toolbar, Tooltip, Update, Upload, URL, Widget, Workaround

## Translate (natural German exists)

| English | German | Notes |
|---------|--------|-------|
| Account | Konto | "Account" acceptable in casual contexts |
| Attachment | Anhang | |
| Bookmark | Lesezeichen | |
| Breadcrumb | Breadcrumb / Brotkrümelnavigation | "Breadcrumb" in dev context, "Pfadnavigation" as alternative |
| Cancel | Abbrechen | |
| Close | Schließen | |
| Confirm | Bestätigen | |
| Copy | Kopieren | |
| Create | Erstellen | |
| Delete | Löschen | |
| Deploy | Bereitstellen | Noun: Bereitstellung; "Deployment" also common |
| Download | Herunterladen / Download | Verb: herunterladen; Noun: Download |
| Edit | Bearbeiten | |
| Error | Fehler | |
| Expand / Collapse | Aufklappen / Zuklappen | Also: Erweitern / Reduzieren |
| File | Datei | |
| Folder | Ordner | |
| Help | Hilfe | |
| History | Verlauf | Browser context |
| Home | Startseite | |
| Loading | Wird geladen | |
| Manage | Verwalten | |
| Milestone | Meilenstein | |
| New | Neu | |
| Open | Öffnen | |
| Overflow (menu) | Mehr / Weitere Optionen | Technical: Überlauf |
| Password | Passwort | |
| Paste | Einfügen | |
| Placeholder | Platzhalter | |
| Preferences | Einstellungen | |
| Privacy | Datenschutz | |
| Prompt | Eingabeaufforderung | "Prompt" acceptable in AI/dev context |
| Refresh | Aktualisieren | |
| Remove | Entfernen | |
| Rename | Umbenennen | |
| Restart | Neu starten | |
| Restore | Wiederherstellen | |
| Save | Speichern | |
| Search | Suchen / Suche | Verb/Noun |
| Security | Sicherheit | |
| Select | Auswählen | |
| Settings | Einstellungen | |
| Share | Teilen | |
| Sidebar | Seitenleiste | |
| Sign in | Anmelden | |
| Sign out | Abmelden | |
| Sign up | Registrieren | |
| Submit | Absenden | |
| Sync | Synchronisieren | |
| Template | Vorlage | |
| Undo | Rückgängig | |
| Username | Benutzername | |
| View | Ansicht / Anzeigen | Noun/Verb |
| Warning | Warnung | |

## Context-Dependent

| English | Formal (Sie) | Informal (du) |
|---------|--------------|---------------|
| Your account | Ihr Konto | Dein Konto |
| Click here | Klicken Sie hier | Klicke hier |
| Please wait | Bitte warten Sie | Bitte warte |
| Enter your email | Geben Sie Ihre E-Mail-Adresse ein | Gib deine E-Mail-Adresse ein |
| Are you sure? | Sind Sie sicher? | Bist du sicher? |
| You have # items | Sie haben # Elemente | Du hast # Elemente |

## Ambiguous Terms

These English words have different German translations depending on context. Check the key name, surrounding strings, or UI context to choose correctly.

| English | As verb (action) | As noun/state | Tip |
|---------|------------------|---------------|-----|
| Open | Öffnen | Offen / Geöffnet | `btn_` → verb, `status_` → state |
| Save | Speichern | Gespeichert | |
| Share | Teilen | Freigabe | |
| View | Anzeigen | Ansicht | |
| Post | Veröffentlichen | Beitrag | Social media context |
| Set | Festlegen | Satz / Gruppe | |
| Match | Abgleichen | Übereinstimmung / Treffer | |
| Report | Melden | Bericht | `btn_report` → Melden, `page_report` → Bericht |
| Block | Blockieren | Block / Baustein | |
| Clear | Leeren / Löschen | Leer | |
| Close | Schließen | Geschlossen | |
| Lock | Sperren | Gesperrt | |

## Common Pitfalls

| Avoid | Prefer | Reason |
|-------|--------|--------|
| Abspeichern | Speichern | Shorter, standard |
| Applikation | App / Anwendung | More natural |
| Attachen | Anhängen | Anglizismus |
| Browsen | Durchsuchen / Stöbern | Too colloquial for UI |
| Canceln | Abbrechen | Anglizismus |
| Deleten | Löschen | Anglizismus |
| Editieren | Bearbeiten | Anglizismus |
| File | Datei | Translate common words |
| Folder | Ordner | Translate common words |
| Konvertieren | Umwandeln | More German |
| Lokation | Standort / Ort | Germanize |
| Managen | Verwalten | Anglizismus in formal contexts |
| Performanz | Leistung | Germanize |
| Validieren | Überprüfen | More natural |

## Placeholder Syntax Reference

Preserve exactly as-is:
- `{variable}` — named placeholder
- `{{variable}}` — escaped/template
- `%s`, `%d`, `%f` — printf-style
- `%1$s`, `%2$d` — positional printf
- `$variable` — shell/PHP style
- `%(name)s` — Python named
- `{0}`, `{1}` — indexed
- `#` — count placeholder inside ICU plural blocks

## ICU MessageFormat Quick Reference

German plural categories: `one` (n=1) and `other` (all else, including 0).

```
{count, plural, one {# Ergebnis} other {# Ergebnisse}}
{count, plural, =0 {Keine Dateien} one {# Datei} other {# Dateien}}
{gender, select, male {sein Profil} female {ihr Profil} other {das Profil}}
```

Watch for adjective agreement in plurals:
- `one {# neuer Tab}` / `other {# neue Tabs}`
- `one {# offene Datei}` / `other {# offene Dateien}`
