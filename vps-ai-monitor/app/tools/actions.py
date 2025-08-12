# app/tools/actions.py
import subprocess
import shutil
from pathlib import Path
import yaml

class Actions:
    def __init__(self, rules_path="rules.yaml"):
        with open(rules_path, "r") as f:
            self.rules = yaml.safe_load(f)

    def restart_service(self, svc: str) -> str:
        if svc not in self.rules.get("allowed_services", []):
            return f"Service {svc} non autorisé"
        r = subprocess.run(["sudo", "systemctl", "restart", svc], capture_output=True, text=True)
        return r.stdout or r.stderr or f"Restart {svc} exécuté."

    def cleanup_logs(self) -> str:
        # exemple: purge journald vieux logs
        subprocess.run(["sudo", "journalctl", "--vacuum-time=7d"], check=False)
        return "journalctl vacuum (7d) exécuté."

    def cleanup_tmp(self) -> str:
        tmp = Path("/tmp")
        count = 0
        for p in tmp.iterdir():
            try:
                if p.is_file():
                    p.unlink()
                    count += 1
                elif p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                    count += 1
            except Exception:
                pass
        return f"Nettoyage /tmp terminé, éléments supprimés: {count}"
