import subprocess
import shutil
from pathlib import Path
import yaml

class Actions:
    def __init__(self, rules_path="rules.yaml"):
        self.rules = {"allowed_services": [], "allowed_containers": [], "policies": []}
        try:
            p = Path(rules_path)
            if p.is_file():
                with open(p, "r") as f:
                    self.rules = yaml.safe_load(f) or self.rules
        except Exception:
            pass

    def restart_service(self, svc: str) -> str:
        if svc not in self.rules.get("allowed_services", []):
            return f"Service {svc} non autorisé"
        try:
            r = subprocess.run(["systemctl", "restart", svc], capture_output=True, text=True)
            return r.stdout or r.stderr or f"Restart {svc} exécuté."
        except FileNotFoundError:
            return "systemctl non disponible dans ce conteneur"
        except Exception as e:
            return f"Echec restart service {svc}: {e}"

    def cleanup_logs(self) -> str:
        subprocess.run(["journalctl", "--vacuum-time=7d"], check=False)
        return "journalctl vacuum (7d) exécuté."

    def cleanup_tmp(self) -> str:
        tmp = Path("/tmp")
        count = 0
        for p in tmp.iterdir():
            try:
                if p.is_file():
                    p.unlink(); count += 1
                elif p.is_dir():
                    shutil.rmtree(p, ignore_errors=True); count += 1
            except Exception:
                pass
        return f"Nettoyage /tmp terminé, éléments supprimés: {count}"
