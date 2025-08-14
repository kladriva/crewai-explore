FROM python:3.11-slim

# On travaille hors du dossier "app" pour traiter "app" comme un package racine
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Ajoute /workspace au PYTHONPATH pour que "import app.*" fonctionne
ENV PYTHONPATH=/workspace

# Copie le contenu de app/ dans /workspace/app
COPY . /workspace/app

# Installe les deps depuis /workspace/app/requirements.txt
RUN pip install --no-cache-dir -r /workspace/app/requirements.txt

# Lance le module "app.crew" (et pas un fichier)
CMD ["/bin/sh","-lc","python -m app.crew & exec uvicorn app.api:app --host 0.0.0.0"]
