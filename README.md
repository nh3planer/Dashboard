# Projekt-Dashboard

Webbasierte Projekt-Dashboard-Anwendung zur Soll-/Ist-Steuerung von Terminen und Kosten.

## Technologie-Stack

- **Oberfläche (Browser):** TypeScript mit React (Vite), Gestaltung in CSS, Diagramme mit Recharts
- **Server:** JavaScript auf Node.js mit dem Web-Framework Express
- **Datenbank:** SQLite in einer einzigen Datei (`data/dashboard.db`), abgefragt mit SQL (better-sqlite3)

Die Datenbank wird beim ersten Start automatisch inkl. Demo-Daten angelegt.

## Funktionen

- **Projektübersicht** mit Status (Geplant / Aktiv / Kritisch / Abgeschlossen), Fortschritt,
  Soll-/Ist-Terminen und Soll-/Ist-Kosten je Projekt
- **KPI-Karten**: Projektzahlen, Budget Soll/Ist, Kostenabweichung, kritische Projekte
- **Terminplan**: Meilensteine je Projekt mit Soll- und Ist-Datum, Verspätungsanzeige,
  Abhaken erledigter Meilensteine (schreibt in die Datenbank)
- **Kosten**: Soll-/Ist-Vergleich je Periode (Balkendiagramm) und kumulierter Kostenverlauf (Liniendiagramm)
- **Fortschritts-Steuerung** direkt aus der Oberfläche (+/−10 %)

## Installation & Start

Voraussetzung: Node.js 20+.

```bash
# Backend
cd server
npm install
npm start                  # http://127.0.0.1:3000

# Frontend (zweites Terminal)
cd client
npm install
npm run dev                # http://127.0.0.1:5173 (Proxy auf Backend)
```

Der Express-Server liefert im Produktivbetrieb auch das gebaute Frontend aus:

```bash
cd client && npm run build
cd ../server && npm start  # komplette App unter http://127.0.0.1:3000
```

## REST-API (Auszug)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/summary` | Projekt- und Kosten-Kennzahlen |
| GET | `/api/projects?details=true` | Projektliste inkl. Aggregaten |
| GET | `/api/projects/:id` | Projekt mit Meilensteinen und Kosten |
| POST | `/api/projects` | Projekt anlegen |
| PUT | `/api/projects/:id` | Projekt aktualisieren |
| POST | `/api/projects/:id/milestones` | Meilenstein anlegen |
| PUT | `/api/milestones/:id` | Meilenstein aktualisieren |
| PUT | `/api/projects/:id/costs/:month` | Kosten Soll/Ist je Periode |

## Verzeichnisse

- `server/` – Express-API + SQLite-Zugriff (`src/db.js`, `src/server.js`)
- `client/` – React-Frontend (Vite, TypeScript)
- `data/` – SQLite-Datenbankdatei (wird ignoriert, automatisch erzeugt)
- `legacy-python/` – frühere Python/FastAPI-Version (referenziert, nicht mehr der aktive Stack)
