# ausbildung-rss-bot

## Purpose
An automated Python tool designed to scan, filter, and track vacancy feeds for IT apprenticeships (Fachinformatiker für Anwendungsentwicklung). The goal of this project is to automate the job search process and demonstrate practical backend logic and AI-assisted development.

## Core Features
* Automated Parsing: Periodically reads data from job portals using RSS and XML feeds.
* Duplicate Prevention: Uses a local storage file (sent_jobs.txt) to log processed vacancies and avoid duplicate entries.
* AI-Assisted Development: Developed and optimized using prompt engineering for fast code generation and debugging.

## Architecture and Files
* parser.py: The main script containing the parsing logic and data processing.
* feed.xml: Configuration file that holds the target RSS URLs and feed sources.
* sent_jobs.txt: A plain text log file used to store the IDs of already processed jobs.

## Technologies Used
* Python 3
* XML parsing and file I/O operations
* Git and GitHub for version control
* AI tools for code generation and refactoring

# Ausbildung RSS Bot

## Zweck
Ein automatisiertes Python-Tool zum Scannen, Filtern und Verfolgen von Ausbildungsplätzen im IT-Bereich (Fachinformatiker für Anwendungsentwicklung). Das Ziel dieses Projekts ist es, den Suchprozess zu automatisieren sowie praktische Backend-Logik und KI-gestützte Entwicklung zu demonstrieren.

## Hauptfunktionen
* Automatisiertes Parsing: Regelmäßiges Auslesen von Daten aus Stellenportalen über RSS- und XML-Feeds.
* Duplikatsprüfung: Verwendet eine lokale Datei (sent_jobs.txt), чтобы регистрировать обработанные вакансии и избегать повторов.
* AI-Assisted Development: Entwickelt und optimiert mittels Prompt Engineering für schnelle Code-Generierung und Fehlersuche.

## Struktur und Dateien
* parser.py: Das Hauptskript mit der Parsing-Logik und Datenverarbeitung.
* feed.xml: Konfigurationsdatei mit den Ziel-RSS-Quellen.
* sent_jobs.txt: Eine Textdatei zur Speicherung bereits verarbeiteter Job-IDs.

## Verwendete Technologien
* Python 3
* XML-Parsing und Datei-Verarbeitung (I/O)
* Git und GitHub zur Versionsverwaltung
* KI-Tools zur Code-Generierung und zum Refactoring
