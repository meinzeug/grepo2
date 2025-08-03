# grepo2

**Git Repository Management Tool mit KI-Integration**

[![Version](https://img.shields.io/badge/version-3.7.3.2-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🚀 Überblick

`grepo2` ist ein fortschrittliches Git Repository Management Tool mit GitHub-Integration und KI-gestützten Features. Die Anwendung kombiniert traditionelle Git-Operationen mit modernen KI-Fähigkeiten für autonome Code-Generierung und intelligente Issue-Bearbeitung.

### ✨ Hauptfeatures

- **🤖 AI-Powered Code Generation**: Autonome Entwicklung mit Codex CLI Integration
- **📋 Intelligentes Issue Management**: Automatische Analyse und Schließung von GitHub Issues
- **🎯 Repository-First Navigation**: Direkter Zugriff auf alle lokalen Repositories
- **🔧 Umfassende Git-Integration**: Alle Git-Operationen in einer intuitiven TUI
- **📊 Automatische Dokumentation**: CHANGELOG.md wird automatisch gepflegt
- **🔒 Sichere Token-Verwaltung**: Verschlüsselte Speicherung von GitHub PATs

## 🏗️ Architektur

### Kernkomponenten

```
grepo2
├── LocalGitAPI          # Git-Operationen (status, commit, push, pull)
├── GitHubAPI           # GitHub Integration (Issues, Comments, Repositories)
├── CodexIntegration    # KI-gestützte Code-Generierung
├── TUI Navigation      # Curses-basierte Benutzeroberfläche
└── Configuration       # Benutzer- und System-Konfiguration
```

### Verzeichnisstruktur

```
~/.config/grepo2/       # Konfigurationsdateien
├── config.json         # Globale Einstellungen
└── users/              # Benutzer-spezifische Konfigurationen
    └── {username}.json

~/github2/{username}/   # Lokale Repository-Verzeichnisse
├── repo1/
├── repo2/
└── backup/

~/.codex/              # Codex CLI Integration
```

## 🛠️ Installation

### Voraussetzungen

- **Python 3.8+**
- **Git CLI**
- **Node.js & npm** (für Codex CLI)
- **GitHub Personal Access Token**

### Automatische Installation

```bash
# grepo2 herunterladen und ausführbar machen
curl -O https://raw.githubusercontent.com/meinzeug/grepo2/main/grepo2_3.7.3.2.py
chmod +x grepo2_3.7.3.2.py

# Erste Ausführung startet automatische Einrichtung
./grepo2_3.7.3.2.py
```

### Systemweite Installation

```bash
# Systemweit installieren (empfohlen)
sudo cp grepo2_3.7.3.2.py /usr/local/bin/grepo2
sudo chmod +x /usr/local/bin/grepo2

# Jetzt von überall aufrufbar
grepo2
```

### Dependencies

```bash
pip install click requests rich
npm install -g @openai/codex  # Für KI-Features
```

## 🚀 Erste Schritte

### 1. Ersteinrichtung

Beim ersten Start wird automatisch die Einrichtung gestartet:

```bash
grepo2
```

**Erforderliche Informationen:**
- GitHub-Benutzername
- [GitHub Personal Access Token](https://github.com/settings/tokens) mit `repo`-Berechtigung
- (Optional) [OpenRouter API Token](https://openrouter.ai/) für erweiterte KI-Features

### 2. Repository-Verwaltung

Nach der Einrichtung zeigt das Hauptmenü alle lokalen Repositories:

```
┌─ grepo2 Hauptmenü ─────────────────────────────────────┐
│ > my-project          (Verwalte Repository: my-project) │
│   website             (Verwalte Repository: website)    │
│   🤖 Codex: Code mit AI generieren                      │
│   Benutzer wechseln                                     │
│   Einstellungen                                         │
│   Exit                                                  │
└────────────────────────────────────────────────────────┘
```

### 3. KI-gestützte Entwicklung

Für automatische Code-Generierung:

1. Repository auswählen
2. "🤖 Codex: Code mit AI generieren" wählen
3. GitHub Issue auswählen (bevorzugt mit "in-work" Label)
4. Codex analysiert und implementiert automatisch

## 🎯 Benutzeroberflächen

### Terminal User Interface (TUI)

**Navigation:**
- **Pfeiltasten**: ↑↓ für Menü-Navigation
- **Enter**: Auswahl bestätigen
- **Q**: Zurück/Beenden

**Hauptmenü-Struktur:**
```
Hauptmenü
├── Repository-Auswahl (direkter Zugriff)
│   ├── Git-Operationen (status, commit, push, pull)
│   ├── Repository-spezifische Codex-Generierung
│   └── Erweiterte Git-Befehle (force push/pull, etc.)
├── 🤖 Globale Codex-Generierung
├── Benutzerverwaltung
├── Einstellungen
│   ├── GitHub Token Management
│   ├── AI-Integration (OpenRouter)
│   └── Repository-Übersicht
└── Projekterstellung
```

### Command Line Interface (CLI)

```bash
grepo2                    # Startet TUI (Standard)
grepo2 go login          # CLI-Login
grepo2 go repo list      # Repository-Liste anzeigen
grepo2 go status         # System-Status prüfen
```

## 🤖 KI-Integration

### Automatisierter Entwicklungsworkflow

1. **Issue-Analyse**: Lädt GitHub Issues mit "in-work" Label
2. **Kontext-Sammlung**: Repository-Struktur, letzte Commits, Kommentare
3. **Prompt-Generierung**: Umfassender Entwicklungsauftrag für Codex
4. **Codex-Ausführung**: Autonome Code-Generierung
5. **AI-Vollständigkeitsanalyse**: JSON-basierte Bewertung mit Confidence-Level
6. **Auto-Close**: Automatisches Schließen bei hoher Confidence (≥80%)

### Unterstützte AI-Modelle

- `openai/gpt-4o` (Standard)
- `anthropic/claude-3.5-sonnet`
- `google/gemini-pro`
- `meta-llama/llama-3-70b-instruct`

### Beispiel-Workflow

```
🎯 ISSUE: #42 - Implement user authentication

📋 BESCHREIBUNG:
Add JWT-based authentication with login/logout functionality

🗂️ REPOSITORY-STRUKTUR:
src/auth.py
src/models/user.py
tests/test_auth.py

📝 LETZTE COMMITS:
- feat: Add user model structure
- fix: Database connection improvements

💬 VORHERIGE KOMMENTARE:
- "Consider using bcrypt for password hashing"
- "Add rate limiting for login attempts"

🤖 CODEX ANALYSE:
✅ Issue als vollständig erkannt (Confidence: 85%)
🎯 Issue automatisch geschlossen
```

## ⚙️ Konfiguration

### GitHub Integration

**Personal Access Token erstellen:**
1. GitHub → Settings → Developer settings → Personal access tokens
2. "Generate new token" klicken
3. Berechtigung `repo` (Full control of private repositories) auswählen
4. Token in grepo2 eintragen

### AI-Integration (Optional)

**OpenRouter Setup:**
1. Account auf [OpenRouter.ai](https://openrouter.ai/) erstellen
2. API-Token generieren
3. In grepo2 Einstellungen → "AI-Anbindung konfigurieren"
4. Token und bevorzugtes Modell auswählen

### Erweiterte Konfiguration

```json
// ~/.config/grepo2/users/{username}.json
{
  "username": "meinzeug",
  "token": "Z2hwX...",  // Base64-kodiert
  "openrouter_token": "sk-or-...",  // Base64-kodiert
  "model": "openai/gpt-4o",
  "created_at": "2025-08-03 10:30:00"
}
```

## 🔧 Git-Operationen

### Unterstützte Befehle

| Operation | Beschreibung | Verwendung |
|-----------|--------------|------------|
| **Status prüfen** | `git status --porcelain` | Zeigt geänderte Dateien |
| **Commit erstellen** | `git commit` | Öffnet Editor oder nutzt Message |
| **Push/Pull** | Standard Git-Sync | Normale Synchronisation |
| **Force Push** | `git push --force` | Überschreibt Remote mit Lokal |
| **Force Pull** | `git reset --hard origin/main` | Überschreibt Lokal mit Remote |
| **Hard Update** | `git push --force-with-lease` | Sicherer Force-Push |
| **Soft Update** | `git pull --ff-only` | Fast-forward-only Pull |

### Repository-Management

```bash
# Repository-spezifische Operationen
┌─ Verwalte: my-project ──────────────────────────────────┐
│ > Status prüfen                                         │
│   Commit erstellen                                      │
│   Online-Repo mit Lokal überschreiben                   │
│   Lokales Repo mit Online überschreiben                 │
│   🤖 Codex für dieses Repository                        │
│   Zurück zum Hauptmenü                                  │
└─────────────────────────────────────────────────────────┘
```

## 📊 Features der aktuellen Version (3.7.3.2)

### 🔧 Navigation Restoration
- **Vollständige Repository-Auswahl** im Hauptmenü wiederhergestellt
- **Modernes Look & Feel** aus v3.7.3.1 beibehalten
- **Alle v3.7.3+ Features** erhalten (Auto-Close, CHANGELOG)

### 🚀 Erweiterte Features
- **Auto-Close Issues**: KI-basierte Vollständigkeitsbewertung
- **CHANGELOG Integration**: Automatische Aktivitätsdokumentation
- **Enhanced Codex**: Repository-spezifische Code-Generierung
- **Smart Issue Management**: Label-basierte Priorisierung

### 📋 Vollständige Menu-Matrix

| Menu Level | Options | Status |
|------------|---------|--------|
| **Main Menu** | Repository List | ✅ Direkter Repository-Zugriff |
| **Main Menu** | Codex Generation | ✅ AI-gestützte Code-Generierung |
| **Main Menu** | User Management | ✅ Profil-Switching |
| **Main Menu** | Settings | ✅ GitHub & AI-Konfiguration |
| **Repository** | Git Operations | ✅ Vollständige Git-Integration |
| **Repository** | Codex for Repo | ✅ Repository-spezifische AI |
| **Settings** | GitHub Token | ✅ PAT-Management |
| **Settings** | AI Integration | ✅ OpenRouter & Modell-Config |

## 🛡️ Sicherheit

### Token-Verwaltung
- **Base64-Obfuskation** für alle sensiblen Daten
- **Keine Klartext-Speicherung** von API-Tokens
- **Lokale Konfiguration** in `~/.config/grepo2/`

### GitHub-Berechtigungen
- **Minimale Berechtigung**: Nur `repo`-Scope erforderlich
- **Token-Validierung** bei jeder Konfiguration
- **Sichere API-Calls** mit User-Agent-Identifikation

## 🔄 Entwicklungsphilosophie

### Incremental Development
- **Kleine Schritte**: Entwicklung in 10-15 nachvollziehbaren Schritten
- **Feature Preservation**: Neue Versionen behalten alle bestehenden Features
- **Regression Handling**: Systematische Behebung durch Patch-Versionen

### Documentation-First
- **CHANGELOG.md**: Umfassende Dokumentation aller Änderungen
- **AGENTS.md**: AI-Entwicklungsrichtlinien für zukünftige Verbesserungen
- **Code Comments**: Ausführliche Kommentierung komplexer Funktionen

## 📈 Roadmap

### Geplante Features
- **Multi-Repository Operations**: Batch-Operationen über mehrere Repos
- **Advanced AI Prompts**: Template-basierte Prompt-Generierung
- **Git Flow Integration**: Automatisierte Branching-Strategien
- **Team Collaboration**: Multi-User-Features
- **Plugin System**: Erweiterbare Architektur

### Aktuelle Entwicklung
Siehe [CHANGELOG.md](CHANGELOG.md) für detaillierte Versionshistorie und [AGENTS.md](AGENTS.md) für AI-Entwicklungsrichtlinien.

## 🤝 Beitragen

### Entwicklung
```bash
# Repository klonen
git clone https://github.com/meinzeug/grepo2.git
cd grepo2

# Dependencies installieren
pip install -r requirements.txt
npm install -g @openai/codex

# Entwicklungsversion starten
python grepo2_3.7.3.2.py
```

### AI-Assisted Development
Das Projekt nutzt systematische AI-gestützte Entwicklung. Siehe [AGENTS.md](AGENTS.md) für:
- **Incremental Development Workflows**
- **Bug Fix Methodologies**
- **Feature Development Standards**
- **Technical Quality Guidelines**

## 📞 Support

### Dokumentation
- **[CHANGELOG.md](CHANGELOG.md)**: Vollständige Versionshistorie
- **[AGENTS.md](AGENTS.md)**: AI-Entwicklungsrichtlinien
- **Inline-Hilfe**: Verwende `Q` in der TUI für Hilfe

### Issues
Bei Problemen oder Feature-Requests erstelle ein [GitHub Issue](https://github.com/meinzeug/grepo2/issues) mit:
- **Version**: `grepo2 go status` ausführen
- **Umgebung**: OS, Python-Version, Git-Version
- **Reproduktion**: Schritte zur Nachstellung des Problems

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) für Details.

---

**grepo2 v3.7.3.2** - Git Repository Management mit KI-Integration  
Entwickelt mit ❤️ und 🤖 von [meinzeug](https://github.com/meinzeug)
