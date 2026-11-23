# Projekt-Dashboard

Eine webbasierte Projekt-Dashboard-Anwendung mit rollenbasierter Zugriffskontrolle (RBAC),
Standard-KPIs und vertraulichen Management-KPIs, Soll-/Ist-Verfolgung von Terminen und Kosten
sowie auswählbaren PDF-Berichten (serverseitig generiert).

## Technologie-Stack (Empfehlung zur Datenanbindung)

- **Backend:** Python / FastAPI
- **Datenbank:** SQLite (Datei `data/dashboard.db`) – wartungsfrei, wird beim ersten Start
  automatisch inkl. Demo-Daten angelegt. Für den Produktivbetrieb kann später ohne Code-Änderung
  auf PostgreSQL o. Ä. migriert werden (DAL in `backend/db.py` gekapselt).
- **Auth:** JWT-Tokens, Passwort-Hashing mit PBKDF2-SHA256
- **PDF-Reports:** ReportLab (serverseitige Generierung)
- **Frontend:** Vanilla JS + Chart.js (lokal unter `static/` verfügbar, kein CDN nötig)

## Installation & Start

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Danach im Browser öffnen: <http://localhost:8000>

> **Hinweis:** Vor Produktivbetrieb den JWT-Schlüssel über `DASHBOARD_JWT_SECRET` setzen.

## Demo-Zugänge (Passwort jeweils `demo123`)

| Benutzername        | Rolle           | Rechte                                                              |
|---------------------|-----------------|---------------------------------------------------------------------|
| `chef`              | Geschäftsführer | Alle Bereiche inkl. Benutzerverwaltung und Management-KPIs          |
| `mgmt`              | Management      | Standard- & Management-KPIs, alle Projekte, PDF-Reports             |
| `pl` / `pl2`        | Projektleiter   | Standard-KPIs, Vollzugriff auf eigene Projekte                      |
| `kunde`             | Kunde / Bauherr | Read-only: Status, Termine und Kundenbericht des eigenen Projekts   |

> **Tipp:** Auf der Anmeldeseite gibt es Ein-Klick-Buttons für alle Demo-Zugänge – kein Tippen nötig.
> Die langen Namen (`geschaeftsfuehrer`, `management`, `projektleiter`) bleiben als Alias weiterhin gültig, Umlaute („geschäftsführer“) und Groß-/Kleinschreibung sind egal.

Neue Benutzer werden über die **Benutzerverwaltung** (nur Geschäftsführer) angelegt –
einschließlich Kunden-/Bauherren-Zugängen mit Projektkopplung.

## KPIs

### Standard-KPIs (Projektteam)
- SPI (Schedule Performance Index, EV/PV) und CPI (Cost Performance Index, EV/AC)
- Fertigstellungsgrad & Meilenstein-Erreichung (termingerecht)
- Ressourcenauslastung & Aufwandsabweichung (inkl. Überlastungs-Warnung)
- Scope-/Änderungsquote (Change Requests)
- Qualitätskennzahlen: Fehlerquote, Nacharbeitsstunden, offene kritische Issues

### Management-KPIs (vertraulich – nur Rollen GF/Management)
Die Management-Ansicht ist im Frontend nur mit entsprechender Berechtigung sichtbar;
der Zugriff wird zusätzlich serverseitig erzwungen (`403` sonst).

- ROI & Business Value / Nutzenrealisierung
- Budgetauslastung & Gesamtkostenabweichung, Deckungsbeitrag, Nachfinanzierungsbedarf
- Portfolio-Status (Ampel) & kritische Pfad-Abweichungen, Kapital in Gefahr
- Top-Risiken & Eskalationsbedarf (Score = Wahrscheinlichkeit × Auswirkung)
- Kapazitätsengpässe über Bereiche hinweg
- Stakeholder-/Kundenzufriedenheit (NPS)

## PDF-Berichte (im Bereich „Berichte“ auswählbar)

| Bericht                  | Inhalt                                        | Rollen                          |
|--------------------------|-----------------------------------------------|---------------------------------|
| Projekt-Statusbericht    | Standard-KPIs, Meilensteine Soll/Ist         | alle                           |
| Kostenbericht            | Soll-/Ist-Kosten je Position                  | GF, Management, Projektleiter  |
| Terminbericht            | Terminplan, Meilensteine                      | alle                           |
| Management-Report        | Management-KPIs, Portfolio, Top-Risiken      | nur GF & Management            |
| Kundenbericht            | vereinfachter Status für Bauherrn             | alle                           |

## Alternative: „Einfach nur ein Link“ – Hosting statt lokaler Installation

Lokales Starten nicht möglich oder nicht gewünscht (z. B. ohne Python / ohne Kommandozeile)? Die Anwendung kann auch als Web-Dienst gehostet werden – danach genügt das Öffnen einer URL im Browser.

Vorbereitet dafür:

- `Dockerfile` (Container-Image mit uvicorn auf Port 8000)
- `render.yaml` (Konfiguration für [Render](https://render.com), Free-Tier-tauglich; erzeugt automatisch einen sicheren JWT-Schlüssel)

**Schritte auf Render (Beispiel, ~5 Minuten, nur Browser nötig):**

1. Dieses GitHub-Repository (bzw. der `main`-Branch nach Merge) muss in Ihrem GitHub-Konto liegen
2. Auf render.com mit GitHub anmelden → **„New Web Service“** → Repository `Dashboard` auswählen
3. Render erkennt `render.yaml`/`Dockerfile` automatisch → Service erstellen
4. Nach wenigen Minuten ist das Dashboard unter `https://<dienstname>.onrender.com` erreichbar (Anmeldung wie oben)

Analog funktionieren Railway, Fly.io, Azure/AWS-Container oder ein firmeneigener Server (nur `docker build` + `docker run -p 8000:8000 ...`).

> Hinweis: Das Free-Tier eignet sich gut für Demo/Evaluation. SQLite liegt dann im Container (beim Demo-Betrieb mit Seed-Daten unproblematisch); für produktiven Betrieb wird ein persistentes Volume oder PostgreSQL empfohlen.

## Projektstruktur

```
backend/
  main.py     – FastAPI-Endpunkte (Auth, KPIs, Projekte, Benutzer, Reports)
  db.py       – SQLite-Schema, Seed-Daten, Datenzugriff
  auth.py     – JWT & Passwort-Hashing
  rbac.py     – Rollen-/Rechteprüfung
  kpi.py      – KPI-Berechnung (Standard & Management)
  reports.py  – PDF-Generierung mit ReportLab
static/       – Frontend (index.html, app.js, style.css, Chart.js)
requirements.txt
```
