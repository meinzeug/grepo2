#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grepo2: Ein TUI- und CLI-Tool zur Vereinfachung der GitHub-Verwaltung.
Erweitert um autonome Code-Generierung mit Codex CLI und OpenRouter Integration.
"""

import sys
import subprocess
import json
import os
import base64
import curses
import textwrap
import shutil
import time
import requests
import re
import filecmp
from pathlib import Path
from typing import List, Tuple, Any, Optional, Callable, Dict
from getpass import getpass

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("❌ Fehler: Notwendige Python-Pakete (rich, click) nicht gefunden.", file=sys.stderr)
    print("   Bitte installieren Sie diese mit: pip install rich click", file=sys.stderr)
    sys.exit(1)


# ─── Section I: Pre-flight & Config ────────────────────────────────────────────

def check_git_cli() -> bool:
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ Fehler: Das Git CLI ('git') ist nicht im System-PATH gefunden.", file=sys.stderr)
        print("   Bitte installieren Sie Git für Dein Betriebssystem.", file=sys.stderr)
        return False

def check_codex_cli() -> bool:
    """Prüft ob Codex CLI installiert ist, installiert es falls nötig"""
    try:
        result = subprocess.run(["codex", "--version"], check=True, capture_output=True, text=True)
        console.print(f"[green]✓ Codex CLI gefunden: {result.stdout.strip()}[/green]")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        console.print("[yellow]⚠ Codex CLI nicht gefunden. Installation wird versucht...[/yellow]")
        try:
            subprocess.run(["npm", "install", "-g", "@openai/codex"], check=True)
            console.print("[green]✓ Codex CLI erfolgreich installiert![/green]")
            return True
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            console.print(f"[red]❌ Codex CLI Installation fehlgeschlagen: {e}[/red]")
            console.print("[yellow]Bitte installieren Sie Node.js und npm, dann: npm install -g @openai/codex[/yellow]")
            return False

CONFIG_DIR  = Path.home() / ".config" / "grepo2"
USERS_DIR   = CONFIG_DIR  / "users"
GITHUB_DIR  = Path.home()  / "github2"
CONFIG_FILE = CONFIG_DIR   / "config.json"
CODEX_DIR   = Path.home()  / ".codex"
for p in (CONFIG_DIR, USERS_DIR, GITHUB_DIR, CODEX_DIR):
    p.mkdir(parents=True, exist_ok=True)

def _obfuscate(data: str) -> str:
    return base64.b64encode(data.encode()).decode()

def _deobfuscate(data: str) -> str:
    return base64.b64decode(data.encode()).decode()

def get_main_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_main_config(cfg: Dict[str, Any]):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


# ─── Section II: Multi-User Config ─────────────────────────────────────────────

def get_active_user() -> Optional[str]:
    return get_main_config().get("active_user")

def set_active_user(username: str):
    cfg = get_main_config()
    cfg['active_user'] = username
    cfg['last_repo_path'] = None
    save_main_config(cfg)

def load_user_config(username: str) -> Optional[Dict[str, Any]]:
    uf = USERS_DIR / f"{username}.json"
    if not uf.exists():
        return None
    with open(uf, 'r') as f:
        try:
            data = json.load(f)
            if "token" in data:
                data["token"] = _deobfuscate(data["token"])
            return data
        except (json.JSONDecodeError, KeyError):
            return None

def save_user_config(username: str, token: str):
    uf = USERS_DIR / f"{username}.json"
    data = {"username": username, "token": _obfuscate(token)}
    with open(uf, 'w') as f:
        json.dump(data, f, indent=2)

def update_user_config(username: str,
                       token: Optional[str] = None,
                       openrouter_token: Optional[str] = None,
                       model: Optional[str] = None):
    uf = USERS_DIR / f"{username}.json"
    if uf.exists():
        with open(uf, 'r') as f:
            try:
                data = json.load(f)
            except:
                data = {"username": username}
    else:
        data = {"username": username}
    if token is not None:
        data["token"] = _obfuscate(token)
    if openrouter_token is not None:
        data["openrouter_token"] = openrouter_token
    if model is not None:
        data["model"] = model
    with open(uf, 'w') as f:
        json.dump(data, f, indent=2)

def get_all_users() -> List[str]:
    return sorted(p.stem for p in USERS_DIR.glob("*.json"))

def delete_user_config(username: str):
    uf = USERS_DIR / f"{username}.json"
    if uf.exists():
        uf.unlink()


# ─── Section III: API Abstractions ──────────────────────────────────────────────

class LocalGitAPI:
    def _run_command(self, repo_path: Path, command: List[str], capture=True) -> Tuple[bool, str]:
        try:
            proc = subprocess.run(
                ["git"] + command,
                cwd=str(repo_path),
                capture_output=capture,
                text=True,
                check=False,
                encoding='utf-8'
            )
            if proc.returncode != 0:
                return False, proc.stderr or proc.stdout
            return True, proc.stdout
        except Exception as e:
            return False, str(e)

    def status(self, path: Path):
        return self._run_command(path, ["status"])

    def commit(self, path: Path):
        return self._run_command(path, ["commit", "-v"], capture=False)

    def force_push_to_remote(self, path: Path):
        ok, msg = self._run_command(path, ["add", "-A"])
        if not ok:
            return False, f"Fehler beim Hinzufügen: {msg}"
        ok, stat = self._run_command(path, ["status", "--porcelain"])
        if ok and stat.strip():
            ok, msg = self._run_command(path, ["commit", "-m", "Auto-Commit vor Force Push"])
            if not ok:
                return False, f"Fehler beim Commit: {msg}"
        ok, br = self._run_command(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if not ok:
            return False, "Branch nicht ermittelbar"
        return self._run_command(path, ["push", "--force", "origin", br.strip()])

    def force_pull_from_remote(self, path: Path):
        git_dir = path / ".git"
        if not git_dir.is_dir():
            if path.exists():
                shutil.rmtree(path)
            ok, msg = gh_api.clone_repo(path.name, str(path))
            if ok:
                return True, "Lokales Repo wurde vollständig aus GitHub neu geklont!"
            else:
                return False, f"Klonen fehlgeschlagen: {msg}"
        ok, br = self._run_command(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if not ok:
            return False, "Branch nicht ermittelbar"
        ok, msg = self._run_command(path, ["fetch", "origin"])
        if not ok:
            return False, msg
        return self._run_command(path, ["reset", "--hard", f"origin/{br.strip()}"])

    def hard_push_update(self, path: Path):
        ok, msg = self._run_command(path, ["add", "-A"])
        if not ok:
            return False, f"Fehler beim Hinzufügen: {msg}"
        ok, stat = self._run_command(path, ["status", "--porcelain"])
        if ok and stat.strip():
            ok, msg = self._run_command(path, ["commit", "-m", "Auto-Commit vor Hard Push"])
            if not ok:
                return False, f"Fehler beim Commit: {msg}"
        ok, br = self._run_command(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if not ok:
            return False, "Branch nicht ermittelbar"
        return self._run_command(path, ["push", "--force-with-lease", "origin", br.strip()])

    def hard_pull_update(self, path: Path):
        ok, msg = self._run_command(path, ["clean", "-fdx"])
        if not ok:
            return False, f"Fehler beim clean: {msg}"
        ok, br = self._run_command(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if not ok:
            return False, "Branch nicht ermittelbar"
        self._run_command(path, ["config", "pull.rebase", "true"])
        return self._run_command(path, ["pull", "--autostash", "origin", br.strip()])

    def soft_push_update(self, path: Path):
        ok, msg = self._run_command(path, ["add", "-A"])
        if not ok:
            return False, f"Fehler beim Hinzufügen: {msg}"
        ok, stat = self._run_command(path, ["status", "--porcelain"])
        if ok and stat.strip():
            ok, msg = self._run_command(path, ["commit", "-m", "Auto-Commit vor Soft Push"])
            if not ok:
                return False, f"Fehler beim Commit: {msg}"
        ok, br = self._run_command(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if not ok:
            return False, "Branch nicht ermittelbar"
        return self._run_command(path, ["push", "origin", br.strip()])

    def soft_pull_update(self, path: Path):
        ok, msg = self._run_command(path, ["add", "-A"])
        if not ok:
            return False, f"Fehler beim Hinzufügen: {msg}"
        ok, stat = self._run_command(path, ["status", "--porcelain"])
        if ok and stat.strip():
            ok, msg = self._run_command(path, ["commit", "-m", "Auto-Commit vor Soft Pull"])
            if not ok:
                return False, f"Fehler beim Commit: {msg}"
        ok, br = self._run_command(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if not ok:
            return False, "Branch nicht ermittelbar"
        return self._run_command(path, ["pull", "--ff-only", "origin", br.strip()])

    def add_all_and_commit(self, path: Path, message: str = "Auto-commit all changes"):
        ok, msg = self._run_command(path, ["add", "-A"])
        if not ok:
            return False, f"Fehler beim Hinzufügen: {msg}"
        ok, stat = self._run_command(path, ["status", "--porcelain"])
        if ok and not stat.strip():
            return True, "Keine Änderungen zu committen."
        return self._run_command(path, ["commit", "-m", message])


class GitHubAPI:
    def __init__(self, username: str, token: str):
        self.username = username
        self.token = token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept":        "application/vnd.github+json",
            "User-Agent":    f"grepo2-{self.username}"
        }

    def _run_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Tuple[bool, Any]:
        try:
            resp = requests.request(method.upper(), f"https://api.github.com/{endpoint}",
                                     headers=self.headers, json=data)
            if resp.status_code >= 400:
                return False, resp.json().get("message", f"HTTP-Fehler {resp.status_code}")
            return True, resp.json() if resp.text else ""
        except Exception as e:
            return False, f"Netzwerkfehler: {e}"

    def repo_exists(self, repo_name: str) -> bool:
        ok, _ = self._run_request('GET', f'repos/{self.username}/{repo_name}')
        return ok

    def create_repo(self, name: str, description: str, private: bool) -> Tuple[bool, Any]:
        return self._run_request('POST', 'user/repos',
                                  data={'name': name, 'description': description, 'private': private})

    def clone_repo(self, repo_name: str, target_dir: str) -> Tuple[bool, Any]:
        clone_url = f"https://{self.username}:{self.token}@github.com/{self.username}/{repo_name}.git"
        try:
            res = subprocess.run(["git", "clone", clone_url, str(target_dir)],
                                 capture_output=True, text=True, check=False)
            if res.returncode != 0:
                return False, res.stderr
            return True, res.stdout
        except FileNotFoundError:
            return False, "Git ist nicht installiert."

    def delete_repo(self, repo_name: str) -> Tuple[bool, Any]:
        return self._run_request('DELETE', f'repos/{self.username}/{repo_name}')

    def update_repo(self, repo_name: str, info: Dict) -> Tuple[bool, Any]:
        return self._run_request('PATCH', f'repos/{self.username}/{repo_name}', data=info)

    def get_issues(self, repo_name: str, state: str = "open", labels: Optional[str] = None, 
                   sort: str = "created", direction: str = "asc") -> Tuple[bool, List[Dict]]:
        """Holt Issues von GitHub Repository"""
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": 100
        }
        if labels:
            params["labels"] = labels
        
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{self.username}/{repo_name}/issues",
                headers=self.headers,
                params=params
            )
            if resp.status_code == 200:
                return True, resp.json()
            else:
                return False, resp.json().get("message", f"HTTP-Fehler {resp.status_code}")
        except Exception as e:
            return False, f"Netzwerkfehler: {e}"

    def get_issue_comments(self, repo_name: str, issue_number: int) -> Tuple[bool, List[Dict]]:
        """Holt Kommentare zu einem Issue"""
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{self.username}/{repo_name}/issues/{issue_number}/comments",
                headers=self.headers
            )
            if resp.status_code == 200:
                return True, resp.json()
            else:
                return False, resp.json().get("message", f"HTTP-Fehler {resp.status_code}")
        except Exception as e:
            return False, f"Netzwerkfehler: {e}"

    def update_issue_labels(self, repo_name: str, issue_number: int, labels: List[str]) -> Tuple[bool, Any]:
        """Aktualisiert Labels eines Issues"""
        try:
            resp = requests.patch(
                f"https://api.github.com/repos/{self.username}/{repo_name}/issues/{issue_number}",
                headers={**self.headers, "Accept": "application/vnd.github+json"},
                json={"labels": labels}
            )
            if resp.status_code == 200:
                return True, resp.json()
            else:
                return False, resp.json().get("message", f"HTTP-Fehler {resp.status_code}")
        except Exception as e:
            return False, f"Netzwerkfehler: {e}"

    def add_issue_comment(self, repo_name: str, issue_number: int, body: str) -> Tuple[bool, Any]:
        """Fügt einen Kommentar zu einem Issue hinzu"""
        try:
            resp = requests.post(
                f"https://api.github.com/repos/{self.username}/{repo_name}/issues/{issue_number}/comments",
                headers={**self.headers, "Accept": "application/vnd.github+json"},
                json={"body": body}
            )
            if resp.status_code == 201:
                return True, resp.json()
            else:
                return False, resp.json().get("message", f"HTTP-Fehler {resp.status_code}")
        except Exception as e:
            return False, f"Netzwerkfehler: {e}"


console = Console()
git_api = LocalGitAPI()
gh_api  = None


# ─── Section IV: Codex Integration ──────────────────────────────────────────────

class CodexIntegration:
    def __init__(self, user_config: Dict[str, Any]):
        self.user_config = user_config
        self.openrouter_token = user_config.get("openrouter_token", "")
        self.model = user_config.get("model", "openai/codex-mini-latest")
        self.live_monitoring = True
        self.current_issue = None
        self.repo_name = None
        
    def set_issue_context(self, issue: Dict, repo_name: str):
        """Setzt den Kontext für Live-Monitoring"""
        self.current_issue = issue
        self.repo_name = repo_name
        
    def log_to_issue(self, message: str, log_type: str = "info"):
        """Fügt Live-Updates als Kommentare zum aktuellen Issue hinzu"""
        if not self.current_issue or not self.repo_name:
            return
            
        timestamp = time.strftime("%H:%M:%S")
        emoji_map = {
            "info": "ℹ️",
            "success": "✅", 
            "error": "❌",
            "warning": "⚠️",
            "progress": "🔄",
            "file": "📄",
            "directory": "📁",
            "delete": "🗑️"
        }
        
        emoji = emoji_map.get(log_type, "📝")
        comment_body = f"""🤖 **Live-Update ({timestamp})**

{emoji} **{log_type.upper()}:** {message}

---
*Live-Monitoring von grepo2 Codex Integration*
"""
        
        try:
            gh_api.add_issue_comment(self.repo_name, self.current_issue['number'], comment_body)
        except Exception as e:
            console.print(f"[yellow]⚠ Live-Update Fehler: {e}[/yellow]")
        
    def ensure_codex_config(self):
        """Stellt sicher, dass Codex CLI für OpenRouter konfiguriert ist"""
        config_file = CODEX_DIR / "config.toml"
        
        # Erstelle/aktualisiere config.toml für OpenRouter Profile
        config_content = f"""
# grepo2 managed Codex configuration
# Default OpenAI Configuration
model = "o4-mini"

# Model Provider Definitions
[model_providers.openai]
name = "OpenAI"
base_url = "https://api.openai.com/v1"
env_key = "OPENAI_API_KEY"

[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"

# Profile für OpenRouter mit spezifischem Modell
[profiles.openrouter]
provider = "openrouter"
model = "{self.model}"

# Profile für direktes OpenAI
[profiles.openai]
provider = "openai"
model = "o4-mini"

# Backup Umgebungsvariablen Setup (commented)
# OPENROUTER_API_KEY={self.openrouter_token}
"""
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        console.print(f"[green]✓ Codex Konfiguration aktualisiert: {config_file}[/green]")
        self.log_to_issue(f"Codex CLI konfiguriert mit Modell: {self.model}", "info")

    def prepare_environment(self):
        """Bereitet die Umgebungsvariablen für Codex vor"""
        env = os.environ.copy()
        
        # Setze OpenRouter Token
        env["OPENROUTER_API_KEY"] = self.openrouter_token
        
        # Backup: Falls Codex OpenAI-kompatible APIs erwartet
        env["OPENAI_API_KEY"] = self.openrouter_token
        env["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"
        
        return env

    def fetch_codebase_context(self, owner: str, repo_name: str, target_dir: Path) -> bool:
        """Holt die aktuelle Codebase von github.com für Kontext"""
        try:
            context_dir = target_dir / "codex" / "codebase"
            if context_dir.exists():
                shutil.rmtree(context_dir)
            context_dir.mkdir(parents=True, exist_ok=True)
            
            # Verwende github.com API für vollständigen Repository-Kontext
            github_url = f"https://github.com/{owner}/{repo_name}/archive/main.tar.gz"
            
            console.print(f"[blue]Lade Codebase-Kontext von: {github_url}[/blue]")
            self.log_to_issue(f"Lade Codebase-Kontext von github.com/{owner}/{repo_name}", "progress")
            
            # Download und extrahiere mit curl/tar
            result = subprocess.run(
                f"curl -sSL {github_url} | tar xz -C {context_dir} --strip-components=1",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Codebase-Kontext erfolgreich geladen[/green]")
                self.log_to_issue("Codebase-Kontext erfolgreich heruntergeladen", "success")
                return True
            else:
                console.print(f"[yellow]⚠ Codebase-Download fehlgeschlagen: {result.stderr}[/yellow]")
                self.log_to_issue(f"Codebase-Download fehlgeschlagen: {result.stderr}", "warning")
                # Fallback: Verwende lokales Git Repository
                console.print("[blue]Verwende lokales Repository als Kontext...[/blue]")
                self.log_to_issue("Verwende lokales Repository als Fallback-Kontext", "info")
                return True
                
        except Exception as e:
            console.print(f"[yellow]⚠ Fehler beim Codebase-Download: {e}[/yellow]")
            self.log_to_issue(f"Fehler beim Codebase-Download: {e}", "error")
            return True  # Fortfahren ohne externen Kontext

    def generate_comprehensive_prompt(self, issue: Dict, comments: List[str], repo_path: Path) -> str:
        """Generiert einen umfassenden Prompt für Codex mit Issue-Kontext"""
        issue_number = issue['number']
        issue_title = issue['title']
        issue_body = issue.get('body', '')
        
        # Analysiere README.md falls vorhanden
        readme_content = ""
        readme_file = repo_path / "README.md"
        if readme_file.exists():
            try:
                with open(readme_file, 'r', encoding='utf-8') as f:
                    readme_content = f.read()[:2000]  # Erste 2000 Zeichen
            except:
                pass

        # Analysiere roadmap.md falls vorhanden
        roadmap_content = ""
        roadmap_file = repo_path / "roadmap.md"
        if roadmap_file.exists():
            try:
                with open(roadmap_file, 'r', encoding='utf-8') as f:
                    roadmap_content = f.read()[:1500]  # Erste 1500 Zeichen
            except:
                pass

        # Erstelle umfassenden Prompt
        prompt = f"""
=== ENTWICKLUNGSAUFTRAG für Issue #{issue_number}: {issue_title} ===

**WICHTIGER HINWEIS:**
Alle deine Aktionen werden automatisch über die GitHub API dokumentiert.
Jede Datei-Erstellung, -Änderung oder -Löschung wird live als Kommentar in Issue #{issue_number} protokolliert.

**PRIMÄRZIEL:** 
Implementiere vollständig und professionell die Anforderungen aus Issue #{issue_number}.

**ISSUE-DETAILS:**
{issue_body}

**BEREITS ERLEDIGTE ARBEITEN (aus Kommentaren):**
{chr(10).join(comments) if comments else "Keine vorherigen Kommentare vorhanden."}

**PROJEKTKONTEXT (README.md):**
{readme_content if readme_content else "Kein README.md gefunden."}

**TECHNISCHE ROADMAP (roadmap.md):**
{roadmap_content if roadmap_content else "Keine Roadmap gefunden."}

**ENTWICKLUNGSRICHTLINIEN:**

1. **Code-Qualität:** Schreibe sauberen, gut dokumentierten Code nach Best Practices
2. **Architektur:** Folge den bestehenden Architekturmustern im Repository
3. **Testing:** Implementiere Tests für neue Funktionalität falls nötig
4. **Dokumentation:** Aktualisiere Dokumentation bei signifikanten Änderungen
5. **Git-Workflow:** Arbeite ausschließlich außerhalb des 'codex/' Verzeichnisses
6. **Dependencies:** Installiere nur notwendige Abhängigkeiten
7. **Security:** Berücksichtige Sicherheitsaspekte bei der Implementierung
8. **Live-Monitoring:** Deine Aktionen werden automatisch dokumentiert

**ERWARTETE DELIVERABLES:**
- Vollständig funktionsfähige Implementierung des Features/Bugfixes
- Getesteter Code der das Issue vollständig löst
- Saubere Commit-Messages falls Commits erstellt werden
- Aktualisierte Dokumentation falls erforderlich

**WORKING METHODOLOGY:**
Analysiere die gesamte Codebase sorgfältig, verstehe die bestehende Architektur, und implementiere die Lösung iterativ. 
Teste deine Implementierung gründlich bevor du sie als abgeschlossen betrachtest.
Alle deine Änderungen werden automatisch überwacht und dokumentiert.

Beginne jetzt mit der Entwicklung:
"""
        
        self.log_to_issue(f"Entwicklungsauftrag generiert für Issue #{issue_number}: {issue_title}", "info")
        return prompt

    def monitor_file_changes(self, repo_path: Path, start_time: float):
        """Überwacht Dateiänderungen und protokolliert sie live"""
        try:
            # Git Status für Änderungen
            ok, git_status = git_api.status(repo_path)
            if ok and git_status.strip():
                # Parse Git Status für detaillierte Änderungen
                lines = git_status.split('\n')
                changes = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('modified:'):
                        file_path = line.split(':', 1)[1].strip()
                        changes.append(f"📝 Geändert: `{file_path}`")
                        self.log_to_issue(f"Datei geändert: {file_path}", "file")
                    elif line.startswith('new file:'):
                        file_path = line.split(':', 1)[1].strip()
                        changes.append(f"📄 Neu erstellt: `{file_path}`")
                        self.log_to_issue(f"Neue Datei erstellt: {file_path}", "success")
                    elif line.startswith('deleted:'):
                        file_path = line.split(':', 1)[1].strip()
                        changes.append(f"🗑️ Gelöscht: `{file_path}`")
                        self.log_to_issue(f"Datei gelöscht: {file_path}", "delete")
                    elif 'Untracked files:' in line:
                        self.log_to_issue("Neue unverfolgte Dateien erkannt", "info")
                
                if changes:
                    summary = f"Dateisystem-Änderungen erkannt:\n" + "\n".join(changes)
                    self.log_to_issue(summary, "progress")
                    
        except Exception as e:
            self.log_to_issue(f"Fehler bei Dateiüberwachung: {e}", "error")

    def execute_codex(self, repo_path: Path, prompt: str) -> Tuple[bool, str]:
        """Führt Codex CLI mit dem gegebenen Prompt aus"""
        try:
            self.ensure_codex_config()
            env = self.prepare_environment()
            
            # Korrigiertes Codex Kommando mit --profile statt --provider
            cmd = [
                "codex", 
                "--full-auto",  # Vollautomatischer Modus
                "--model", self.model,
                "--profile", "openrouter",  # Verwende Profile statt Provider
                prompt
            ]
            
            console.print(f"[blue]Starte Codex mit Kommando:[/] {' '.join(cmd[:4])} [...]")
            console.print(f"[blue]Arbeitsverzeichnis:[/] {repo_path}")
            console.print(f"[blue]Modell:[/] {self.model}")
            console.print(f"[blue]Profile:[/] openrouter")
            
            self.log_to_issue(f"Starte Codex-Ausführung mit Modell: {self.model}", "progress")
            
            start_time = time.time()
            
            # Führe Codex aus mit erweiterten Timeouts
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Codex arbeitet an Issue...", total=None)
                
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(repo_path),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Live-Monitoring während Codex läuft
                monitoring_interval = 30  # Alle 30 Sekunden prüfen
                last_check = start_time
                
                while proc.poll() is None:
                    current_time = time.time()
                    if current_time - last_check >= monitoring_interval:
                        elapsed = current_time - start_time
                        self.log_to_issue(f"Codex läuft seit {elapsed:.0f}s - überwache Fortschritt...", "progress")
                        self.monitor_file_changes(repo_path, start_time)
                        last_check = current_time
                    time.sleep(5)  # Kurze Pause zwischen Checks
                
                try:
                    # Erweiterte Timeout für komplexe Tasks (10 Minuten)
                    stdout, stderr = proc.communicate(timeout=10)  # Kurzer Timeout da Prozess bereits beendet
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate()
                    self.log_to_issue("Codex Timeout erreicht (10 Min) - Prozess beendet", "error")
                    return False, "Codex Timeout erreicht (10 Min) - Task zu komplex oder hängt"
            
            end_time = time.time()
            duration = end_time - start_time
            
            console.print(f"[cyan]--- CODEX STDOUT ---[/cyan]")
            console.print(stdout)
            console.print(f"[magenta]--- CODEX STDERR ---[/magenta]")
            console.print(stderr)
            console.print(f"[blue]Rückgabecode: {proc.returncode} | Dauer: {duration:.1f}s[/blue]")
            
            # Finale Dateiänderungen protokollieren
            self.log_to_issue(f"Codex-Ausführung abgeschlossen nach {duration:.1f}s", "success")
            self.monitor_file_changes(repo_path, start_time)
            
            if proc.returncode == 0:
                self.log_to_issue("Codex-Ausführung erfolgreich beendet", "success")
                return True, f"Codex erfolgreich ausgeführt in {duration:.1f}s\n\nOutput:\n{stdout}"
            else:
                error_msg = f"Codex Fehler (Code {proc.returncode}):\n{stderr}"
                self.log_to_issue(f"Codex-Fehler: {stderr[:200]}...", "error")
                return False, error_msg
                
        except Exception as e:
            self.log_to_issue(f"Unerwarteter Fehler bei Codex-Ausführung: {e}", "error")
            return False, f"Unerwarteter Fehler: {e}"


def run_curses_menu(title: str, options: List[Tuple[str,str]], context: str="") -> Optional[int]:
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
    console.clear()
    console.rule(f"[bold cyan]{title}")
    with console.status("Führe Befehl aus..."):
        ok, res = func(*args)
    if ok:
        console.print(res or "[green]✓ Erfolgreich[/green]")
    else:
        console.print(f"[bold red]Fehler:[/]\n{res}")
    input("\nDrücke Enter zum Fortfahren...")


def tui_change_github_token():
    console.clear()
    console.rule("[bold cyan]GitHub PAT ändern")
    user = get_active_user()
    if not user:
        console.print("[red]Kein aktiver Benutzer![/red]")
        input()
        return
    new = getpass("Neues GitHub PAT: ")
    if not new.strip():
        console.print("[yellow]Abgebrochen[/yellow]")
        input()
        return
    update_user_config(user, token=new)
    global gh_api
    cfg = load_user_config(user)
    gh_api = GitHubAPI(cfg["username"], cfg["token"])
    console.print("[green]✓ GitHub PAT aktualisiert![/green]")
    input()


def tui_ki_anbindung():
    console.clear()
    console.rule("[bold cyan]KI-Anbindung konfigurieren")
    user = get_active_user()
    cfg = load_user_config(user) or {}
    old_tok = cfg.get("openrouter_token", "")
    old_model = cfg.get("model", "openai/codex-mini-latest")
    
    console.print("[yellow]Empfohlene Modelle für Code-Generierung:[/yellow]")
    console.print("• openai/codex-mini-latest (optimiert für Codex CLI)")
    console.print("• openai/gpt-4o (sehr gut für komplexe Tasks)")
    console.print("• anthropic/claude-3.5-sonnet (excellent für Code)")
    console.print("• qwen/qwen-2.5-coder-32b-instruct (spezialisiert)")
    console.print()
    
    tok = input(f"Openrouter.ai Token [{old_tok}]: ") or old_tok
    model = input(f"Language Modell [{old_model}]: ") or old_model
    update_user_config(user, openrouter_token=tok, model=model)
    console.print("\n[green]✓ KI-Anbindung gespeichert![/green]")
    input()


def tui_settings_menu():
    opts = [
        ("GitHub PAT ändern", "Personal Access Token für GitHub"),
        ("KI-Anbindung",       "Openrouter.ai Token & Modell"),
        ("Codex Installation prüfen", "Prüft und installiert Codex CLI"),
        ("Zurück",             "Hauptmenü")
    ]
    while True:
        c = run_curses_menu("Einstellungen", opts, f"Aktiver Benutzer: {gh_api.username}")
        if c is None or c == 3:
            break
        if c == 0:
            tui_change_github_token()
        elif c == 1:
            tui_ki_anbindung()
        elif c == 2:
            console.clear()
            console.rule("[bold cyan]Codex CLI Installation prüfen")
            if check_codex_cli():
                console.print("[green]✓ Codex CLI ist betriebsbereit![/green]")
            else:
                console.print("[red]❌ Codex CLI Installation fehlgeschlagen![/red]")
            input()


def tui_generate_roadmap(repo_path: Path):
    console.clear()
    console.rule(f"[bold cyan]Roadmap generieren: {repo_path.name}")

    readme = repo_path / "README.md"
    if not readme.exists():
        console.print(f"[red]❌ Keine README.md in {repo_path} gefunden![/red]")
        input("Drücke Enter, um zurückzugehen…")


def tui_codex_generate(repo_path: Path):
    """Hauptfunktion für autonome Code-Generierung mit Codex"""
    console.clear()
    console.rule(f"[bold cyan]Autonome Code-Generierung: {repo_path.name}")

    user = get_active_user()
    ucfg = load_user_config(user) or {}
    
    # Prüfe KI-Konfiguration
    openrouter_token = ucfg.get("openrouter_token", "")
    model = ucfg.get("model", "openai/codex-mini-latest")
    
    if not openrouter_token:
        console.print("[red]❌ KI-Anbindung nicht konfiguriert![/red]")
        console.print("Bitte konfiguriere OpenRouter Token in den Einstellungen.")
        input("Enter…")
        return

    # Prüfe Codex CLI
    if not check_codex_cli():
        console.print("[red]❌ Codex CLI nicht verfügbar![/red]")
        input("Enter…")
        return

    # Initialisiere Codex Integration
    codex = CodexIntegration(ucfg)
    
    console.print(f"[blue]Verwende Modell: {model}[/blue]")
    console.print("[blue]Suche nach Issues mit 'in-work' Label...[/blue]")

    # 1. Finde Issue mit "in-work" Label oder ältestes offenes Issue
    owner = gh_api.username
    repo_name = repo_path.name
    
    # Setze Issue-Kontext für Live-Monitoring
    # Suche nach Issues mit "in-work" Label
    ok, inwork_issues = gh_api.get_issues(repo_name, state="open", labels="in-work", sort="created", direction="asc")
    
    selected_issue = None
    
    if ok and inwork_issues:
        selected_issue = inwork_issues[0]
        console.print(f"[green]✓ Gefunden: Issue #{selected_issue['number']} mit 'in-work' Label[/green]")
    else:
        console.print("[yellow]Kein Issue mit 'in-work' Label gefunden. Suche ältestes offenes Issue...[/yellow]")
        
        # Suche ältestes offenes Issue
        ok, open_issues = gh_api.get_issues(repo_name, state="open", sort="created", direction="asc")
        
        if ok and open_issues:
            selected_issue = open_issues[0]
            issue_number = selected_issue['number']
            
            # Füge "in-work" Label hinzu
            current_labels = [label['name'] for label in selected_issue.get('labels', [])]
            if "in-work" not in current_labels:
                current_labels.append("in-work")
                
                ok, _ = gh_api.update_issue_labels(repo_name, issue_number, current_labels)
                if ok:
                    console.print(f"[green]✓ Label 'in-work' zu Issue #{issue_number} hinzugefügt[/green]")
                else:
                    console.print(f"[yellow]⚠ Konnte Label nicht hinzufügen, aber fahre fort...[/yellow]")
        else:
            console.print("[red]❌ Keine offenen Issues gefunden![/red]")
            input("Enter…")
            return

    if not selected_issue:
        console.print("[red]❌ Kein Issue zur Bearbeitung gefunden![/red]")
        input("Enter…")
        return

    # Setze Issue-Kontext für Live-Monitoring
    codex.set_issue_context(selected_issue, repo_name)

    issue_number = selected_issue['number']
    issue_title = selected_issue['title']
    issue_body = selected_issue.get('body', '')

    console.print(f"\n[bold green]📋 Bearbeite Issue #{issue_number}: {issue_title}[/bold green]")
    console.print(f"[dim]{issue_body[:200]}{'...' if len(issue_body) > 200 else ''}[/dim]\n")

    # Initial Log
    codex.log_to_issue(f"🚀 Starte autonome Code-Generierung für Issue #{issue_number}: {issue_title}", "progress")

    # 2. Lade Issue-Kommentare
    console.print("[blue]Lade Issue-Kommentare...[/blue]")
    ok, comments_data = gh_api.get_issue_comments(repo_name, issue_number)
    
    comments = []
    if ok:
        for comment in comments_data:
            body = comment.get('body', '').strip()
            if body:
                comments.append(body)
        console.print(f"[green]✓ {len(comments)} Kommentare geladen[/green]")
        codex.log_to_issue(f"Analysiere {len(comments)} vorhandene Issue-Kommentare", "info")
    else:
        console.print("[yellow]⚠ Kommentare konnten nicht geladen werden[/yellow]")
        codex.log_to_issue("Keine vorherigen Kommentare gefunden", "warning")

    # 3. Hole Codebase-Kontext von github.com
    console.print("[blue]Lade aktuellen Codebase-Kontext...[/blue]")
    codex.fetch_codebase_context(owner, repo_name, repo_path)

    # 4. Generiere umfassenden Prompt
    console.print("[blue]Generiere Entwicklungsauftrag...[/blue]")
    prompt = codex.generate_comprehensive_prompt(selected_issue, comments, repo_path)
    
    # Zeige Prompt-Vorschau
    console.print("\n" + "="*80)
    console.print("[bold cyan]PROMPT VORSCHAU (erste 500 Zeichen):[/bold cyan]")
    console.print("="*80)
    console.print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    console.print("="*80 + "\n")

    if input("🚀 Codex starten? (j/n): ").lower() != 'j':
        console.print("[yellow]Abgebrochen[/yellow]")
        codex.log_to_issue("❌ Code-Generierung vom Benutzer abgebrochen", "warning")
        input()
        return

    # 5. Führe Codex aus mit Live-Monitoring
    console.print("\n[bold green]🤖 Starte autonome Code-Generierung mit Codex...[/bold green]")
    
    start_time = time.time()
    success, result = codex.execute_codex(repo_path, prompt)
    end_time = time.time()
    duration = end_time - start_time

    # 6. Verarbeite Ergebnisse
    console.print(f"\n[bold]📊 CODEX ERGEBNISSE[/bold]")
    console.print(f"[blue]Dauer: {duration:.1f} Sekunden[/blue]")
    
    if success:
        console.print(f"[green]✅ Codex erfolgreich ausgeführt![/green]")
        console.print("\n[bold]Ausgabe:[/bold]")
        console.print(Panel.fit(result, title="Codex Output", border_style="green"))
        
        # 7. NEUE PHASE: Automatische Issue-Vollständigkeitsanalyse
        console.print("\n[bold blue]🔍 STARTE AUTOMATISCHE ISSUE-ANALYSE...[/bold blue]")
        
        analysis_success, analysis_result = codex.analyze_issue_completion(selected_issue, repo_path)
        
        if analysis_success:
            # Issue als vollständig markiert - schließe es automatisch
            console.print("[bold green]✅ ISSUE ALS VOLLSTÄNDIG ANALYSIERT - SCHLIEßE AUTOMATISCH[/bold green]")
            
            # Schließe Issue über GitHub API
            try:
                close_response = requests.patch(
                    f"https://api.github.com/repos/{owner}/{repo_name}/issues/{issue_number}",
                    headers={
                        "Authorization": f"Bearer {ucfg.get('token')}",
                        "Accept": "application/vnd.github+json"
                    },
                    json={"state": "closed"}
                )
                
                if close_response.status_code == 200:
                    console.print(f"[green]✅ Issue #{issue_number} automatisch geschlossen![/green]")
                    
                    # Finale Abschluss-Kommentar
                    final_comment = f"""🎉 **ISSUE AUTOMATISCH ABGESCHLOSSEN**

✅ **Status:** Vollständig implementiert  
⏱️ **Gesamtdauer:** {duration:.1f} Sekunden  
🤖 **Modell:** {model}

**KI-Analyse:**
{analysis_result}

**Zusammenfassung:**
Dieses Issue wurde vollständig und erfolgreich durch autonome Code-Generierung implementiert. Alle Anforderungen wurden erfüllt und der Code wurde erfolgreich integriert.

---
*Automatisch abgeschlossen von grepo2 Codex Integration*
"""
                    
                    ok, _ = gh_api.add_issue_comment(repo_name, issue_number, final_comment)
                    if ok:
                        console.print("[green]✓ Abschluss-Kommentar hinzugefügt[/green]")
                else:
                    console.print(f"[yellow]⚠ Issue konnte nicht geschlossen werden: HTTP {close_response.status_code}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠ Fehler beim Schließen des Issues: {e}[/yellow]")
                
        else:
            # Issue unvollständig - füge Analyse als Kommentar hinzu
            console.print("[bold yellow]⚠️ ISSUE UNVOLLSTÄNDIG - FÜGE ANALYSE-KOMMENTAR HINZU[/bold yellow]")
            
            analysis_comment = f"""🔍 **AUTOMATISCHE VOLLSTÄNDIGKEITSANALYSE**

⚠️ **Status:** Issue noch nicht vollständig umgesetzt  
⏱️ **Analysedauer:** {duration:.1f} Sekunden  
🤖 **Analysiert mit:** {model}

**Detaillierte Analyse:**
{analysis_result}

**Status:** Issue bleibt offen für weitere Bearbeitung.

---
*Automatische Analyse von grepo2 Codex Integration*
"""
            
            ok, _ = gh_api.add_issue_comment(repo_name, issue_number, analysis_comment)
            if ok:
                console.print("[green]✓ Analyse-Kommentar zu Issue hinzugefügt[/green]")
            
            console.print("\n[bold]Analyse-Details:[/bold]")
            console.print(Panel.fit(analysis_result, title="Issue-Analyse", border_style="yellow"))

    else:
        console.print(f"[red]❌ Codex Fehler![/red]")
        console.print("\n[bold]Fehlerdetails:[/bold]")
        console.print(Panel.fit(result, title="Codex Error", border_style="red"))
        
        # Füge Fehler-Kommentar zum Issue hinzu
        error_comment = f"""🤖 **Autonome Code-Generierung fehlgeschlagen**

**Ausführungszeit:** {duration:.1f} Sekunden  
**Modell:** {model}  
**Status:** ❌ Fehler

**Fehlerdetails:**
```
{result[:800]}{"..." if len(result) > 800 else ""}
```

---
*Generiert von grepo2 Codex Integration*
"""
        
        ok, _ = gh_api.add_issue_comment(repo_name, issue_number, error_comment)
        if ok:
            console.print("[yellow]⚠ Fehler-Kommentar zu Issue hinzugefügt[/yellow]")

    # 8. Git Status anzeigen
    console.print("\n[bold]📁 Git Status nach Codex-Ausführung:[/bold]")
    ok, git_status = git_api.status(repo_path)
    if ok:
        console.print(git_status)
        # Finale Dateiübersicht loggen
        if git_status.strip():
            codex.log_to_issue("📊 Finale Git-Status-Übersicht nach Abschluss verfügbar", "info")
    else:
        console.print(f"[red]Git Status Fehler: {git_status}[/red]")

    input("\n🔄 Drücke Enter, um zum Menü zurückzukehren...")


def tui_auto_development_mode(repo_path: Path):
    """Kontinuierlicher automatischer Entwicklungsmodus mit Live-Monitoring"""
    console.clear()
    console.rule(f"[bold cyan]Automatischer Entwicklungsmodus: {repo_path.name}")
    
    console.print("[yellow]⚠ EXPERIMENTELLER MODUS ⚠[/yellow]")
    console.print("Dieser Modus führt kontinuierlich Codex aus, bis alle Issues abgearbeitet sind.")
    console.print("Alle Aktionen werden live in den entsprechenden Issues dokumentiert!")
    console.print("Das kann sehr lange dauern und viele API-Calls verbrauchen!")
    console.print()
    
    max_iterations = input("Maximale Anzahl Iterationen [5]: ") or "5"
    try:
        max_iterations = int(max_iterations)
    except:
        max_iterations = 5
    
    if input(f"🚀 Automatischen Modus für max. {max_iterations} Iterationen starten? (j/n): ").lower() != 'j':
        return

    user = get_active_user()
    ucfg = load_user_config(user) or {}
    
    if not ucfg.get("openrouter_token"):
        console.print("[red]❌ KI-Anbindung nicht konfiguriert![/red]")
        input()
        return

    iteration = 0
    total_duration = 0
    completed_issues = []
    failed_issues = []
    
    console.print(f"\n[bold green]🔄 Starte automatischen Entwicklungsmodus...[/bold green]")
    
    # Erstelle Übersichts-Issue für den automatischen Modus
    overview_issue_data = {
        "title": f"🤖 Automatischer Entwicklungsmodus - {repo_path.name}",
        "body": f"""# Automatischer Entwicklungsmodus gestartet

**Repository:** {repo_path.name}  
**Maximale Iterationen:** {max_iterations}  
**Gestartet:** {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Modell:** {ucfg.get('model', 'nicht konfiguriert')}

Dieser automatische Modus wird kontinuierlich Issues bearbeiten bis alle abgeschlossen sind oder das Iterationslimit erreicht wird.

## Status
- ⏳ **Status:** Läuft
- 🔄 **Iteration:** 0/{max_iterations}
- ✅ **Abgeschlossen:** 0 Issues
- ❌ **Fehlgeschlagen:** 0 Issues

Alle Einzelaktionen werden in den jeweiligen Issues live dokumentiert.
""",
        "labels": ["automation", "development-mode"]
    }
    
    try:
        overview_resp = requests.post(
            f"https://api.github.com/repos/{gh_api.username}/{repo_path.name}/issues",
            headers={
                "Authorization": f"Bearer {ucfg.get('token')}",
                "Accept": "application/vnd.github+json"
            },
            json=overview_issue_data
        )
        
        overview_issue_number = None
        if overview_resp.status_code == 201:
            overview_issue_number = overview_resp.json().get('number')
            console.print(f"[green]✓ Übersichts-Issue #{overview_issue_number} erstellt[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Übersichts-Issue konnte nicht erstellt werden: {e}[/yellow]")
        overview_issue_number = None
    
    while iteration < max_iterations:
        iteration += 1
        console.print(f"\n[bold blue]═══ ITERATION {iteration}/{max_iterations} ═══[/bold blue]")
        
        # Update Übersichts-Issue
        if overview_issue_number:
            try:
                update_comment = f"""🔄 **Iteration {iteration}/{max_iterations} gestartet**

**Zeitpunkt:** {time.strftime('%H:%M:%S')}  
**Bisherige Erfolge:** {len(completed_issues)}  
**Bisherige Fehler:** {len(failed_issues)}

Suche nach offenen Issues...
"""
                gh_api.add_issue_comment(repo_path.name, overview_issue_number, update_comment)
            except:
                pass
        
        # Prüfe auf offene Issues (exkludiere Übersichts-Issue)
        ok, open_issues = gh_api.get_issues(repo_path.name, state="open", sort="created", direction="asc")
        
        if ok:
            # Filtere Übersichts-Issue aus
            filtered_issues = [issue for issue in open_issues if issue.get('number') != overview_issue_number]
        else:
            filtered_issues = []
        
        if not ok or not filtered_issues:
            console.print("[green]🎉 Alle Issues abgearbeitet oder keine gefunden![/green]")
            if overview_issue_number:
                try:
                    final_comment = f"""🎉 **AUTOMATISCHER ENTWICKLUNGSMODUS ABGESCHLOSSEN**

**Abschlusszeitpunkt:** {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Iterationen durchgeführt:** {iteration-1}/{max_iterations}  
**Grund:** Alle Issues abgearbeitet

## Endergebnis:
- ✅ **Erfolgreich abgeschlossen:** {len(completed_issues)} Issues
- ❌ **Fehlgeschlagen:** {len(failed_issues)} Issues
- ⏱️ **Gesamtdauer:** {total_duration:.1f} Sekunden

### Erfolgreich abgeschlossene Issues:
{chr(10).join([f"- ✅ {issue}" for issue in completed_issues]) if completed_issues else "Keine"}

### Fehlgeschlagene Issues:
{chr(10).join([f"- ❌ {issue}" for issue in failed_issues]) if failed_issues else "Keine"}
"""
                    gh_api.add_issue_comment(repo_path.name, overview_issue_number, final_comment)
                    
                    # Schließe Übersichts-Issue
                    requests.patch(
                        f"https://api.github.com/repos/{gh_api.username}/{repo_path.name}/issues/{overview_issue_number}",
                        headers={
                            "Authorization": f"Bearer {ucfg.get('token')}",
                            "Accept": "application/vnd.github+json"
                        },
                        json={"state": "closed"}
                    )
                except:
                    pass
            break
        
        console.print(f"[blue]📋 Gefunden: {len(filtered_issues)} offene Issues[/blue]")
        
        # Führe eine Codex-Iteration aus
        start_time = time.time()
        
        # Initialisiere Codex Integration mit Live-Monitoring
        codex = CodexIntegration(ucfg)
        
        # Hole nächstes Issue
        current_issue = filtered_issues[0]
        issue_number = current_issue['number']
        issue_title = current_issue['title']
        
        console.print(f"[green]🎯 Bearbeite Issue #{issue_number}: {issue_title}[/green]")
        
        # Setze Issue-Kontext für Live-Monitoring
        codex.set_issue_context(current_issue, repo_path.name)
        
        # Hole Kommentare
        ok, comments_data = gh_api.get_issue_comments(repo_path.name, issue_number)
        comments = [c.get('body', '') for c in (comments_data if ok else [])]
        
        # Hole Codebase-Kontext
        codex.fetch_codebase_context(gh_api.username, repo_path.name, repo_path)
        
        # Generiere und führe Prompt aus
        prompt = codex.generate_comprehensive_prompt(current_issue, comments, repo_path)
        success, result = codex.execute_codex(repo_path, prompt)
        
        iteration_time = time.time() - start_time
        total_duration += iteration_time
        
        if success:
            console.print(f"[green]✅ Iteration {iteration} erfolgreich ({iteration_time:.1f}s)[/green]")
            
            # Führe Issue-Vollständigkeitsanalyse durch
            analysis_success, analysis_result = codex.analyze_issue_completion(current_issue, repo_path)
            
            if analysis_success:
                # Issue automatisch schließen
                try:
                    requests.patch(
                        f"https://api.github.com/repos/{gh_api.username}/{repo_path.name}/issues/{issue_number}",
                        headers={
                            "Authorization": f"Bearer {ucfg.get('token')}",
                            "Accept": "application/vnd.github+json"
                        },
                        json={"state": "closed"}
                    )
                    completed_issues.append(f"#{issue_number}: {issue_title}")
                except:
                    pass
            else:
                completed_issues.append(f"#{issue_number}: {issue_title} (teilweise)")
            
        else:
            console.print(f"[red]❌ Iteration {iteration} fehlgeschlagen ({iteration_time:.1f}s)[/red]")
            console.print(f"[yellow]Fehler: {result[:200]}...[/yellow]")
            failed_issues.append(f"#{issue_number}: {issue_title}")
        
        # Update Übersichts-Issue
        if overview_issue_number:
            try:
                iteration_summary = f"""📊 **Iteration {iteration} abgeschlossen**

**Issue:** #{issue_number} - {issue_title}  
**Status:** {"✅ Erfolgreich" if success else "❌ Fehlgeschlagen"}  
**Dauer:** {iteration_time:.1f}s

**Aktueller Stand:**
- ✅ **Erfolgreich:** {len(completed_issues)}
- ❌ **Fehlgeschlagen:** {len(failed_issues)}
- ⏱️ **Gesamtdauer:** {total_duration:.1f}s
"""
                gh_api.add_issue_comment(repo_path.name, overview_issue_number, iteration_summary)
            except:
                pass
        
        # Kurze Pause zwischen Iterationen
        time.sleep(2)
        
        # Git Status anzeigen
        ok, git_status = git_api.status(repo_path)
        if ok and git_status.strip():
            console.print(f"[dim]Git Changes:\n{git_status[:300]}...[/dim]")
    
    # Finale Zusammenfassung
    console.print(f"\n[bold green]📊 AUTOMATISCHER ENTWICKLUNGSMODUS ABGESCHLOSSEN[/bold green]")
    console.print(f"[blue]Gesamtdauer: {total_duration:.1f} Sekunden[/blue]")
    console.print(f"[blue]Iterationen: {iteration}/{max_iterations}[/blue]")
    console.print(f"[blue]Erfolgreich: {len(completed_issues)}[/blue]")
    console.print(f"[blue]Fehlgeschlagen: {len(failed_issues)}[/blue]")
    
    if completed_issues:
        console.print("\n[bold]Erfolgreich bearbeitete Issues:[/bold]")
        for issue in completed_issues:
            console.print(f"  ✅ {issue}")
    
    if failed_issues:
        console.print("\n[bold]Fehlgeschlagene Issues:[/bold]")
        for issue in failed_issues:
            console.print(f"  ❌ {issue}")
    
    input("\n🔄 Drücke Enter, um zurückzukehren...")


def tui_projekterstellung_menu(repo_path: Path):
    options = [
        ("Roadmap generieren",              "Erstelle eine technische Roadmap"),
        ("Projekt auf GitHub einrichten",   "Erstelle Issues auf GitHub"),
        ("🤖 Code generieren mit Codex",    "Autonome KI-Code-Generierung"),
        ("Automatischer Entwicklungsmodus", "Kontinuierliche autonome Entwicklung"),
        ("Zurück",                          "Hauptmenü")
    ]
    while True:
        choice = run_curses_menu("Projekterstellung", options, f"Projekterstellung – {repo_path.name}")
        if choice is None or choice == 4:
            break
        elif choice == 0:
            tui_generate_roadmap(repo_path)
        elif choice == 1:
            tui_setup_github_project(repo_path)
        elif choice == 2:
            tui_codex_generate(repo_path)
        elif choice == 3:
            tui_auto_development_mode(repo_path)


def tui_manage_repo(repo_path: Path):
    options = [
        ("Status prüfen", "Zeigt `git status` an."),
        ("Commit erstellen", "Öffnet Editor für `git commit`."),
        ("Online-Repo mit Lokal überschreiben", "git push --force"),
        ("Lokales Repo mit Online überschreiben", "hart reset/clone"),
        ("Online-Repo hart aktualisieren", "git push --force-with-lease"),
        ("Lokales Repo hart aktualisieren", "git pull --autostash (clean)"),
        ("Online-Repo soft aktualisieren", "normaler git push"),
        ("Lokales Repo soft aktualisieren", "git pull --ff-only"),
        ("Pro Options", "Erweiterte Git-Befehle"),
        ("Zurück zum Hauptmenü", "")
    ]
    context = f"Aktiver Benutzer: {gh_api.username} | Repo: {repo_path.name}"
    while True:
        choice = run_curses_menu(f"Verwalte: {repo_path.name}", options, context)
        if choice is None or choice == 9:
            break
        if choice == 0:
            _execute_and_display("Git Status", git_api.status, repo_path)
        elif choice == 1:
            _execute_and_display("Git Commit", git_api.commit, repo_path)
        elif choice == 2:
            console.clear()
            console.print("[bold red]WARNUNG:[/] überschreibt GitHub")
            if input("Fortfahren? (j/n): ").lower() == 'j':
                _execute_and_display("Force Push", git_api.force_push_to_remote, repo_path)
        elif choice == 3:
            console.clear()
            console.print("[bold red]WARNUNG:[/] überschreibt lokal")
            if input("Fortfahren? (j/n): ").lower() == 'j':
                _execute_and_display("Force Pull", git_api.force_pull_from_remote, repo_path)
        elif choice == 4:
            _execute_and_display("Hard Push", git_api.hard_push_update, repo_path)
        elif choice == 5:
            _execute_and_display("Hard Pull", git_api.hard_pull_update, repo_path)
        elif choice == 6:
            _execute_and_display("Soft Push", git_api.soft_push_update, repo_path)
        elif choice == 7:
            _execute_and_display("Soft Pull", git_api.soft_pull_update, repo_path)
        elif choice == 8:
            console.clear()
            console.print("Pro Options in Arbeit")
            input()


def tui_user_menu():
    options = [
        ("Benutzer auswählen", "Profil wechseln"),
        ("Neuen Benutzer verbinden", "GitHub PAT anlegen"),
        ("Benutzer löschen", "Profil entfernen"),
        ("Zurück", "Hauptmenü")
    ]
    context = f"Aktiver Benutzer: {gh_api.username}"
    while True:
        c = run_curses_menu("Benutzerverwaltung", options, context)
        if c is None or c == 3:
            return False
        if c == 0:
            users = get_all_users()
            if not users:
                console.clear()
                console.print("Keine Benutzer")
                input()
                continue
            uopts = [(u, "") for u in users] + [("Zurück", "")]
            uc = run_curses_menu("Wähle Benutzer", uopts, context)
            if uc is not None and uc < len(users):
                set_active_user(users[uc])
                console.clear()
                console.print(f"Aktueller Benutzer: {users[uc]}")
                time.sleep(1)
                return True
        elif c == 1:
            console.clear()
            console.rule("[bold cyan]Neuen Benutzer verbinden")
            user = input("GitHub Benutzer: ")
            if not user:
                continue
            tok = getpass("PAT: ")
            if not tok:
                continue
            save_user_config(user, tok)
            if input("Wechseln? (j/n): ").lower() == 'j':
                set_active_user(user)
                time.sleep(1)
                return True
        elif c == 2:
            users = get_all_users()
            active = get_active_user()
            to_del = [u for u in users if u != active]
            if not to_del:
                console.clear()
                console.print("Keine zum Löschen")
                input()
                continue
            dopts = [(u, "") for u in to_del] + [("Zurück", "")]
            dc = run_curses_menu("Lösche Benutzer", dopts, context)
            if dc is not None and dc < len(to_del):
                if input(f"Löschen {to_del[dc]}? (j/n): ").lower() == 'j':
                    delete_user_config(to_del[dc])
                    console.print("✓")
                    input()


def tui_create_new_repo():
    """Erstellt ein neues Repository lokal und auf GitHub"""
    console.clear()
    console.rule("[bold cyan]Neues Repository erstellen")
    
    repo_name = input("Repository Name: ").strip()
    if not repo_name:
        console.print("[yellow]Abgebrochen[/yellow]")
        input()
        return
    
    description = input("Beschreibung (optional): ").strip()
    private = input("Privates Repository? (j/n) [n]: ").lower() == 'j'
    
    user = get_active_user()
    user_dir = GITHUB_DIR / user
    repo_path = user_dir / repo_name
    
    if repo_path.exists():
        console.print(f"[red]❌ Repository {repo_name} existiert bereits lokal![/red]")
        input()
        return
    
    # Prüfe ob Repository auf GitHub bereits existiert
    if gh_api.repo_exists(repo_name):
        console.print(f"[red]❌ Repository {repo_name} existiert bereits auf GitHub![/red]")
        input()
        return
    
    console.print(f"[blue]Erstelle Repository '{repo_name}'...[/blue]")
    
    # Erstelle Repository auf GitHub
    ok, result = gh_api.create_repo(repo_name, description, private)
    if not ok:
        console.print(f"[red]❌ GitHub Repository Erstellung fehlgeschlagen: {result}[/red]")
        input()
        return
    
    console.print("[green]✓ Repository auf GitHub erstellt[/green]")
    
    # Clone Repository lokal
    ok, result = gh_api.clone_repo(repo_name, str(repo_path))
    if not ok:
        console.print(f"[red]❌ Lokales Klonen fehlgeschlagen: {result}[/red]")
        input()
        return
    
    console.print(f"[green]✓ Repository lokal geklont: {repo_path}[/green]")
    
    # Erstelle initiale Dateien
    readme_content = f"""# {repo_name}

{description if description else 'Ein neues Projekt'}

## Installation

```bash
# Klone das Repository
git clone https://github.com/{user}/{repo_name}.git
cd {repo_name}
```

## Verwendung

Dokumentation folgt...

## Beitragen

Pull Requests sind willkommen!

## Lizenz

MIT
"""
    
    try:
        with open(repo_path / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        # Erstelle .gitignore
        gitignore_content = """# Logs
*.log
npm-debug.log*

# Dependencies
node_modules/
__pycache__/
*.pyc

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Build outputs
dist/
build/
*.egg-info/

# Environment
.env
.env.local

# grepo2 specific
codex/
"""
        
        with open(repo_path / ".gitignore", "w", encoding="utf-8") as f:
            f.write(gitignore_content)
        
        console.print("[green]✓ Initiale Dateien erstellt[/green]")
        
        # Committe initiale Dateien
        ok, _ = git_api.add_all_and_commit(repo_path, "Initial commit: Add README.md and .gitignore")
        if ok:
            console.print("[green]✓ Initial commit erstellt[/green]")
            
            # Pushe zu GitHub
            ok, _ = git_api.soft_push_update(repo_path)
            if ok:
                console.print("[green]✓ Changes zu GitHub gepusht[/green]")
                console.print(f"\n[bold green]🎉 Repository '{repo_name}' erfolgreich erstellt![/bold green]")
                console.print(f"[blue]Lokal: {repo_path}[/blue]")
                console.print(f"[blue]GitHub: https://github.com/{user}/{repo_name}[/blue]")
            else:
                console.print("[yellow]⚠ Push zu GitHub fehlgeschlagen[/yellow]")
        else:
            console.print("[yellow]⚠ Initial commit fehlgeschlagen[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Fehler beim Erstellen der Dateien: {e}[/red]")
    
    input("\nDrücke Enter zum Fortfahren...")


def tui_first_time_setup():
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]Willkommen bei grepo2![/bold cyan]\n\n"
        "Dieses Tool vereinfacht die Verwaltung deiner GitHub-Repositories.\n"
        "Mit autonomer KI-Code-Generierung durch Codex CLI und Live-Monitoring.\n"
        "Lass uns mit der Einrichtung beginnen.",
        title="🚀 Ersteinrichtung",
        border_style="cyan"
    ))
    console.print("\n[yellow]Schritt 1:[/yellow] GitHub-Verbindung einrichten")
    console.print("Du benötigst einen GitHub Personal Access Token (PAT).")
    console.print("Erstelle einen unter: https://github.com/settings/tokens")
    console.print("Benötigte Berechtigungen: repo (Full control of private repositories)\n")
    username = input("GitHub-Benutzername: ")
    if not username:
        console.print("[red]Kein Benutzername eingegeben. Setup abgebrochen.[/red]")
        return False
    token = getpass("Personal Access Token (PAT): ")
    if not token:
        console.print("[red]Kein Token eingegeben. Setup abgebrochen.[/red]")
        return False
    console.print("\n[yellow]Teste Verbindung zu GitHub...[/yellow]")
    test_api = GitHubAPI(username, token)
    success, _ = test_api._run_request('GET', 'user')
    if not success:
        console.print("[red]❌ Verbindung fehlgeschlagen. Bitte überprüfe Benutzername und Token.[/red]")
        return False
    console.print("[green]✓ Verbindung erfolgreich![/green]")
    save_user_config(username, token)
    set_active_user(username)
    (GITHUB_DIR / username).mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓ Benutzer '{username}' wurde erfolgreich eingerichtet![/green]")
    console.print(f"[green]✓ Lokales Verzeichnis erstellt: {GITHUB_DIR / username}[/green]")
    
    console.print("\n[yellow]Schritt 2:[/yellow] KI-Integration (optional)")
    if input("Möchtest du die KI-Integration (OpenRouter) jetzt konfigurieren? (j/n): ").lower() == 'j':
        console.print("Erstelle einen Account und API-Key unter: https://openrouter.ai/")
        or_token = getpass("OpenRouter API Token (optional): ")
        model = input("Bevorzugtes Modell [openai/codex-mini-latest]: ") or "openai/codex-mini-latest"
        if or_token:
            update_user_config(username, openrouter_token=or_token, model=model)
            console.print("[green]✓ KI-Integration konfiguriert![/green]")
    
    console.print("\n[yellow]Schritt 3:[/yellow] Codex CLI Installation")
    if check_codex_cli():
        console.print("[green]✓ Codex CLI ist bereit![/green]")
    else:
        console.print("[yellow]⚠ Codex CLI nicht verfügbar. Installation über: npm install -g @openai/codex[/yellow]")
    
    console.print("\n[yellow]Schritt 4:[/yellow] Systemweite Installation (optional)")
    if input("Möchtest du grepo2 systemweit installieren? (j/n): ").lower() == 'j':
        script_path = Path(sys.argv[0]).resolve()
        target_path = Path("/usr/local/bin/grepo2")
        try:
            subprocess.run(["sudo", "cp", str(script_path), str(target_path)], check=True)
            subprocess.run(["sudo", "chmod", "+x", str(target_path)], check=True)
            console.print("[green]✓ grepo2 wurde systemweit installiert![/green]")
            console.print("Du kannst es jetzt von überall mit 'grepo2' aufrufen.")
        except subprocess.CalledProcessError:
            console.print("[yellow]⚠ Systemweite Installation fehlgeschlagen. Manuell installieren:[/yellow]")
            console.print(f"  sudo cp {script_path} /usr/local/bin/grepo2")
            console.print("  sudo chmod +x /usr/local/bin/grepo2")
    console.print("\n[bold green]🎉 Setup abgeschlossen![/bold green]")
    console.print("Features von grepo2:")
    console.print("• 🤖 Autonome Code-Generierung mit Codex CLI")
    console.print("• 📋 Automatische Issue-Bearbeitung mit Live-Monitoring")
    console.print("• 🔍 Intelligente Issue-Vollständigkeitsanalyse")
    console.print("• 🗺️ Roadmap-Generierung")
    console.print("• 🔄 Git-Workflow-Automatisierung")
    console.print("• ✅ Automatisches Issue-Schließen bei Vollständigkeit")
    input("\nDrücke Enter, um zum Hauptmenü zu gelangen...")
    return True


def run_tui():
    while True:
        user = get_active_user()
        user_dir = GITHUB_DIR / user
        repos = sorted([d for d in user_dir.iterdir() if d.is_dir() and d.name != "backup"], key=lambda p: p.name)
        repo_opts = [(r.name, f"Repository in {r}") for r in repos]
        fixed_opts = [
            ("Benutzer wechseln",           "Profil wechseln"),
            ("Neues Repository erstellen",  "Erstelle neues Repo & klone"),
            ("Einstellungen",               "grepo2 & KI-Einstellungen"),
            ("Projekterstellung",           "Roadmap & Issues & Codex"),
            ("🤖 Autonomer Entwicklungsmodus", "KI entwickelt kontinuierlich"),
            ("Exit",                        "Beenden")
        ]
        opts = repo_opts + fixed_opts
        sel = run_curses_menu("grepo2 Hauptmenü", opts, f"Aktiver Benutzer: {user} | Repos: {len(repos)}")
        if sel is None or sel == len(opts) - 1:
            return False
        if sel < len(repo_opts):
            tui_manage_repo(repos[sel])
        else:
            idx = sel - len(repo_opts)
            if idx == 0:
                if tui_user_menu():
                    return True
            elif idx == 1:
                tui_create_new_repo()
            elif idx == 2:
                tui_settings_menu()
            elif idx == 3:
                if not repos:
                    console.print("[yellow]Keine Repositories vorhanden[/yellow]")
                    input()
                else:
                    choice = run_curses_menu(
                        "Repo für Projekterstellung wählen",
                        [(r.name, f"Pfad: {r}") for r in repos],
                        f"Aktiver Benutzer: {user}"
                    )
                    if choice is not None:
                        tui_projekterstellung_menu(repos[choice])
            elif idx == 4:
                if not repos:
                    console.print("[yellow]Keine Repositories vorhanden[/yellow]")
                    input()
                else:
                    choice = run_curses_menu(
                        "Repo für autonomen Entwicklungsmodus wählen",
                        [(r.name, f"🤖 KI-Entwicklung für {r.name}") for r in repos],
                        f"Aktiver Benutzer: {user}"
                    )
                    if choice is not None:
                        tui_auto_development_mode(repos[choice])


@click.group()
def go():
    pass

@go.group()
def repo():
    pass

@repo.command()
def list():
    active = get_active_user()
    if not active:
        console.print("[red]Kein aktiver Benutzer[/red]")
        return
    ud = GITHUB_DIR / active
    if not ud.exists():
        console.print(f"[yellow]Kein Verzeichnis für Benutzer {active}[/yellow]")
        return
    repos = [d for d in ud.iterdir() if d.is_dir() and d.name != "backup"]
    if not repos:
        console.print("[yellow]Keine Repositories gefunden.[/yellow]")
        return
    table = Table(title=f"Repositories für {active}")
    table.add_column("Name", style="cyan")
    table.add_column("Pfad", style="dim")
    for r in sorted(repos):
        table.add_row(r.name, str(r))
    console.print(table)

@repo.command()
def create():
    """Erstellt ein neues Repository über CLI"""
    active = get_active_user()
    if not active:
        console.print("[red]Kein aktiver Benutzer[/red]")
        return
    
    cfg = load_user_config(active)
    if not cfg:
        console.print("[red]Benutzer-Konfiguration nicht gefunden[/red]")
        return
    
    global gh_api
    gh_api = GitHubAPI(cfg["username"], cfg["token"])
    
    tui_create_new_repo()

@repo.command()
@click.argument('repo_name')
def codex(repo_name):
    """Führt Codex für ein spezifisches Repository aus"""
    active = get_active_user()
    if not active:
        console.print("[red]Kein aktiver Benutzer[/red]")
        return
    
    cfg = load_user_config(active)
    if not cfg:
        console.print("[red]Benutzer-Konfiguration nicht gefunden[/red]")
        return
    
    global gh_api
    gh_api = GitHubAPI(cfg["username"], cfg["token"])
    
    repo_path = GITHUB_DIR / active / repo_name
    if not repo_path.exists():
        console.print(f"[red]Repository {repo_name} nicht gefunden in {repo_path}[/red]")
        return
    
    # Direkte Codex-Ausführung ohne TUI
    console.print(f"[green]Starte Codex für {repo_name}...[/green]")
    
    codex_integration = CodexIntegration(cfg)
    
    # Finde Issue
    ok, issues = gh_api.get_issues(repo_name, state="open", sort="created", direction="asc")
    if not ok or not issues:
        console.print("[yellow]Keine offenen Issues gefunden[/yellow]")
        return
    
    issue = issues[0]
    codex_integration.set_issue_context(issue, repo_name)
    
    ok, comments_data = gh_api.get_issue_comments(repo_name, issue['number'])
    comments = [c.get('body', '') for c in (comments_data if ok else [])]
    
    codex_integration.fetch_codebase_context(active, repo_name, repo_path)
    prompt = codex_integration.generate_comprehensive_prompt(issue, comments, repo_path)
    
    success, result = codex_integration.execute_codex(repo_path, prompt)
    
    if success:
        console.print("[green]✅ Codex erfolgreich ausgeführt[/green]")
        
        # Führe automatische Issue-Analyse durch
        analysis_success, analysis_result = codex_integration.analyze_issue_completion(issue, repo_path)
        
        if analysis_success:
            console.print("[green]✅ Issue automatisch geschlossen[/green]")
        else:
            console.print("[yellow]⚠ Issue bleibt offen für weitere Bearbeitung[/yellow]")
            
        console.print(result)
    else:
        console.print("[red]❌ Codex fehlgeschlagen[/red]")
        console.print(result)


if __name__ == "__main__":
    if not check_git_cli():
        sys.exit(1)

    # ─── Systemweite Installation/Version-Check korrigiert ─────────────────────────
    script_path = Path(__file__).resolve()
    target_path = Path("/usr/local/bin/grepo2")
    try:
        if script_path != target_path:
            if not target_path.exists():
                if input(f"grepo2 ist nicht systemweit installiert ({target_path}). Installieren? (j/n): ").lower() == 'j':
                    subprocess.run(["sudo", "cp", str(script_path), str(target_path)], check=True)
                    subprocess.run(["sudo", "chmod", "+x", str(target_path)], check=True)
                    console.print("[green]grepo2 wurde systemweit installiert![/green]")
            else:
                same = False
                try:
                    same = filecmp.cmp(str(script_path), str(target_path), shallow=False)
                except Exception as e:
                    console.print(f"[yellow]Vergleich fehlgeschlagen: {e}[/yellow]")
                if not same:
                    if input("Systemweite Version weicht ab. Aktualisieren? (j/n): ").lower() == 'j':
                        subprocess.run(["sudo", "cp", str(script_path), str(target_path)], check=True)
                        subprocess.run(["sudo", "chmod", "+x", str(target_path)], check=True)
                        console.print("[green]grepo2 systemweite Version aktualisiert![/green]")
    except Exception as e:
        console.print(f"[yellow]Manuell installieren: sudo cp {script_path} {target_path} ({e})[/yellow]")

    # ─── Startup korrigiert ───────────────────────────────────────────────────────────────────
    # Prüfe ob CLI-Modus gewünscht ist
    if len(sys.argv) > 1 and sys.argv[1] == "go":
        sys.argv.pop(1)  # Entferne "go" Argument
        click.cli = go
        go()
    else:
        # TUI-Modus
        while True:
            user = get_active_user()
            if not user:
                if not tui_first_time_setup():
                    sys.exit(0)
                user = get_active_user()
            
            # Lade Benutzer-Konfiguration und initialisiere GitHub API
            cfg = load_user_config(user)
            if not cfg:
                console.print("[red]Benutzer-Konfiguration beschädigt. Ersteinrichtung neu starten...[/red]")
                if not tui_first_time_setup():
                    sys.exit(0)
                continue
            
            gh_api = GitHubAPI(cfg["username"], cfg["token"])
            
            # Starte TUI und prüfe ob Neustart gewünscht
            if not run_tui():
                break
        return
    with open(readme, "r", encoding="utf-8") as f:
        full_text = f.read()
    size = len(full_text.encode("utf-8"))
    console.print(f"[green]✓ README.md gefunden ({size} Bytes)[/green]")
    input("Drücke Enter, um fortzufahren…")
    snippet = full_text if len(full_text) <= 100 else full_text[:50] + "\n...\n" + full_text[-50:]

    user = get_active_user()
    ucfg = load_user_config(user) or {}
    token = ucfg.get("openrouter_token")
    if not token:
        console.print("[red]❌ KI-Anbindung nicht konfiguriert![/red]")
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

    preview_msg = (
        "README.md (gekürzt) als Lastenheft:\n\n"
        f"```markdown\n{snippet}\n```\n\n"
        "Erzeuge daraus 'roadmap.md' im Format:\n"
        "PHASE X – <Phasen-Titel>\n"
        "[ ] Kurztitel: DETAILLIERTE technische Anweisung mit mindestens drei vollständigen Sätzen.\n"
    )

    api_user_msg = (
        "Hier die vollständige README.md als Lastenpflichtenheft:\n\n"
        f"```markdown\n{full_text}\n```\n\n"
        "Erzeuge daraus 'roadmap.md' im Format:\n"
        "PHASE X – <Phasen-Titel>\n"
        "[ ] Kurztitel: DETAILLIERTE technische Anweisung mit mindestens drei vollständigen Sätzen.\n"
    )

    console.clear()
    console.rule("[bold cyan]Prompt-Vorschau")
    console.print(Panel.fit(system,      title="System Prompt",         border_style="blue"))
    console.print(Panel.fit(preview_msg, title="User Prompt (gekürzt)", border_style="green"))
    if input("Anfrage senden? (j/n): ").lower() != 'j':
        console.print("[yellow]Abgebrochen[/yellow]")
        input()
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "text/event-stream",
        "Content-Type":  "application/json; charset=utf-8"
    }

    console.print(f"[blue]Sende Streaming-POST…[/blue]")
    payload = {
        "model":     ucfg.get("model", "openai/codex-mini-latest"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": api_user_msg}
        ],
        "stream": True
    }
    url = "https://openrouter.ai/api/v1/chat/completions"
    content = ""
    done = False
    try:
        with requests.post(
            url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=120
        ) as resp:
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
                        done = True
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            print(delta, end="", flush=True)
                            content += delta
                    except json.JSONDecodeError as je:
                        console.print(f"[red]JSON-Error:{je}[/red]")
                if done:
                    break
            print()
    except Exception as e:
        console.print(f"[red]Fehler beim Generieren der Roadmap: {e}[/red]")
        input("Drücke Enter…")
        return

    out = repo_path / "roadmap.md"
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[green]✓ roadmap.md erstellt: {out}[/green]")
    except Exception as e:
        console.print(f"[red]Fehler beim Speichern: {e}[/red]")
    input()


def tui_setup_github_project(repo_path: Path):
    console.clear()
    console.rule(f"[bold cyan]Projekt auf GitHub einrichten: {repo_path.name}")

    roadmap = repo_path / "roadmap.md"
    console.print(f"[blue]Verwende Roadmap-Datei: {roadmap.resolve()}[/blue]")
    if not roadmap.exists():
        console.print(f"[red]❌ Keine roadmap.md in {repo_path} gefunden![/red]")
        input("Drücke Enter, um zurückzugehen…")
        return

    with open(roadmap, "r", encoding="utf-8") as f:
        lines = f.readlines()

    issues = []
    current_phase = None
    for raw in lines:
        m_phase = re.match(r'^\s*PHASE\s+(\d+)', raw, re.IGNORECASE)
        if m_phase:
            current_phase = m_phase.group(1)
            continue
        m_issue = re.match(r'^\s*\[\s*\]\s*(.+)', raw)
        if m_issue and current_phase:
            content = m_issue.group(1).strip()
            parts = content.split(":", 1)
            if len(parts) != 2:
                continue
            raw_title, raw_body = parts
            title = raw_title.strip().strip("*").strip()
            body = raw_body.strip()
            labels = ["enhancement", f"phase-{current_phase}"]
            issues.append({"title": title, "body": body, "labels": labels})

    if not issues:
        console.print("[yellow]Keine Issues in roadmap.md gefunden.[/yellow]")
        input("Drücke Enter…")
        return

    console.print("[bold]Vorschau der ersten 3 Issues:[/bold]\n")
    for iss in issues[:3]:
        console.print(f"• [bold]Title:[/bold] {iss['title']}")
        console.print(f"  [bold]Description:[/bold] {iss['body']}")
        console.print(f"  [bold]Flags:[/bold] {', '.join(iss['labels'])}\n")

    console.print(f"[bold]Gesamt Issues:[/bold] {len(issues)}")
    if input("Issues auf GitHub übertragen? (j/n): ").lower() != 'j':
        console.print("[yellow]Abgebrochen[/yellow]")
        input()
        return

    owner = gh_api.username
    repo = repo_path.name
    ucfg = load_user_config(owner) or {}
    token = ucfg.get("token")
    if not token:
        console.print("[red]❌ GitHub PAT nicht gefunden![/red]")
        input()
        return

    headers = {
        "Accept":               "application/vnd.github+json",
        "Authorization":        f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    created = 0
    for iss in issues:
        payload = {
            "title":  iss["title"],
            "body":   iss["body"],
            "labels": iss["labels"]
        }
        resp = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers=headers,
            json=payload,
            timeout=10
        )
        if resp.status_code == 201:
            num = resp.json().get("number")
            console.print(f"[green]✓ Issue erstellt #{num}: {iss['title']}[/green]")
            created += 1
        else:
            msg = resp.json().get("message", "Unbekannter Fehler")
            console.print(f"[red]✗ Fehler bei '{iss['title']}': {resp.status_code} {msg}[/red]")
        time.sleep(1)

    console.print(f"\n[bold]Erstellte Issues:[/bold] {created}")
    input("Drücke Enter, um zurückzugehen…")


def get_current_codebase_content(repo_path: Path) -> str:
    """Sammelt den gesamten aktuellen Code aus dem Repository"""
    codebase_content = []
    
    # Wichtige Dateierweiterungen für Code
    code_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.sass',
        '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift',
        '.kt', '.scala', '.clj', '.r', '.m', '.vue', '.svelte', '.sql', '.sh',
        '.yaml', '.yml', '.json', '.xml', '.toml', '.ini', '.cfg', '.conf'
    }
    
    try:
        for file_path in repo_path.rglob('*'):
            # Überspringe Verzeichnisse und versteckte/ignorierte Dateien
            if (file_path.is_dir() or 
                file_path.name.startswith('.') or
                    'node_modules' in file_path.parts or
                    '__pycache__' in file_path.parts or
                    'codex' in file_path.parts or
                    '.git' in file_path.parts):
                    continue
                
                # Nur Code-Dateien und wichtige Konfigurationsdateien
                if file_path.suffix.lower() in code_extensions or file_path.name in ['README.md', 'package.json', 'requirements.txt', 'Dockerfile']:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            relative_path = file_path.relative_to(repo_path)
                            codebase_content.append(f"=== {relative_path} ===\n{content}\n")
                    except (UnicodeDecodeError, PermissionError):
                        # Überspringe Binärdateien oder nicht lesbare Dateien
                        continue
                        
        except Exception as e:
            console.print(f"[yellow]⚠ Fehler beim Sammeln der Codebase: {e}[/yellow]")
        
        return "\n".join(codebase_content)

    def analyze_issue_completion(self, issue: Dict, repo_path: Path) -> Tuple[bool, str]:
        """Analysiert ob das Issue vollständig umgesetzt wurde"""
        try:
            self.log_to_issue("Starte automatische Issue-Vollständigkeitsanalyse", "progress")
            
            # Hole aktuelle Codebase
            current_code = self.get_current_codebase_content(repo_path)
            
            # Hole ursprüngliche Codebase von github.com zum Vergleich
            owner = gh_api.username
            repo_name = self.repo_name
            github_url = f"https://github.com/{owner}/{repo_name}"
            
            # Erstelle Analyse-Prompt
            analysis_prompt = f"""Du bist ein erfahrener Software-Architekt und Code-Reviewer. 

**AUFGABE:** Analysiere ob das folgende GitHub Issue vollständig umgesetzt wurde.

**ORIGINAL ISSUE:**
Issue #{issue['number']}: {issue['title']}

**Issue Beschreibung:**
{issue.get('body', 'Keine Beschreibung')}

**AKTUELLE CODEBASE NACH ÄNDERUNGEN:**
{current_code[:15000]}{"... (gekürzt)" if len(current_code) > 15000 else ""}

**ANALYSIERE FOLGENDES:**

1. **Vollständigkeit:** Wurden alle Anforderungen aus dem Issue umgesetzt?
2. **Code-Qualität:** Ist der implementierte Code sauber und funktional?
3. **Integration:** Fügt sich der neue Code nahtlos in die bestehende Architektur ein?
4. **Testing:** Sind ausreichend Tests vorhanden (falls erforderlich)?
5. **Dokumentation:** Ist die Dokumentation aktualisiert worden (falls nötig)?

**ANTWORT-FORMAT:**

```json
{{
  "issue_completed": true/false,
  "completion_percentage": 0-100,
  "analysis": "Detaillierte Analyse der Implementierung",
  "missing_requirements": ["Liste fehlender Anforderungen falls vorhanden"],
  "next_steps": ["Konkrete nächste Schritte falls Issue nicht vollständig"],
  "code_quality_rating": 1-10,
  "summary": "Kurze Zusammenfassung der Analyse"
}}
```

Sei objektiv und gründlich in deiner Analyse. Wenn das Issue vollständig umgesetzt wurde, setze `issue_completed` auf `true`. Andernfalls gib konkrete nächste Schritte an."""

            # Sende Anfrage an OpenRouter
            headers = {
                "Authorization": f"Bearer {self.openrouter_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": analysis_prompt}
                ],
                "temperature": 0.1  # Niedrige Temperatur für objektive Analyse
            }
            
            console.print("[blue]Sende Issue-Analyse an OpenRouter...[/blue]")
            self.log_to_issue("Analysiere Issue-Vollständigkeit mit KI", "progress")
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis_text = result['choices'][0]['message']['content']
                
                # Versuche JSON aus der Antwort zu extrahieren
                try:
                    # Finde JSON-Block in der Antwort
                    json_start = analysis_text.find('{')
                    json_end = analysis_text.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = analysis_text[json_start:json_end]
                        analysis_data = json.loads(json_str)
                        
                        is_completed = analysis_data.get('issue_completed', False)
                        percentage = analysis_data.get('completion_percentage', 0)
                        analysis = analysis_data.get('analysis', 'Keine Analyse verfügbar')
                        next_steps = analysis_data.get('next_steps', [])
                        summary = analysis_data.get('summary', 'Keine Zusammenfassung')
                        
                        console.print(f"[blue]Issue-Analyse abgeschlossen: {percentage}% vollständig[/blue]")
                        
                        if is_completed:
                            self.log_to_issue(f"✅ Issue als vollständig analysiert ({percentage}%): {summary}", "success")
                            return True, f"Issue vollständig umgesetzt ({percentage}%)\n\nAnalyse: {analysis}"
                        else:
                            next_steps_text = "\n".join([f"• {step}" for step in next_steps])
                            detailed_analysis = f"""**ISSUE NICHT VOLLSTÄNDIG UMGESETZT ({percentage}%)**

**Analyse:**
{analysis}

**Nächste Schritte:**
{next_steps_text}

**Zusammenfassung:**
{summary}"""
                            
                            self.log_to_issue(f"⚠️ Issue unvollständig ({percentage}%): {summary}", "warning")
                            return False, detailed_analysis
                    else:
                        raise ValueError("Kein gültiges JSON in Antwort gefunden")
                        
                except (json.JSONDecodeError, ValueError) as e:
                    # Fallback: Verwende rohe Antwort
                    console.print(f"[yellow]JSON-Parsing fehlgeschlagen, verwende rohe Analyse[/yellow]")
                    self.log_to_issue("Issue-Analyse abgeschlossen (manuelles Format)", "info")
                    return False, f"Analyse (Rohformat):\n{analysis_text}"
            else:
                error_msg = f"OpenRouter API Fehler: {response.status_code}"
                self.log_to_issue(f"Fehler bei Issue-Analyse: {error_msg}", "error")
                return False, f"Fehler bei der Analyse: {error_msg}"
                
        except Exception as e:
            error_msg = f"Fehler bei Issue-Analyse: {e}"
            console.print(f"[red]Analyse-Fehler: {e}[/red]")
            self.log_to_issue(error_msg, "error")
            return False, error_msg