# app/tools/actions.py
import subprocess
import shutil
import shlex
import logging
from pathlib import Path
import yaml
from app.state.audit import log_action


class Actions:
    def __init__(self, rules_path: str = "rules.yaml"):
        """
        rules.yaml attendu, par ex.:
        allowed_services:
          - nginx
        allowed_containers:
          - web
          - redis
        allowed_cache:
          web:
            - /var/www/app/cache
          redis: []
        policies: []
        """
        self.logger = logging.getLogger("actions")

        # valeurs par défaut
        self.rules = {
            "allowed_services": [],
            "allowed_containers": [],
            "allowed_cache": {},
            "policies": [],
        }

        # charger le fichier si présent
        try:
            p = Path(rules_path)
            if p.is_file():
                with open(p, "r") as f:
                    loaded = yaml.safe_load(f) or {}
                    if isinstance(loaded, dict):
                        self.rules.update(loaded)
        except Exception as e:
            self.logger.warning("Impossible de charger %s: %s", rules_path, e)

        # alias pratiques
        self.allowed_services = list(self.rules.get("allowed_services", []))
        self.allowed_containers = list(self.rules.get("allowed_containers", []))
        self.allowed_cache = dict(self.rules.get("allowed_cache", {}))

    # -----------------------
    # Services (systemd)
    # -----------------------
    def restart_service(self, svc: str) -> str:
        if svc not in self.allowed_services:
            msg = f"Service {svc} non autorisé"
            log_action("auto-restart-service", svc, "refusé (non autorisé)", {"message": msg})
            return msg

        try:
            r = subprocess.run(
                ["systemctl", "restart", svc],
                capture_output=True, text=True
            )
            result = f"systemctl restart {svc}: rc={r.returncode}"
            payload = {"stdout": (r.stdout or "").strip(), "stderr": (r.stderr or "").strip()}
            log_action("auto-restart-service", svc, result, payload)
            return payload["stdout"] or payload["stderr"] or result
        except FileNotFoundError:
            msg = "systemctl non disponible dans ce conteneur"
            log_action("auto-restart-service", svc, msg, {})
            return msg
        except Exception as e:
            msg = f"Echec restart service {svc}: {e}"
            log_action("auto-restart-service", svc, msg, {})
            return msg

    # -----------------------
    # Maintenance hôte
    # -----------------------
    def cleanup_logs(self) -> str:
        try:
            r = subprocess.run(
                ["journalctl", "--vacuum-time=7d"],
                capture_output=True, text=True, check=False
            )
            result = f"journalctl vacuum 7d: rc={r.returncode}"
            payload = {"stdout": (r.stdout or "").strip(), "stderr": (r.stderr or "").strip()}
            log_action("auto-cleanup-logs", "journalctl", result, payload)
            return payload["stdout"] or payload["stderr"] or result
        except FileNotFoundError:
            msg = "journalctl indisponible"
            log_action("auto-cleanup-logs", "journalctl", msg, {})
            return msg
        except Exception as e:
            msg = f"cleanup_logs échec: {e}"
            log_action("auto-cleanup-logs", "journalctl", msg, {})
            return msg

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
                # on ignore les erreurs unitaires
                pass
        msg = f"Nettoyage /tmp terminé, éléments supprimés: {count}"
        log_action("auto-cleanup-tmp", "/tmp", msg, {"deleted_count": count})
        return msg

    # -----------------------
    # Cache dans conteneur Docker
    # -----------------------
    def clear_cache(self, container: str, path: str) -> dict:
        """
        Purge un répertoire de cache *dans* un conteneur Docker autorisé.
        Sécurisé par whitelist: container + path doivent être autorisés.
        """
        
        if container not in self.allowed_containers:
            msg = f"clear_cache refusé: conteneur '{container}' non autorisé"
            self.logger.warning(msg)
            log_action("auto-clear-cache", container, "refusé (container non autorisé)", {"path": path})
            return {"ok": False, "error": msg}

        allowed_paths = set(self.allowed_cache.get(container, []))
        if path not in allowed_paths:
            msg = f"clear_cache refusé: chemin '{path}' non autorisé pour {container}"
            self.logger.warning(msg)
            log_action("auto-clear-cache", container, "refusé (path non autorisé)", {"path": path})
            return {"ok": False, "error": msg}

        # commande sûre: supprimer uniquement le contenu du dossier (pas le dossier)
        inner = f"test -d {shlex.quote(path)} && find {shlex.quote(path)} -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +"
        try:
            r = subprocess.run(
                ["docker", "exec", container, "sh", "-lc", inner],
                capture_output=True, text=True, check=False
            )
            payload = {"stdout": (r.stdout or "").strip(), "stderr": (r.stderr or "").strip(), "path": path}
            if r.returncode == 0:
                result = f"clear_cache ok: rc=0"
                self.logger.info("AUTO-ACTION clear_cache: %s:%s", container, path)
                log_action("auto-clear-cache", container, result, payload)
                return {"ok": True, "action": f"clear_cache {container}:{path}", **payload}
            else:
                result = f"clear_cache échec: rc={r.returncode}"
                self.logger.error("clear_cache échec (%s:%s) rc=%s stderr=%s",
                                  container, path, r.returncode, payload["stderr"])
                log_action("auto-clear-cache", container, result, payload)
                return {"ok": False, "error": payload["stderr"]}
        except Exception as e:
            msg = f"clear_cache exception: {e}"
            self.logger.exception("clear_cache exception")
            log_action("auto-clear-cache", container, msg, {"path": path})
            return {"ok": False, "error": str(e)}

