import subprocess

def tail_journal(unit: str = None, lines: int = 200):
    cmd = ["journalctl", "-n", str(lines), "--no-pager", "-o", "short-iso"]
    if unit:
        cmd += ["-u", unit]
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return out.stdout.splitlines()