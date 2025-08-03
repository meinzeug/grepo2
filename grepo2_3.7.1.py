#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grepo2: Ein TUI- und CLI-Tool zur Vereinfachung der GitHub-Verwaltung.
Erweitert um autonome Code-Generierung mit Codex CLI und OpenRouter Integration.
Version 3.7.1 - Mit wiederhergestellter curses-TUI Navigation
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


# Console-Objekt initialisieren
console = Console()


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


# Globale Objekte
git_api = LocalGitAPI()
gh_api  = None


# ─── Section IV: Wiederhergestellte Curses TUI ─────────────────────────────────

def run_curses_menu(title: str, options: List[Tuple[str,str]], context: str="") -> Optional[int]:
    """Originale curses-basierte TUI mit Pfeiltasten-Navigation"""
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
    console.clear()
    console.rule(f"[bold cyan]{title}")
    with console.status("Führe Befehl aus..."):
        ok, res = func(*args)
    if ok:
        console.print(res or "[green]✓ Erfolgreich[/green]")
    else:
        console.print(f"[bold red]Fehler:[/]\n{res}")
    input("\nDrücke Enter zum Fortfahren...")


# ─── Section V: TUI-Funktionen ──────────────────────────────────────────────────

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
        ("Zurück zum Hauptmenü", "")
    ]
    context = f"Aktiver Benutzer: {gh_api.username} | Repo: {repo_path.name}"
    while True:
        choice = run_curses_menu(f"Verwalte: {repo_path.name}", options, context)
        if choice is None or choice == 8:
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


# ─── Section VI: Codex Integration ──────────────────────────────────────────────

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

    def execute_codex(self, repo_path: Path, prompt: str) -> Tuple[bool, str]:
        """Führt Codex CLI mit dem gegebenen Prompt aus"""
        try:
            # Vereinfachte Codex-Ausführung für TUI-Kompatibilität
            cmd = [
                "codex", 
                "--full-auto",
                "--model", self.model,
                prompt
            ]
            
            console.print(f"[blue]Starte Codex mit Modell: {self.model}[/blue]")
            self.log_to_issue(f"Starte Codex-Ausführung mit Modell: {self.model}", "progress")
            
            start_time = time.time()
            
            proc = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 Minuten Timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if proc.returncode == 0:
                self.log_to_issue("Codex-Ausführung erfolgreich beendet", "success")
                return True, f"Codex erfolgreich ausgeführt in {duration:.1f}s\n\nOutput:\n{proc.stdout}"
            else:
                error_msg = f"Codex Fehler (Code {proc.returncode}):\n{proc.stderr}"
                self.log_to_issue(f"Codex-Fehler: {proc.stderr[:200]}...", "error")
                return False, error_msg
                
        except Exception as e:
            self.log_to_issue(f"Unerwarteter Fehler bei Codex-Ausführung: {e}", "error")
            return False, f"Unerwarteter Fehler: {e}"


def tui_codex_generate(repo_path: Path):
    """Vereinfachte Codex-Generierung für TUI"""
    console.clear()
    console.rule(f"[bold cyan]Code-Generierung: {repo_path.name}")

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

    # Einfacher Prompt-Input für TUI
    console.print(f"[blue]Verwende Modell: {model}[/blue]")
    console.print("\n[yellow]Entwicklungsauftrag eingeben:[/yellow]")
    prompt = input("Prompt: ").strip()
    
    if not prompt:
        console.print("[yellow]Abgebrochen[/yellow]")
        input()
        return

    # Initialisiere Codex Integration
    codex = CodexIntegration(ucfg)
    
    console.print("\n[bold green]🤖 Starte Code-Generierung...[/bold green]")
    
    success, result = codex.execute_codex(repo_path, prompt)
    
    if success:
        console.print(f"[green]✅ Codex erfolgreich ausgeführt![/green]")
        console.print("\n[bold]Ausgabe:[/bold]")
        console.print(Panel.fit(result, title="Codex Output", border_style="green"))
    else:
        console.print(f"[red]❌ Codex Fehler![/red]")
        console.print("\n[bold]Fehlerdetails:[/bold]")
        console.print(Panel.fit(result, title="Codex Error", border_style="red"))

    input("\n🔄 Drücke Enter, um zum Menü zurückzukehren...")


def tui_projekterstellung_menu(repo_path: Path):
    options = [
        ("🤖 Code generieren mit Codex",    "Vereinfachte KI-Code-Generierung"),
        ("Roadmap generieren",              "Erstelle eine technische Roadmap (falls implementiert)"),
        ("Projekt auf GitHub einrichten",   "Erstelle Issues auf GitHub (falls implementiert)"),
        ("Zurück",                          "Hauptmenü")
    ]
    while True:
        choice = run_curses_menu("Projekterstellung", options, f"Projekterstellung – {repo_path.name}")
        if choice is None or choice == 3:
            break
        elif choice == 0:
            tui_codex_generate(repo_path)
        elif choice == 1:
            console.clear()
            console.print("[yellow]Roadmap-Generierung noch nicht vollständig implementiert[/yellow]")
            input()
        elif choice == 2:
            console.clear()
            console.print("[yellow]GitHub-Projekt-Setup noch nicht implementiert[/yellow]")
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
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]Willkommen bei grepo2![/bold cyan]\n\n"
        "Dieses Tool vereinfacht die Verwaltung deiner GitHub-Repositories.\n"
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
    
    console.print("\n[bold green]Setup abgeschlossen![/bold green]")
    input("\nDrücke Enter, um zum Hauptmenü zu gelangen...")
    return True


def run_tui():
    """Hauptmenü mit wiederhergestellter Curses-Navigation"""
    while True:
        user = get_active_user()
        user_dir = GITHUB_DIR / user
        repos = sorted([d for d in user_dir.iterdir() if d.is_dir() and d.name != "backup"], key=lambda p: p.name)
        
        repo_opts = [(r.name, "") for r in repos]
        fixed_opts = [
            ("Benutzer wechseln",          "Profil wechseln"),
            ("Neues Repository erstellen",  "Erstelle neues Repo & klone"),
            ("Einstellungen",               "grepo2-Einstellungen"),
            ("Projekterstellung",           "Roadmap & Issues & Codex"),
            ("Exit",                        "Beenden")
        ]
        opts = repo_opts + fixed_opts
        
        sel = run_curses_menu("grepo2 Hauptmenü", opts, f"Aktiver Benutzer: {user}")
        
        if sel is None or sel == len(opts) - 1:
            return False
        
        if sel < len(repo_opts):
            # Repository verwalten
            tui_manage_repo(repos[sel])
        else:
            # Fixe Optionen
            idx = sel - len(repo_opts)
            if idx == 0:
                if tui_user_menu():
                    return True
            elif idx == 1:
                console.clear()
                console.print("[yellow]Noch nicht implementiert[/yellow]")
                input()
            elif idx == 2:
                tui_settings_menu()
            elif idx == 3:
                if not repos:
                    console.print("[yellow]Keine Repositories vorhanden[/yellow]")
                    input()
                else:
                    choice = run_curses_menu(
                        "Repo für Projekterstellung wählen",
                        [(r.name, "") for r in repos],
                        f"Aktiver Benutzer: {user}"
                    )
                    if choice is not None:
                        tui_projekterstellung_menu(repos[choice])


# ─── Section VII: Click CLI ──────────────────────────────────────────────────────

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


# ─── Section VIII: Hauptprogramm ─────────────────────────────────────────────────

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

    # ─── Startup ─────────────────────────────────────────────────────────────────────
    while True:
        # CLI-Modus
        if len(sys.argv) > 1 and sys.argv[1] == "go":
            sys.argv.pop(1)
            click.cli = go
            go()
            break
        
        # TUI-Modus
        user = get_active_user()
        if not user:
            if not tui_first_time_setup():
                sys.exit(0)
            user = get_active_user()
        
        cfg = load_user_config(user)
        gh_api = GitHubAPI(cfg["username"], cfg["token"])
        
        if not run_tui():
            break
