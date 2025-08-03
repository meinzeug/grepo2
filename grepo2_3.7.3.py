#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grepo2: Ein TUI- und CLI-Tool zur Vereinfachung der GitHub-Verwaltung.
Erweitert um autonome Code-Generierung mit Codex CLI und OpenRouter Integration.
Version 3.7.3 - Mit automatischem Issue-Closing und CHANGELOG.md Integration
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
from datetime import datetime
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


# Console-Objekt initialisieren
console = Console()


# ─── Section III: CHANGELOG Management ──────────────────────────────────────────

def write_to_changelog(repo_path: Path, message: str, log_type: str = "info"):
    """Schreibt alle Änderungen ins CHANGELOG.md"""
    changelog_file = repo_path / "CHANGELOG.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    emoji_map = {
        "info": "ℹ️",
        "success": "✅", 
        "error": "❌",
        "warning": "⚠️",
        "progress": "🔄",
        "file": "📄",
        "directory": "📁",
        "delete": "🗑️",
        "analysis": "🔍",
        "closed": "🎯"
    }
    
    emoji = emoji_map.get(log_type, "📝")
    entry = f"- **{timestamp}** {emoji} **{log_type.upper()}:** {message}\n"
    
    try:
        # Lese existierende Inhalte
        if changelog_file.exists():
            with open(changelog_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        else:
            existing_content = "# CHANGELOG\n\nAlle Änderungen an diesem Projekt werden in dieser Datei dokumentiert.\n\n"
        
        # Füge neuen Eintrag am Anfang ein (nach dem Header)
        lines = existing_content.split('\n')
        if len(lines) > 3:  # Header existiert
            lines.insert(4, entry.rstrip())
        else:
            lines.append(entry.rstrip())
        
        # Schreibe zurück
        with open(changelog_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            
    except Exception as e:
        console.print(f"[yellow]⚠ CHANGELOG-Fehler: {e}[/yellow]")


# ─── Section IV: GitHub API ─────────────────────────────────────────────────────

class GitHubAPI:
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"token {token}"})

    def get_user_info(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        try:
            resp = self.session.get("https://api.github.com/user", timeout=10)
            if resp.status_code == 200:
                return True, resp.json()
            else:
                return False, None
        except Exception:
            return False, None

    def list_repositories(self, username: str) -> List[Dict[str, Any]]:
        repos = []
        page = 1
        while True:
            try:
                resp = self.session.get(
                    f"https://api.github.com/users/{username}/repos",
                    params={"page": page, "per_page": 100, "sort": "updated"},
                    timeout=10
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                if not data:
                    break
                repos.extend(data)
                page += 1
            except Exception:
                break
        return repos

    def get_repository_details(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self.session.get(f"https://api.github.com/repos/{owner}/{repo}", timeout=10)
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None

    def create_repository(self, repo_name: str, description: str = "", private: bool = True) -> Tuple[bool, Optional[Dict[str, Any]]]:
        payload = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": True
        }
        try:
            resp = self.session.post("https://api.github.com/user/repos", json=payload, timeout=10)
            if resp.status_code == 201:
                return True, resp.json()
            else:
                return False, resp.json() if resp.text else None
        except Exception:
            return False, None

    def delete_repository(self, owner: str, repo: str) -> bool:
        try:
            resp = self.session.delete(f"https://api.github.com/repos/{owner}/{repo}", timeout=10)
            return resp.status_code == 204
        except Exception:
            return False

    def get_issues(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """Holt Issues eines Repositories"""
        try:
            resp = self.session.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                params={"state": state, "per_page": 100},
                timeout=10
            )
            return resp.json() if resp.status_code == 200 else []
        except Exception:
            return []

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """Holt Kommentare eines Issues"""
        try:
            resp = self.session.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments",
                timeout=10
            )
            return resp.json() if resp.status_code == 200 else []
        except Exception:
            return []

    def add_issue_comment(self, owner: str, repo: str, issue_number: int, comment: str) -> bool:
        """Fügt einen Kommentar zu einem Issue hinzu"""
        try:
            resp = self.session.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments",
                json={"body": comment},
                timeout=10
            )
            return resp.status_code == 201
        except Exception:
            return False

    def close_issue(self, owner: str, repo: str, issue_number: int, comment: str = None) -> bool:
        """Schließt ein Issue und fügt optional einen Kommentar hinzu"""
        try:
            # Füge erst einen Kommentar hinzu, falls gewünscht
            if comment:
                self.add_issue_comment(owner, repo, issue_number, comment)
            
            # Schließe das Issue
            resp = self.session.patch(
                f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}",
                json={"state": "closed"},
                timeout=10
            )
            return resp.status_code == 200
        except Exception:
            return False

    def get_repository_content(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """Holt Repository-Inhalte für besseren Kontext"""
        try:
            resp = self.session.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                timeout=10
            )
            return resp.json() if resp.status_code == 200 else []
        except Exception:
            return []


# ─── Section V: Local Git API ───────────────────────────────────────────────────

class LocalGitAPI:
    @staticmethod
    def is_git_repo(path: Path) -> bool:
        return (path / ".git").exists()

    @staticmethod
    def clone_repository(clone_url: str, target_path: Path, access_token: str = None) -> bool:
        if target_path.exists():
            return False
        
        # URL mit Token falls vorhanden
        if access_token and clone_url.startswith("https://github.com/"):
            clone_url = clone_url.replace("https://", f"https://{access_token}@")
        
        try:
            subprocess.run(["git", "clone", clone_url, str(target_path)], 
                         check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def get_repo_info(path: Path) -> Optional[Dict[str, str]]:
        if not LocalGitAPI.is_git_repo(path):
            return None
        
        try:
            # Remote URL
            result = subprocess.run(["git", "remote", "get-url", "origin"], 
                                  cwd=path, capture_output=True, text=True, check=True)
            remote_url = result.stdout.strip()
            
            # Branch
            result = subprocess.run(["git", "branch", "--show-current"], 
                                  cwd=path, capture_output=True, text=True, check=True)
            branch = result.stdout.strip()
            
            # Status
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  cwd=path, capture_output=True, text=True, check=True)
            status = "clean" if not result.stdout.strip() else "dirty"
            
            return {
                "remote_url": remote_url,
                "branch": branch,
                "status": status
            }
        except subprocess.CalledProcessError:
            return None

    @staticmethod
    def get_file_tree(path: Path, max_depth: int = 3) -> List[str]:
        """Erstellt einen Dateibaum für besseren Kontext"""
        tree = []
        
        def scan_dir(current_path: Path, depth: int, prefix: str = ""):
            if depth > max_depth:
                return
            
            try:
                items = sorted(current_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                for i, item in enumerate(items):
                    if item.name.startswith('.'):
                        continue
                    
                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    tree.append(f"{prefix}{current_prefix}{item.name}")
                    
                    if item.is_dir() and depth < max_depth:
                        next_prefix = prefix + ("    " if is_last else "│   ")
                        scan_dir(item, depth + 1, next_prefix)
            except PermissionError:
                pass
        
        scan_dir(path, 0)
        return tree

    @staticmethod
    def get_recent_commits(path: Path, count: int = 5) -> List[Dict[str, str]]:
        """Holt letzte Commits für Kontext"""
        try:
            result = subprocess.run([
                "git", "log", "--oneline", f"-{count}", "--pretty=format:%h|%s|%an|%ad", 
                "--date=short"
            ], cwd=path, capture_output=True, text=True, check=True)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) == 4:
                        commits.append({
                            "hash": parts[0],
                            "message": parts[1], 
                            "author": parts[2],
                            "date": parts[3]
                        })
            return commits
        except subprocess.CalledProcessError:
            return []


# ─── Section VI: Enhanced Codex Integration ────────────────────────────────────

class CodexIntegration:
    def __init__(self, openrouter_token: str, model: str = "openai/gpt-4o"):
        self.openrouter_token = openrouter_token
        self.model = model
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {openrouter_token}",
            "Content-Type": "application/json"
        })

    def _call_openrouter_api(self, messages: List[Dict[str, str]], max_tokens: int = 4000) -> Optional[str]:
        """Direkter API-Call an OpenRouter"""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            resp = self.session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                timeout=60
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                console.print(f"[red]OpenRouter API Fehler: {resp.status_code}[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]OpenRouter API Exception: {e}[/red]")
            return None

    def analyze_issue_completion(self, issue_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analysiert ob ein Issue als vollständig betrachtet werden kann"""
        
        # Erstelle Analyse-Prompt
        messages = [
            {"role": "system", "content": """Du bist ein Experte für Projektmanagement und Code-Analyse. 
Analysiere das gegebene GitHub Issue und den Kontext, um zu bestimmen:

1. COMPLETION_STATUS: Ist das Issue vollständig gelöst? (COMPLETE/INCOMPLETE/NEEDS_CLARIFICATION)
2. CONFIDENCE: Wie sicher bist du? (HIGH/MEDIUM/LOW)
3. REASONS: Warum triffst du diese Entscheidung?
4. NEXT_STEPS: Was sollte als nächstes getan werden?
5. SHOULD_CLOSE: Sollte das Issue geschlossen werden? (YES/NO)

Antworte im JSON-Format mit diesen exakten Schlüsseln."""},
            
            {"role": "user", "content": f"""
ISSUE ANALYSE:

**Issue Titel:** {issue_data.get('title', 'N/A')}
**Issue Body:** {issue_data.get('body', 'N/A')}
**Labels:** {', '.join([label.get('name', '') for label in issue_data.get('labels', [])])}
**State:** {issue_data.get('state', 'N/A')}

**Letzte Kommentare:**
{context.get('recent_comments', 'Keine Kommentare verfügbar')}

**Repository Kontext:**
{context.get('repo_context', 'Kein Repository-Kontext verfügbar')}

**Datei-Struktur:**
{context.get('file_tree', 'Keine Datei-Struktur verfügbar')}

Analysiere dieses Issue und gib deine Bewertung zurück.
"""}
        ]
        
        # API Call
        response = self._call_openrouter_api(messages, max_tokens=1000)
        
        if response:
            try:
                # Versuche JSON zu parsen
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                else:
                    json_str = response.strip()
                
                analysis = json.loads(json_str)
                
                # Validiere erwartete Felder
                required_fields = ['COMPLETION_STATUS', 'CONFIDENCE', 'REASONS', 'NEXT_STEPS', 'SHOULD_CLOSE']
                for field in required_fields:
                    if field not in analysis:
                        analysis[field] = 'UNKNOWN'
                
                return analysis
                
            except json.JSONDecodeError:
                console.print("[yellow]⚠ Konnte AI-Antwort nicht als JSON parsen[/yellow]")
                return {
                    'COMPLETION_STATUS': 'NEEDS_CLARIFICATION',
                    'CONFIDENCE': 'LOW', 
                    'REASONS': 'JSON Parse Error in AI Response',
                    'NEXT_STEPS': 'Manual review required',
                    'SHOULD_CLOSE': 'NO',
                    'raw_response': response
                }
        
        return {
            'COMPLETION_STATUS': 'ERROR',
            'CONFIDENCE': 'LOW',
            'REASONS': 'API call failed',
            'NEXT_STEPS': 'Retry analysis',
            'SHOULD_CLOSE': 'NO'
        }

    def execute_codex_for_issue(self, issue_data: Dict[str, Any], repo_path: Path, github_api: GitHubAPI) -> bool:
        """Führt Codex-Generierung für ein Issue aus"""
        try:
            # Sammle Repository-Kontext
            context = self._gather_repository_context(repo_path, github_api, issue_data)
            
            # Erstelle umfassenden Prompt
            prompt = self._create_comprehensive_prompt(issue_data, context)
            
            # Codex ausführen
            console.print("[cyan]🤖 Führe Codex-Generierung aus...[/cyan]")
            success = self._execute_codex_command(prompt, repo_path)
            
            if success:
                # Analysiere Vollständigkeit 
                analysis = self.analyze_issue_completion(issue_data, context)
                
                # Formatiere Analyse-Kommentar
                analysis_comment = self._format_analysis_comment(analysis, context)
                
                # Extrahiere Issue-Info
                owner, repo_name = self._extract_repo_info(repo_path)
                issue_number = issue_data.get('number')
                
                if owner and repo_name and issue_number:
                    # Schreibe ins CHANGELOG
                    write_to_changelog(
                        repo_path, 
                        f"Codex-Generierung für Issue #{issue_number}: {issue_data.get('title', 'N/A')}", 
                        "analysis"
                    )
                    
                    # Entscheide über Schließung
                    if analysis.get('SHOULD_CLOSE') == 'YES' and analysis.get('COMPLETION_STATUS') == 'COMPLETE':
                        # Issue schließen mit Kommentar
                        close_comment = f"{analysis_comment}\n\n🎯 **Issue automatisch geschlossen** - Analyse zeigt Vollständigkeit."
                        github_api.close_issue(owner, repo_name, issue_number, close_comment)
                        
                        write_to_changelog(
                            repo_path,
                            f"Issue #{issue_number} automatisch geschlossen: {analysis.get('REASONS', 'N/A')}",
                            "closed"
                        )
                        
                        console.print(f"[green]✅ Issue #{issue_number} automatisch geschlossen![/green]")
                    else:
                        # Nur Kommentar hinzufügen
                        github_api.add_issue_comment(owner, repo_name, issue_number, analysis_comment)
                        
                        write_to_changelog(
                            repo_path,
                            f"Analyse-Kommentar zu Issue #{issue_number} hinzugefügt",
                            "info"
                        )
                        
                        console.print(f"[blue]ℹ️ Analyse-Kommentar zu Issue #{issue_number} hinzugefügt[/blue]")
                
                return True
            
            return False
            
        except Exception as e:
            console.print(f"[red]❌ Fehler bei Codex-Ausführung: {e}[/red]")
            return False

    def _gather_repository_context(self, repo_path: Path, github_api: GitHubAPI, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sammelt umfassenden Repository-Kontext"""
        context = {}
        
        # Repository Info
        repo_info = LocalGitAPI.get_repo_info(repo_path)
        if repo_info:
            context['repo_info'] = repo_info
        
        # Datei-Struktur
        context['file_tree'] = '\n'.join(LocalGitAPI.get_file_tree(repo_path))
        
        # Letzte Commits
        context['recent_commits'] = LocalGitAPI.get_recent_commits(repo_path)
        
        # Issue-Kommentare
        owner, repo_name = self._extract_repo_info(repo_path)
        if owner and repo_name:
            comments = github_api.get_issue_comments(owner, repo_name, issue_data.get('number', 0))
            context['recent_comments'] = '\n'.join([f"- {c.get('body', '')[:200]}..." for c in comments[-3:]])
        
        return context

    def _create_comprehensive_prompt(self, issue_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Erstellt einen umfassenden Prompt für Codex"""
        
        prompt = f"""# GitHub Issue Code Generation Task

## Issue Details
**Title:** {issue_data.get('title', 'N/A')}
**Description:** {issue_data.get('body', 'N/A')}
**Labels:** {', '.join([label.get('name', '') for label in issue_data.get('labels', [])])}

## Repository Context
**File Structure:**
```
{context.get('file_tree', 'N/A')}
```

**Recent Comments:**
{context.get('recent_comments', 'No recent comments')}

**Recent Commits:**
{chr(10).join([f"- {c.get('hash', '')}: {c.get('message', '')}" for c in context.get('recent_commits', [])])}

## Task
Generate code to address this issue completely. Consider:
1. The existing codebase structure
2. The specific requirements in the issue
3. Best practices for the detected programming language
4. Comprehensive testing if applicable

Please generate production-ready code that fully resolves this issue.
"""
        return prompt

    def _execute_codex_command(self, prompt: str, repo_path: Path) -> bool:
        """Führt den Codex-Befehl aus"""
        try:
            # Erstelle temporäre Prompt-Datei
            prompt_file = repo_path / ".codex_prompt.tmp"
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            # Führe Codex aus
            result = subprocess.run([
                "codex", "generate", 
                "--prompt-file", str(prompt_file),
                "--apply"
            ], cwd=repo_path, capture_output=True, text=True, timeout=120)
            
            # Säubere temporäre Datei
            if prompt_file.exists():
                prompt_file.unlink()
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠ Codex-Timeout nach 2 Minuten[/yellow]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Codex-Ausführung fehlgeschlagen: {e}[/red]")
            return False

    def _format_analysis_comment(self, analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Formatiert die Analyse als GitHub-Kommentar"""
        
        status_emoji = {
            'COMPLETE': '✅',
            'INCOMPLETE': '🔄', 
            'NEEDS_CLARIFICATION': '❓',
            'ERROR': '❌'
        }
        
        confidence_emoji = {
            'HIGH': '🎯',
            'MEDIUM': '🎪',
            'LOW': '🎲'
        }
        
        status = analysis.get('COMPLETION_STATUS', 'UNKNOWN')
        confidence = analysis.get('CONFIDENCE', 'UNKNOWN')
        
        comment = f"""## 🤖 AI-Analyse des Issues

{status_emoji.get(status, '❓')} **Status:** {status}
{confidence_emoji.get(confidence, '❓')} **Konfidenz:** {confidence}

### 📝 Gründe:
{analysis.get('REASONS', 'Keine Gründe angegeben')}

### ⏭️ Nächste Schritte:
{analysis.get('NEXT_STEPS', 'Keine nächsten Schritte definiert')}

### 🔍 Repository-Kontext analysiert:
- Datei-Struktur: {len(context.get('file_tree', '').split(chr(10)))} Dateien/Ordner
- Letzte Commits: {len(context.get('recent_commits', []))} analysiert
- Kommentare: {len(context.get('recent_comments', '').split(chr(10)))} berücksichtigt

---
*Generiert von grepo2 v3.7.3 am {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        return comment

    def _extract_repo_info(self, repo_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """Extrahiert Owner und Repo-Name aus Repository"""
        try:
            repo_info = LocalGitAPI.get_repo_info(repo_path)
            if repo_info and 'remote_url' in repo_info:
                url = repo_info['remote_url']
                if 'github.com' in url:
                    # Extrahiere aus verschiedenen URL-Formaten
                    if url.endswith('.git'):
                        url = url[:-4]
                    
                    parts = url.split('/')
                    if len(parts) >= 2:
                        return parts[-2], parts[-1]
            
            return None, None
        except Exception:
            return None, None


# ─── Section VII: TUI Functions ──────────────────────────────────────────────────

def safe_curses_wrapper(func: Callable) -> Any:
    """Wrapper für sichere Curses-Ausführung"""
    try:
        return curses.wrapper(func)
    except KeyboardInterrupt:
        return None
    except Exception as e:
        print(f"TUI Fehler: {e}", file=sys.stderr)
        return None

def run_curses_menu(options: List[str], title: str = "Auswahl") -> Optional[int]:
    """Curses-basiertes Auswahlmenü"""
    def menu_impl(stdscr):
        curses.curs_set(0)  # Cursor ausblenden
        stdscr.clear()
        
        current_option = 0
        
        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            # Titel
            title_x = max(0, (width - len(title)) // 2)
            stdscr.addstr(1, title_x, title, curses.A_BOLD)
            stdscr.addstr(2, title_x, "=" * len(title), curses.A_BOLD)
            
            # Optionen
            start_y = 4
            for idx, option in enumerate(options):
                y = start_y + idx
                if y >= height - 2:
                    break
                
                x = 2
                if idx == current_option:
                    stdscr.addstr(y, x, f"> {option}", curses.A_REVERSE)
                else:
                    stdscr.addstr(y, x, f"  {option}")
            
            # Anweisungen
            instruction_y = height - 2
            stdscr.addstr(instruction_y, 2, "↑↓: Navigieren | Enter: Auswählen | q: Beenden")
            
            stdscr.refresh()
            
            # Input
            key = stdscr.getch()
            
            if key == curses.KEY_UP and current_option > 0:
                current_option -= 1
            elif key == curses.KEY_DOWN and current_option < len(options) - 1:
                current_option += 1
            elif key in (curses.KEY_ENTER, 10, 13):  # Enter
                return current_option
            elif key in (ord('q'), ord('Q'), 27):  # q oder ESC
                return None
    
    return safe_curses_wrapper(menu_impl)

def display_repository_info(repo_info: Dict[str, Any]):
    """Zeigt Repository-Informationen formatiert an"""
    table = Table(title="📁 Repository Details")
    table.add_column("Eigenschaft", style="cyan", no_wrap=True)
    table.add_column("Wert", style="white")
    
    # Standard Repository Informationen
    fields = [
        ("Name", repo_info.get("name", "N/A")),
        ("Vollständiger Name", repo_info.get("full_name", "N/A")),
        ("Beschreibung", repo_info.get("description") or "Keine Beschreibung"),
        ("Privat", "Ja" if repo_info.get("private") else "Nein"),
        ("Sprache", repo_info.get("language") or "Nicht erkannt"),
        ("Forks", str(repo_info.get("forks_count", 0))),
        ("Stars", str(repo_info.get("stargazers_count", 0))),
        ("Issues", str(repo_info.get("open_issues_count", 0))),
        ("Erstellt", repo_info.get("created_at", "N/A")[:10]),
        ("Letztes Update", repo_info.get("updated_at", "N/A")[:10]),
        ("Clone URL (HTTPS)", repo_info.get("clone_url", "N/A")),
        ("Clone URL (SSH)", repo_info.get("ssh_url", "N/A"))
    ]
    
    for field, value in fields:
        table.add_row(field, str(value))
    
    console.print(table)

def get_repo_selection_with_details(repos: List[Dict[str, Any]], github_api: GitHubAPI) -> Optional[Dict[str, Any]]:
    """Interaktive Repository-Auswahl mit Details"""
    if not repos:
        console.print("[red]❌ Keine Repositories gefunden![/red]")
        return None
    
    # Sortiere nach letztem Update
    repos_sorted = sorted(repos, key=lambda x: x.get("updated_at", ""), reverse=True)
    
    # Erstelle Optionen für Curses-Menü
    options = []
    for repo in repos_sorted:
        name = repo.get("name", "Unbekannt")
        desc = repo.get("description") or "Keine Beschreibung"
        lang = repo.get("language") or "?"
        private = "🔒" if repo.get("private") else "🔓"
        
        # Kürze Beschreibung
        if len(desc) > 50:
            desc = desc[:47] + "..."
        
        option = f"{private} {name} ({lang}) - {desc}"
        options.append(option)
    
    # Zeige Auswahlmenü
    console.print(f"\n[bold blue]📁 Repository auswählen ({len(repos_sorted)} verfügbar)[/bold blue]")
    selected_idx = run_curses_menu(options, "Repository auswählen")
    
    if selected_idx is not None:
        selected_repo = repos_sorted[selected_idx]
        
        # Hole detaillierte Informationen
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Lade Repository-Details...", total=None)
            
            owner = selected_repo.get("owner", {}).get("login")
            repo_name = selected_repo.get("name")
            
            if owner and repo_name:
                detailed_info = github_api.get_repository_details(owner, repo_name)
                if detailed_info:
                    selected_repo.update(detailed_info)
        
        return selected_repo
    
    return None

def tui_codex_generate():
    """TUI für Codex-Code-Generierung mit vollständiger Issue-Integration"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer gesetzt. Bitte zuerst einloggen.[/red]")
        return

    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden.[/red]")
        return

    # Prüfe auf OpenRouter Token
    openrouter_token = user_config.get("openrouter_token")
    if not openrouter_token:
        console.print("[yellow]⚠ Kein OpenRouter Token gefunden.[/yellow]")
        openrouter_token = getpass("OpenRouter API Token eingeben: ").strip()
        if not openrouter_token:
            console.print("[red]❌ OpenRouter Token erforderlich für Codex-Integration![/red]")
            return
        
        # Speichere Token
        update_user_config(active_user, openrouter_token=openrouter_token)
        console.print("[green]✓ OpenRouter Token gespeichert![/green]")

    # Prüfe Codex CLI
    if not check_codex_cli():
        return

    # GitHub API initialisieren
    github_api = GitHubAPI(user_config["token"])
    codex = CodexIntegration(openrouter_token, user_config.get("model", "openai/gpt-4o"))

    # Repository-Auswahl
    console.print("\n[bold blue]🔍 Lade Repositories...[/bold blue]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Repositories laden...", total=None)
        repos = github_api.list_repositories(active_user)

    if not repos:
        console.print("[red]❌ Keine Repositories gefunden![/red]")
        return

    selected_repo = get_repo_selection_with_details(repos, github_api)
    if not selected_repo:
        console.print("[yellow]⚪ Auswahl abgebrochen.[/yellow]")
        return

    # Repository-Details anzeigen
    display_repository_info(selected_repo)

    # Lokalen Pfad bestimmen/erstellen
    repo_name = selected_repo.get("name")
    repo_path = GITHUB_DIR / repo_name

    # Repository lokal verfügbar machen
    if not repo_path.exists():
        console.print(f"\n[yellow]📁 Repository '{repo_name}' nicht lokal gefunden.[/yellow]")
        clone_url = selected_repo.get("clone_url")
        
        if not clone_url:
            console.print("[red]❌ Keine Clone-URL gefunden![/red]")
            return

        console.print(f"[blue]📥 Klone Repository nach {repo_path}...[/blue]")
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Repository klonen...", total=None)
            success = LocalGitAPI.clone_repository(clone_url, repo_path, user_config["token"])

        if not success:
            console.print("[red]❌ Repository-Klonen fehlgeschlagen![/red]")
            return
        
        console.print("[green]✅ Repository erfolgreich geklont![/green]")

    # Issues laden und verarbeiten
    console.print(f"\n[bold blue]🔍 Lade Issues für {repo_name}...[/bold blue]")
    
    owner = selected_repo.get("owner", {}).get("login")
    if not owner:
        console.print("[red]❌ Repository-Owner nicht gefunden![/red]")
        return

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Issues laden...", total=None)
        open_issues = github_api.get_issues(owner, repo_name, "open")

    if not open_issues:
        console.print("[yellow]⚪ Keine offenen Issues gefunden.[/yellow]")
        return

    # Filtere "in-work" Issues (mit bestimmten Labels)
    work_labels = ["in-work", "in-progress", "working", "development", "coding"]
    in_work_issues = []
    
    for issue in open_issues:
        issue_labels = [label.get("name", "").lower() for label in issue.get("labels", [])]
        if any(work_label in issue_labels for work_label in work_labels):
            in_work_issues.append(issue)

    if not in_work_issues:
        console.print("[yellow]⚪ Keine Issues mit 'in-work' Labels gefunden.[/yellow]")
        console.print("Labels zum Markieren: in-work, in-progress, working, development, coding")
        return

    # Issue-Auswahl
    console.print(f"\n[bold green]🎯 {len(in_work_issues)} Issues in Bearbeitung gefunden![/bold green]")
    
    # Erstelle Optionen für Issue-Auswahl  
    issue_options = []
    for issue in in_work_issues:
        title = issue.get("title", "Unbekannt")
        number = issue.get("number", "?")
        labels = ", ".join([label.get("name", "") for label in issue.get("labels", [])])
        
        if len(title) > 60:
            title = title[:57] + "..."
        
        option = f"#{number}: {title} [{labels}]"
        issue_options.append(option)

    selected_issue_idx = run_curses_menu(issue_options, "Issue für Codex auswählen")
    
    if selected_issue_idx is None:
        console.print("[yellow]⚪ Issue-Auswahl abgebrochen.[/yellow]")
        return

    selected_issue = in_work_issues[selected_issue_idx]
    
    # Issue-Details anzeigen
    console.print(f"\n[bold blue]🎯 Gewähltes Issue:[/bold blue]")
    issue_panel = Panel(
        f"**Titel:** {selected_issue.get('title', 'N/A')}\n"
        f"**Nummer:** #{selected_issue.get('number', 'N/A')}\n"
        f"**Labels:** {', '.join([label.get('name', '') for label in selected_issue.get('labels', [])])}\n"
        f"**Beschreibung:** {selected_issue.get('body', 'Keine Beschreibung')[:200]}..."
    )
    console.print(issue_panel)

    # Codex für dieses Issue ausführen
    console.print("\n[bold cyan]🤖 Starte erweiterte Codex-Generierung...[/bold cyan]")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Codex-Generierung läuft...", total=None)
        success = codex.execute_codex_for_issue(selected_issue, repo_path, github_api)

    if success:
        console.print("\n[bold green]✅ Codex-Generierung erfolgreich abgeschlossen![/bold green]")
        console.print("[blue]ℹ️ Issue wurde analysiert und ggf. automatisch geschlossen.[/blue]")
        console.print(f"[cyan]📄 CHANGELOG.md wurde in {repo_path} aktualisiert.[/cyan]")
    else:
        console.print("\n[bold red]❌ Codex-Generierung fehlgeschlagen![/bold red]")
        write_to_changelog(repo_path, f"Codex-Generierung für Issue #{selected_issue.get('number')} fehlgeschlagen", "error")


# ─── Section VIII: Repository Management ────────────────────────────────────────

def tui_list_repositories():
    """Zeigt Repositories in einer TUI an"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer gesetzt.[/red]")
        return

    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden.[/red]")
        return

    github_api = GitHubAPI(user_config["token"])

    console.print(f"\n[bold blue]🔍 Lade Repositories für {active_user}...[/bold blue]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Repositories laden...", total=None)
        repos = github_api.list_repositories(active_user)

    if not repos:
        console.print("[red]❌ Keine Repositories gefunden![/red]")
        return

    selected_repo = get_repo_selection_with_details(repos, github_api)
    if selected_repo:
        display_repository_info(selected_repo)

def tui_create_repository():
    """TUI für Repository-Erstellung"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer gesetzt.[/red]")
        return

    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden.[/red]")
        return

    github_api = GitHubAPI(user_config["token"])

    console.print("\n[bold blue]📁 Neues Repository erstellen[/bold blue]")
    
    repo_name = console.input("[cyan]Repository-Name:[/cyan] ").strip()
    if not repo_name:
        console.print("[red]❌ Repository-Name ist erforderlich![/red]")
        return

    description = console.input("[cyan]Beschreibung (optional):[/cyan] ").strip()
    
    private_choice = console.input("[cyan]Privat? (j/N):[/cyan] ").strip().lower()
    private = private_choice in ['j', 'ja', 'y', 'yes']

    console.print(f"\n[yellow]📋 Repository-Einstellungen:[/yellow]")
    console.print(f"  Name: {repo_name}")
    console.print(f"  Beschreibung: {description or 'Keine'}")
    console.print(f"  Privat: {'Ja' if private else 'Nein'}")

    confirm = console.input("\n[cyan]Repository erstellen? (j/N):[/cyan] ").strip().lower()
    if confirm not in ['j', 'ja', 'y', 'yes']:
        console.print("[yellow]⚪ Erstellung abgebrochen.[/yellow]")
        return

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Repository erstellen...", total=None)
        success, result = github_api.create_repository(repo_name, description, private)

    if success:
        console.print("[green]✅ Repository erfolgreich erstellt![/green]")
        console.print(f"[blue]🔗 URL: {result.get('html_url', 'N/A')}[/blue]")
        
        # Frage nach lokalem Klonen
        clone_choice = console.input("[cyan]Lokal klonen? (j/N):[/cyan] ").strip().lower()
        if clone_choice in ['j', 'ja', 'y', 'yes']:
            clone_url = result.get("clone_url")
            if clone_url:
                local_path = GITHUB_DIR / repo_name
                console.print(f"[blue]📥 Klone nach {local_path}...[/blue]")
                
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                    task = progress.add_task("Repository klonen...", total=None)
                    clone_success = LocalGitAPI.clone_repository(clone_url, local_path, user_config["token"])
                
                if clone_success:
                    console.print("[green]✅ Repository erfolgreich geklont![/green]")
                else:
                    console.print("[red]❌ Klonen fehlgeschlagen![/red]")
    else:
        console.print("[red]❌ Repository-Erstellung fehlgeschlagen![/red]")
        if result:
            console.print(f"[red]Fehler: {result.get('message', 'Unbekannter Fehler')}[/red]")

def tui_delete_repository():
    """TUI für Repository-Löschung"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer gesetzt.[/red]")
        return

    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden.[/red]")
        return

    github_api = GitHubAPI(user_config["token"])

    console.print(f"\n[bold red]🗑️ Repository löschen für {active_user}[/bold red]")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Repositories laden...", total=None)
        repos = github_api.list_repositories(active_user)

    if not repos:
        console.print("[red]❌ Keine Repositories gefunden![/red]")
        return

    selected_repo = get_repo_selection_with_details(repos, github_api)
    if not selected_repo:
        console.print("[yellow]⚪ Auswahl abgebrochen.[/yellow]")
        return

    repo_name = selected_repo.get("name")
    console.print(f"\n[bold red]⚠️ WARNUNG: Repository '{repo_name}' wird unwiderruflich gelöscht![/bold red]")
    
    confirm1 = console.input(f"[red]Zum Bestätigen '{repo_name}' eingeben:[/red] ").strip()
    if confirm1 != repo_name:
        console.print("[yellow]⚪ Löschung abgebrochen (Name stimmt nicht überein).[/yellow]")
        return

    confirm2 = console.input("[red]Endgültig löschen? Tippe 'DELETE':[/red] ").strip()
    if confirm2 != "DELETE":
        console.print("[yellow]⚪ Löschung abgebrochen.[/yellow]")
        return

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Repository löschen...", total=None)
        success = github_api.delete_repository(active_user, repo_name)

    if success:
        console.print("[green]✅ Repository erfolgreich gelöscht![/green]")
        
        # Lokale Kopie löschen
        local_path = GITHUB_DIR / repo_name
        if local_path.exists():
            delete_local = console.input("[cyan]Lokale Kopie auch löschen? (j/N):[/cyan] ").strip().lower()
            if delete_local in ['j', 'ja', 'y', 'yes']:
                try:
                    shutil.rmtree(local_path)
                    console.print("[green]✅ Lokale Kopie gelöscht![/green]")
                except Exception as e:
                    console.print(f"[red]❌ Fehler beim Löschen der lokalen Kopie: {e}[/red]")
    else:
        console.print("[red]❌ Repository-Löschung fehlgeschlagen![/red]")


# ─── Section IX: User Management ────────────────────────────────────────────────

def tui_user_management():
    """TUI für Benutzerverwaltung"""
    while True:
        options = [
            "Neuen Benutzer anlegen",
            "Aktiven Benutzer wechseln", 
            "Benutzer konfigurieren",
            "Benutzer löschen",
            "Alle Benutzer anzeigen",
            "Zurück zum Hauptmenü"
        ]
        
        choice = run_curses_menu(options, "Benutzerverwaltung")
        
        if choice is None or choice == 5:  # Zurück
            break
        elif choice == 0:  # Neuer Benutzer
            tui_add_user()
        elif choice == 1:  # Benutzer wechseln
            tui_switch_user()
        elif choice == 2:  # Benutzer konfigurieren
            tui_configure_user()
        elif choice == 3:  # Benutzer löschen
            tui_delete_user()
        elif choice == 4:  # Alle anzeigen
            tui_list_users()

def tui_add_user():
    """TUI zum Hinzufügen eines neuen Benutzers"""
    console.print("\n[bold blue]👤 Neuen Benutzer anlegen[/bold blue]")
    
    username = console.input("[cyan]GitHub-Benutzername:[/cyan] ").strip()
    if not username:
        console.print("[red]❌ Benutzername ist erforderlich![/red]")
        return

    if load_user_config(username):
        console.print(f"[yellow]⚠ Benutzer '{username}' existiert bereits![/yellow]")
        return

    token = getpass("GitHub Personal Access Token: ").strip()
    if not token:
        console.print("[red]❌ Token ist erforderlich![/red]")
        return

    # Token validieren
    github_api = GitHubAPI(token)
    console.print("[blue]🔍 Validiere GitHub-Token...[/blue]")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Token validieren...", total=None)
        success, user_info = github_api.get_user_info()

    if not success:
        console.print("[red]❌ Token-Validierung fehlgeschlagen![/red]")
        return

    # OpenRouter Token (optional)
    openrouter_token = getpass("OpenRouter API Token (optional, für Codex): ").strip()
    model = "openai/gpt-4o"  # Default
    
    if openrouter_token:
        model_input = console.input(f"[cyan]AI-Model (default: {model}):[/cyan] ").strip()
        if model_input:
            model = model_input

    # Benutzer speichern
    save_user_config(username, token)
    if openrouter_token:
        update_user_config(username, openrouter_token=openrouter_token, model=model)

    console.print(f"[green]✅ Benutzer '{username}' erfolgreich angelegt![/green]")
    console.print(f"[blue]📧 GitHub: {user_info.get('email', 'N/A')}[/blue]")
    
    # Als aktiven Benutzer setzen
    set_active = console.input("[cyan]Als aktiven Benutzer setzen? (J/n):[/cyan] ").strip().lower()
    if set_active not in ['n', 'no', 'nein']:
        set_active_user(username)
        console.print(f"[green]✅ '{username}' ist jetzt der aktive Benutzer![/green]")

def tui_switch_user():
    """TUI zum Wechseln des aktiven Benutzers"""
    users = get_all_users()
    if not users:
        console.print("[red]❌ Keine Benutzer gefunden![/red]")
        return

    current_user = get_active_user()
    
    # Erstelle Optionen
    options = []
    for user in users:
        marker = " (aktiv)" if user == current_user else ""
        options.append(f"{user}{marker}")

    choice = run_curses_menu(options, "Benutzer wechseln")
    
    if choice is not None:
        selected_user = users[choice]
        if selected_user != current_user:
            set_active_user(selected_user)
            console.print(f"[green]✅ Aktiver Benutzer gewechselt zu '{selected_user}'![/green]")
        else:
            console.print("[blue]ℹ️ Benutzer war bereits aktiv.[/blue]")

def tui_configure_user():
    """TUI zur Benutzer-Konfiguration"""
    users = get_all_users()
    if not users:
        console.print("[red]❌ Keine Benutzer gefunden![/red]")
        return

    choice = run_curses_menu(users, "Benutzer konfigurieren")
    
    if choice is not None:
        username = users[choice]
        user_config = load_user_config(username)
        
        if not user_config:
            console.print("[red]❌ Benutzer-Konfiguration nicht gefunden![/red]")
            return

        console.print(f"\n[bold blue]⚙️ Konfiguration für '{username}'[/bold blue]")
        
        # GitHub Token
        change_token = console.input("[cyan]GitHub Token ändern? (j/N):[/cyan] ").strip().lower()
        if change_token in ['j', 'ja', 'y', 'yes']:
            new_token = getpass("Neues GitHub Token: ").strip()
            if new_token:
                update_user_config(username, token=new_token)
                console.print("[green]✅ GitHub Token aktualisiert![/green]")

        # OpenRouter Token
        current_openrouter = user_config.get("openrouter_token", "Nicht gesetzt")
        console.print(f"[blue]Aktueller OpenRouter Token: {'Gesetzt' if current_openrouter != 'Nicht gesetzt' else 'Nicht gesetzt'}[/blue]")
        
        change_openrouter = console.input("[cyan]OpenRouter Token ändern? (j/N):[/cyan] ").strip().lower()
        if change_openrouter in ['j', 'ja', 'y', 'yes']:
            new_openrouter = getpass("OpenRouter Token (leer = entfernen): ").strip()
            update_user_config(username, openrouter_token=new_openrouter or None)
            console.print("[green]✅ OpenRouter Token aktualisiert![/green]")

        # AI Model
        current_model = user_config.get("model", "openai/gpt-4o")
        console.print(f"[blue]Aktuelles AI-Model: {current_model}[/blue]")
        
        change_model = console.input("[cyan]AI-Model ändern? (j/N):[/cyan] ").strip().lower()
        if change_model in ['j', 'ja', 'y', 'yes']:
            new_model = console.input(f"[cyan]Neues Model (default: {current_model}):[/cyan] ").strip()
            if new_model:
                update_user_config(username, model=new_model)
                console.print("[green]✅ AI-Model aktualisiert![/green]")

def tui_delete_user():
    """TUI zum Löschen eines Benutzers"""
    users = get_all_users()
    if not users:
        console.print("[red]❌ Keine Benutzer gefunden![/red]")
        return

    choice = run_curses_menu(users, "Benutzer löschen")
    
    if choice is not None:
        username = users[choice]
        current_user = get_active_user()
        
        console.print(f"\n[bold red]🗑️ Benutzer '{username}' löschen[/bold red]")
        
        if username == current_user:
            console.print("[yellow]⚠️ Dies ist der aktive Benutzer![/yellow]")
        
        confirm = console.input(f"[red]'{username}' wirklich löschen? (j/N):[/red] ").strip().lower()
        if confirm in ['j', 'ja', 'y', 'yes']:
            delete_user_config(username)
            console.print(f"[green]✅ Benutzer '{username}' gelöscht![/green]")
            
            if username == current_user:
                remaining_users = get_all_users()
                if remaining_users:
                    set_active_user(remaining_users[0])
                    console.print(f"[blue]ℹ️ Aktiver Benutzer gewechselt zu '{remaining_users[0]}'[/blue]")
                else:
                    # Keinen aktiven Benutzer setzen
                    cfg = get_main_config()
                    cfg['active_user'] = None
                    save_main_config(cfg)
                    console.print("[yellow]⚠ Kein aktiver Benutzer mehr gesetzt.[/yellow]")

def tui_list_users():
    """TUI zur Anzeige aller Benutzer"""
    users = get_all_users()
    if not users:
        console.print("[red]❌ Keine Benutzer gefunden![/red]")
        return

    current_user = get_active_user()
    
    table = Table(title="👥 Registrierte Benutzer")
    table.add_column("Benutzername", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("OpenRouter", style="blue")
    table.add_column("AI-Model", style="magenta")
    
    for user in users:
        config = load_user_config(user)
        status = "Aktiv" if user == current_user else "Inaktiv"
        openrouter = "✓" if config and config.get("openrouter_token") else "✗"
        model = config.get("model", "N/A") if config else "N/A"
        
        table.add_row(user, status, openrouter, model)
    
    console.print(table)


# ─── Section X: Main Menu & CLI ──────────────────────────────────────────────────

def main_tui():
    """Hauptmenü der TUI"""
    if not check_git_cli():
        return

    while True:
        active_user = get_active_user()
        
        if active_user:
            title = f"grepo2 v3.7.3 - Aktiver Benutzer: {active_user}"
        else:
            title = "grepo2 v3.7.3 - Kein aktiver Benutzer"

        options = [
            "🤖 Codex: Code mit AI generieren",
            "📁 Repositories anzeigen",
            "➕ Neues Repository erstellen", 
            "🗑️ Repository löschen",
            "👤 Benutzerverwaltung",
            "❌ Beenden"
        ]

        choice = run_curses_menu(options, title)

        if choice is None or choice == 5:  # Beenden
            console.print("[green]👋 Auf Wiedersehen![/green]")
            break
        elif choice == 0:  # Codex
            tui_codex_generate()
        elif choice == 1:  # Repositories anzeigen
            tui_list_repositories()
        elif choice == 2:  # Neues Repository
            tui_create_repository()
        elif choice == 3:  # Repository löschen
            tui_delete_repository()
        elif choice == 4:  # Benutzerverwaltung
            tui_user_management()

        if choice is not None and choice != 5:
            console.input("\n[dim]Drücke Enter zum Fortfahren...[/dim]")


# ─── Section XI: Click CLI Commands ──────────────────────────────────────────────

@click.group()
def cli():
    """grepo2: GitHub-Repository-Management mit KI-Integration"""
    pass

@cli.command()
def tui():
    """Startet die Terminal-Benutzeroberfläche"""
    main_tui()

@cli.command()
@click.option('--username', prompt='GitHub Username', help='GitHub-Benutzername')
@click.option('--token', prompt='GitHub Token', hide_input=True, help='GitHub Personal Access Token')
def login(username, token):
    """Benutzer einloggen oder anlegen"""
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

@cli.command()
def logout():
    """Aktiven Benutzer abmelden"""
    active_user = get_active_user()
    if not active_user:
        console.print("[yellow]⚠ Kein aktiver Benutzer gesetzt.[/yellow]")
        return
    
    cfg = get_main_config()
    cfg['active_user'] = None
    save_main_config(cfg)
    
    console.print(f"[green]✅ Benutzer '{active_user}' abgemeldet![/green]")

@cli.command()
def status():
    """Zeigt den aktuellen Status an"""
    active_user = get_active_user()
    
    console.print("[bold blue]📊 grepo2 Status[/bold blue]")
    console.print(f"Aktiver Benutzer: {active_user or 'Keiner'}")
    console.print(f"Config-Verzeichnis: {CONFIG_DIR}")
    console.print(f"GitHub-Verzeichnis: {GITHUB_DIR}")
    
    if active_user:
        user_config = load_user_config(active_user)
        if user_config:
            console.print(f"OpenRouter Token: {'Gesetzt' if user_config.get('openrouter_token') else 'Nicht gesetzt'}")
            console.print(f"AI-Model: {user_config.get('model', 'openai/gpt-4o')}")

@cli.command()
def list_repos():
    """Listet alle Repositories auf"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer gesetzt.[/red]")
        return

    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden.[/red]")
        return

    github_api = GitHubAPI(user_config["token"])
    
    console.print(f"[blue]🔍 Lade Repositories für {active_user}...[/blue]")
    repos = github_api.list_repositories(active_user)
    
    if not repos:
        console.print("[red]❌ Keine Repositories gefunden![/red]")
        return

    table = Table(title=f"📁 Repositories von {active_user}")
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

@cli.command()
@click.argument('repo_name')
@click.option('--description', '-d', default='', help='Repository-Beschreibung')
@click.option('--private', is_flag=True, help='Privates Repository erstellen')
def create_repo(repo_name, description, private):
    """Erstellt ein neues Repository"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer gesetzt.[/red]")
        return

    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden.[/red]")
        return

    github_api = GitHubAPI(user_config["token"])
    
    console.print(f"[blue]📁 Erstelle Repository '{repo_name}'...[/blue]")
    success, result = github_api.create_repository(repo_name, description, private)
    
    if success:
        console.print("[green]✅ Repository erfolgreich erstellt![/green]")
        console.print(f"[blue]🔗 URL: {result.get('html_url', 'N/A')}[/blue]")
    else:
        console.print("[red]❌ Repository-Erstellung fehlgeschlagen![/red]")
        if result:
            console.print(f"[red]Fehler: {result.get('message', 'Unbekannter Fehler')}[/red]")

@cli.command()
@click.argument('repo_name')
@click.option('--force', is_flag=True, help='Löschen ohne Bestätigung erzwingen')
def delete_repo(repo_name, force):
    """Löscht ein Repository"""
    active_user = get_active_user()
    if not active_user:
        console.print("[red]❌ Kein aktiver Benutzer gesetzt.[/red]")
        return

    user_config = load_user_config(active_user)
    if not user_config:
        console.print("[red]❌ Benutzer-Konfiguration nicht gefunden.[/red]")
        return

    github_api = GitHubAPI(user_config["token"])
    
    if not force:
        console.print(f"[red]⚠️ WARNUNG: Repository '{repo_name}' wird unwiderruflich gelöscht![/red]")
        confirm = console.input(f"Zum Bestätigen '{repo_name}' eingeben: ").strip()
        if confirm != repo_name:
            console.print("[yellow]⚪ Löschung abgebrochen.[/yellow]")
            return

    console.print(f"[red]🗑️ Lösche Repository '{repo_name}'...[/red]")
    success = github_api.delete_repository(active_user, repo_name)
    
    if success:
        console.print("[green]✅ Repository erfolgreich gelöscht![/green]")
    else:
        console.print("[red]❌ Repository-Löschung fehlgeschlagen![/red]")

@cli.command()
def codex():
    """Startet Codex-Code-Generierung"""
    tui_codex_generate()

@cli.command()
def users():
    """Zeigt alle registrierten Benutzer"""
    users_list = get_all_users()
    if not users_list:
        console.print("[red]❌ Keine Benutzer gefunden![/red]")
        return

    current_user = get_active_user()
    
    table = Table(title="👥 Registrierte Benutzer")
    table.add_column("Benutzername", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("OpenRouter", style="blue")
    
    for user in users_list:
        config = load_user_config(user)
        status = "Aktiv" if user == current_user else "Inaktiv"
        openrouter = "✓" if config and config.get("openrouter_token") else "✗"
        
        table.add_row(user, status, openrouter)
    
    console.print(table)


# ─── Section XII: Main Entry Point ───────────────────────────────────────────────

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚪ Unterbrochen durch Benutzer.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Unerwarteter Fehler: {e}[/red]")
        import traceback
        console.print("[dim]" + traceback.format_exc() + "[/dim]")
