#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grepo2: Ein TUI- und CLI-Tool zur Vereinfachung der GitHub-Verwaltung.
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

CONFIG_DIR  = Path.home() / ".config" / "grepo2"
USERS_DIR   = CONFIG_DIR  / "users"
GITHUB_DIR  = Path.home()  / "github2"
CONFIG_FILE = CONFIG_DIR   / "config.json"
for p in (CONFIG_DIR, USERS_DIR, GITHUB_DIR):
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


console = Console()
git_api = LocalGitAPI()
gh_api  = None


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
    old_model = cfg.get("model", "")
    tok = input(f"Openrouter.ai Token [{old_tok}]: ") or old_tok
    model = input(f"Language Modell [{old_model}]: ") or old_model
    update_user_config(user, openrouter_token=tok, model=model)
    console.print("\n[green]✓ KI-Anbindung gespeichert![/green]")
    input()


def tui_settings_menu():
    opts = [
        ("GitHub PAT ändern", "Personal Access Token für GitHub"),
        ("KI-Anbindung",       "Openrouter.ai Token & Modell"),
        ("Zurück",             "Hauptmenü")
    ]
    while True:
        c = run_curses_menu("Einstellungen", opts, f"Aktiver Benutzer: {gh_api.username}")
        if c is None or c == 2:
            break
        if c == 0:
            tui_change_github_token()
        elif c == 1:
            tui_ki_anbindung()


def tui_generate_roadmap(repo_path: Path):
    console.clear()
    console.rule(f"[bold cyan]Roadmap generieren: {repo_path.name}")

    readme = repo_path / "README.md"
    if not readme.exists():
        console.print(f"[red]❌ Keine README.md in {repo_path} gefunden![/red]")
        input("Drücke Enter, um zurückzugehen…")
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
        "model":     ucfg.get("model", ""),
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
            console.print(f"[blue]Response headers: {resp.headers}[/blue]")
            resp.raise_for_status()
            buffer = ""
            for chunk in resp.iter_content(chunk_size=1024, decode_unicode=True):
                console.print(f"[grey]Chunk received ({len(chunk)} bytes)[/grey]")
                buffer += chunk
                while True:
                    idx = buffer.find("\n")
                    if idx == -1:
                        break
                    line = buffer[:idx].strip()
                    buffer = buffer[idx+1:]
                    console.print(f"[grey]Line: {line}[/grey]")
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


def ensure_codex_openrouter_config(openrouter_token: str):
    codex_dir = Path.home() / ".codex"
    typo      = codex_dir / "cofig.toml"
    codex_conf= codex_dir / "config.toml"
    codex_dir.mkdir(parents=True, exist_ok=True)
    if typo.exists() and not codex_conf.exists():
        typo.rename(codex_conf)

    content = codex_conf.read_text(encoding="utf-8") if codex_conf.exists() else ""
    provider_block = (
        '[model_providers.openrouter]\n'
        'name     = "OpenRouter"\n'
        'base_url = "https://openrouter.ai/api/v1"\n'
        'env_key  = "OPENROUTER_API_KEY"\n'
        'model_provider = "openrouter"\n'
    )
    if '[model_providers.openrouter]' not in content:
        content += "\n" + provider_block
    if f"# OPENROUTER_API_KEY=" not in content:
        content += f"\n# OPENROUTER_API_KEY={openrouter_token}\n"
    codex_conf.write_text(content, encoding="utf-8")

    os.environ["OPENAI_API_BASE"]    = "https://openrouter.ai/api/v1"
    os.environ["OPENAI_API_KEY"]     = openrouter_token
    os.environ["OPENROUTER_API_KEY"] = openrouter_token


def tui_codex_generate(repo_path: Path):
    console.clear()
    console.rule(f"[bold cyan]Code generieren mit Codex: {repo_path.name}")

    user = get_active_user()
    ucfg = load_user_config(user) or {}
    ortok = ucfg.get("openrouter_token", "")
    model = ucfg.get("model", "")
    if not ortok or not model:
        console.print("[red]❌ KI-Anbindung nicht konfiguriert![/red]")
        input("Enter…")
        return
    ensure_codex_openrouter_config(ortok)

    owner = gh_api.username
    repo = repo_path.name

    # 1) Wähle Issue mit Label "in-work", ansonsten ältestes offenes und setze "in-work"
    headers = {"Authorization": f"Bearer {load_user_config(owner)['token']}"}  
    resp_inwork = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        params={"state": "open", "labels": "in-work", "sort": "created", "direction": "asc", "per_page": 1},
        headers=headers
    )
    inwork_issues = resp_inwork.json() if resp_inwork.status_code == 200 else []
    if inwork_issues:
        issue = inwork_issues[0]
        console.print(f"[blue]Verwende in-work Issue #{issue['number']}[/blue]")
    else:
        resp_old = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            params={"state": "open", "sort": "created", "direction": "asc", "per_page": 1},
            headers=headers
        )
        if resp_old.status_code != 200 or not resp_old.json():
            console.print("[yellow]Keine offenen Issues gefunden.[/yellow]")
            input("Enter…")
            return
        issue = resp_old.json()[0]
        num = issue['number']
        lbls = [l['name'] for l in issue.get('labels', [])] + ["in-work"]
        patch = requests.patch(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{num}",
            headers={**headers, "Accept": "application/vnd.github+json"},
            json={"labels": lbls}
        )
        console.print(f"[blue]Setze Label 'in-work' auf Issue #{num}: HTTP {patch.status_code}[/blue]")

    num   = issue['number']
    title = issue['title']
    body  = issue.get('body', "")

    # 2) Lade Kommentare
    resp_comments = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{num}/comments",
        headers=headers
    )
    comments = []
    if resp_comments.status_code == 200:
        for c in resp_comments.json():
            comments.append(c.get('body', '').strip())
    console.print(f"[blue]Gefundene Kommentare: {len(comments)}[/blue]")

    # 3) Hole Codebase-Archiv von uithub.com
    codex_ctx = repo_path / "codex" / "codebase"
    if codex_ctx.exists():
        shutil.rmtree(codex_ctx)
    codex_ctx.mkdir(parents=True, exist_ok=True)
    archive_url = f"https://uithub.com/{owner}/{repo}/archive/main.tar.gz"
    cmd_fetch = f"curl -sSL {archive_url} | tar xz -C {codex_ctx}"
    console.print(f"[blue]Hole Codebase von: {archive_url}[/blue]")
    console.print(f"[blue]Rufe auf: {cmd_fetch}[/blue]")
    st, out = subprocess.getstatusoutput(cmd_fetch)
    console.print(f"[blue]Fetch output ({st}):\n{out}[/blue]")

    # 4) Erzeuge Prompt mit Issue, Kommentaren und Kontext
    prompt = (
        f"Bearbeite Issue #{num} '{title}':\n{body}\n\n"
        f"Bereits erledigte Kommentare:\n" + ("\n".join(comments) if comments else "<keine>") + "\n\n"
        "Arbeite nur außerhalb des 'codex/'-Verzeichnisses und generiere sinnvollen Code. "
        "Verwende dabei die gesamte aktuelle Codebase, die gerade heruntergeladen wurde."
    )

    console.print(f"[blue]Codex für Issue #{num}: {title}[/blue]")
    console.print(f"[blue]Prompt:[/blue]\n{prompt}")

    ver = subprocess.run(["codex", "--version"], capture_output=True, text=True)
    console.print(f"[blue]Codex Version: {ver.stdout.strip()}[/blue]")
    env = os.environ.copy()
    console.print(f"[blue]Env OPENAI_API_BASE={env.get('OPENAI_API_BASE')}[/blue]")
    console.print(f"[blue]Env OPENAI_API_KEY=<hidden>[/blue]")

    # 5) Starte Codex
    cmd = ["codex", "exec", "--full-auto", "--model", model, prompt]
    console.print(f"[blue]Ausführen:[/] {' '.join(cmd)}")
    console.print(f"[blue]Arbeitsverzeichnis:[/] {repo_path}")

    start = time.time()
    proc = subprocess.Popen(cmd, cwd=str(repo_path), env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        console.print("[red]✗ Codex TimeoutExpired, beendet[/red]")
    end = time.time()

    console.print(f"[cyan]-- stdout --\n{out}[/cyan]")
    console.print(f"[magenta]-- stderr --\n{err}[/magenta]")
    console.print(f"[blue]Rückgabecode: {proc.returncode} | Dauer: {end-start:.1f}s[/blue]")
    console.print("[green]✓ Codex-Durchlauf abgeschlossen[/green]")
    input()


def tui_projekterstellung_menu(repo_path: Path):
    options = [
        ("Roadmap generieren",            "Erstelle eine technische Roadmap"),
        ("Projekt auf GitHub einrichten", "Erstelle Issues auf GitHub"),
        ("Code generieren mit Codex",     "Lasse Codex automatisiert coden"),
        ("Zurück",                        "Hauptmenü")
    ]
    while True:
        choice = run_curses_menu("Projekterstellung", options, f"Projekterstellung – {repo_path.name}")
        if choice is None or choice == 3:
            break
        elif choice == 0:
            tui_generate_roadmap(repo_path)
        elif choice == 1:
            tui_setup_github_project(repo_path)
        elif choice == 2:
            tui_codex_generate(repo_path)


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
    console.print("\n[yellow]Schritt 2:[/yellow] Systemweite Installation (optional)")
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
            console.print("  sudo chmod +x {target_path}")
    console.print("\n[bold green]Setup abgeschlossen![/bold green]")
    input("\nDrücke Enter, um zum Hauptmenü zu gelangen...")
    return True


def run_tui():
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
            tui_manage_repo(repos[sel])
        else:
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

    # ─── Startup ───────────────────────────────────────────────────────────────────
    while True:
        if len(sys.argv) > 1 and sys.argv[1] == "go":
            sys.argv.pop(1)
            click.cli = go
            go()
            break
        user = get_active_user()
        if not user:
            if not tui_first_time_setup():
                sys.exit(0)
            user = get_active_user()
        cfg = load_user_config(user)
        gh_api = GitHubAPI(cfg["username"], cfg["token"])
        if not run_tui():
            break
