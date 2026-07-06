# Aisle 5 – Home Assistant Integration

Custom Component, das Läden, Listen und Öffnungszeiten aus [Aisle 5](https://github.com/apeterka/Aisle_5) (Einkaufslisten-App) in Home Assistant abbildet: eine `todo`-Liste pro Laden, automatisch angelegte Zonen aus den Ladenkoordinaten, und ein `binary_sensor` je Laden für „aktuell geöffnet".

## Installation

### Über HACS (empfohlen)

1. HACS → Integrationen → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**.
2. URL `https://github.com/apeterka/Aisle_5-homeassistant` eintragen, Kategorie **Integration**.
3. "Aisle 5" installieren, Home Assistant neu starten.

### Manuell

1. `custom_components/aisle5` in das `custom_components`-Verzeichnis deiner Home-Assistant-Konfiguration kopieren (z. B. `/config/custom_components/aisle5`).
2. Home Assistant neu starten.

### Einrichtung

1. In Aisle 5 unter **Einstellungen > Home Assistant** einen API-Key generieren.
2. In Home Assistant: **Einstellungen > Geräte & Dienste > Integration hinzufügen > Aisle 5**, Adresse und den generierten API-Key eintragen.

> **Welche Adresse eintragen?** Bei einem Docker-Deployment (siehe [DEPLOYMENT_GUIDE.md](https://github.com/apeterka/Aisle_5/blob/main/DEPLOYMENT_GUIDE.md) im Aisle-5-Hauptrepo) läuft der Backend-Container intern auf Port 3001 und ist **nicht** öffentlich erreichbar – das Frontend-Nginx leitet `/api/*` bereits an ihn weiter. Verwende daher die gleiche Adresse wie für die App im Browser, z. B. `http://<vm-ip>` (Port 80) oder deine Domain, **nicht** `http://<vm-ip>:3001`. Nur bei lokaler Entwicklung ohne Docker (`npm start` im `backend`-Ordner) ist `http://localhost:3001` korrekt.

Beim ersten Sync werden automatisch Zonen für alle Läden mit hinterlegten Koordinaten angelegt (Standard-Radius 150 m) und pro Laden eine `todo`-Liste erstellt. Die Integration registriert außerdem automatisch einen Webhook in Aisle 5, sodass Änderungen (Artikel hinzugefügt/abgehakt) sofort statt erst beim nächsten 15-Minuten-Poll ankommen.

### Zonen-Radius anpassen

Über **Einstellungen → Geräte & Dienste → Aisle 5 → Konfigurieren** lässt sich der Radius (in Metern) für alle automatisch angelegten Zonen ändern. Bereits bestehende Zonen werden dabei aktualisiert, nicht dupliziert.

## Erinnerungs-Automatisierung

Sobald Zonen und `todo`-Listen existieren, kann pro Laden eine Automatisierung eingerichtet werden: Zonen-Enter-Trigger auf der eigenen `person`-Entity + Bedingung „`todo`-Liste nicht leer" + Benachrichtigung.

## Hintergrund

Dieses Repository enthält ausschließlich die Home-Assistant-seitige Integration. Die Architektur-Entscheidungen (API-Key-Auth, signierte Webhooks, automatische Zonen-Erzeugung) sind dokumentiert in [ADR-0026](https://github.com/apeterka/Aisle_5/blob/main/docs/adr/0026-home-assistant-integration.md) und [ADR-0027](https://github.com/apeterka/Aisle_5/blob/main/docs/adr/0027-ha-integration-eigenes-repo.md) im [Aisle-5-Hauptrepo](https://github.com/apeterka/Aisle_5).
