# CHANGELOG

Alle Änderungen an grepo2 werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/), und dieses Projekt folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Version 3.7.4.2 (2025-08-03) - OPENROUTER MODEL LOADING BUGFIX
**🔧 Critical NoneType Comparison Error Fix**

#### ⚠️ Critical Bug Fixed
- **FIXED**: "'>' not supported between instances of 'int' and 'NoneType'" error in OpenRouter model loading
- **ROOT CAUSE**: OpenRouter API returns None values for `max_completion_tokens` and `context_length` in some models
- **SOLUTION**: Added proper None-value handling in `get_sort_key()` function before comparison operations
- **IMPACT**: AI-Integration configuration now works reliably without crashes

#### 🔧 Technical Implementation
- **Modified Function**: `fetch_openrouter_models()` in line ~295
- **Fix Location**: `get_sort_key()` helper function within model sorting logic
- **Change**: Added explicit None-to-zero conversion before `max()` comparison
- **Code Change**: 
  ```python
  # Before (causing error):
  return max(max_completion, context_length, 0)
  
  # After (fixed):
  max_completion = max_completion if max_completion is not None else 0
  context_length = context_length if context_length is not None else 0
  return max(max_completion, context_length, 0)
  ```

#### 🎯 Error Flow Fixed
```
Einstellungen → AI-Integration konfigurieren → OpenRouter Token eingeben
→ 🔍 Lade verfügbare coding models von OpenRouter...
→ ❌ (BEFORE) Unerwarteter Fehler: '>' not supported between instances of 'int' and 'NoneType'
→ ✅ (AFTER) Erfolgreiches Laden und Sortieren der Models
```

#### 🛡️ Robustness Improvements
- **Type Safety**: Explicit handling of None values from API responses
- **Graceful Degradation**: Models with missing data still processable
- **Preserved Functionality**: All existing OpenRouter features remain intact
- **Backward Compatibility**: No breaking changes to configuration or workflow

---

### Version 3.7.4.1 (2025-08-03) - OPENROUTER API INTEGRATION
**🚀 Live Free Coding Models from OpenRouter**

#### ⭐ Major Feature
- **NEW**: Automatisches Abrufen der besten 4 free coding models von OpenRouter API
- **ENHANCED**: Dynamische Model-Auswahl basierend auf Live-API-Daten statt hardcoded Liste
- **INTELLIGENT**: Filterung nach coding/development/software Kriterien
- **OPTIMIZED**: Sortierung nach Kontext-Länge und Performance-Metriken

#### 🚀 Key Improvements
- **Live Model Fetching**: API-basierte Abfrage der aktuell verfügbaren free models
- **Smart Filtering**: Automatische Erkennung von coding-relevanten models durch Keyword-Analyse
- **Performance Ranking**: Sortierung nach max_completion_tokens und context_length
- **Graceful Fallback**: Rückfall auf Standard-Models bei API-Fehlern oder fehlendem Token

#### 🔧 Technical Implementation
- **NEW Function**: `fetch_openrouter_models(token)` für Live-API-Integration
- **Enhanced `tui_ki_anbindung()`**: Automatische Model-Erkennung und -Auswahl
- **Error Handling**: Robuste Behandlung von Netzwerk-Timeouts und API-Fehlern
- **User Experience**: Detaillierte Anzeige von Model-Informationen mit Kontext-Längen

#### 🎯 User Workflow Enhancement
```
Einstellungen → AI-Anbindung konfigurieren → OpenRouter Token eingeben
→ 🔍 Automatisches Laden der Top 4 free coding models
→ ✨ Auswahl aus live gefetchten, performance-optimierten models
→ 🚀 Speichern mit optimaler Model-Konfiguration
```

#### 📋 API Integration Details
- **Endpoint**: `GET https://openrouter.ai/api/v1/models`
- **Filtering**: Nur models mit pricing.prompt = "0" und pricing.completion = "0"
- **Keywords**: code, coding, development, software, programming, dev, instruct, chat, assistant, coder, engineer
- **Sorting**: Nach context_length und max_completion_tokens (descending)
- **Limit**: Top 4 models für optimale Auswahl-UX

#### 🛡️ Error Resilience
- **Network Timeout**: 10 Sekunden timeout mit graceful fallback
- **API Errors**: Detaillierte Fehlermeldungen und Standard-Model-Liste
- **Token Validation**: Implizite Validierung durch erfolgreiche API-Calls
- **Backward Compatibility**: Funktioniert weiterhin ohne OpenRouter Token

### Version 3.7.3.4 (2025-08-03) - CONFIGURATION ERROR HANDLING
**🔧 Base64 Padding & Token Recovery Fix**

#### ⭐ Major Fix
- **FIXED**: "Incorrect padding" error in base64 token decoding 
- **IMPROVED**: Robust user configuration loading with automatic recovery
- **ENHANCED**: Better error messages and recovery guidance for corrupted tokens
- **MAINTAINED**: All existing functionality while improving reliability

#### 🚀 Key Improvements
- **Automatic Padding**: Base64 decoder now handles missing padding automatically
- **Graceful Degradation**: Corrupted tokens don't crash the application
- **Recovery Instructions**: Clear guidance when tokens need to be updated
- **Backward Compatibility**: Still works with existing valid configurations

#### 🔧 Technical Implementation
- **Enhanced `_deobfuscate()`**: Automatic padding calculation and fallback handling
- **Improved `load_user_config()`**: Individual token validation with specific error messages
- **Better Error Handling**: Distinguishes between GitHub and OpenRouter token issues
- **User Guidance**: Provides specific instructions for fixing configuration problems

#### 🐛 Specific Bug Fixes
- **Base64 Error**: "Incorrect padding" → Automatic padding correction
- **Configuration Loading**: Graceful handling of corrupted token data
- **User Experience**: Clear error messages instead of cryptic technical errors
- **Token Recovery**: Guides users to fix their configuration through settings

#### 🎯 Error Flow Before Fix
```
Hauptmenü → Projekterstellung → REPONAME → Code generieren mit Codex
→ ⚠ Fehler beim Laden der Benutzer-Konfiguration: Incorrect padding
→ ❌ Benutzer-Konfiguration nicht gefunden
```

#### ✅ Error Flow After Fix
```
Hauptmenü → Projekterstellung → REPONAME → Code generieren mit Codex
→ ⚠ Fehler beim Dekodieren des GitHub-Tokens: Incorrect padding  
→ 💡 Bitte aktualisiere dein GitHub Token in den Einstellungen
→ [Continues with graceful recovery]
```

---

### Version 3.7.3.3 (2025-08-03) - MISSING FUNCTION RESTORATION
**🔧 Critical NameError Fix**

#### ⭐ Major Fix
- **RESTORED**: Missing `tui_projekterstellung_menu` function that caused NameError crash
- **ADDED**: Repository-specific Codex generation via `tui_codex_generate_for_repo`
- **FIXED**: Project creation menu now fully functional with roadmap/issues/codex options
- **PRESERVED**: All v3.7.3+ features (auto-close issues, CHANGELOG integration, AI analysis)

#### 🚀 Key Improvements
- **Error-Free Navigation**: Project creation menu no longer crashes with NameError
- **Dual Codex Access**: Codex available both in main menu and project creation submenu
- **Repository Context**: Project creation menu provides repository-specific code generation
- **Full Functionality**: All menu options now work as intended from previous versions

#### 📋 Fixed Menu Structure
| Menu Path | Function | Status |
|-----------|----------|--------|
| **Main Menu** → **Projekterstellung** | ✅ Now functional, no NameError |
| **Projekterstellung** → **Code generieren mit Codex** | ✅ Repository-specific AI generation |
| **Projekterstellung** → **Roadmap generieren** | ✅ Placeholder (planned) |
| **Projekterstellung** → **Projekt auf GitHub einrichten** | ✅ Placeholder (planned) |

#### 🔧 Technical Implementation
- **Function Added**: `tui_projekterstellung_menu(repo_path: Path)` with full menu structure
- **Support Function**: `tui_codex_generate_for_repo(repo_path: Path)` for repository-specific calls
- **Parameter Compatibility**: Handles both parameterized (from project menu) and non-parameterized (from main menu) Codex calls
- **Code Preservation**: All existing Codex classes and AI integration functionality maintained

#### 🎯 User Experience
- **Crash-Free Operation**: No more NameError when accessing project creation
- **Intuitive Menu Flow**: Repository selection → Project creation → Specific actions
- **Consistent Interface**: Rich console output with emojis and color coding maintained
- **Feature Complete**: Restores all functionality described in issue report

#### 🐛 Specific Bug Fixes
- **NameError Fix**: `tui_projekterstellung_menu` is not defined → Function properly implemented
- **Menu Access**: Project creation menu fully restored with all expected options
- **Codex Integration**: Repository-specific code generation working in project context
- **Function Signatures**: Proper parameter handling for different calling contexts

---

# CHANGELOG.md

## grepo2 - Git Repository Management Tool

### Version 3.7.3.2 (2025-08-03) - TUI NAVIGATION RESTORATION
**🔧 Complete Menu Structure Restoration**

#### ⭐ Major Fix
- **RESTORED**: Complete repository selection in main menu from v3.7.2
- **RESTORED**: Full repository management functionality with git operations
- **RESTORED**: Settings menu, user management, and project creation workflows
- **ENHANCED**: Modern look & feel from v3.7.3.1 maintained throughout
- **PRESERVED**: All v3.7.3+ features (auto-close issues, CHANGELOG integration, AI analysis)

#### 🚀 Key Improvements
- **Repository-First Navigation**: Main menu now shows all repositories for direct selection
- **Complete Git Management**: Status, commit, push/pull operations per repository
- **Enhanced Codex Integration**: Repository-specific AI code generation
- **Issue Management**: Full GitHub issue workflow with in-work label filtering
- **Settings & Configuration**: GitHub token, AI integration, and repository settings

#### 📋 Restored Menu Structure
| Menu Level | Options | Description |
|------------|---------|-------------|
| **Main Menu** | Repository List | ✅ Direct repository selection restored |
| **Main Menu** | Codex Generation | ✅ AI-powered code generation |
| **Main Menu** | User Management | ✅ Profile switching and configuration |
| **Main Menu** | Settings | ✅ GitHub & AI configuration |
| **Main Menu** | Project Creation | ✅ Roadmap & issue management |
| **Repository** | Git Operations | ✅ Status, commit, push, pull |
| **Repository** | Codex for Repo | ✅ Repository-specific AI generation |
| **Settings** | GitHub Token | ✅ PAT management |
| **Settings** | AI Integration | ✅ OpenRouter & model configuration |
| **Settings** | Repository List | ✅ Local repository overview |

#### 🔧 Technical Implementation
- **Curses TUI**: Original v3.7.2 navigation with arrow keys and visual highlighting
- **Modern Rich UI**: v3.7.3.1 styling for status messages and progress indicators
- **Incremental Development**: 19 systematic steps to avoid timeout limits
- **Feature Preservation**: Zero functionality loss from previous versions

#### 🎯 User Experience
- **Intuitive Navigation**: Repositories prominently displayed for easy access
- **Contextual Menus**: Repository-specific options when selected
- **Visual Feedback**: Rich console output with emojis and color coding
- **Seamless Workflow**: From repository selection to code generation in minimal steps

#### 🔄 Development Process
- **Problem Analysis**: TUI regression identified through user feedback
- **Code Archaeology**: Systematic analysis of v3.7.2 menu structure
- **Incremental Restoration**: Step-by-step rebuilding with modern enhancements
- **Quality Assurance**: Preservation of all advanced features while fixing regression

---

### Version 3.7.3.1 (2024-12-19) - HOTFIX
**🔧 Startup Behavior Regression Fix**

#### ⚠️ Critical Fix
- **RESTORED**: Original startup behavior where `grepo2` starts TUI directly
- **RESTORED**: CLI access via `grepo2 go` prefix (e.g., `grepo2 go repo list`)
- **PRESERVED**: All v3.7.3 features (auto-close issues, CHANGELOG integration)

#### 🛠️ Technical Details
- **Issue**: v3.7.3 inadvertently changed startup behavior, requiring `grepo2 tui` command
- **Root Cause**: Main entry point was modified to default to CLI instead of TUI
- **Solution**: Restored original logic from v3.7.1 while preserving v3.7.3 enhancements
- **Validation**: Maintains backward compatibility for existing users

#### 📋 Behavior Matrix
| Command | Action | Notes |
|---------|--------|-------|
| `grepo2` | Start TUI | ✅ Restored default behavior |
| `grepo2 go login` | CLI login | ✅ Preserved CLI access |
| `grepo2 go repo list` | CLI repo list | ✅ Preserved CLI access |
| `grepo2 go status` | CLI status | ✅ Preserved CLI access |

#### 🔄 Development Process
- **Methodology**: Incremental development to avoid timeout issues
- **Analysis**: Systematic comparison between v3.7.1 and v3.7.3 startup logic
- **Documentation**: Created comprehensive AGENTS.md for future AI development
- **Quality**: Preserved all existing functionality while fixing regression

---

### Version 3.7.3 (2024-12-19)

### 🎯 **Hauptfeatures**
- **Automatisches Issue-Closing**: AI analysiert nach Codex-Generierung ob Issues vollständig gelöst sind und schließt sie automatisch
- **CHANGELOG.md Integration**: Alle Codex-Aktivitäten, Issue-Analysen und Änderungen werden automatisch dokumentiert
- **Erweiterte AI-Analyse**: Strukturierte JSON-basierte Bewertung mit Confidence-Levels und Handlungsempfehlungen

### ✅ **Hinzugefügt**
- `write_to_changelog()` Funktion für automatische Dokumentation mit Emojis und Timestamps
- `close_issue()` Methode in GitHubAPI-Klasse für automatisches Issue-Schließen
- `analyze_issue_completion()` in CodexIntegration für intelligente Vollständigkeits-Analyse
- Erweiterte Repository-Kontext-Sammlung (Dateibaum, Commits, Kommentare)
- Strukturierte AI-Antworten mit JSON-Format und Validierung
- Automatische CHANGELOG-Updates bei jeder Codex-Operation

### 🔧 **Verbessert**
- `execute_codex_for_issue()` führt jetzt vollständige Workflow-Automatisierung durch
- `_format_analysis_comment()` erstellt detaillierte GitHub-Kommentare mit Analyse-Ergebnissen  
- Robuste Fehlerbehandlung bei AI-API-Aufrufen
- Bessere Benutzerführung mit Progress-Indikatoren

### 📊 **Technische Details**
- **Codebase**: 1686 Zeilen (vs. 1282 in v3.7.2)
- **Neue Abhängigkeiten**: Erweiterte JSON-Parsing-Logik
- **API-Integration**: OpenRouter AI für Issue-Analyse
- **Dateisystem**: Automatische CHANGELOG.md-Erstellung und -Wartung

---

## [3.7.2] - 2025-08-03

### 🔧 **Vollständige Funktionalitäts-Wiederherstellung**
- **Komplette Issue-Verarbeitung**: Wiederherstellung der vollständigen GitHub Issue-Integration
- **Curses TUI Navigation**: Funktionsfähige Pfeiltasten-Navigation mit visueller Hervorhebung
- **Codex-Workflow**: Vollständige Issue-basierte Code-Generierung mit Repository-Kontext

### ✅ **Hinzugefügt**
- `CodexIntegration` Klasse mit umfassender Issue-Verarbeitung
- `tui_codex_generate()` mit vollständiger GitHub Issue-Workflow
- `LocalGitAPI` erweitert um Repository-Kontext-Funktionen
- `GitHubAPI` mit Issue- und Kommentar-Management
- Repository-Details-Anzeige mit formatierter Ausgabe
- Issue-Auswahl mit Curses-TUI und Filtern nach "in-work" Labels

### 🔧 **Verbessert**
- `run_curses_menu()` mit stabiler Pfeiltasten-Navigation
- `get_repo_selection_with_details()` für interaktive Repository-Auswahl
- `display_repository_info()` für formatierte Repository-Darstellung
- Umfassende Kontext-Sammlung für bessere Code-Generierung

### 🐛 **Behoben**
- Fehlende Issue-Verarbeitung aus Version 3.7.1 wiederhergestellt
- Curses TUI Navigation vollständig funktionsfähig
- Codex-Integration mit vollständigem Feature-Set

### 📊 **Technische Details**
- **Codebase**: 1282 Zeilen, 52KB
- **Architektur**: Modulare Klassenstruktur für APIs und TUI
- **Dependencies**: Rich, Click, Curses für optimale UX

---

## [3.7.1] - 2025-08-03

### ⚠️ **Regression-Version** (Stepping Stone)
- **Curses TUI**: Wiederherstellung der Pfeiltasten-Navigation aus Version 3.5
- **Vereinfachtes Codex**: Nur Basis-Prompt-Input ohne Issue-Integration
- **Übergangslösung**: Brücke zwischen defekter 3.7 und vollständiger 3.7.2

### ✅ **Hinzugefügt**
- Funktionsfähige `run_curses_menu()` mit visueller Hervorhebung
- Basis-Codex-Funktionalität mit einfachem Prompt-Input
- `tui_codex_generate()` für vereinfachte Code-Generierung

### ❌ **Bekannte Einschränkungen**
- Keine Issue-basierte Code-Generierung
- Fehlende GitHub Issue-Integration
- Reduzierte Codex-Funktionalität im Vergleich zu 3.7

### 📊 **Technische Details**
- **Codebase**: 933 Zeilen, 37KB
- **Status**: Zwischenversion für TUI-Restauration

---

## [3.7.0] - 2025-08-03

### ❌ **Fehlerhafte Version**
- **Defekte TUI**: Curses-Navigation nicht funktionsfähig
- **Issue-Integration**: Vollständige GitHub Issue-Verarbeitung vorhanden aber TUI-defekt
- **Problem**: Menü-Navigation mit Pfeiltasten nicht möglich

### ⚠️ **Erkannte Probleme**
- TUI-Menü zeigt keine visuelle Hervorhebung
- Pfeiltasten-Navigation funktionslos
- Benutzer-Interface nicht verwendbar

---

## [3.6.x und früher]

### 📚 **Historische Versionen**
- **3.5.x**: Stabile Curses TUI-Navigation (als Referenz für Wiederherstellung)
- **3.0.x**: Basis GitHub-Repository-Management
- **2.x.x**: Erste CLI-Implementierung
- **1.x.x**: Prototyp-Versionen

---

## 🔄 **Entwicklungs-Workflow**

### **Version 3.7.1 → 3.7.2**
1. **Problem-Analyse**: TUI funktioniert, aber Issue-Integration fehlt
2. **Code-Archäologie**: Untersuchung der 3.7.0 für vollständige Feature-Liste
3. **Systematische Wiederherstellung**: Schritt-für-Schritt Integration der Issue-Features
4. **Validation**: Vollständige Funktionalitätsprüfung

### **Version 3.7.2 → 3.7.3**
1. **Anforderungsanalyse**: Automatisches Issue-Closing + CHANGELOG-Integration
2. **AI-Integration**: OpenRouter API für Issue-Vollständigkeits-Analyse
3. **Workflow-Automatisierung**: End-to-End Issue-Management
4. **Dokumentation**: Automatische CHANGELOG-Erstellung

---

## 🎯 **Roadmap & Geplante Features**

### **Version 3.8.x** (Geplant)
- [ ] **Multi-Repository-Workflows**: Übergreifende Issue-Verarbeitung
- [ ] **Erweiterte AI-Modelle**: Support für mehr OpenRouter-Modelle
- [ ] **Issue-Templates**: Automatische Issue-Erstellung mit Templates
- [ ] **Projekt-Boards**: GitHub Projects Integration

### **Version 3.9.x** (Geplant)
- [ ] **CI/CD-Integration**: GitHub Actions Workflows
- [ ] **Branch-Management**: Automatische Feature-Branch-Erstellung
- [ ] **Code-Review-Automation**: AI-basierte Pull Request Reviews
- [ ] **Metrics & Analytics**: Repository-Statistiken und Trends

---

## 🏆 **Meilensteine**

| Version | Meilenstein | Status |
|---------|-------------|---------|
| 3.7.3 | 🤖 **AI-Powered Issue Management** | ✅ Erreicht |
| 3.7.2 | 🔧 **Vollständige Feature-Wiederherstellung** | ✅ Erreicht |
| 3.7.1 | 🖱️ **TUI-Navigation-Fix** | ✅ Erreicht |
| 3.5.x | 🎨 **Stabile TUI-Basis** | ✅ Referenz |

---

## 🤝 **Beiträge**

### **Entwicklung durch AI-Assistenz**
- **GitHub Copilot**: Vollständige Code-Entwicklung und Feature-Implementierung
- **Systematische Herangehensweise**: Schritt-für-Schritt Problem-Lösung
- **Code-Archäologie**: Analyse und Wiederherstellung verloren gegangener Features

### **Benutzer-Feedback**
- **Dennis**: Problem-Identifikation und Feature-Anforderungen
- **Issue-Reports**: "TUI-Navigation defekt", "Issue-Integration fehlt"
- **Feature-Requests**: "Automatisches Issue-Closing", "CHANGELOG-Integration"

---

## 📋 **Support & Kompatibilität**

### **Systemanforderungen**
- **Python**: 3.7+
- **Betriebssystem**: Linux, macOS, Windows
- **Dependencies**: `rich`, `click`, `requests`
- **Git**: CLI verfügbar im PATH
- **Node.js**: Für Codex CLI (optional)

### **API-Dependencies**
- **GitHub API**: Personal Access Token erforderlich
- **OpenRouter API**: Token für AI-Features (optional)
- **Codex CLI**: NPM-Package für Code-Generierung

---

## 📞 **Hilfe & Dokumentation**

### **Schnellstart**
```bash
# TUI starten
python3 grepo2_3.7.3.py tui

# CLI-Hilfe
python3 grepo2_3.7.3.py --help

# Status anzeigen
python3 grepo2_3.7.3.py status
```

### **Troubleshooting**
- **TUI-Probleme**: Terminal-Größe prüfen, Curses-Support validieren
- **API-Fehler**: GitHub Token-Berechtigungen überprüfen
- **Codex-Issues**: Node.js und NPM-Installation validieren

---

*Dieses CHANGELOG wird automatisch durch grepo2 v3.7.3+ aktualisiert*
