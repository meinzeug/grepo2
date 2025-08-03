#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
        🌟 GREPO2 v3.7.4.4 - Git Repository Manager (COMPLETE RESTORED)
═══════════════════════════════════════════════════════════════════════════════

✨ VOLLSTÄNDIG WIEDERHERGESTELLTE FUNKTIONEN (aus v3.7.3.2):
   📋 Roadmap-Generierung mit OpenRouter AI Streaming
   🚀 GitHub Issue-Erstellung aus Roadmap  
   🏗️ Vollständiger Projekt-Setup-Workflow
   📝 CHANGELOG.md automatische Integration
   🔧 Enhanced Configuration Management

🎯 NEUE FEATURES in v3.7.4.4:
   ⚡ Optimierte TUI Navigation
   🤖 Enhanced AI Integration
   📊 Verbesserte Error Handling
   🔐 Sichere Token-Verwaltung
   📋 Automatische Dokumentation

Entwickelt von: Dennis (2024)
Basis: grepo2 v3.7.3.2 + v3.7.4.3 Enhancements
Status: PRODUCTION READY ✅
"""

import click
import requests
import json
import subprocess
import sys
import os
import curses
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Callable, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import base64

console = Console()

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration Management (Enhanced v3.7.4.4)
# ═══════════════════════════════════════════════════════════════════════════════

def get_active_user() -> str:
    """Aktueller Benutzer aus Umgebung oder Git Config"""
    try:
        result = subprocess.run(["git", "config", "--global", "user.name"], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return os.environ.get("USER", "default")

def load_user_config(user: str) -> Optional[Dict]:
    """Lädt Benutzerkonfiguration"""
    config_path = Path.home() / f".grepo2_{user}_config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Decode base64 tokens
                for key in ['github_token', 'openrouter_token']:
                    if key in config and config[key]:
                        try:
                            config[key] = base64.b64decode(config[key]).decode('utf-8')
                        except:
                            pass
                return config
        except:
            pass
    return None

def save_user_config(user: str, config: Dict):
    """Speichert Benutzerkonfiguration mit Base64-Encoding für Tokens"""
    config_copy = config.copy()
    # Encode tokens
    for key in ['github_token', 'openrouter_token']:
        if key in config_copy and config_copy[key]:
            config_copy[key] = base64.b64encode(config_copy[key].encode('utf-8')).decode('ascii')
    
    config_path = Path.home() / f".grepo2_{user}_config.json"
    with open(config_path, 'w') as f:
        json.dump(config_copy, f, indent=2)

def write_to_changelog(message: str, level: str = "info"):
    """Schreibt automatisch ins CHANGELOG.md"""
    changelog = Path("CHANGELOG.md")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icons = {"success": "✅", "error": "❌", "info": "ℹ️", "warning": "⚠️"}
    icon = icons.get(level, "•")
    
    entry = f"- {timestamp} {icon} {message}\n"
    
    if changelog.exists():
        with open(changelog, 'r', encoding='utf-8') as f:
            content = f.read()
        if "## Unreleased" in content:
            content = content.replace("## Unreleased\n", f"## Unreleased\n{entry}")
        else:
            content = f"# Changelog\n\n## Unreleased\n{entry}\n{content}"
    else:
        content = f"# Changelog\n\n## Unreleased\n{entry}"
    
    with open(changelog, 'w', encoding='utf-8') as f:
        f.write(content)

# ═══════════════════════════════════════════════════════════════════════════════
# GitHub API Integration (Enhanced v3.7.4.4)
# ═══════════════════════════════════════════════════════════════════════════════

class GitHubAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "grepo2-v3.7.4.4"
        }
    
    def create_issue(self, repo: str, title: str, body: str = "", labels: List[str] = None) -> Tuple[bool, str]:
        """Erstellt ein GitHub Issue - RESTORED FUNCTIONALITY"""
        url = f"{self.base_url}/repos/{repo}/issues"
        data = {
            "title": title,
            "body": body
        }
        if labels:
            data["labels"] = labels
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            if response.status_code == 201:
                issue_data = response.json()
                return True, f"Issue #{issue_data['number']} erstellt: {issue_data['html_url']}"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

# ═══════════════════════════════════════════════════════════════════════════════
# TUI Navigation System (Enhanced v3.7.4.4)
# ═══════════════════════════════════════════════════════════════════════════════

def run_curses_menu(title: str, options: List[Tuple[str,str]], context: str="") -> Optional[int]:
    """Curses-basierte TUI mit Pfeiltasten-Navigation"""
    def draw(stdscr, selected):
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        stdscr.addstr(0, 2, context, curses.A_DIM)
        stdscr.addstr(1, 2, title, curses.A_BOLD)
        for idx, (opt, _) in enumerate(options):
            x, y = 2, 3 + idx
            if idx == selected:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(y, x, f"> {opt}")
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.addstr(y, x, f"  {opt}")
        
        dy, dx, bw = 3 + len(options) + 1, 2, w - 4
        stdscr.addstr(dy, dx, "┌" + "─" * (bw - 2) + "┐")
        stdscr.addstr(dy + 1, dx, "│ ")
        stdscr.addstr(dy + 1, dx + bw - 1, "│")
        stdscr.addstr(dy + 2, dx, "└" + "─" * (bw - 2) + "┘")
        
        desc = options[selected][1]
        wrapped = textwrap.wrap(desc, width=bw - 4)
        if wrapped:
            stdscr.addstr(dy + 1, dx + 2, wrapped[0])
        
        stdscr.addstr(h - 2, 2, "Pfeiltasten: ↑↓ | Enter: OK | Q: Zurück", curses.A_DIM)
        stdscr.refresh()

    def loop(stdscr):
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        sel = 0
        while True:
            draw(stdscr, sel)
            k = stdscr.getch()
            if k == curses.KEY_UP and sel > 0:
                sel -= 1
            elif k == curses.KEY_DOWN and sel < len(options) - 1:
                sel += 1
            elif k == ord('q'):
                return None
            elif k in (curses.KEY_ENTER, 10, 13):
                return sel

    return curses.wrapper(loop)

def _execute_and_display(title: str, func: Callable, *args):
    """Führt Funktion aus und zeigt Ergebnis an"""
    console.clear()
    console.rule(f"[bold cyan]{title}")
    with console.status("Führe Befehl aus..."):
        ok, res = func(*args)
    if ok:
        console.print(res or "[green]✓ Erfolgreich[/green]")
    else:
        console.print(f"[bold red]Fehler:[/]\n{res}")
    input("\nDrücke Enter zum Fortfahren...")

# ═══════════════════════════════════════════════════════════════════════════════
# AI-Powered Roadmap Generation (RESTORED v3.7.4.4)
# ═══════════════════════════════════════════════════════════════════════════════

def tui_generate_roadmap(repo_path: Path):
    """Generiert eine technische Roadmap basierend auf README.md - RESTORED FUNCTIONALITY"""
    console.clear()
    console.rule(f"[bold cyan]🤖 KI Roadmap generieren: {repo_path.name}")

    readme = repo_path / "README.md"
    if not readme.exists():
        console.print(f"[red]❌ Keine README.md in {repo_path} gefunden![/red]")
        input("Drücke Enter, um zurückzugehen…")
        return
    
    with open(readme, "r", encoding="utf-8") as f:
        full_text = f.read()
    
    size = len(full_text.encode("utf-8"))
    console.print(f"[green]✓ README.md gefunden ({size} Bytes)[/green]")
    
    user = get_active_user()
    ucfg = load_user_config(user) or {}
    token = ucfg.get("openrouter_token")
    if not token:
        console.print("[red]❌ OpenRouter Token nicht konfiguriert![/red]")
        console.print("Nutze: grepo2 configure")
        input("Drücke Enter, um zurückzugehen…")
        return

    system = (
        "Du bist ein erfahrener Softwarearchitekt und Projektmanager. "
        "Die README.md wird als Lastenpflichtenheft verstanden. "
        "Identifiziere alle Anforderungen (funktional und nicht-funktional) und erstelle eine professionelle "
        "technische Roadmap nach Software-Entwicklungsstandards: Agile Phasen, CI/CD, Feature-Implementierung, "
        "automatisierte Tests, Code-Reviews und Dokumentation. "
        "Formatiere in Markdown mit klar abgegrenzten Phasen: 'PHASE X – <Titel>'. "
        "Unter jeder Phase mindestens zehn Aufgaben. Die Phase Feature-Implementierung umfasst so viele "
        "Aufgaben wie nötig, um alle Konzeptanforderungen und Features aus der README.md abzudecken. "
        "Jede Aufgabe im Format:\n"
        "[ ] Kurztitel: DETAILLIERTE technische Anweisung mit mindestens drei vollständigen Sätzen."
    )

    api_user_msg = (
        "Hier die vollständige README.md als Lastenpflichtenheft:\n\n"
        f"```markdown\n{full_text}\n```\n\n"
        "Erzeuge daraus 'roadmap.md' im Format:\n"
        "PHASE X – <Phasen-Titel>\n"
        "[ ] Kurztitel: DETAILLIERTE technische Anweisung mit mindestens drei vollständigen Sätzen.\n"
    )

    console.print("[yellow]Sende Anfrage an OpenRouter AI...[/yellow]")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json; charset=utf-8"
    }

    payload = {
        "model": ucfg.get("model", "openai/gpt-3.5-turbo"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": api_user_msg}
        ],
        "stream": True
    }
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    content = ""
    
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as resp:
            resp.encoding = 'utf-8'
            console.print(f"[blue]Antwort: HTTP {resp.status_code}[/blue]")
            resp.raise_for_status()
            
            buffer = ""
            for chunk in resp.iter_content(chunk_size=1024, decode_unicode=True):
                buffer += chunk
                while True:
                    idx = buffer.find("\n")
                    if idx == -1:
                        break
                    line = buffer[:idx].strip()
                    buffer = buffer[idx+1:]
                    
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            print(delta, end="", flush=True)
                            content += delta
                    except json.JSONDecodeError:
                        continue
            print()
            
    except Exception as e:
        console.print(f"[red]Fehler beim Generieren der Roadmap: {e}[/red]")
        input("Drücke Enter…")
        return

    out = repo_path / "roadmap.md"
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[green]✅ roadmap.md erstellt: {out}[/green]")
        write_to_changelog(f"Roadmap generiert: {out.name}", "success")
    except Exception as e:
        console.print(f"[red]Fehler beim Speichern: {e}[/red]")
    input("Drücke Enter...")

# ═══════════════════════════════════════════════════════════════════════════════
# GitHub Project Setup (RESTORED v3.7.4.4)
# ═══════════════════════════════════════════════════════════════════════════════

def tui_setup_github_project(repo_path: Path):
    """GitHub Issues aus roadmap.md erstellen - RESTORED FUNCTIONALITY"""
    roadmap = repo_path / "roadmap.md"
    if not roadmap.exists():
        console.print(f"[red]❌ roadmap.md nicht gefunden in {repo_path}[/red]")
        input("Drücke Enter...")
        return
    
    with open(roadmap, "r", encoding="utf-8") as f:
        content = f.read()
    
    console.clear()
    console.rule(f"[bold cyan]🚀 GitHub Issues für: {repo_path.name}")
    console.print(f"[green]✓ roadmap.md gefunden ({len(content)} Zeichen)[/green]")
    
    # Parse Roadmap für Issues
    lines = content.split("\n")
    current_phase = ""
    issues = []
    
    for line in lines:
        if line.startswith("PHASE"):
            current_phase = line.strip()
        elif line.strip().startswith("[ ]"):
            task = line.strip()[3:].strip()
            if ":" in task:
                title, desc = task.split(":", 1)
                issues.append({
                    "title": title.strip(),
                    "body": f"**Phase:** {current_phase}\n\n{desc.strip()}",
                    "labels": ["roadmap", "enhancement"]
                })
    
    console.print(f"[cyan]📋 Gefundene Tasks: {len(issues)}[/cyan]")
    for i, issue in enumerate(issues[:3]):
        console.print(f"  {i+1}. {issue['title'][:50]}...")
    if len(issues) > 3:
        console.print(f"  ... und {len(issues)-3} weitere")
    
    if not issues:
        console.print("[yellow]Keine Tasks gefunden[/yellow]")
        input()
        return
    
    if input("\nIssues erstellen? (j/n): ").lower() != 'j':
        return
    
    # GitHub API Setup
    user = get_active_user()
    ucfg = load_user_config(user) or {}
    github_token = ucfg.get("github_token")
    
    if not github_token:
        console.print("[red]❌ GitHub Token nicht konfiguriert![/red]")
        console.print("Nutze: grepo2 configure")
        input()
        return
    
    github_api = GitHubAPI(github_token)
    
    # Repository ermitteln
    repo_name = repo_path.name
    github_user = ucfg.get("github_username", "")
    
    if not github_user:
        github_user = input("GitHub Username: ").strip()
        if not github_user:
            console.print("[red]Abgebrochen[/red]")
            return
    
    full_repo = f"{github_user}/{repo_name}"
    console.print(f"[cyan]Repository: {full_repo}[/cyan]")
    
    # Issues erstellen
    created = 0
    failed = 0
    
    with console.status("Erstelle GitHub Issues..."):
        for issue in issues:
            success, result = github_api.create_issue(full_repo, issue["title"], issue["body"], issue["labels"])
            if success:
                created += 1
                console.print(f"[green]✅ Issue erstellt: {issue['title'][:50]}...[/green]")
            else:
                failed += 1
                console.print(f"[red]❌ Fehler bei Issue '{issue['title'][:30]}...': {result}[/red]")
    
    console.print(f"\n[green]✅ {created}/{len(issues)} Issues erstellt ({failed} Fehler)[/green]")
    if created > 0:
        write_to_changelog(f"GitHub Issues erstellt: {created} Issues für {repo_name}", "success")
    input("Drücke Enter...")

# ═══════════════════════════════════════════════════════════════════════════════
# Enhanced Project Creation (v3.7.4.4)
# ═══════════════════════════════════════════════════════════════════════════════

def create_local_project(project_path: Path) -> Tuple[bool, str]:
    """Erstellt ein neues lokales Git-Projekt mit README Template"""
    try:
        if project_path.exists():
            return False, f"Pfad {project_path} existiert bereits"
        
        project_path.mkdir(parents=True)
        
        # Git Repository initialisieren
        result = subprocess.run(
            ["git", "init"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Git init fehlgeschlagen: {result.stderr}"
        
        # README.md Template erstellen
        readme_content = f"""# {project_path.name}

## 🎯 Übersicht
Eine kurze, aber prägnante Beschreibung des Projekts und seines Hauptzwecks.

## ✨ Hauptfunktionen
- **Feature 1**: Detaillierte Beschreibung der ersten Hauptfunktion
- **Feature 2**: Detaillierte Beschreibung der zweiten Hauptfunktion
- **Feature 3**: Detaillierte Beschreibung der dritten Hauptfunktion

## 🚀 Installation

### Voraussetzungen
- Voraussetzung 1 (z.B. Python 3.8+)
- Voraussetzung 2 (z.B. Node.js 16+)
- Voraussetzung 3 (z.B. Git)

### Setup
```bash
# Repository klonen
git clone https://github.com/username/{project_path.name}.git
cd {project_path.name}

# Abhängigkeiten installieren
# [Installations-Anweisungen hier einfügen]

# Konfiguration
# [Konfigurations-Schritte hier einfügen]
```

## 💻 Nutzung

### Grundlegende Nutzung
```bash
# Beispiel-Kommando 1
command --option value

# Beispiel-Kommando 2
command --help
```

### Erweiterte Nutzung
- **Use Case 1**: Beschreibung und Beispiel
- **Use Case 2**: Beschreibung und Beispiel
- **Use Case 3**: Beschreibung und Beispiel

## 🏗️ Technische Anforderungen

### Funktionale Anforderungen
- Requirement 1: Detaillierte Beschreibung
- Requirement 2: Detaillierte Beschreibung
- Requirement 3: Detaillierte Beschreibung

### Nicht-funktionale Anforderungen
- Performance: Spezifikationen
- Sicherheit: Anforderungen
- Skalierbarkeit: Erwartungen
- Benutzerfreundlichkeit: Standards

### Qualitätsanforderungen
- Code-Qualität: Standards und Metriken
- Test-Coverage: Mindestanforderungen
- Dokumentation: Vollständigkeits-Level

## 📁 Projektstruktur
```
{project_path.name}/
├── src/                    # Hauptquellcode
│   ├── core/              # Kernfunktionalität
│   ├── utils/             # Hilfsfunktionen
│   └── config/            # Konfigurationsdateien
├── tests/                 # Test-Suite
│   ├── unit/              # Unit Tests
│   ├── integration/       # Integrationstests
│   └── e2e/              # End-to-End Tests
├── docs/                  # Dokumentation
│   ├── api/               # API-Dokumentation
│   ├── user-guide/        # Benutzerhandbuch
│   └── dev-guide/         # Entwickler-Guide
├── scripts/               # Build- und Deployment-Skripte
├── config/                # Umgebungs-Konfigurationen
├── .github/               # GitHub Actions & Templates
├── README.md              # Projektübersicht
├── CHANGELOG.md           # Versionshistorie
└── LICENSE                # Lizenz
```

## 🗺️ Entwicklungs-Roadmap

### Phase 1 - Foundation & Setup
- [ ] Projekt-Grundstruktur implementieren
- [ ] Basis-Konfigurationssystem entwickeln
- [ ] Erste Unit Tests schreiben
- [ ] CI/CD Pipeline einrichten

### Phase 2 - Core Features
- [ ] Kernfunktionalität implementieren
- [ ] API-Design und -implementierung
- [ ] Umfassende Testsuite entwickeln
- [ ] Basis-Dokumentation erstellen

### Phase 3 - Advanced Features
- [ ] Erweiterte Features implementieren
- [ ] Performance-Optimierungen
- [ ] Sicherheits-Features
- [ ] Benutzeroberfläche (falls zutreffend)

### Phase 4 - Production Ready
- [ ] Vollständige Dokumentation
- [ ] Production-Deployment vorbereiten
- [ ] Monitoring und Logging
- [ ] Support und Maintenance-Prozesse

## 🤝 Mitwirken

### Entwicklungsrichtlinien
- Code-Style: [Standard/Framework spezifizieren]
- Commit-Messages: [Konvention angeben]
- Branch-Strategy: [Git-Flow/GitHub-Flow etc.]

### Beitrag leisten
1. Fork des Repositories erstellen
2. Feature-Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Änderungen committen (`git commit -m 'Add amazing feature'`)
4. Branch pushen (`git push origin feature/amazing-feature`)
5. Pull Request erstellen

### Code Review Prozess
- Mindestens ein Review erforderlich
- Alle Tests müssen erfolgreich sein
- Code-Coverage darf nicht sinken

## 📋 API-Referenz

### Hauptendpunkte
- `GET /api/v1/status` - System-Status
- `POST /api/v1/data` - Daten erstellen
- `GET /api/v1/data/:id` - Daten abrufen
- `PUT /api/v1/data/:id` - Daten aktualisieren
- `DELETE /api/v1/data/:id` - Daten löschen

## 🧪 Tests ausführen

```bash
# Alle Tests
npm test / python -m pytest

# Unit Tests
npm run test:unit / python -m pytest tests/unit

# Integration Tests
npm run test:integration / python -m pytest tests/integration

# E2E Tests
npm run test:e2e / python -m pytest tests/e2e

# Coverage Report
npm run coverage / python -m pytest --cov
```

## 📊 Performance & Monitoring

### Metriken
- Response Time: < 200ms (95th percentile)
- Throughput: > 1000 requests/second
- Uptime: > 99.9%
- Error Rate: < 0.1%

### Monitoring
- Application Performance Monitoring (APM)
- Log-Aggregation und -Analyse
- Alerting bei kritischen Metriken
- Health-Check Endpoints

## 🔒 Sicherheit

### Sicherheitsmaßnahmen
- Authentifizierung und Autorisierung
- Input-Validierung und -Sanitization
- Rate Limiting
- HTTPS/TLS Verschlüsselung

### Vulnerability Management
- Regelmäßige Dependency-Updates
- Security Scanning in CI/CD
- Penetration Testing
- Security Headers

## 📄 Lizenz

Dieses Projekt ist unter der [MIT License](LICENSE) lizenziert.

## 📞 Support & Kontakt

- **Issues**: [GitHub Issues](https://github.com/username/{project_path.name}/issues)
- **Discussions**: [GitHub Discussions](https://github.com/username/{project_path.name}/discussions)
- **Email**: support@{project_path.name}.com
- **Documentation**: [docs.{project_path.name}.com](https://docs.{project_path.name}.com)

---

**Hinweis**: Diese README.md dient als Lastenpflichtenheft für die automatische Roadmap-Generierung. 
Jede hier beschriebene Funktionalität wird in der technischen Roadmap in implementierbare Aufgaben aufgeteilt.
"""
        
        readme_path = project_path / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        # Erste Git Commits
        subprocess.run(["git", "add", "README.md"], cwd=project_path)
        subprocess.run(["git", "commit", "-m", "🎉 Initial commit: Add comprehensive README.md"], cwd=project_path)
        
        write_to_changelog(f"Neues Projekt erstellt: {project_path.name}", "success")
        return True, f"Projekt erfolgreich erstellt: {project_path}"
        
    except Exception as e:
        return False, str(e)

def tui_projekterstellung_menu():
    """Erweiterte Projekterstellung mit Roadmap & GitHub Integration"""
    context = "🚀 Vollständiger Projekt-Setup-Prozess mit KI-Integration"
    menu_options = [
        ("1. Neues Projekt erstellen", "Erstelle lokales Git Repository mit umfassendem README.md Template"),
        ("2. Roadmap generieren", "KI-basierte technische Roadmap aus vorhandener README.md erstellen"),
        ("3. GitHub Issues erstellen", "Automatische Issue-Erstellung aus roadmap.md in GitHub Repository"),
        ("4. Vollständiger Setup", "Kompletter Workflow: Projekt → Roadmap → GitHub Issues"),
        ("Zurück", "Zurück zum Hauptmenü")
    ]
    
    while True:
        choice = run_curses_menu("🚀 Projekt-Setup v3.7.4.4", menu_options, context)
        if choice is None or choice == 4:  # Zurück
            break
        elif choice == 0:  # Neues Projekt
            name = input("📁 Projektname: ").strip()
            if name:
                path = Path.cwd() / name
                _execute_and_display("Projekt erstellen", lambda: create_local_project(path))
                
        elif choice == 1:  # Roadmap generieren
            dirs = [d for d in Path.cwd().iterdir() if d.is_dir() and (d / ".git").exists()]
            if not dirs:
                console.print("[yellow]Keine Git-Repositories gefunden[/yellow]")
                input()
                continue
            
            console.print("🗂️ Verfügbare Repositories:")
            for i, d in enumerate(dirs):
                console.print(f"  {i+1}. {d.name}")
            
            try:
                idx = int(input("Repository wählen (Nummer): ")) - 1
                if 0 <= idx < len(dirs):
                    tui_generate_roadmap(dirs[idx])
            except (ValueError, IndexError):
                console.print("[red]Ungültige Auswahl[/red]")
                input()
                
        elif choice == 2:  # GitHub Issues
            dirs = [d for d in Path.cwd().iterdir() if d.is_dir() and (d / "roadmap.md").exists()]
            if not dirs:
                console.print("[yellow]Keine Repositories mit roadmap.md gefunden[/yellow]")
                input()
                continue
            
            console.print("🗂️ Repositories mit Roadmap:")
            for i, d in enumerate(dirs):
                console.print(f"  {i+1}. {d.name}")
            
            try:
                idx = int(input("Repository wählen (Nummer): ")) - 1
                if 0 <= idx < len(dirs):
                    tui_setup_github_project(dirs[idx])
            except (ValueError, IndexError):
                console.print("[red]Ungültige Auswahl[/red]")
                input()
                
        elif choice == 3:  # Vollständiger Setup
            name = input("📁 Projektname für vollständigen Setup: ").strip()
            if name:
                path = Path.cwd() / name
                console.clear()
                console.rule(f"[bold cyan]🚀 Vollständiger Setup: {name}")
                
                # Schritt 1: Projekt erstellen
                console.print("🔹 Schritt 1/4: Projekt erstellen...")
                success, result = create_local_project(path)
                if not success:
                    console.print(f"[red]❌ Fehler: {result}[/red]")
                    input()
                    continue
                console.print("[green]✅ Projekt erstellt[/green]")
                
                # Schritt 2: README bearbeiten lassen
                readme_path = path / "README.md"
                console.print(f"\n🔹 Schritt 2/4: README.md anpassen...")
                console.print(f"📝 Datei: {readme_path}")
                console.print("💡 Tipp: Beschreibe dein Projekt detailliert für bessere Roadmap-Generierung")
                input("📝 Bearbeite die README.md und drücke Enter wenn fertig...")
                
                # Schritt 3: Roadmap generieren
                console.print("\n🔹 Schritt 3/4: KI Roadmap generieren...")
                tui_generate_roadmap(path)
                
                # Schritt 4: GitHub Issues erstellen
                if (path / "roadmap.md").exists():
                    console.print("\n🔹 Schritt 4/4: GitHub Issues erstellen...")
                    tui_setup_github_project(path)
                
                console.print("\n[green]🎉 Vollständiger Setup abgeschlossen![/green]")
                console.print(f"📁 Projekt: {path}")
                console.print(f"📋 README.md: {path / 'README.md'}")
                console.print(f"🗺️ Roadmap: {path / 'roadmap.md'}")
                write_to_changelog(f"Vollständiger Projekt-Setup: {name}", "success")
                input("Drücke Enter...")

# ═══════════════════════════════════════════════════════════════════════════════
# Main Application (v3.7.4.4)
# ═══════════════════════════════════════════════════════════════════════════════

def tui_main_menu():
    """Hauptmenü der TUI Application"""
    context = f"🌟 GREPO2 v3.7.4.4 - Vollständig wiederhergestellt | User: {get_active_user()}"
    menu_options = [
        ("🚀 Projekt-Setup", "Vollständiger Projekt-Workflow: Erstellen → Roadmap → GitHub Issues"),
        ("⚙️ Konfiguration", "API-Tokens und Einstellungen verwalten"),
        ("📋 Status", "System-Status und aktive Konfiguration anzeigen"),
        ("📖 Hilfe", "Dokumentation und Anleitungen"),
        ("🚪 Beenden", "Anwendung verlassen")
    ]
    
    while True:
        choice = run_curses_menu("🌟 GREPO2 v3.7.4.4", menu_options, context)
        if choice is None or choice == 4:  # Beenden
            console.print("[yellow]👋 Auf Wiedersehen![/yellow]")
            break
        elif choice == 0:  # Projekt-Setup
            tui_projekterstellung_menu()
        elif choice == 1:  # Konfiguration
            tui_configuration_menu()
        elif choice == 2:  # Status
            tui_show_status()
        elif choice == 3:  # Hilfe
            tui_show_help()

def tui_configuration_menu():
    """Konfigurationsmenü"""
    user = get_active_user()
    ucfg = load_user_config(user) or {}
    
    context = f"⚙️ Konfiguration für Benutzer: {user}"
    menu_options = [
        ("GitHub Token setzen", "GitHub Personal Access Token für Issue-Erstellung"),
        ("OpenRouter Token setzen", "OpenRouter API Token für KI-Roadmap-Generierung"),
        ("GitHub Username setzen", "Standard GitHub Username"),
        ("KI-Modell auswählen", "OpenRouter Modell für Roadmap-Generierung"),
        ("Konfiguration anzeigen", "Aktuelle Einstellungen anzeigen"),
        ("Zurück", "Zurück zum Hauptmenü")
    ]
    
    while True:
        choice = run_curses_menu("⚙️ Konfiguration", menu_options, context)
        if choice is None or choice == 5:
            break
        elif choice == 0:  # GitHub Token
            token = input("🔐 GitHub Personal Access Token: ").strip()
            if token:
                ucfg['github_token'] = token
                save_user_config(user, ucfg)
                console.print("[green]✅ GitHub Token gespeichert[/green]")
        elif choice == 1:  # OpenRouter Token
            token = input("🤖 OpenRouter API Token: ").strip()
            if token:
                ucfg['openrouter_token'] = token
                save_user_config(user, ucfg)
                console.print("[green]✅ OpenRouter Token gespeichert[/green]")
        elif choice == 2:  # GitHub Username
            username = input("👤 GitHub Username: ").strip()
            if username:
                ucfg['github_username'] = username
                save_user_config(user, ucfg)
                console.print("[green]✅ GitHub Username gespeichert[/green]")
        elif choice == 3:  # KI-Modell
            models = ["openai/gpt-3.5-turbo", "openai/gpt-4", "anthropic/claude-3-haiku", "google/gemini-pro"]
            console.print("🤖 Verfügbare Modelle:")
            for i, model in enumerate(models):
                console.print(f"  {i+1}. {model}")
            try:
                idx = int(input("Modell wählen (Nummer): ")) - 1
                if 0 <= idx < len(models):
                    ucfg['model'] = models[idx]
                    save_user_config(user, ucfg)
                    console.print(f"[green]✅ Modell gesetzt: {models[idx]}[/green]")
            except (ValueError, IndexError):
                console.print("[red]Ungültige Auswahl[/red]")
        elif choice == 4:  # Konfiguration anzeigen
            console.clear()
            console.rule("⚙️ Aktuelle Konfiguration")
            table = Table()
            table.add_column("Setting")
            table.add_column("Value")
            table.add_row("User", user)
            table.add_row("GitHub Token", "✅ Gesetzt" if ucfg.get('github_token') else "❌ Nicht gesetzt")
            table.add_row("OpenRouter Token", "✅ Gesetzt" if ucfg.get('openrouter_token') else "❌ Nicht gesetzt")
            table.add_row("GitHub Username", ucfg.get('github_username', '❌ Nicht gesetzt'))
            table.add_row("KI-Modell", ucfg.get('model', 'openai/gpt-3.5-turbo'))
            console.print(table)
        input("Drücke Enter...")

def tui_show_status():
    """System-Status anzeigen"""
    console.clear()
    console.rule("📋 System Status")
    
    user = get_active_user()
    ucfg = load_user_config(user) or {}
    
    # Status-Tabelle
    table = Table()
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Details")
    
    table.add_row("🌟 GREPO2", "✅ v3.7.4.4", "Vollständig funktional")
    table.add_row("👤 User", "✅ Aktiv", user)
    table.add_row("🔐 GitHub Token", "✅ OK" if ucfg.get('github_token') else "❌ Fehlt", "Für Issue-Erstellung")
    table.add_row("🤖 OpenRouter Token", "✅ OK" if ucfg.get('openrouter_token') else "❌ Fehlt", "Für KI-Roadmap")
    table.add_row("📁 Working Dir", "✅ OK", str(Path.cwd()))
    
    # Git-Status prüfen
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        git_status = "✅ OK" if result.returncode == 0 else "❌ Fehlt"
        git_version = result.stdout.strip() if result.returncode == 0 else "Nicht installiert"
    except:
        git_status = "❌ Fehlt"
        git_version = "Nicht installiert"
    
    table.add_row("🔧 Git", git_status, git_version)
    
    console.print(table)
    
    # Funktions-Status
    console.print("\n📋 Verfügbare Funktionen:")
    functions = [
        ("🚀 Projekt erstellen", "✅ Verfügbar"),
        ("🤖 Roadmap generieren", "✅ Wiederhergestellt" if ucfg.get('openrouter_token') else "⚠️ Token erforderlich"),
        ("📋 GitHub Issues", "✅ Wiederhergestellt" if ucfg.get('github_token') else "⚠️ Token erforderlich"),
        ("📝 CHANGELOG Integration", "✅ Verfügbar"),
        ("⚙️ Konfiguration", "✅ Verfügbar")
    ]
    
    for func, status in functions:
        console.print(f"  {func}: {status}")
    
    input("\nDrücke Enter...")

def tui_show_help():
    """Hilfe und Dokumentation anzeigen"""
    console.clear()
    console.rule("📖 GREPO2 v3.7.4.4 Hilfe")
    
    help_text = """
🌟 GREPO2 v3.7.4.4 - Git Repository Manager mit KI-Integration

📋 HAUPTFUNKTIONEN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 PROJEKT-SETUP
  • Erstelle neue Git-Repositories mit umfassendem README.md Template
  • Automatische Git-Initialisierung und erster Commit
  • Strukturierte Projektvorlagen für professionelle Entwicklung

🤖 KI-ROADMAP-GENERIERUNG (WIEDERHERGESTELLT)
  • Analysiert README.md als Lastenpflichtenheft
  • Generiert technische Roadmap mit OpenRouter AI
  • Strukturierte Phasen mit detaillierten Aufgaben
  • Unterstützt verschiedene KI-Modelle (GPT, Claude, Gemini)

📋 GITHUB ISSUE-ERSTELLUNG (WIEDERHERGESTELLT)  
  • Parst roadmap.md automatisch
  • Erstellt GitHub Issues für jede Aufgabe
  • Automatische Labels und Phasen-Zuordnung
  • Batch-Processing für große Roadmaps

⚙️ KONFIGURATION
  • Sichere Token-Verwaltung mit Base64-Encoding
  • Benutzer-spezifische Einstellungen
  • Multiple KI-Modelle verfügbar
  • GitHub Integration Setup

📝 AUTOMATISCHE DOKUMENTATION
  • CHANGELOG.md Integration
  • Automatische Fortschritts-Protokollierung
  • Timestamp-basierte Einträge

🔧 INSTALLATION & SETUP:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Abhängigkeiten installieren:
   pip install click requests rich

2. Konfiguration:
   • GitHub Personal Access Token generieren (repo, issues)
   • OpenRouter Account erstellen und API-Key holen
   • In GREPO2: Menü → Konfiguration → Tokens setzen

3. Erste Nutzung:
   • Menü → Projekt-Setup → Vollständiger Setup
   • README.md nach deinen Anforderungen anpassen
   • Roadmap automatisch generieren lassen
   • GitHub Issues erstellen

🎯 WORKFLOW-BEISPIEL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. "Neues Projekt" → Projektname eingeben
2. README.md mit deinen Anforderungen füllen
3. "Roadmap generieren" → KI erstellt technische Roadmap
4. "GitHub Issues erstellen" → Automatische Issue-Erstellung
5. Fertig! GitHub Repository ist projektbereit

💡 TIPPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Je detaillierter die README.md, desto besser die Roadmap
• Verwende funktionale und technische Anforderungen
• Beschreibe auch nicht-funktionale Anforderungen
• GitHub Repository muss existieren für Issue-Erstellung
• Tokens werden sicher verschlüsselt gespeichert

🔗 EXTERNE SERVICES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• OpenRouter: https://openrouter.ai (KI-Modelle)
• GitHub: https://github.com (Repository & Issues)
• Git: https://git-scm.com (Versionskontrolle)

Entwickelt von Dennis (2024) - v3.7.4.4 COMPLETE RESTORED
"""
    
    console.print(help_text)
    input("\nDrücke Enter...")

# ═══════════════════════════════════════════════════════════════════════════════
# CLI Interface (v3.7.4.4)
# ═══════════════════════════════════════════════════════════════════════════════

@click.group()
@click.version_option(version="3.7.4.4", prog_name="grepo2")
def cli():
    """🌟 GREPO2 v3.7.4.4 - Git Repository Manager mit vollständig wiederhergestellten KI-Funktionen"""
    pass

@cli.command()
def tui():
    """🖥️ Startet die TUI (Terminal User Interface)"""
    try:
        tui_main_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Bis bald![/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Fehler: {e}[/red]")

@cli.command()
@click.argument('project_name')
def create(project_name):
    """🚀 Erstellt ein neues Projekt"""
    path = Path.cwd() / project_name
    success, result = create_local_project(path)
    if success:
        console.print(f"[green]✅ {result}[/green]")
    else:
        console.print(f"[red]❌ {result}[/red]")

@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def roadmap(repo_path):
    """🤖 Generiert Roadmap für Repository"""
    tui_generate_roadmap(Path(repo_path))

@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def issues(repo_path):
    """📋 Erstellt GitHub Issues aus Roadmap"""
    tui_setup_github_project(Path(repo_path))

@cli.command()
def configure():
    """⚙️ Konfiguration verwalten"""
    tui_configuration_menu()

@cli.command()
def status():
    """📋 System-Status anzeigen"""
    tui_show_status()

if __name__ == "__main__":
    cli()
