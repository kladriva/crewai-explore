# app/tools/actions.py
import subprocess
import shutil
import shlex
import logging
import yaml

from pathlib import Path

from app.state.audit import log_action
from datetime import datetime


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
        
    def _fmt_time(self, s: str | None) -> str | None:
        if not s or s in ("", "0001-01-01T00:00:00Z"):
            return None
        # normalise en ISO court
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat(timespec="seconds")
        except Exception:
            return s

    def docker_list(self) -> list[dict]:
        """
        Liste tous les conteneurs avec infos utiles.
        """
        out: list[dict] = []
        try:
            import docker  # pip install docker
            cli = docker.from_env()
            for c in cli.containers.list(all=True):
                attrs = c.attrs or {}
                ports_txt: list[str] = []
                ports = attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
                for container_port, mappings in ports.items():
                    if mappings:
                        for m in mappings:
                            host_ip = m.get("HostIp", "0.0.0.0")
                            host_port = m.get("HostPort")
                            ports_txt.append(f"{host_ip}:{host_port}->{container_port}")
                    else:
                        # Port exposé sans mapping
                        ports_txt.append(f"{container_port}")

                img = (c.image.tags[0] if c.image and c.image.tags else (c.image.short_id if c.image else ""))
                created = self._fmt_time(attrs.get("Created"))
                started = self._fmt_time(attrs.get("State", {}).get("StartedAt"))
                status = (c.status or "").lower()
                state = "up" if status == "running" else "down"

                out.append({
                    "name": c.name,
                    "image": img,
                    "ports": ports_txt,
                    "first_deploy": created,
                    "last_start": started,
                    "state": state,
                })
        except Exception:
            logging.exception("docker_list failed")
        return out

    def docker_control(self, name: str, action: str) -> dict:
        """
        start/stop/restart un conteneur.
        """
        logger = logging.getLogger("actions")
        try:
            import docker
            cli = docker.from_env()
            c = cli.containers.get(name)
            if action == "start":
                c.start()
                msg = f"start container {name}"
            elif action == "stop":
                c.stop()
                msg = f"stop container {name}"
            elif action == "restart":
                c.restart()
                msg = f"restart container {name}"
            else:
                return {"ok": False, "error": f"action inconnue: {action}"}

            # journal d’audit si dispo
            try:
                from app.state.audit import log_action
                log_action(f"AUTO-ACTION {msg}")
            except Exception:
                pass

            logger.info(msg)
            return {"ok": True, "message": msg}
        except Exception as e:
            logger.exception("docker_control failed")
            return {"ok": False, "error": str(e)}

