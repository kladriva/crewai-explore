from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import docker
from datetime import datetime, timezone

router = APIRouter(prefix="/api/containers", tags=["containers"])


class Port(BaseModel):
    private: int
    public: Optional[int] = None
    protocol: str = "tcp"


class ContainerInfo(BaseModel):
    id: str
    name: str
    image: str
    state: str             
    status: Optional[str]   
    ports: List[Port]
    first_deploy: str       
    last_start: Optional[str]


def _to_iso(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        # Docker donne un format ISO avec 'Z'
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return s


@router.get("", response_model=List[ContainerInfo])
def list_containers():
    """
    Recense tous les conteneurs Docker (all=True) avec:
    - ports publiés
    - état / statut
    - date de création (first_deploy)
    - dernier démarrage (last_start)
    """
    try:
        cli = docker.from_env()
        out: List[ContainerInfo] = []

        for c in cli.containers.list(all=True):
            attrs = c.attrs or {}
            state = (attrs.get("State") or {})
            net = (attrs.get("NetworkSettings") or {})
            pmap = net.get("Ports") or {}

            ports: List[Port] = []
            for key, mappings in pmap.items():
                # key ex: "80/tcp"
                priv_str, proto = key.split("/")
                private = int(priv_str)
                if mappings:
                    for m in mappings:
                        public = int(m.get("HostPort")) if m.get("HostPort") else None
                        ports.append(Port(private=private, public=public, protocol=proto))
                else:
                    ports.append(Port(private=private, public=None, protocol=proto))

            image = (attrs.get("Config") or {}).get("Image")
            if not image:
                # fallback: tag de l'image
                if c.image and c.image.tags:
                    image = c.image.tags[0]
                else:
                    image = getattr(c.image, "id", "unknown")

            out.append(ContainerInfo(
                id=c.short_id,
                name=c.name,
                image=str(image),
                state=state.get("Status", c.status or ""),
                status=state.get("Status", c.status or ""),
                ports=ports,
                first_deploy=_to_iso(attrs.get("Created")),
                last_start=_to_iso(state.get("StartedAt"))
            ))

        out.sort(key=lambda x: x.name.lower())
        return out

    except docker.errors.DockerException as e:
        msg = getattr(e, "explanation", None) or str(e)
        raise HTTPException(status_code=503, detail=f"Docker indisponible: {msg}")


@router.post("/{name}/start")
def start_container(name: str):
    cli = docker.from_env()
    try:
        c = cli.containers.get(name)
        c.start()
        return {"ok": True, "action": "start", "name": name}
    except docker.errors.NotFound:
        raise HTTPException(404, f"Conteneur {name} introuvable")
    except docker.errors.APIError as e:
        msg = getattr(e, "explanation", None) or str(e)
        raise HTTPException(500, f"Impossible de démarrer {name}: {msg}")


@router.post("/{name}/stop")
def stop_container(name: str):
    cli = docker.from_env()
    try:
        c = cli.containers.get(name)
        c.stop(timeout=10)
        return {"ok": True, "action": "stop", "name": name}
    except docker.errors.NotFound:
        raise HTTPException(404, f"Conteneur {name} introuvable")
    except docker.errors.APIError as e:
        msg = getattr(e, "explanation", None) or str(e)
        raise HTTPException(500, f"Impossible d'arrêter {name}: {msg}")
