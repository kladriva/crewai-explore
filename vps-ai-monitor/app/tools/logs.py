import os, subprocess

def tail_journal(unit: str = None, lines: int = 200):
    # Désactivé par défaut, active-le en mettant READ_JOURNAL=1 dans l'env
    if os.getenv("READ_JOURNAL", "0").lower() not in ("1", "true", "yes"):
        return []
    try:
        cmd = ["journalctl", "-n", str(lines), "--no-pager", "-o", "short-iso"]
        if unit:
            cmd += ["-u", unit]
        out = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return out.stdout.splitlines() if out.returncode == 0 else []
    except FileNotFoundError:
        # Pas de binaire journalctl dans l'image -> on ignore proprement
        return []