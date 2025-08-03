#!/usr/bin/env python3
"""
grepo2 v3.7.4 - Git Repository Management Tool
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Configuration Error Handling:
   • Robuste Base64-Dekodierung mit automatischer Padding-Korrektur
   • Bessere Fehlerbehandlung für beschädigte Token-Daten
   • Benutzerfreundliche Recovery-Hinweise bei Konfigurationsproblemen

🔧 Key Features:
   • Repository-Auswahl im Hauptmenü
   • Vollständige Repository-Verwaltung  
   • Benutzer-Management
   • Einstellungen und Projekterstellung (FUNKTIONSFÄHIG)
   • AI-powered Issue Management (v3.7.3)
   • Automatisches CHANGELOG.md Management (v3.7.3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import os
import json
import subprocess
import time
import curses
import textwrap
import base64
import filecmp
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from getpass import getpass

import click
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track

console = Console()

# ─── Section I: Core Infrastructure ─────────────────────────────────────────────

def check_git_cli() -> bool:
    """Prüft ob Git CLI verfügbar ist"""
    try:
        result = subprocess.run(["git", "--version"], check=True, capture_output=True, text=True)
        console.print(f"[green]✓ Git CLI gefunden: {result.stdout.strip()}[/green]")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        console.print("[red]❌ Git CLI nicht gefunden. Bitte installieren Sie Git.[/red]")
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
    """Deobfuscate base64 encoded data with proper padding handling"""
    try:
        # Add padding if necessary (base64 strings must be multiples of 4)
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return base64.b64decode(data.encode()).decode()
    except Exception as e:
        # If deobfuscation fails, assume data is already plain text (backward compatibility)
        console.print(f"[yellow]⚠ Deobfuscation failed, using raw data: {e}[/yellow]")
        return data


# ─── Section II: Configuration Management ───────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Lädt die globale Konfiguration"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[yellow]⚠ Fehler beim Laden der Konfiguration: {e}[/yellow]")
    return {}

def save_config(config: Dict[str, Any]) -> None:
    """Speichert die globale Konfiguration"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        console.print(f"[red]❌ Fehler beim Speichern der Konfiguration: {e}[/red]")

def get_active_user() -> Optional[str]:
    """Gibt den aktiven Benutzer zurück"""
    config = load_config()
    return config.get("active_user")

def set_active_user(username: str) -> None:
    """Setzt den aktiven Benutzer"""
    config = load_config()
    config["active_user"] = username
    save_config(config)

def load_user_config(username: str) -> Optional[Dict[str, Any]]:
    """Lädt die Konfiguration eines Benutzers"""
    user_file = USERS_DIR / f"{username}.json"
    if user_file.exists():
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Deobfuscate sensitive data with error handling
                if "token" in data and data["token"]:
                    try:
                        data["token"] = _deobfuscate(data["token"])
                    except Exception as e:
                        console.print(f"[yellow]⚠ Fehler beim Dekodieren des GitHub-Tokens: {e}[/yellow]")
                        console.print("[blue]💡 Bitte aktualisiere dein GitHub Token in den Einstellungen[/blue]")
                        data["token"] = ""  # Reset corrupted token
                
                if "openrouter_token" in data and data["openrouter_token"]:
                    try:
                        data["openrouter_token"] = _deobfuscate(data["openrouter_token"])
                    except Exception as e:
                        console.print(f"[yellow]⚠ Fehler beim Dekodieren des OpenRouter-Tokens: {e}[/yellow]")
                        console.print("[blue]💡 Bitte aktualisiere dein OpenRouter Token in den Einstellungen[/blue]")
                        data["openrouter_token"] = ""  # Reset corrupted token
                
                return data
        except Exception as e:
            console.print(f"[yellow]⚠ Fehler beim Laden der Benutzer-Konfiguration: {e}[/yellow]")
            console.print("[blue]💡 Die Konfigurationsdatei könnte beschädigt sein[/blue]")
    return None

def save_user_config(username: str, token: str, openrouter_token: str = "", model: str = "openai/gpt-4o") -> None:
    """Speichert die Konfiguration eines Benutzers"""
    user_file = USERS_DIR / f"{username}.json"
    config = {
        "username": username,
        "token": _obfuscate(token),
        "openrouter_token": _obfuscate(openrouter_token) if openrouter_token else "",
        "model": model,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        console.print(f"[green]✓ Benutzer-Konfiguration gespeichert: {user_file}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Fehler beim Speichern der Benutzer-Konfiguration: {e}[/red]")


# ─── Section III: CHANGELOG.md Integration (v3.7.3 Feature) ─────────────────────

def write_to_changelog(message: str, category: str = "info") -> None:
    """Schreibt automatisch in CHANGELOG.md mit Timestamp und Emoji"""
    changelog_path = Path.cwd() / "CHANGELOG.md"
    
    emoji_map = {
        "info": "ℹ️",
        "success": "✅", 
        "warning": "⚠️",
        "error": "❌",
        "feature": "🚀",
        "fix": "🔧",
        "docs": "📝",
        "test": "🧪",
        "refactor": "♻️"
    }
    
    emoji = emoji_map.get(category, "📝")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n**{timestamp}** {emoji} **{category.upper()}**: {message}\n"
    
    try:
        # Lese existierenden Inhalt
        content = ""
        if changelog_path.exists():
            with open(changelog_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Füge neuen Eintrag nach der ersten Überschrift ein
        lines = content.split('\n')
        insert_pos = 0
        
        # Finde Position nach "## [Unreleased]" oder ähnlich
        for i, line in enumerate(lines):
            if line.startswith('## ') and 'unreleased' in line.lower():
                insert_pos = i + 1
                break
            elif line.startswith('### ') and i > 5:  # Nach ersten paar Zeilen
                insert_pos = i
                break
        
        # Füge Eintrag ein
        lines.insert(insert_pos, entry)
        
        # Schreibe zurück
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            
    except Exception as e:
        console.print(f"[yellow]⚠ CHANGELOG.md Update fehlgeschlagen: {e}[/yellow]")


# ─── Section IV: GitHub API Integration ─────────────────────────────────────────

class GitHubAPI:
    """GitHub API Client mit erweiterten Features für v3.7.4"""
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "grepo2-v3.7.4"
        }
        self.base_url = "https://api.github.com"

    def get_user_info(self) -> Tuple[bool, Dict[str, Any]]:
        """Holt Benutzerinformationen"""
        try:
            response = requests.get(f"{self.base_url}/user", headers=self.headers)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return False, {"error": str(e)}

    def list_repositories(self, username: str) -> List[Dict[str, Any]]:
        """Listet alle Repositories eines Benutzers auf"""
        try:
            all_repos = []
            page = 1
            while True:
                response = requests.get(
                    f"{self.base_url}/users/{username}/repos",
                    headers=self.headers,
                    params={"page": page, "per_page": 100, "sort": "updated"}
                )
                if response.status_code != 200:
                    break
                    
                repos = response.json()
                if not repos:
                    break
                    
                all_repos.extend(repos)
                page += 1
                
            return all_repos
        except Exception as e:
            console.print(f"[red]❌ Fehler beim Laden der Repositories: {e}[/red]")
            return []

    def get_repository_info(self, owner: str, repo: str) -> Tuple[bool, Dict[str, Any]]:
        """Holt detaillierte Repository-Informationen"""
        try:
            response = requests.get(f"{self.base_url}/repos/{owner}/{repo}", headers=self.headers)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return False, {"error": str(e)}

    def list_issues(self, owner: str, repo: str, state: str = "open") -> Tuple[bool, List[Dict[str, Any]]]:
        """Listet Issues eines Repositories auf"""
        try:
            response = requests.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues",
                headers=self.headers,
                params={"state": state, "per_page": 100}
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            console.print(f"[red]❌ Fehler beim Laden der Issues: {e}[/red]")
            return False, []

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> Tuple[bool, List[Dict[str, Any]]]:
        """Holt alle Kommentare zu einem Issue"""
        try:
            response = requests.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=self.headers
            )
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, []
        except Exception as e:
            console.print(f"[red]❌ Fehler beim Laden der Kommentare: {e}[/red]")
            return False, []

    def create_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> bool:
        """Erstellt einen Kommentar zu einem Issue"""
        try:
            response = requests.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=self.headers,
                json={"body": body}
            )
            return response.status_code == 201
        except Exception as e:
            console.print(f"[red]❌ Fehler beim Erstellen des Kommentars: {e}[/red]")
            return False

    def close_issue(self, owner: str, repo: str, issue_number: int, comment: str = "") -> bool:
        """Schließt ein Issue (v3.7.3 Feature)"""
        try:
            # Füge optional einen Kommentar hinzu
            if comment:
                self.create_issue_comment(owner, repo, issue_number, comment)
            
            # Schließe das Issue
            response = requests.patch(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                headers=self.headers,
                json={"state": "closed"}
            )
            
            if response.status_code == 200:
                write_to_changelog(f"Issue #{issue_number} automatisch geschlossen", "success")
                return True
            else:
                write_to_changelog(f"Issue #{issue_number} konnte nicht geschlossen werden (HTTP {response.status_code})", "error")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Fehler beim Schließen des Issues: {e}[/red]")
            write_to_changelog(f"Fehler beim Schließen von Issue #{issue_number}: {e}", "error")
            return False


# ─── Section V: Local Git API ───────────────────────────────────────────────────

class LocalGitAPI:
    """Lokale Git-Operationen mit erweiterten Features"""
    
    def __init__(self):
        pass

    def _run_git_command(self, command: List[str], cwd: Path) -> Tuple[bool, str]:
        """Führt ein Git-Kommando aus"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip() or str(e)

    def status(self, repo_path: Path) -> Tuple[bool, str]:
        """Git Status"""
        return self._run_git_command(["git", "status", "--porcelain"], repo_path)

    def commit(self, repo_path: Path, message: str = "") -> Tuple[bool, str]:
        """Git Commit mit Editor oder Message"""
        if message:
            return self._run_git_command(["git", "commit", "-m", message], repo_path)
        else:
            return self._run_git_command(["git", "commit"], repo_path)

    def push(self, repo_path: Path) -> Tuple[bool, str]:
        """Git Push"""
        return self._run_git_command(["git", "push"], repo_path)

    def pull(self, repo_path: Path) -> Tuple[bool, str]:
        """Git Pull"""
        return self._run_git_command(["git", "pull"], repo_path)

    def force_push_to_remote(self, repo_path: Path) -> Tuple[bool, str]:
        """Überschreibt Remote mit lokalen Änderungen"""
        return self._run_git_command(["git", "push", "--force"], repo_path)

    def force_pull_from_remote(self, repo_path: Path) -> Tuple[bool, str]:
        """Überschreibt lokale Änderungen mit Remote"""
        success1, _ = self._run_git_command(["git", "fetch", "--all"], repo_path)
        if success1:
            return self._run_git_command(["git", "reset", "--hard", "origin/main"], repo_path)
        return False, "Fetch fehlgeschlagen"

    def hard_push_update(self, repo_path: Path) -> Tuple[bool, str]:
        """Force-with-lease Push"""
        return self._run_git_command(["git", "push", "--force-with-lease"], repo_path)

    def hard_pull_update(self, repo_path: Path) -> Tuple[bool, str]:
        """Hard Pull mit Autostash"""
        return self._run_git_command(["git", "pull", "--autostash"], repo_path)

    def soft_push_update(self, repo_path: Path) -> Tuple[bool, str]:
        """Normaler Push"""
        return self.push(repo_path)

    def soft_pull_update(self, repo_path: Path) -> Tuple[bool, str]:
        """Fast-forward-only Pull"""
        return self._run_git_command(["git", "pull", "--ff-only"], repo_path)

    def get_recent_commits(self, repo_path: Path, count: int = 10) -> List[str]:
        """Holt die letzten Commits"""
        success, output = self._run_git_command([
            "git", "log", "--oneline", f"-{count}"
        ], repo_path)
        
        if success and output:
            return output.split('\n')
        return []

    def get_file_tree(self, repo_path: Path) -> List[str]:
        """Holt den Dateibaum des Repositories"""
        success, output = self._run_git_command([
            "git", "ls-tree", "-r", "--name-only", "HEAD"
        ], repo_path)
        
        if success and output:
            return output.split('\n')
        return []

    def clone_repository(self, clone_url: str, target_path: Path) -> Tuple[bool, str]:
        """Klont ein Repository"""
        try:
            result = subprocess.run([
                "git", "clone", clone_url, str(target_path)
            ], capture_output=True, text=True, check=True)
            return True, "Repository erfolgreich geklont"
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip() or str(e)


# ─── Section VI: Codex Integration (v3.7.3+ Features) ───────────────────────────

class CodexIntegration:
    """AI-Powered Code Generation mit Issue-Integration (v3.7.3+)"""
    
    def __init__(self, github_api: GitHubAPI, git_api: LocalGitAPI):
        self.github_api = github_api
        self.git_api = git_api
        self.openrouter_token = ""
        self.model = "openai/gpt-4o"
        
    def setup_ai_integration(self, token: str, model: str = "openai/gpt-4o"):
        """Konfiguriert AI-Integration"""
        self.openrouter_token = token
        self.model = model

    def log_to_issue(self, message: str, level: str = "info"):
        """Loggt Nachrichten und schreibt in CHANGELOG.md"""
        write_to_changelog(f"Codex: {message}", level)
        
        level_emoji = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌"
        }
        emoji = level_emoji.get(level, "📝")
        console.print(f"[blue]{emoji} {message}[/blue]")

    def fetch_codebase_context(self, owner: str, repo: str, repo_path: Path):
        """Sammelt Repository-Kontext für bessere Code-Generierung"""
        self.log_to_issue("Sammle Repository-Kontext für AI-Analyse", "info")
        
        # Dateisystem-Kontext
        file_tree = self.git_api.get_file_tree(repo_path)
        recent_commits = self.git_api.get_recent_commits(repo_path, 5)
        
        # Repository-Informationen
        success, repo_info = self.github_api.get_repository_info(owner, repo)
        
        context = {
            "files": file_tree[:50],  # Erste 50 Dateien
            "recent_commits": recent_commits,
            "repo_info": repo_info if success else {},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.log_to_issue(f"Kontext gesammelt: {len(file_tree)} Dateien, {len(recent_commits)} Commits", "success")
        return context

    def generate_comprehensive_prompt(self, issue: Dict[str, Any], comments: List[str], repo_path: Path) -> str:
        """Erstellt umfassenden Prompt für Code-Generierung"""
        issue_title = issue.get('title', 'Ohne Titel')
        issue_body = issue.get('body', 'Keine Beschreibung')
        issue_number = issue.get('number', 0)
        
        # Repository-Kontext
        file_tree = self.git_api.get_file_tree(repo_path)
        recent_commits = self.git_api.get_recent_commits(repo_path, 3)
        
        prompt = f"""
ENTWICKLUNGSAUFTRAG für Repository: {repo_path.name}ENTWICKLUNGSAUFTRAG für Repository: {repo_path.name}
═══════════════════════════════════════════════════

🎯 ISSUE: #{issue_number} - {issue_title}

📋 BESCHREIBUNG:
{issue_body}

🗂️ REPOSITORY-STRUKTUR (Auszug):
{chr(10).join(file_tree[:20])}

📝 LETZTE COMMITS:
{chr(10).join(recent_commits)}

💬 VORHERIGE KOMMENTARE:
{chr(10).join(comments[-3:]) if comments else "Keine vorherigen Kommentare"}

📁 ARBEITSVERZEICHNIS: {repo_path}

🎯 AUFGABE:
Analysiere das Issue und implementiere eine vollständige Lösung. 
Berücksichtige die Repository-Struktur und vorherige Änderungen.
Erstelle alle notwendigen Dateien und Änderungen.

⚡ WICHTIG: 
- Nutze den verfügbaren Repository-Kontext
- Halte dich an bestehende Code-Konventionen
- Teste deine Implementierung
- Dokumentiere Änderungen

BEGINNE JETZT:
"""
        
        self.log_to_issue(f"Prompt generiert für Issue #{issue_number}: {len(prompt)} Zeichen", "success")
        return prompt

    def execute_codex(self, repo_path: Path, prompt: str) -> Tuple[bool, str]:
        """Führt Codex mit dem generierten Prompt aus"""
        self.log_to_issue("Starte Codex-Ausführung", "info")
        
        try:
            # Erstelle temporäre Prompt-Datei
            prompt_file = CODEX_DIR / f"prompt_{int(time.time())}.txt"
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            # Führe Codex aus
            result = subprocess.run([
                "codex", 
                str(prompt_file),
                "--directory", str(repo_path)
            ], capture_output=True, text=True, timeout=300)
            
            # Cleanup
            if prompt_file.exists():
                prompt_file.unlink()
            
            if result.returncode == 0:
                self.log_to_issue("Codex erfolgreich ausgeführt", "success")
                return True, result.stdout
            else:
                self.log_to_issue(f"Codex Fehler: {result.stderr}", "error")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            self.log_to_issue("Codex Timeout nach 5 Minuten", "error")
            return False, "Timeout: Codex-Ausführung dauerte zu lange"
        except Exception as e:
            self.log_to_issue(f"Codex Ausführungsfehler: {e}", "error")
            return False, str(e)

    def analyze_issue_completion(self, issue: Dict[str, Any], codex_output: str) -> Dict[str, Any]:
        """Analysiert ob ein Issue vollständig gelöst wurde (v3.7.3 Feature)"""
        if not self.openrouter_token:
            self.log_to_issue("Keine OpenRouter Token - überspringe AI-Analyse", "warning")
            return {"completed": False, "confidence": 0, "reason": "No AI token"}
        
        self.log_to_issue("Starte AI-basierte Issue-Vollständigkeits-Analyse", "info")
        
        try:
            # Erstelle Analyse-Prompt
            analysis_prompt = f"""
Analysiere ob das folgende GitHub Issue vollständig gelöst wurde:

ISSUE TITEL: {issue.get('title', 'N/A')}
ISSUE BESCHREIBUNG: {issue.get('body', 'N/A')}

CODEX OUTPUT: {codex_output[:2000]}...

Gib eine JSON-Antwort mit folgender Struktur:
{{
    "completed": true/false,
    "confidence": 0-100,
    "reason": "Detaillierte Begründung",
    "next_steps": ["Schritt 1", "Schritt 2"],
    "recommendation": "close" oder "keep_open"
}}
"""
            
            # OpenRouter API Call
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": analysis_prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                ai_response = response.json()
                content = ai_response['choices'][0]['message']['content']
                
                # Parse JSON aus AI-Antwort
                import json
                try:
                    result = json.loads(content)
                    self.log_to_issue(f"AI-Analyse abgeschlossen: {result.get('confidence', 0)}% Confidence", "success")
                    return result
                except json.JSONDecodeError:
                    # Fallback wenn JSON-Parsing fehlschlägt
                    self.log_to_issue("AI-Antwort konnte nicht als JSON geparst werden", "warning")
                    return {
                        "completed": "true" in content.lower() and "completed" in content.lower(),
                        "confidence": 75 if "completed" in content.lower() else 25,
                        "reason": content[:200],
                        "recommendation": "close" if "close" in content.lower() else "keep_open"
                    }
            else:
                self.log_to_issue(f"OpenRouter API Fehler: {response.status_code}", "error")
                return {"completed": False, "confidence": 0, "reason": "API Error"}
                
        except Exception as e:
            self.log_to_issue(f"AI-Analyse Fehler: {e}", "error")
            return {"completed": False, "confidence": 0, "reason": str(e)}

    def _format_analysis_comment(self, analysis: Dict[str, Any], codex_output: str) -> str:
        """Formatiert AI-Analyse als GitHub-Kommentar"""
        status_emoji = "✅" if analysis.get("completed", False) else "⚠️"
        confidence = analysis.get("confidence", 0)
        reason = analysis.get("reason", "Keine Begründung verfügbar")
        
        comment = f"""## {status_emoji} Automatische Issue-Analyse

**Status**: {"Abgeschlossen" if analysis.get("completed", False) else "In Bearbeitung"}
**Confidence**: {confidence}%

**Analyse**: {reason}

**Empfehlung**: {analysis.get("recommendation", "keep_open").replace("_", " ").title()}

### 🤖 Codex-Ausführung
```
{codex_output[:500]}{'...' if len(codex_output) > 500 else ''}
```

### 📊 Details
- **Timestamp**: {time.strftime("%Y-%m-%d %H:%M:%S")}
- **AI-Model**: {self.model}
- **grepo2 Version**: 3.7.3.2

---
*Automatisch generiert von grepo2 v3.7.3.2*
"""
        return comment

    def execute_codex_for_issue(self, repo_path: Path, issue: Dict[str, Any], owner: str, repo: str) -> bool:
        """Vollständiger Workflow: Issue analysieren, Codex ausführen, AI-Analyse, Auto-Close (v3.7.3+)"""
        issue_number = issue.get('number', 0)
        self.log_to_issue(f"Starte vollständigen Workflow für Issue #{issue_number}", "info")
        
        try:
            # 1. Lade Issue-Kommentare
            console.print("[blue]Lade Issue-Kommentare...[/blue]")
            ok, comments_data = self.github_api.get_issue_comments(owner, repo, issue_number)
            comments = []
            if ok:
                for comment in comments_data:
                    body = comment.get('body', '').strip()
                    if body:
                        comments.append(body)
                console.print(f"[green]✓ {len(comments)} Kommentare geladen[/green]")
                self.log_to_issue(f"Analysiere {len(comments)} vorhandene Issue-Kommentare", "info")
            else:
                console.print("[yellow]⚠ Kommentare konnten nicht geladen werden[/yellow]")
                self.log_to_issue("Keine vorherigen Kommentare gefunden", "warning")

            # 2. Hole Codebase-Kontext
            console.print("[blue]Lade aktuellen Codebase-Kontext...[/blue]")
            self.fetch_codebase_context(owner, repo, repo_path)

            # 3. Generiere umfassenden Prompt
            console.print("[blue]Generiere Entwicklungsauftrag...[/blue]")
            prompt = self.generate_comprehensive_prompt(issue, comments, repo_path)
            
            # Zeige Prompt-Vorschau
            console.print("\n" + "="*80)
            console.print("[bold cyan]PROMPT VORSCHAU (erste 500 Zeichen):[/bold cyan]")
            console.print("="*80)
            console.print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            console.print("="*80 + "\n")

            if input("🚀 Codex starten? (j/n): ").lower() != 'j':
                console.print("[yellow]Abgebrochen[/yellow]")
                self.log_to_issue("❌ Code-Generierung vom Benutzer abgebrochen", "warning")
                return False

            # 4. Führe Codex aus mit Live-Monitoring
            console.print("\n[bold green]🤖 Starte autonome Code-Generierung mit Codex...[/bold green]")
            
            start_time = time.time()
            success, result = self.execute_codex(repo_path, prompt)
            end_time = time.time()
            duration = end_time - start_time

            # 5. Verarbeite Ergebnisse
            console.print(f"\n[bold]📊 CODEX ERGEBNISSE[/bold]")
            console.print(f"[blue]Dauer: {duration:.1f} Sekunden[/blue]")
            
            if success:
                console.print(f"[green]✅ Codex erfolgreich ausgeführt![/green]")
                console.print("\n[bold]Ausgabe:[/bold]")
                console.print(Panel.fit(result, title="Codex Output", border_style="green"))
                
                # 6. AI-Vollständigkeitsanalyse (v3.7.3 Feature)
                console.print("\n[blue]🤖 Starte AI-basierte Issue-Vollständigkeits-Analyse...[/blue]")
                analysis = self.analyze_issue_completion(issue, result)
                
                # 7. Erstelle detaillierten GitHub-Kommentar
                analysis_comment = self._format_analysis_comment(analysis, result)
                comment_success = self.github_api.create_issue_comment(owner, repo, issue_number, analysis_comment)
                
                if comment_success:
                    console.print("[green]✓ Analyse-Kommentar zu Issue hinzugefügt[/green]")
                    self.log_to_issue("GitHub-Kommentar mit Analyse-Ergebnissen erstellt", "success")
                else:
                    console.print("[yellow]⚠ Kommentar konnte nicht erstellt werden[/yellow]")
                
                # 8. Automatisches Issue-Closing bei hoher Confidence (v3.7.3 Feature)
                confidence = analysis.get("confidence", 0)
                should_close = analysis.get("completed", False) and confidence >= 80
                
                if should_close:
                    console.print(f"\n[bold green]🎯 Issue als vollständig erkannt (Confidence: {confidence}%)[/bold green]")
                    if input("Issue automatisch schließen? (j/n): ").lower() == 'j':
                        close_comment = f"🤖 **Automatisch geschlossen**\n\nIssue wurde durch AI-Analyse als vollständig gelöst erkannt (Confidence: {confidence}%).\n\n{analysis.get('reason', '')}"
                        
                        if self.github_api.close_issue(owner, repo, issue_number, close_comment):
                            console.print("[bold green]✅ Issue automatisch geschlossen![/bold green]")
                            self.log_to_issue(f"Issue #{issue_number} automatisch geschlossen mit {confidence}% Confidence", "success")
                        else:
                            console.print("[red]❌ Issue konnte nicht geschlossen werden[/red]")
                else:
                    console.print(f"\n[yellow]⚠ Issue als unvollständig erkannt (Confidence: {confidence}%)[/yellow]")
                    console.print("[blue]💡 Empfehlung: Weitere Entwicklung erforderlich[/blue]")
                    self.log_to_issue(f"Issue #{issue_number} bleibt offen - weitere Arbeit erforderlich", "info")
                
                return True
                
            else:
                console.print(f"[red]❌ Codex-Ausführung fehlgeschlagen![/red]")
                console.print(f"[red]Fehler: {result}[/red]")
                
                # Erstelle Fehler-Kommentar
                error_comment = f"❌ **Codex-Ausführung fehlgeschlagen**\n\n```\n{result}\n```\n\n*Automatisch generiert von grepo2 v3.7.3.2*"
                self.github_api.create_issue_comment(owner, repo, issue_number, error_comment)
                
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Workflow-Fehler: {e}[/red]")
            self.log_to_issue(f"Workflow-Fehler für Issue #{issue_number}: {e}", "error")
            return False


# ─── Section VII: TUI Navigation (Wiederhergestellt aus v3.7.2) ─────────────────

def run_curses_menu(title: str, options: List[Tuple[str,str]], context: str="") -> Optional[int]:
    """Original curses-basierte TUI mit Pfeiltasten-Navigation (aus v3.7.2)"""
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
        
        # Beschreibungs-Box
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


# ─── Section VIII: TUI Functions (Vollständig wiederhergestellt) ────────────────

def tui_codex_generate():
    """Codex Code-Generierung mit GitHub Issue-Integration (v3.7.3+ Features)"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer gesetzt[/red]")
        return

    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden[/red]")
        return

    # GitHub API initialisieren
    github_api = GitHubAPI(user_config["token"])
    git_api = LocalGitAPI()
    codex = CodexIntegration(github_api, git_api)
    
    # AI-Integration konfigurieren falls verfügbar
    if user_config.get("openrouter_token"):
        codex.setup_ai_integration(user_config["openrouter_token"], user_config.get("model", "openai/gpt-4o"))

    # Repository-Auswahl
    user_dir = GITHUB_DIR / active_user
    repos = sorted([d for d in user_dir.iterdir() if d.is_dir() and d.name != "backup"], key=lambda p: p.name)
    
    if not repos:
        console.print("[red]❌ Keine lokalen Repositories gefunden![/red]")
        console.print(f"[blue]💡 Erstelle Repositories in: {user_dir}[/blue]")
        input()
        return

    repo_options = [(r.name, f"Lokaler Pfad: {r}") for r in repos]
    repo_choice = run_curses_menu("Repository für Codex auswählen", repo_options, f"Aktiver Benutzer: {active_user}")
    
    if repo_choice is None:
        return
    
    repo_path = repos[repo_choice]
    repo_name = repo_path.name
    
    # Repository-Info anzeigen
    console.clear()
    console.print(f"[bold cyan]📁 Repository: {repo_name}[/bold cyan]")
    console.print(f"[blue]📂 Pfad: {repo_path}[/blue]")
    
    # GitHub Issues laden
    console.print("[blue]🔍 Lade GitHub Issues...[/blue]")
    success, issues = github_api.list_issues(active_user, repo_name)
    
    if not success or not issues:
        console.print("[yellow]⚠ Keine offenen Issues gefunden oder API-Fehler[/yellow]")
        console.print("[blue]💡 Erstelle Issues auf GitHub für bessere Codex-Integration[/blue]")
        input()
        return

    # Issue-Auswahl mit modernem Rich-Interface
    console.print(f"[green]✓ {len(issues)} Issues gefunden[/green]")
    
    # Filtere nach "in-work" Label (v3.7.2 Feature)
    in_work_issues = [issue for issue in issues if any(label.get('name', '') == 'in-work' for label in issue.get('labels', []))]
    
    if in_work_issues:
        console.print(f"[blue]🏷️ {len(in_work_issues)} Issues mit 'in-work' Label gefunden[/blue]")
        issues_to_show = in_work_issues
    else:
        console.print("[yellow]💡 Keine 'in-work' Issues - zeige alle offenen Issues[/yellow]")
        issues_to_show = issues

    # Issue-Optionen für Curses-Menü
    issue_options = []
    for issue in issues_to_show[:10]:  # Erste 10 Issues
        title = issue.get('title', 'Ohne Titel')
        number = issue.get('number', 0)
        labels = [label.get('name', '') for label in issue.get('labels', [])]
        label_str = f" [{', '.join(labels)}]" if labels else ""
        
        option_text = f"#{number}: {title[:50]}{'...' if len(title) > 50 else ''}"
        desc_text = f"Labels: {label_str}\nBeschreibung: {issue.get('body', 'Keine Beschreibung')[:100]}..."
        
        issue_options.append((option_text, desc_text))

    issue_choice = run_curses_menu("GitHub Issue auswählen", issue_options, f"Repository: {repo_name}")
    
    if issue_choice is None:
        return
    
    selected_issue = issues_to_show[issue_choice]
    
    # Starte Codex-Workflow mit allen v3.7.3+ Features
    console.clear()
    console.print(f"[bold green]🚀 Starte Codex für Issue #{selected_issue['number']}[/bold green]")
    console.print(f"[blue]📝 {selected_issue['title']}[/blue]")
    
    success = codex.execute_codex_for_issue(repo_path, selected_issue, active_user, repo_name)
    
    if success:
        console.print("\n[bold green]✅ Codex-Workflow erfolgreich abgeschlossen![/bold green]")
    else:
        console.print("\n[bold red]❌ Codex-Workflow fehlgeschlagen![/bold red]")
    
    input("\nDrücke Enter, um zum Hauptmenü zu gelangen...")
    return True

def tui_manage_repo(repo_path: Path):
    """Repository-Verwaltung mit Git-Operationen (wiederhergestellt aus v3.7.2)"""
    active_user = get_active_user()
    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden[/red]")
        return

    git_api = LocalGitAPI()
    
    options = [
        ("Status prüfen", "Zeigt `git status` an."),
        ("Commit erstellen", "Öffnet Editor für `git commit`."),
        ("Online-Repo mit Lokal überschreiben", "git push --force"),
        ("Lokales Repo mit Online überschreiben", "hart reset/clone"),
        ("Online-Repo hart aktualisieren", "git push --force-with-lease"),
        ("Lokales Repo hart aktualisieren", "git pull --autostash (clean)"),
        ("Online-Repo soft aktualisieren", "normaler git push"),
        ("Lokales Repo soft aktualisieren", "git pull --ff-only"),
        ("🤖 Codex für dieses Repository", "AI-powered Code-Generierung"),
        ("Zurück zum Hauptmenü", "")
    ]
    context = f"Aktiver Benutzer: {active_user} | Repo: {repo_path.name}"
    while True:
        choice = run_curses_menu(f"Verwalte: {repo_path.name}", options, context)
        if choice is None or choice == 9:
            break
        if choice == 0:
            _execute_and_display("Git Status", git_api.status, repo_path)
        elif choice == 1:
            _execute_and_display("Git Commit", git_api.commit, repo_path)
        elif choice == 2:
            _execute_and_display("Force Push", git_api.force_push_to_remote, repo_path)
        elif choice == 3:
            _execute_and_display("Force Pull", git_api.force_pull_from_remote, repo_path)
        elif choice == 4:
            _execute_and_display("Hard Push Update", git_api.hard_push_update, repo_path)
        elif choice == 5:
            _execute_and_display("Hard Pull Update", git_api.hard_pull_update, repo_path)
        elif choice == 6:
            _execute_and_display("Soft Push Update", git_api.soft_push_update, repo_path)
        elif choice == 7:
            _execute_and_display("Soft Pull Update", git_api.soft_pull_update, repo_path)
        elif choice == 8:
            tui_codex_generate()

def tui_settings_menu():
    """Einstellungen-Menü (wiederhergestellt aus v3.7.2)"""
    options = [
        ("GitHub Token ändern", "PAT aktualisieren"),
        ("AI-Anbindung konfigurieren", "OpenRouter Token & Model"),
        ("Lokale Repositories anzeigen", "Repository-Übersicht"),
        ("Zurück", "Hauptmenü")
    ]
    context = f"Aktiver Benutzer: {get_active_user()}"
    while True:
        c = run_curses_menu("Einstellungen", options, context)
        if c is None or c == 3:
            break
        elif c == 0:
            tui_change_github_token()
        elif c == 1:
            tui_ki_anbindung()
        elif c == 2:
            tui_show_repositories()

def tui_change_github_token():
    """GitHub Token ändern"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer[/red]")
        input()
        return
    
    console.clear()
    console.print(f"[bold cyan]GitHub Token für {active_user} ändern[/bold cyan]")
    console.print("Erstelle einen neuen Token unter: https://github.com/settings/tokens")
    console.print("Benötigte Berechtigungen: repo (Full control of private repositories)\n")
    
    new_token = getpass("Neuer Personal Access Token: ")
    if not new_token:
        console.print("[yellow]Abgebrochen[/yellow]")
        input()
        return
    
    # Token validieren
    github_api = GitHubAPI(new_token)
    success, user_info = github_api.get_user_info()
    if not success:
        console.print("[red]❌ Token-Validierung fehlgeschlagen![/red]")
        input()
        return
    
    # Aktuelle Konfiguration laden und Token aktualisieren
    user_config = load_user_config(active_user) or {}
    save_user_config(
        active_user, 
        new_token,
        user_config.get("openrouter_token", ""),
        user_config.get("model", "openai/gpt-4o")
    )
    
    console.print("[green]✅ GitHub Token erfolgreich aktualisiert![/green]")
    input()

def tui_ki_anbindung():
    """KI-Anbindung konfigurieren"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer[/red]")
        input()
        return
    
    console.clear()
    console.print("[bold cyan]🤖 AI-Integration konfigurieren[/bold cyan]")
    console.print("Für erweiterte Codex-Features benötigst du einen OpenRouter API-Token.")
    console.print("Registrierung: https://openrouter.ai/\n")
    
    openrouter_token = getpass("OpenRouter API Token (optional): ")
    
    console.print("\nVerfügbare AI-Modelle:")
    models = [
        "openai/gpt-4o",
        "anthropic/claude-3.5-sonnet",
        "google/gemini-pro",
        "meta-llama/llama-3-70b-instruct"
    ]
    
    for i, model in enumerate(models):
        console.print(f"{i+1}. {model}")
    
    try:
        model_choice = int(input(f"\nModell wählen (1-{len(models)}): ")) - 1
        if 0 <= model_choice < len(models):
            selected_model = models[model_choice]
        else:
            selected_model = "openai/gpt-4o"
    except ValueError:
        selected_model = "openai/gpt-4o"
    
    # Aktuelle Konfiguration laden und aktualisieren
    user_config = load_user_config(active_user)
    if user_config:
        save_user_config(
            active_user,
            user_config["token"],
            openrouter_token,
            selected_model
        )
        console.print(f"[green]✅ AI-Integration konfiguriert![/green]")
        console.print(f"[blue]Model: {selected_model}[/blue]")
        if openrouter_token:
            console.print("[blue]OpenRouter Token gesetzt[/blue]")
        else:
            console.print("[yellow]Ohne OpenRouter Token sind erweiterte AI-Features deaktiviert[/yellow]")
    else:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden[/red]")
    
    input()

def tui_show_repositories():
    """Zeigt lokale Repositories an"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer[/red]")
        input()
        return
    
    user_dir = GITHUB_DIR / active_user
    repos = sorted([d for d in user_dir.iterdir() if d.is_dir() and d.name != "backup"], key=lambda p: p.name)
    
    console.clear()
    console.print(f"[bold cyan]📁 Lokale Repositories für {active_user}[/bold cyan]")
    console.print(f"[blue]Basis-Verzeichnis: {user_dir}[/blue]\n")
    
    if not repos:
        console.print("[yellow]⚠ Keine Repositories gefunden[/yellow]")
        console.print(f"[blue]💡 Erstelle Repositories in: {user_dir}[/blue]")
    else:
        table = Table(title="Repository-Übersicht")
        table.add_column("Name", style="cyan")
        table.add_column("Pfad", style="blue")
        table.add_column("Größe", style="green")
        
        for repo in repos:
            try:
                size = sum(f.stat().st_size for f in repo.rglob('*') if f.is_file())
                size_str = f"{size // 1024} KB" if size < 1024*1024 else f"{size // (1024*1024)} MB"
            except:
                size_str = "N/A"
            
            table.add_row(repo.name, str(repo), size_str)
        
        console.print(table)
    
    input("\nDrücke Enter zum Fortfahren...")

def tui_user_menu():
    """Benutzerverwaltung (wiederhergestellt aus v3.7.2)"""
    options = [
        ("Benutzer auswählen", "Profil wechseln"),
        ("Neuen Benutzer verbinden", "GitHub PAT anlegen"),
        ("Benutzer löschen", "Profil entfernen"),
        ("Zurück", "Hauptmenü")
    ]
    context = f"Aktiver Benutzer: {get_active_user()}"
    while True:
        c = run_curses_menu("Benutzerverwaltung", options, context)
        if c is None or c == 3:
            break
        elif c == 0:
            console.clear()
            console.print("[yellow]Benutzer-Auswahl noch nicht implementiert[/yellow]")
            input()
        elif c == 1:
            console.clear()
            console.print("[yellow]Neuer Benutzer noch nicht implementiert[/yellow]")
            input()
        elif c == 2:
            console.clear()
            console.print("[yellow]Benutzer löschen noch nicht implementiert[/yellow]")
            input()
    return False

def tui_first_time_setup():
    """Erste Benutzer-Einrichtung (wiederhergestellt aus v3.7.2 mit v3.7.3+ Features)"""
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]Willkommen bei grepo2 v3.7.3.2![/bold cyan]\n\n"
        "Dieses Tool vereinfacht die Verwaltung deiner GitHub-Repositories\n"
        "mit erweiterten AI-Features für automatisierte Entwicklung.\n"
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
    github_api = GitHubAPI(token)
    success, user_info = github_api.get_user_info()
    if not success:
        console.print("[red]❌ Verbindung fehlgeschlagen. Bitte überprüfe Benutzername und Token.[/red]")
        return False
    
    console.print("[green]✓ Verbindung erfolgreich![/green]")
    
    # Erweiterte AI-Setup (v3.7.3+ Feature)
    console.print("\n[yellow]Schritt 2 (Optional):[/yellow] AI-Integration einrichten")
    console.print("Für erweiterte Codex-Features kannst du einen OpenRouter API-Token hinzufügen.")
    console.print("Registrierung: https://openrouter.ai/ (optional, kann später eingerichtet werden)\n")
    
    setup_ai = input("AI-Integration jetzt einrichten? (j/n): ").lower() == 'j'
    openrouter_token = ""
    model = "openai/gpt-4o"
    
    if setup_ai:
        openrouter_token = getpass("OpenRouter API Token (Enter für später): ")
        if openrouter_token:
            console.print("Verfügbare AI-Modelle:")
            models = [
                "openai/gpt-4o",
                "anthropic/claude-3.5-sonnet", 
                "google/gemini-pro"
            ]
            for i, m in enumerate(models):
                console.print(f"{i+1}. {m}")
            
            try:
                choice = int(input(f"Modell wählen (1-{len(models)}, Enter für Standard): ") or "1") - 1
                if 0 <= choice < len(models):
                    model = models[choice]
            except ValueError:
                pass
    
    # Speichere Benutzer
    save_user_config(username, token, openrouter_token, model)
    set_active_user(username)
    (GITHUB_DIR / username).mkdir(parents=True, exist_ok=True)
    
    console.print(f"\n[green]✅ Benutzer '{username}' wurde erfolgreich eingerichtet![/green]")
    console.print(f"[green]✅ Lokales Verzeichnis erstellt: {GITHUB_DIR / username}[/green]")
    console.print(f"[blue]📧 GitHub: {user_info.get('email', 'N/A')}[/blue]")
    
    if openrouter_token:
        console.print(f"[blue]🤖 AI-Model: {model}[/blue]")
        console.print("[blue]🎯 Erweiterte Codex-Features aktiviert![/blue]")
    else:
        console.print("[yellow]💡 AI-Features können später in den Einstellungen aktiviert werden[/yellow]")
    
    # CHANGELOG-Eintrag (v3.7.3+ Feature)
    write_to_changelog(f"Neuer Benutzer '{username}' erfolgreich eingerichtet", "success")
    
    console.print("\n[bold green]🎉 Setup abgeschlossen![/bold green]")
    console.print("[blue]Verwende das Hauptmenü zur Navigation oder 'grepo2 go' für CLI-Befehle[/blue]")
    input("\nDrücke Enter, um zum Hauptmenü zu gelangen...")
    return True


def tui_projekterstellung_menu(repo_path: Path):
    """Projekterstellungsmenü (wiederhergestellt aus v3.7.2 mit v3.7.3+ Funktionen)"""
    options = [
        ("🤖 Code generieren mit Codex",    "Repository-spezifische KI-Code-Generierung mit Issues"),
        ("Roadmap generieren",              "Erstelle eine technische Roadmap (geplant)"),
        ("Projekt auf GitHub einrichten",   "Erstelle Issues auf GitHub (geplant)"),
        ("Zurück",                          "Hauptmenü")
    ]
    while True:
        choice = run_curses_menu("Projekterstellung", options, f"Projekterstellung – {repo_path.name}")
        if choice is None or choice == 3:
            break
        elif choice == 0:
            # Verwende Repository-spezifische Codex-Generierung
            tui_codex_generate_for_repo(repo_path)
        elif choice == 1:
            console.clear()
            console.print("[yellow]Roadmap-Generierung noch nicht vollständig implementiert[/yellow]")
            console.print("[blue]💡 Geplant für zukünftige Version[/blue]")
            input("Drücke Enter zum Fortfahren...")
        elif choice == 2:
            console.clear()
            console.print("[yellow]GitHub-Projekt-Setup noch nicht implementiert[/yellow]")
            console.print("[blue]💡 Geplant für zukünftige Version[/blue]")
            input("Drücke Enter zum Fortfahren...")


def tui_codex_generate_for_repo(repo_path: Path):
    """Repository-spezifische Codex-Generierung (kompatibel mit v3.7.2 Aufruf)"""
    console.clear()
    console.rule(f"[bold cyan]Repository-spezifische Code-Generierung: {repo_path.name}[/bold cyan]")
    
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer gesetzt[/red]")
        input("Drücke Enter zum Fortfahren...")
        return

    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden[/red]")
        console.print("[blue]💡 Gehe zu Einstellungen → GitHub Token ändern[/blue]")
        input("Drücke Enter zum Fortfahren...")
        return
    
    # Check if GitHub token is available and valid
    if not user_config.get("token"):
        console.print("[red]❌ GitHub Token fehlt oder ist beschädigt[/red]")
        console.print("[blue]💡 Gehe zu Einstellungen → GitHub Token ändern[/blue]")
        input("Drücke Enter zum Fortfahren...")
        return

    # GitHub API initialisieren
    github_api = GitHubAPI(user_config["token"])
    git_api = LocalGitAPI()
    codex = CodexIntegration(github_api, git_api)
    
    # AI-Integration konfigurieren falls verfügbar
    if user_config.get("openrouter_token"):
        codex.setup_ai_integration(user_config["openrouter_token"], user_config.get("model", "openai/gpt-4o"))
        console.print(f"[green]✓ AI-Integration aktiviert: {user_config.get('model', 'openai/gpt-4o')}[/green]")
    else:
        console.print("[yellow]⚠ AI-Integration nicht konfiguriert[/yellow]")
        console.print("[blue]💡 Konfiguriere OpenRouter Token in den Einstellungen für erweiterte Features[/blue]")

    # Repository-Info anzeigen
    console.print(f"[blue]📂 Repository: {repo_path}[/blue]")
    repo_name = repo_path.name
    
    # GitHub Issues laden für das spezifische Repository
    console.print("[blue]🔍 Lade GitHub Issues...[/blue]")
    success, issues = github_api.list_issues(active_user, repo_name)
    
    if not success or not issues:
        console.print("[yellow]⚠ Keine offenen Issues gefunden oder API-Fehler[/yellow]")
        console.print("[blue]💡 Erstelle Issues auf GitHub für bessere Codex-Integration[/blue]")
        input("Drücke Enter zum Fortfahren...")
        return

    # Issue-Auswahl mit modernem Rich-Interface
    console.print(f"[green]✓ {len(issues)} Issues gefunden[/green]")
    
    # Filtere nach "in-work" Label (v3.7.2 Feature)
    in_work_issues = [issue for issue in issues if any(label.get('name', '') == 'in-work' for label in issue.get('labels', []))]
    
    if in_work_issues:
        console.print(f"[blue]🏷️ {len(in_work_issues)} Issues mit 'in-work' Label gefunden[/blue]")
        issues_to_show = in_work_issues
    else:
        console.print("[yellow]💡 Keine 'in-work' Issues - zeige alle offenen Issues[/yellow]")
        issues_to_show = issues

    # Issue-Optionen für Curses-Menü
    issue_options = []
    for issue in issues_to_show[:10]:  # Erste 10 Issues
        title = issue.get('title', 'Ohne Titel')
        number = issue.get('number', 0)
        labels = [label.get('name', '') for label in issue.get('labels', [])]
        label_str = f" [{', '.join(labels)}]" if labels else ""
        issue_options.append((f"#{number}: {title[:60]}", f"Labels: {label_str}"))
    
    if not issue_options:
        console.print("[yellow]Keine Issues zum Bearbeiten verfügbar[/yellow]")
        input("Drücke Enter zum Fortfahren...")
        return

    # Issue auswählen
    selected_issue_idx = run_curses_menu(
        f"Issue für {repo_name} auswählen", 
        issue_options, 
        f"Repository: {repo_path}"
    )
    
    if selected_issue_idx is None:
        return
    
    selected_issue = issues_to_show[selected_issue_idx]
    console.print(f"[green]✓ Issue #{selected_issue['number']} ausgewählt[/green]")
    
    # Führe Codex für das ausgewählte Issue aus
    try:
        write_to_changelog(f"Repository-spezifische Codex-Generierung gestartet für {repo_name} Issue #{selected_issue['number']}", "info")
        codex.execute_codex_for_issue(repo_path, selected_issue, active_user, repo_name)
    except Exception as e:
        console.print(f"[red]❌ Fehler bei Codex-Ausführung: {e}[/red]")
        write_to_changelog(f"Codex-Fehler für {repo_name}: {e}", "error")
    
    input("Drücke Enter zum Fortfahren...")


# ─── Section IX: Main TUI (Vollständig wiederhergestellt aus v3.7.2) ───────────

def run_tui():
    """Hauptmenü mit wiederhergestellter Repository-Auswahl und vollständiger Navigation"""
    while True:
        user = get_active_user()
        user_dir = GITHUB_DIR / user
        repos = sorted([d for d in user_dir.iterdir() if d.is_dir() and d.name != "backup"], key=lambda p: p.name)
        
        # Repository-Optionen (Kernfunktion wiederhergestellt!)
        repo_opts = [(r.name, f"Verwalte Repository: {r.name}") for r in repos]
        
        # Fixe Optionen
        fixed_opts = [
            ("🤖 Codex: Code mit AI generieren", "Issue-basierte Code-Generierung"),
            ("Benutzer wechseln", "Profil wechseln"),
            ("Neues Repository erstellen", "Erstelle neues Repo & klone"),
            ("Einstellungen", "grepo2-Einstellungen & AI-Konfiguration"),
            ("Projekterstellung", "Roadmap & Issues & Codex"),
            ("Exit", "Beenden")
        ]
        opts = repo_opts + fixed_opts
        
        context = f"Aktiver Benutzer: {user} | Repositories: {len(repos)} | grepo2 v3.7.4"
        sel = run_curses_menu("grepo2 Hauptmenü", opts, context)
        
        if sel is None or sel == len(opts) - 1:  # Exit
            console.print("[green]👋 Auf Wiedersehen![/green]")
            return False
        
        if sel < len(repo_opts):
            # Repository verwalten (WIEDERHERGESTELLT!)
            tui_manage_repo(repos[sel])
        else:
            # Fixe Optionen
            idx = sel - len(repo_opts)
            if idx == 0:  # Codex
                tui_codex_generate()
            elif idx == 1:  # Benutzer wechseln
                if tui_user_menu():
                    return True
            elif idx == 2:  # Neues Repository
                console.clear()
                console.print("[yellow]Repository-Erstellung noch nicht implementiert[/yellow]")
                console.print("[blue]💡 Erstelle Repositories manuell in GitHub und klone sie lokal[/blue]")
                input()
            elif idx == 3:  # Einstellungen
                tui_settings_menu()
            elif idx == 4:  # Projekterstellung
                if not repos:
                    console.print("[yellow]Keine Repositories vorhanden[/yellow]")
                    input()
                else:
                    choice = run_curses_menu(
                        "Repo für Projekterstellung wählen",
                        [(r.name, f"Projektmanagement für {r.name}") for r in repos],
                        f"Aktiver Benutzer: {user}"
                    )
                    if choice is not None:
                        tui_projekterstellung_menu(repos[choice])


# ─── Section X: CLI Commands (Originalverhalten) ────────────────────────────────

@click.group()
def go():
    """CLI-Kommandos für erweiterte Funktionen"""
    pass

@go.group()
def repo():
    """Repository-Management-Befehle"""
    pass

@repo.command()
def list():
    """Listet alle Repositories auf"""
    active = get_active_user()
    if not active:
        console.print("[red]Kein aktiver Benutzer[/red]")
        return
    
    user_config = load_user_config(active)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden.[/red]")
        return

    github_api = GitHubAPI(user_config["token"])
    
    console.print(f"[blue]🔍 Lade Repositories für {active}...[/blue]")
    repos = github_api.list_repositories(active)
    
    if not repos:
        console.print("[red]❌ Keine Repositories gefunden![/red]")
        return

    table = Table(title=f"📁 Repositories von {active}")
    table.add_column("Name", style="cyan")
    table.add_column("Sprache", style="blue")
    table.add_column("Privat", style="red")
    table.add_column("Beschreibung", style="white")
    
    for repo in repos[:20]:  # Erste 20
        name = repo.get("name", "N/A")
        language = repo.get("language") or "N/A"
        private = "🔒" if repo.get("private") else "🔓"
        description = repo.get("description") or "Keine Beschreibung"
        
        if len(description) > 50:
            description = description[:47] + "..."
        
        table.add_row(name, language, private, description)
    
    console.print(table)
    
    if len(repos) > 20:
        console.print(f"[dim]... und {len(repos) - 20} weitere[/dim]")

@go.command()
def login():
    """Benutzer einloggen"""
    username = input("GitHub-Benutzername: ")
    if not username:
        console.print("[red]❌ Benutzername ist erforderlich![/red]")
        return
    
    token = getpass("GitHub Personal Access Token: ")
    if not token:
        console.print("[red]❌ Token ist erforderlich![/red]")
        return
    
    # Validiere Token
    github_api = GitHubAPI(token)
    console.print("[blue]🔍 Validiere GitHub-Token...[/blue]")
    
    success, user_info = github_api.get_user_info()
    if not success:
        console.print("[red]❌ Token-Validierung fehlgeschlagen![/red]")
        return

    # Speichere Benutzer
    save_user_config(username, token)
    set_active_user(username)
    
    console.print(f"[green]✅ Erfolgreich eingeloggt als '{username}'![/green]")
    console.print(f"[blue]📧 GitHub: {user_info.get('email', 'N/A')}[/blue]")

@go.command()
def status():
    """Zeigt den aktuellen Status an"""
    active_user = get_active_user()
    
    console.print("[bold blue]📊 grepo2 v3.7.3.2 Status[/bold blue]")
    console.print(f"Aktiver Benutzer: {active_user or 'Keiner'}")
    console.print(f"Config-Verzeichnis: {CONFIG_DIR}")
    console.print(f"GitHub-Verzeichnis: {GITHUB_DIR}")
    
    if active_user:
        user_config = load_user_config(active_user)
        if user_config:
            console.print(f"OpenRouter Token: {'Gesetzt' if user_config.get('openrouter_token') else 'Nicht gesetzt'}")
            console.print(f"AI-Model: {user_config.get('model', 'openai/gpt-4o')}")


# ─── Section XI: Main Entry Point (Originalverhalten wiederhergestellt) ─────────

if __name__ == "__main__":
    if not check_git_cli():
        sys.exit(1)

    # ─── Systemweite Installation/Version-Check ─────────────────────────────────────
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

    except Exception as e:
        console.print(f"[yellow]Manuell installieren: sudo cp {script_path} {target_path} ({e})[/yellow]")

    # ─── Startup (Originalverhalten wiederhergestellt) ───────────────────────────────
    while True:
        # CLI-Modus für "go" Befehle
        if len(sys.argv) > 1 and sys.argv[1] == "go":
            sys.argv.pop(1)
            click.cli = go
            go()
            break
        
        # TUI-Modus (Standard wenn ohne Argumente aufgerufen)
        user = get_active_user()
        if not user:
            if not tui_first_time_setup():
                sys.exit(0)
            user = get_active_user()
        
        # Starte TUI
        run_tui()
        break
