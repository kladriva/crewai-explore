import subprocess
import shutil
import subprocess
import shlex
import logging
from pathlib import Path
import yaml

class Actions:
    def __init__(self, rules_path="rules.yaml"):
        self.rules = {"allowed_services": [], "allowed_containers": [], "policies": []}
        self.allowed_cache = self.rules.get("allowed_cache", {})
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
    
    def clear_cache(self, container: str, path: str) -> dict:
        """
        Purge un répertoire de cache *dans* un conteneur Docker autorisé.
        Sécurisé par whitelist: container + path doivent être autorisés.
        """
        logger = logging.getLogger("actions")
        # contrôles de sécurité
        if container not in self.allowed_containers:
            msg = f"clear_cache refusé: conteneur '{container}' non autorisé"
            logger.warning(msg)
            return {"ok": False, "error": msg}

        allowed_paths = set(self.allowed_cache.get(container, []))
        if path not in allowed_paths:
            msg = f"clear_cache refusé: chemin '{path}' non autorisé pour {container}"
            logger.warning(msg)
            return {"ok": False, "error": msg}

        # commande sûre: on ne supprime que le contenu du dossier (pas le dossier)
        cmd = f"sh -lc 'test -d {shlex.quote(path)} && find {shlex.quote(path)} -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +'"
        try:
            r = subprocess.run(
                ["docker", "exec", container, "sh", "-lc", cmd],
                capture_output=True, text=True, check=False
            )
            ok = (r.returncode == 0)
            if ok:
                logger.info(f"AUTO-ACTION clear_cache: {container}:{path}")
                return {"ok": True, "action": f"clear_cache {container}:{path}", "stdout": r.stdout.strip()}
            else:
                logger.error(f"clear_cache échec ({container}:{path}) rc={r.returncode} stderr={r.stderr.strip()}")
                return {"ok": False, "error": r.stderr.strip()}
        except Exception as e:
            logger.exception("clear_cache exception")
            return {"ok": False, "error": str(e)}

