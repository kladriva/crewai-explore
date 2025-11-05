#!/usr/bin/env bash
set -euo pipefail

# Paramètres à adapter
NODE_NAME="en-data"
MASTER_HOST="109.199.102.139"
MASTER_PORT="50051"
MASTER_USER="root"
MASTER_SCP_PATH="/root/projects/crewai-explore/vps-monitoring-ai/slave/collector.py"
DOCKER_DISABLED="0"   # mets 1 si pas de Docker sur le nœud

# Préparation
sudo mkdir -p /opt/monitoring
sudo chown "$USER":"$USER" /opt/monitoring
cd /opt/monitoring

# Copier le collector depuis le master (ou remplace par curl si tu as une URL)
scp ${MASTER_USER}@${MASTER_HOST}:${MASTER_SCP_PATH} /opt/monitoring/collector.py

# Environnement Python
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --no-cache-dir psutil docker

# Service systemd
sudo tee /etc/systemd/system/vps-collector.service >/dev/null <<EOF
[Unit]
Description=VPS Monitoring Metrics Collector
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=/opt/monitoring
Environment=NODE_NAME=${NODE_NAME}
Environment=MASTER_HOST=${MASTER_HOST}
Environment=MASTER_PORT=${MASTER_PORT}
Environment=COLLECTION_INTERVAL=5
Environment=HEARTBEAT_INTERVAL=30
Environment=DOCKER_DISABLED=${DOCKER_DISABLED}
ExecStart=/opt/monitoring/.venv/bin/python /opt/monitoring/collector.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Démarrage
sudo systemctl daemon-reload
sudo systemctl enable --now vps-collector
sudo systemctl status vps-collector --no-pager