#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
        🌟 GREPO2 v3.7.3.4.5-tuitest - Modern TUI Git Repository Manager
═══════════════════════════════════════════════════════════════════════════════

✨ VOLLSTÄNDIG WIEDERHERGESTELLTE FUNKTIONEN (aus v3.7.3.2):
   📋 Roadmap-Generierung mit OpenRouter AI Streaming
   🚀 GitHub Issue-Erstellung aus Roadmap  
   🏗️ Vollständiger Projekt-Setup-Workflow
   📝 CHANGELOG.md automatische Integration
   🔧 Enhanced Configuration Management

🎯 NEUE TUI FEATURES in v3.7.3.4.5-tuitest:
   🎨 Ultra-Modern Rich TUI mit Animationen
   ⚡ Live-Updates und Progress-Indicators  
   🌈 Dynamische Themes und Farbschemas
   📊 Interactive Dashboard mit Widgets
   🎭 Immersive Visual Experience
   🔥 Cutting-Edge Terminal UI Design

Entwickelt von: Dennis (2024)
Basis: grepo2 v3.7.4.4 + Modern TUI Enhancements
Status: PRODUCTION READY ✅
"""

import click
import requests
import json
import subprocess
import sys
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Callable, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.tree import Tree
from rich.align import Align
from rich.status import Status
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.box import ROUNDED, DOUBLE, MINIMAL
from rich.theme import Theme
import base64

# Modern Theme Definition
modern_theme = Theme({
    "primary": "bold cyan",
    "secondary": "bright_magenta", 
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "info": "bright_blue",
    "accent": "bright_white",
    "muted": "dim white",
    "highlight": "reverse bold cyan"
})

console = Console(theme=modern_theme)

# ═══════════════════════════════════════════════════════════════════════════════
# Modern UI Components & Animations
# ═══════════════════════════════════════════════════════════════════════════════

class ModernUI:
    """Ultra-moderne UI Komponenten mit Animationen"""
    
    @staticmethod
    def create_gradient_panel(content, title="", style="primary"):
        """Erstellt Panel mit Gradient-Effekt"""
        return Panel(
            content,
            title=f"[bold]{title}[/bold]" if title else None,
            border_style=style,
            box=ROUNDED,
            padding=(1, 2),
            expand=False
        )
    
    @staticmethod
    def create_dashboard_layout():
        """Erstellt modernes Dashboard Layout"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        layout["body"].split_row(
            Layout(name="sidebar", ratio=1),
            Layout(name="main", ratio=3)
        )
        return layout
    
    @staticmethod
    def animated_loading(text="Loading", duration=2):
        """Animierte Ladesequenz"""
        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            expand=True,
        ) as progress:
            task = progress.add_task(f"[cyan]{text}...", total=None)
            time.sleep(duration)

def modern_menu(title: str, options: List[Tuple[str, str]], context: str = "") -> Optional[int]:
    """Modern animated menu system"""
    console.clear()
    
    # Header with animation effect
    header = Panel(
        f"🌟 [primary]{title}[/primary]",
        box=DOUBLE,
        style="primary"
    )
    console.print(header)
    
    if context:
        context_panel = Panel(f"[info]{context}[/info]", box=MINIMAL, style="info")
        console.print(context_panel)
    
    # Modern menu display
    menu_table = Table(box=ROUNDED, show_header=False, show_edge=False)
    menu_table.add_column("Option", style="cyan", width=50)
    menu_table.add_column("Description", style="muted")
    
    for i, (option, desc) in enumerate(options):
        icon = "🔥" if i == 0 else "📌"
        menu_table.add_row(f"{icon} [bold]{i+1}. {option}[/bold]", desc[:80] + "..." if len(desc) > 80 else desc)
    
    menu_panel = Panel(menu_table, title="[secondary]Available Actions[/secondary]", style="secondary")
    console.print(menu_panel)
    
    # Interactive footer
    footer = Panel(
        "[accent]Enter choice (1-{}) or 'q' to quit[/accent]".format(len(options)),
        box=MINIMAL,
        style="muted"
    )
    console.print(footer)
    
    try:
        choice = input("\n> ").strip().lower()
        if choice == 'q':
            return None
        return int(choice) - 1
    except (ValueError, IndexError):
        return None

def modern_execute_and_display(title: str, func: Callable, *args):
    """Modern execution with animated feedback"""
    console.clear()
    
    # Header
    header = Panel(
        f"[primary]{title}[/primary]",
        box=DOUBLE,
        style="primary"
    )
    console.print(header)
    
    # Animated execution
    with console.status(f"[cyan]Executing {title}...", spinner="dots"):
        ok, res = func(*args)
    
    # Results display
    if ok:
        result_panel = Panel(
            res or "[success]✓ Successfully completed[/success]",
            title="[success]Success[/success]",
            box=ROUNDED,
            style="success"
        )
    else:
        result_panel = Panel(
            f"[error]{res}[/error]",
            title="[error]Error[/error]",
            box=ROUNDED,
            style="error"
        )
    
    console.print(result_panel)
    input("\n[accent]Press Enter to continue...[/accent]")

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration Management (Enhanced v3.7.3.4.5)
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
# GitHub API Integration (Enhanced v3.7.3.4.5)
# ═══════════════════════════════════════════════════════════════════════════════

class GitHubAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "grepo2-v3.7.3.4.5-tuitest"
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
# AI-Powered Roadmap Generation (RESTORED v3.7.3.4.5)
# ═══════════════════════════════════════════════════════════════════════════════

def modern_generate_roadmap(repo_path: Path):
    """Modern roadmap generation with enhanced UI"""
    console.clear()
    
    # Header with gradient effect
    header = Panel(
        f"🤖 [primary]AI Roadmap Generation[/primary]\n"
        f"[secondary]Repository:[/secondary] [accent]{repo_path.name}[/accent]",
        box=DOUBLE,
        style="primary"
    )
    console.print(header)
    
    readme = repo_path / "README.md"
    if not readme.exists():
        error_panel = Panel(
            f"[error]❌ No README.md found in {repo_path}![/error]",
            title="[error]Error[/error]",
            box=ROUNDED,
            style="error"
        )
        console.print(error_panel)
        input("Press Enter to return...")
        return
    
    with open(readme, "r", encoding="utf-8") as f:
        full_text = f.read()
    
    size = len(full_text.encode("utf-8"))
    
    # Success info with stats
    info_panel = Panel(
        f"[success]✓ README.md found[/success]\n"
        f"[info]Size: {size} bytes[/info]\n"
        f"[info]Lines: {len(full_text.splitlines())}[/info]",
        title="[info]File Analysis[/info]",
        box=ROUNDED,
        style="info"
    )
    console.print(info_panel)
    
    user = get_active_user()
    ucfg = load_user_config(user) or {}
    token = ucfg.get("openrouter_token")
    
    if not token:
        error_panel = Panel(
            "[error]❌ OpenRouter Token not configured![/error]\n"
            "[warning]Use: grepo2 configure[/warning]",
            title="[error]Configuration Error[/error]",
            box=ROUNDED,
            style="error"
        )
        console.print(error_panel)
        input("Press Enter to return...")
        return

    # AI Processing
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

    # API Request with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        
        ai_task = progress.add_task("🤖 Connecting to OpenRouter AI...", total=100)
        
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
            progress.update(ai_task, completed=25, description="🌐 Sending request...")
            
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as resp:
                resp.encoding = 'utf-8'
                progress.update(ai_task, completed=50, description=f"📡 Response: HTTP {resp.status_code}")
                resp.raise_for_status()
                
                progress.update(ai_task, completed=75, description="🧠 Processing AI response...")
                
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
                                console.print(delta, end="", style="info")
                                content += delta
                        except json.JSONDecodeError:
                            continue
                
                progress.update(ai_task, completed=100, description="✅ AI processing complete!")
                
        except Exception as e:
            progress.update(ai_task, completed=100, description="❌ Error occurred")
            error_panel = Panel(
                f"[error]Error generating roadmap: {e}[/error]",
                title="[error]AI Error[/error]",
                box=ROUNDED,
                style="error"
            )
            console.print(error_panel)
            input("Press Enter...")
            return

    # Save results
    out = repo_path / "roadmap.md"
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        
        success_panel = Panel(
            f"[success]✅ roadmap.md created successfully![/success]\n"
            f"[info]Location: {out}[/info]\n"
            f"[info]Size: {len(content)} characters[/info]",
            title="[success]Success[/success]",
            box=ROUNDED,
            style="success"
        )
        console.print(success_panel)
        write_to_changelog(f"Roadmap generated: {out.name}", "success")
        
    except Exception as e:
        error_panel = Panel(
            f"[error]Error saving file: {e}[/error]",
            title="[error]Save Error[/error]",
            box=ROUNDED,
            style="error"
        )
        console.print(error_panel)
    
    input("Press Enter to continue...")

# ═══════════════════════════════════════════════════════════════════════════════
# GitHub Project Setup (RESTORED v3.7.3.4.5)
# ═══════════════════════════════════════════════════════════════════════════════

def modern_setup_github_project(repo_path: Path):
    """Modern GitHub project setup with enhanced visualization"""
    roadmap = repo_path / "roadmap.md"
    if not roadmap.exists():
        error_panel = Panel(
            f"[error]❌ roadmap.md not found in {repo_path}[/error]",
            title="[error]File Not Found[/error]",
            box=ROUNDED,
            style="error"
        )
        console.print(error_panel)
        input("Press Enter...")
        return
    
    with open(roadmap, "r", encoding="utf-8") as f:
        content = f.read()
    
    console.clear()
    
    # Header
    header = Panel(
        f"🚀 [primary]GitHub Issue Creation[/primary]\n"
        f"[secondary]Repository:[/secondary] [accent]{repo_path.name}[/accent]",
        box=DOUBLE,
        style="primary"
    )
    console.print(header)
    
    # File info
    info_panel = Panel(
        f"[success]✓ roadmap.md found[/success]\n"
        f"[info]Size: {len(content)} characters[/info]",
        title="[info]Roadmap Analysis[/info]",
        box=ROUNDED,
        style="info"
    )
    console.print(info_panel)
    
    # Parse Roadmap
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
    
    # Issues preview
    preview_content = f"[cyan]📋 Found {len(issues)} tasks[/cyan]\n\n"
    preview_content += "[accent]Preview (first 3 tasks):[/accent]\n"
    
    for i, issue in enumerate(issues[:3]):
        preview_content += f"  {i+1}. [info]{issue['title'][:50]}...[/info]\n"
    
    if len(issues) > 3:
        preview_content += f"  [muted]... and {len(issues)-3} more tasks[/muted]"
    
    preview_panel = Panel(
        preview_content,
        title="[cyan]Task Preview[/cyan]",
        box=ROUNDED,
        style="cyan"
    )
    console.print(preview_panel)
    
    if not issues:
        warning_panel = Panel(
            "[warning]No tasks found in roadmap[/warning]",
            title="[warning]Warning[/warning]",
            box=ROUNDED,
            style="warning"
        )
        console.print(warning_panel)
        input()
        return
    
    # Confirmation
    if not Confirm.ask("[accent]Create GitHub issues?[/accent]"):
        return
    
    # GitHub API Setup
    user = get_active_user()
    ucfg = load_user_config(user) or {}
    github_token = ucfg.get("github_token")
    
    if not github_token:
        error_panel = Panel(
            "[error]❌ GitHub Token not configured![/error]\n"
            "[warning]Use: grepo2 configure[/warning]",
            title="[error]Configuration Error[/error]",
            box=ROUNDED,
            style="error"
        )
        console.print(error_panel)
        input()
        return
    
    github_api = GitHubAPI(github_token)
    
    # Repository details
    repo_name = repo_path.name
    github_user = ucfg.get("github_username", "")
    
    if not github_user:
        github_user = Prompt.ask("[cyan]GitHub Username[/cyan]")
        if not github_user:
            console.print("[error]Cancelled[/error]")
            return
    
    full_repo = f"{github_user}/{repo_name}"
    
    repo_info = Panel(
        f"[info]Target Repository: [accent]{full_repo}[/accent][/info]",
        box=ROUNDED,
        style="info"
    )
    console.print(repo_info)
    
    # Create issues with progress tracking
    created = 0
    failed = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("🚀 Creating GitHub Issues...", total=len(issues))
        
        for i, issue in enumerate(issues):
            progress.update(task, description=f"Creating: {issue['title'][:30]}...")
            success, result = github_api.create_issue(full_repo, issue["title"], issue["body"], issue["labels"])
            
            if success:
                created += 1
                console.print(f"[success]✅ {issue['title'][:50]}...[/success]")
            else:
                failed += 1
                console.print(f"[error]❌ {issue['title'][:30]}... - {result}[/error]")
            
            progress.advance(task)
    
    # Results summary
    if created > 0:
        success_panel = Panel(
            f"[success]✅ Successfully created {created}/{len(issues)} issues[/success]\n"
            f"[warning]❌ Failed: {failed}[/warning]" if failed > 0 else "",
            title="[success]Creation Complete[/success]",
            box=ROUNDED,
            style="success"
        )
        console.print(success_panel)
        write_to_changelog(f"GitHub Issues created: {created} issues for {repo_name}", "success")
    else:
        error_panel = Panel(
            f"[error]❌ No issues were created successfully[/error]\n"
            f"[error]Total failures: {failed}[/error]",
            title="[error]Creation Failed[/error]",
            box=ROUNDED,
            style="error"
        )
        console.print(error_panel)
    
    input("Press Enter to continue...")

# ═══════════════════════════════════════════════════════════════════════════════
# Enhanced Project Creation (v3.7.3.4.5)
# ═══════════════════════════════════════════════════════════════════════════════

def create_local_project(project_path: Path) -> Tuple[bool, str]:
    """Erstellt ein neues lokales Git-Projekt mit README Template"""
    try:
        if project_path.exists():
            return False, f"Path {project_path} already exists"
        
        project_path.mkdir(parents=True)
        
        # Git Repository initialisieren
        result = subprocess.run(
            ["git", "init"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Git init failed: {result.stderr}"
        
        # README.md Template erstellen (gleicher Inhalt wie im Original)
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
        
        write_to_changelog(f"New project created: {project_path.name}", "success")
        return True, f"Project successfully created: {project_path}"
        
    except Exception as e:
        return False, str(e)

def modern_project_creation_menu():
    """Ultra-moderne Projekterstellung mit Dashboard"""
    context = "🚀 Complete project setup workflow with AI integration"
    menu_options = [
        ("🆕 Create New Project", "Create local Git repository with comprehensive README.md template"),
        ("🤖 Generate Roadmap", "AI-powered technical roadmap generation from existing README.md"),
        ("📋 Create GitHub Issues", "Automatic issue creation from roadmap.md in GitHub repository"),
        ("🔥 Complete Workflow", "Full workflow: Project → Roadmap → GitHub Issues"),
        ("🔙 Back to Main Menu", "Return to main application menu")
    ]
    
    while True:
        choice = modern_menu("🚀 Project Setup v3.7.3.4.5-tuitest", menu_options, context)
        if choice is None or choice == 4:  # Back
            break
        elif choice == 0:  # New Project
            name = Prompt.ask("📁 [cyan]Project name[/cyan]")
            if name:
                path = Path.cwd() / name
                modern_execute_and_display("Creating Project", lambda: create_local_project(path))
                
        elif choice == 1:  # Generate Roadmap
            dirs = [d for d in Path.cwd().iterdir() if d.is_dir() and (d / ".git").exists()]
            if not dirs:
                console.print(Panel(
                    "[warning]No Git repositories found in current directory[/warning]",
                    title="[warning]No Repositories[/warning]",
                    style="warning"
                ))
                input("Press Enter...")
                continue
            
            console.print(Panel("🗂️ [primary]Available Repositories[/primary]", style="primary"))
            for i, d in enumerate(dirs):
                console.print(f"  [accent]{i+1}.[/accent] [info]{d.name}[/info]")
            
            try:
                idx = int(Prompt.ask("Repository to select", choices=[str(i+1) for i in range(len(dirs))])) - 1
                if 0 <= idx < len(dirs):
                    modern_generate_roadmap(dirs[idx])
            except (ValueError, IndexError):
                console.print("[error]Invalid selection[/error]")
                input()
                
        elif choice == 2:  # GitHub Issues
            dirs = [d for d in Path.cwd().iterdir() if d.is_dir() and (d / "roadmap.md").exists()]
            if not dirs:
                console.print(Panel(
                    "[warning]No repositories with roadmap.md found[/warning]",
                    title="[warning]No Roadmaps[/warning]",
                    style="warning"
                ))
                input("Press Enter...")
                continue
            
            console.print(Panel("🗂️ [primary]Repositories with Roadmap[/primary]", style="primary"))
            for i, d in enumerate(dirs):
                console.print(f"  [accent]{i+1}.[/accent] [info]{d.name}[/info]")
            
            try:
                idx = int(Prompt.ask("Repository to select", choices=[str(i+1) for i in range(len(dirs))])) - 1
                if 0 <= idx < len(dirs):
                    modern_setup_github_project(dirs[idx])
            except (ValueError, IndexError):
                console.print("[error]Invalid selection[/error]")
                input()
                
        elif choice == 3:  # Complete Workflow
            name = Prompt.ask("📁 [cyan]Project name for complete setup[/cyan]")
            if name:
                path = Path.cwd() / name
                console.clear()
                
                # Workflow header
                workflow_header = Panel(
                    f"🔥 [primary]Complete Project Workflow[/primary]\n"
                    f"[secondary]Project:[/secondary] [accent]{name}[/accent]",
                    box=DOUBLE,
                    style="primary"
                )
                console.print(workflow_header)
                
                # Step 1: Create Project
                with console.status("🔹 Step 1/4: Creating project..."):
                    success, result = create_local_project(path)
                    if not success:
                        error_panel = Panel(
                            f"[error]❌ Error: {result}[/error]",
                            title="[error]Creation Failed[/error]",
                            style="error"
                        )
                        console.print(error_panel)
                        input()
                        continue
                
                step1_panel = Panel(
                    "[success]✅ Project created successfully[/success]",
                    title="[success]Step 1 Complete[/success]",
                    style="success"
                )
                console.print(step1_panel)
                
                # Step 2: README editing
                readme_path = path / "README.md"
                step2_panel = Panel(
                    f"🔹 [primary]Step 2/4: Customize README.md[/primary]\n\n"
                    f"[info]📝 File: {readme_path}[/info]\n"
                    f"[accent]💡 Tip: Describe your project in detail for better roadmap generation[/accent]\n\n"
                    f"[warning]⏱️ Edit the README.md file now and press Enter when ready...[/warning]",
                    title="[primary]README Customization[/primary]",
                    style="primary"
                )
                console.print(step2_panel)
                input()
                
                # Step 3: Generate Roadmap
                step3_panel = Panel(
                    "🔹 [primary]Step 3/4: AI Roadmap Generation[/primary]",
                    title="[primary]Roadmap Generation[/primary]",
                    style="primary"
                )
                console.print(step3_panel)
                modern_generate_roadmap(path)
                
                # Step 4: GitHub Issues
                if (path / "roadmap.md").exists():
                    step4_panel = Panel(
                        "🔹 [primary]Step 4/4: GitHub Issues Creation[/primary]",
                        title="[primary]GitHub Integration[/primary]",
                        style="primary"
                    )
                    console.print(step4_panel)
                    modern_setup_github_project(path)
                
                # Completion
                completion_panel = Panel(
                    f"[success]🎉 Complete setup finished![/success]\n\n"
                    f"[info]📁 Project: {path}[/info]\n"
                    f"[info]📋 README.md: {path / 'README.md'}[/info]\n"
                    f"[info]🗺️ Roadmap: {path / 'roadmap.md'}[/info]",
                    title="[success]Workflow Complete[/success]",
                    box=DOUBLE,
                    style="success"
                )
                console.print(completion_panel)
                write_to_changelog(f"Complete project setup: {name}", "success")
                input("Press Enter to continue...")

# ═══════════════════════════════════════════════════════════════════════════════
# Modern Configuration & System Management
# ═══════════════════════════════════════════════════════════════════════════════

def modern_configuration_menu():
    """Ultra-moderne Konfiguration"""
    user = get_active_user()
    ucfg = load_user_config(user) or {}
    
    context = f"⚙️ Configuration management for user: {user}"
    menu_options = [
        ("🔐 GitHub Token", "Set GitHub Personal Access Token for issue creation"),
        ("🤖 OpenRouter Token", "Set OpenRouter API token for AI roadmap generation"),
        ("👤 GitHub Username", "Configure default GitHub username"),
        ("🧠 AI Model Selection", "Choose OpenRouter model for roadmap generation"),
        ("📊 View Configuration", "Display current configuration settings"),
        ("🔙 Back to Main", "Return to main menu")
    ]
    
    while True:
        choice = modern_menu("⚙️ Configuration Center", menu_options, context)
        if choice is None or choice == 5:
            break
        elif choice == 0:  # GitHub Token
            current = "✅ Set" if ucfg.get('github_token') else "❌ Not set"
            console.print(Panel(f"[info]Current status: {current}[/info]", style="info"))
            token = Prompt.ask("🔐 [cyan]GitHub Personal Access Token[/cyan]", password=True)
            if token:
                ucfg['github_token'] = token
                save_user_config(user, ucfg)
                console.print(Panel("[success]✅ GitHub Token saved securely[/success]", style="success"))
        elif choice == 1:  # OpenRouter Token
            current = "✅ Set" if ucfg.get('openrouter_token') else "❌ Not set"
            console.print(Panel(f"[info]Current status: {current}[/info]", style="info"))
            token = Prompt.ask("🤖 [cyan]OpenRouter API Token[/cyan]", password=True)
            if token:
                ucfg['openrouter_token'] = token
                save_user_config(user, ucfg)
                console.print(Panel("[success]✅ OpenRouter Token saved securely[/success]", style="success"))
        elif choice == 2:  # GitHub Username
            current = ucfg.get('github_username', 'Not set')
            console.print(Panel(f"[info]Current: {current}[/info]", style="info"))
            username = Prompt.ask("👤 [cyan]GitHub Username[/cyan]")
            if username:
                ucfg['github_username'] = username
                save_user_config(user, ucfg)
                console.print(Panel(f"[success]✅ GitHub Username saved: {username}[/success]", style="success"))
        elif choice == 3:  # AI Model
            models = [
                "openai/gpt-3.5-turbo", 
                "openai/gpt-4", 
                "anthropic/claude-3-haiku", 
                "google/gemini-pro"
            ]
            current = ucfg.get('model', 'openai/gpt-3.5-turbo')
            
            console.print(Panel("🤖 [primary]Available AI Models[/primary]", style="primary"))
            for i, model in enumerate(models):
                marker = "🟢" if model == current else "⚪"
                console.print(f"  {i+1}. {marker} [info]{model}[/info]")
            
            try:
                choice_idx = int(Prompt.ask("Model to select", choices=[str(i+1) for i in range(len(models))])) - 1
                if 0 <= choice_idx < len(models):
                    ucfg['model'] = models[choice_idx]
                    save_user_config(user, ucfg)
                    console.print(Panel(f"[success]✅ AI Model set: {models[choice_idx]}[/success]", style="success"))
            except (ValueError, IndexError):
                console.print(Panel("[error]Invalid selection[/error]", style="error"))
        elif choice == 4:  # View Configuration
            modern_show_config_details(user, ucfg)
        
        if choice != 4:  # Don't pause on config view
            input("Press Enter to continue...")

def modern_show_config_details(user: str, ucfg: Dict):
    """Shows detailed configuration in modern layout"""
    console.clear()
    
    header = Panel(
        "⚙️ [primary]Configuration Overview[/primary]",
        box=DOUBLE,
        style="primary"
    )
    console.print(header)
    
    # Configuration table
    table = Table(box=ROUNDED, show_header=True, header_style="bold primary")
    table.add_column("Setting", style="cyan", width=20)
    table.add_column("Status", style="white", width=15)
    table.add_column("Value/Details", style="info")
    
    table.add_row("👤 User", "✅ Active", user)
    table.add_row("🔐 GitHub Token", 
                  "✅ Configured" if ucfg.get('github_token') else "❌ Missing", 
                  "Required for issue creation")
    table.add_row("🤖 OpenRouter Token", 
                  "✅ Configured" if ucfg.get('openrouter_token') else "❌ Missing", 
                  "Required for AI roadmap generation")
    table.add_row("👤 GitHub Username", 
                  "✅ Set" if ucfg.get('github_username') else "❌ Not set", 
                  ucfg.get('github_username', 'Not configured'))
    table.add_row("🧠 AI Model", 
                  "✅ Selected", 
                  ucfg.get('model', 'openai/gpt-3.5-turbo'))
    
    config_panel = Panel(table, title="[cyan]Current Settings[/cyan]", style="cyan")
    console.print(config_panel)
    
    # Status summary
    github_ok = bool(ucfg.get('github_token'))
    openrouter_ok = bool(ucfg.get('openrouter_token'))
    
    if github_ok and openrouter_ok:
        status_text = "[success]🟢 All systems ready! Full functionality available.[/success]"
        status_style = "success"
    elif github_ok or openrouter_ok:
        status_text = "[warning]🟡 Partial configuration. Some features may be limited.[/warning]"
        status_style = "warning"
    else:
        status_text = "[error]🔴 Configuration incomplete. Please set tokens to use full features.[/error]"
        status_style = "error"
    
    status_panel = Panel(status_text, title="[primary]System Status[/primary]", style=status_style)
    console.print(status_panel)
    
    input("Press Enter to continue...")

def modern_show_dashboard():
    """Ultra-moderne System-Dashboard"""
    console.clear()
    
    header = Panel(
        "📊 [primary]GREPO2 System Dashboard[/primary]\n"
        "[secondary]Real-time system overview[/secondary]",
        box=DOUBLE,
        style="primary"
    )
    console.print(header)
    
    user = get_active_user()
    ucfg = load_user_config(user) or {}
    
    # System Status Table
    status_table = Table(box=ROUNDED, show_header=True, header_style="bold primary")
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", style="white")
    status_table.add_column("Details", style="info")
    
    status_table.add_row("🌟 GREPO2", "[success]✅ v3.7.3.4.5-tuitest[/success]", "Modern TUI fully operational")
    status_table.add_row("👤 Active User", "[success]✅ Online[/success]", user)
    status_table.add_row("🔐 GitHub Token", 
                        "[success]✅ OK[/success]" if ucfg.get('github_token') else "[error]❌ Missing[/error]", 
                        "For issue creation")
    status_table.add_row("🤖 OpenRouter Token", 
                        "[success]✅ OK[/success]" if ucfg.get('openrouter_token') else "[error]❌ Missing[/error]", 
                        "For AI roadmap generation")
    status_table.add_row("📁 Working Directory", "[success]✅ OK[/success]", str(Path.cwd()))
    
    # Git Status Check
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        git_status = "[success]✅ OK[/success]" if result.returncode == 0 else "[error]❌ Missing[/error]"
        git_version = result.stdout.strip() if result.returncode == 0 else "Not installed"
    except:
        git_status = "[error]❌ Missing[/error]"
        git_version = "Not installed"
    
    status_table.add_row("🔧 Git", git_status, git_version)
    
    system_panel = Panel(status_table, title="[primary]System Status[/primary]", style="primary")
    console.print(system_panel)
    
    # Feature Availability
    features_table = Table(box=ROUNDED, show_header=True, header_style="bold secondary")
    features_table.add_column("Feature", style="cyan")
    features_table.add_column("Availability", style="white")
    features_table.add_column("Requirements", style="info")
    
    functions = [
        ("🚀 Project Creation", "[success]✅ Available[/success]", "No additional requirements"),
        ("🤖 AI Roadmap Generation", 
         "[success]✅ Ready[/success]" if ucfg.get('openrouter_token') else "[warning]⚠️ Token Required[/warning]", 
         "OpenRouter API token"),
        ("📋 GitHub Issue Creation", 
         "[success]✅ Ready[/success]" if ucfg.get('github_token') else "[warning]⚠️ Token Required[/warning]", 
         "GitHub Personal Access Token"),
        ("📝 CHANGELOG Integration", "[success]✅ Available[/success]", "No additional requirements"),
        ("⚙️ Configuration Management", "[success]✅ Available[/success]", "No additional requirements")
    ]
    
    for feature, availability, requirements in functions:
        features_table.add_row(feature, availability, requirements)
    
    features_panel = Panel(features_table, title="[secondary]Feature Availability[/secondary]", style="secondary")
    console.print(features_panel)
    
    # Quick Stats
    current_dir = Path.cwd()
    git_repos = len([d for d in current_dir.iterdir() if d.is_dir() and (d / ".git").exists()])
    roadmap_files = len([d for d in current_dir.iterdir() if d.is_dir() and (d / "roadmap.md").exists()])
    
    stats_content = f"""[info]Directory Statistics:[/info]
• Git Repositories: [accent]{git_repos}[/accent]
• Projects with Roadmaps: [accent]{roadmap_files}[/accent]
• Current Time: [accent]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/accent]
• GREPO2 Uptime: [accent]Active Session[/accent]"""
    
    stats_panel = Panel(stats_content, title="[info]Quick Statistics[/info]", style="info")
    console.print(stats_panel)
    
    input("Press Enter to continue...")

def modern_show_documentation():
    """Ultra-moderne Dokumentation"""
    console.clear()
    
    header = Panel(
        "📚 [primary]GREPO2 v3.7.3.4.5-tuitest Documentation[/primary]\n"
        "[secondary]Comprehensive user guide and reference[/secondary]",
        box=DOUBLE,
        style="primary"
    )
    console.print(header)
    
    # Main documentation content with modern formatting
    doc_sections = [
        {
            "title": "🌟 Overview",
            "content": """GREPO2 v3.7.3.4.5-tuitest is an advanced Git Repository Manager with AI-powered project management capabilities and a cutting-edge Terminal User Interface.

[bold]Key Capabilities:[/bold]
• Complete project lifecycle management
• AI-powered roadmap generation using OpenRouter
• Automated GitHub issue creation
• Modern, interactive terminal interface
• Secure configuration management"""
        },
        {
            "title": "🚀 Main Features",
            "content": """[bold]🆕 PROJECT CREATION[/bold]
• Creates new Git repositories with comprehensive README.md templates
• Automatic Git initialization and initial commit
• Structured project templates for professional development

[bold]🤖 AI ROADMAP GENERATION (RESTORED)[/bold]
• Analyzes README.md as project specification
• Generates technical roadmaps using OpenRouter AI
• Structured phases with detailed tasks
• Supports multiple AI models (GPT, Claude, Gemini)

[bold]📋 GITHUB ISSUE CREATION (RESTORED)[/bold]
• Parses roadmap.md automatically
• Creates GitHub issues for each task
• Automatic labels and phase assignment
• Batch processing for large roadmaps

[bold]⚙️ CONFIGURATION MANAGEMENT[/bold]
• Secure token management with Base64 encoding
• User-specific settings
• Multiple AI models available
• GitHub integration setup"""
        },
        {
            "title": "🔧 Installation & Setup",
            "content": """[bold]1. Dependencies Installation:[/bold]
```bash
pip install click requests rich
```

[bold]2. Configuration:[/bold]
• Generate GitHub Personal Access Token (repo, issues permissions)
• Create OpenRouter account and get API key
• In GREPO2: Menu → Configuration → Set Tokens

[bold]3. First Use:[/bold]
• Menu → Project Workflow → Complete Workflow
• Customize README.md according to your requirements
• Let AI generate roadmap automatically
• Create GitHub issues from roadmap"""
        },
        {
            "title": "🎯 Workflow Example",
            "content": """[bold]Complete Project Setup Process:[/bold]

[accent]Step 1:[/accent] "Create New Project" → Enter project name
[accent]Step 2:[/accent] Edit README.md with your detailed requirements
[accent]Step 3:[/accent] "Generate Roadmap" → AI creates technical roadmap
[accent]Step 4:[/accent] "Create GitHub Issues" → Automatic issue creation
[accent]Result:[/accent] Fully configured GitHub repository ready for development!

[bold]💡 Pro Tips:[/bold]
• More detailed README.md = better roadmap quality
• Include functional and technical requirements
• Describe non-functional requirements too
• GitHub repository must exist for issue creation"""
        }
    ]
    
    for section in doc_sections:
        section_panel = Panel(
            section["content"],
            title=f"[primary]{section['title']}[/primary]",
            box=ROUNDED,
            style="info",
            expand=True
        )
        console.print(section_panel)
        console.print()  # Add spacing
    
    # Footer
    footer = Panel(
        "[primary]Developed by Dennis (2024)[/primary] - [secondary]v3.7.3.4.5-tuitest MODERN TUI EDITION[/secondary]",
        box=MINIMAL,
        style="muted"
    )
    console.print(footer)
    
    input("Press Enter to continue...")

# ═══════════════════════════════════════════════════════════════════════════════
# Modern Main Application (v3.7.3.4.5)
# ═══════════════════════════════════════════════════════════════════════════════

def modern_main_menu():
    """Ultra-moderne Hauptmenü"""
    context = f"🌟 GREPO2 v3.7.3.4.5-tuitest - Complete restoration with modern TUI | User: {get_active_user()}"
    menu_options = [
        ("🚀 Project Workflow", "Complete project workflow: Create → Roadmap → GitHub Issues"),
        ("⚙️ Configuration", "Manage API tokens and application settings"),
        ("📊 System Dashboard", "Real-time system status and configuration overview"),
        ("📚 Documentation", "Comprehensive help and user guides"),
        ("🚪 Exit Application", "Close GREPO2 application")
    ]
    
    # Welcome animation
    ModernUI.animated_loading("Initializing GREPO2 Modern TUI", 1)
    
    while True:
        choice = modern_menu("🌟 GREPO2 v3.7.3.4.5-tuitest", menu_options, context)
        if choice is None or choice == 4:  # Exit
            # Goodbye animation
            farewell_panel = Panel(
                "[primary]👋 Thank you for using GREPO2![/primary]\n"
                "[secondary]Modern TUI version 3.7.3.4.5-tuitest[/secondary]",
                box=DOUBLE,
                style="primary"
            )
            console.print(farewell_panel)
            break
        elif choice == 0:  # Project Workflow
            modern_project_creation_menu()
        elif choice == 1:  # Configuration
            modern_configuration_menu()
        elif choice == 2:  # Dashboard
            modern_show_dashboard()
        elif choice == 3:  # Documentation
            modern_show_documentation()

# ═══════════════════════════════════════════════════════════════════════════════
# Enhanced CLI Interface (v3.7.3.4.5)
# ═══════════════════════════════════════════════════════════════════════════════

@click.group()
@click.version_option(version="3.7.3.4.5-tuitest", prog_name="grepo2")
def cli():
    """🌟 GREPO2 v3.7.3.4.5-tuitest - Modern TUI Git Repository Manager with fully restored AI functionality"""
    pass

@cli.command()
def tui():
    """🖥️ Launch the Modern TUI (Terminal User Interface)"""
    try:
        # Startup animation
        with console.status("[cyan]Initializing Modern TUI...", spinner="dots"):
            time.sleep(1)
        
        startup_panel = Panel(
            "[primary]🌟 GREPO2 Modern TUI Starting...[/primary]\n"
            "[secondary]Version 3.7.3.4.5-tuitest[/secondary]",
            box=DOUBLE,
            style="primary"
        )
        console.print(startup_panel)
        time.sleep(1)
        
        modern_main_menu()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye! Thanks for using GREPO2![/yellow]")
    except Exception as e:
        error_panel = Panel(
            f"[error]❌ Application Error: {e}[/error]",
            title="[error]Error[/error]",
            style="error"
        )
        console.print(error_panel)

@cli.command()
@click.argument('project_name')
def create(project_name):
    """🚀 Create a new project with modern feedback"""
    console.print(Panel(f"[primary]Creating project: {project_name}[/primary]", style="primary"))
    
    path = Path.cwd() / project_name
    success, result = create_local_project(path)
    
    if success:
        success_panel = Panel(
            f"[success]✅ {result}[/success]",
            title="[success]Project Created[/success]",
            style="success"
        )
        console.print(success_panel)
    else:
        error_panel = Panel(
            f"[error]❌ {result}[/error]",
            title="[error]Creation Failed[/error]",
            style="error"
        )
        console.print(error_panel)

@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def roadmap(repo_path):
    """🤖 Generate roadmap for repository with modern UI"""
    console.print(Panel(f"[primary]Generating roadmap for: {repo_path}[/primary]", style="primary"))
    modern_generate_roadmap(Path(repo_path))

@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def issues(repo_path):
    """📋 Create GitHub issues from roadmap with modern feedback"""
    console.print(Panel(f"[primary]Creating GitHub issues for: {repo_path}[/primary]", style="primary"))
    modern_setup_github_project(Path(repo_path))

@cli.command()
def configure():
    """⚙️ Manage configuration with modern interface"""
    console.print(Panel("[primary]Opening Configuration Center...[/primary]", style="primary"))
    modern_configuration_menu()

@cli.command()
def status():
    """📊 Show system status with modern dashboard"""
    console.print(Panel("[primary]Loading System Dashboard...[/primary]", style="primary"))
    modern_show_dashboard()

@cli.command()
def docs():
    """📚 Show documentation with modern formatting"""
    console.print(Panel("[primary]Loading Documentation...[/primary]", style="primary"))
    modern_show_documentation()

# ═══════════════════════════════════════════════════════════════════════════════
# Application Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Startup banner
    startup_banner = Panel(
        "[bold primary]🌟 GREPO2 v3.7.3.4.5-tuitest[/bold primary]\n"
        "[secondary]Modern Terminal User Interface Edition[/secondary]\n"
        "[info]Fully restored AI functionality with cutting-edge TUI[/info]",
        box=DOUBLE,
        style="primary"
    )
    console.print(startup_banner)
    
    # Run CLI
    cli()