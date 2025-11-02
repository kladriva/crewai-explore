# 🚀 Quick Start Guide - VPS Monitoring AI

## Installation Rapide (10 minutes)

### 1. Prérequis
```bash
# Vérifier Python 3.9+
python --version

# Vérifier Docker
docker --version
```

### 2. Installation

```bash
# Cloner et naviguer
cd vps-monitoring-ai

# Copier configuration
cp .env.example .env

# IMPORTANT: Éditer .env et ajouter votre clé OpenAI
nano .env  # Ajouter: OPENAI_API_KEY=sk-your-key-here
```

### 3. Démarrage avec Docker (Recommandé)

```bash
# Lancer tout le stack
docker-compose up -d

# Vérifier les services
docker-compose ps

# Créer un utilisateur admin
docker-compose exec backend python -c "
from backend.database.models import User, UserRole
from backend.database.connection import get_db_context
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

with get_db_context() as db:
    admin = User(
        username='admin',
        email='admin@example.com',
        hashed_password=pwd_context.hash('admin123'),
        role=UserRole.ADMIN
    )
    db.add(admin)
    db.commit()
print('Admin créé: username=admin, password=admin123')
"
```

### 4. Accéder à l'Application

- **Frontend** : http://localhost:3000
- **API Docs** : http://localhost:8000/api/docs
- **Login** : admin / admin123

### 5. Configurer un Slave Node (Optionnel)

Sur un nœud slave :
```bash
# Installer dépendances
pip install psutil docker grpcio

# Copier le collector
scp slave/collector.py user@slave:/opt/monitoring/

# Configuration
export MASTER_HOST=<ip-du-master>
export NODE_NAME=slave-01

# Lancer
python /opt/monitoring/collector.py
```

## Test Rapide

### Tester l'API

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Simuler des métriques (test)
curl -X POST http://localhost:8000/api/v1/metrics/process \
  -H "Content-Type: application/json" \
  -d '{
    "node_name": "test-node",
    "node_ip": "192.168.1.100",
    "system_metrics": {
      "cpu_percent": 85.5,
      "memory_percent": 92.0,
      "disk_percent": 78.0,
      "memory_used_mb": 7500,
      "disk_used_gb": 150
    },
    "containers": []
  }'
```

### Observer les Agents CrewAI en Action

```bash
# Logs en temps réel
docker-compose logs -f backend

# Vous verrez les 4 agents travailler :
# Observer → Analyzer → Executor → Alerter
```

## Configuration Avancée

### Ajuster les Seuils

Éditez `.env` :
```env
CPU_CRITICAL_THRESHOLD=85
MEMORY_CRITICAL_THRESHOLD=90
DISK_CRITICAL_THRESHOLD=95
```

### Activer les Alertes

```env
# Email (Gmail)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

## Troubleshooting

### Backend ne démarre pas
```bash
# Vérifier les logs
docker-compose logs backend

# Recréer les containers
docker-compose down
docker-compose up -d --build
```

### Base de données vide
```bash
# Réinitialiser
docker-compose exec backend python -c "from backend.database.connection import init_database; init_database()"
```

### OpenAI Errors
```bash
# Vérifier la clé
docker-compose exec backend python -c "import os; print(os.getenv('OPENAI_API_KEY'))"

# Tester l'accès
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

## Prochaines Étapes

1. ✅ Lire le [README.md](README.md) complet
2. ✅ Ajouter des nœuds slaves
3. ✅ Configurer les alertes Email/Telegram
4. ✅ Entraîner les modèles ML avec vos données
5. ✅ Personnaliser les seuils et actions

## Support

- 📖 Documentation complète : [README.md](README.md)
- 🐛 Issues : GitHub Issues
- 💬 Questions : Ouvrir une discussion

---

**Félicitations ! Votre système de monitoring intelligent est opérationnel ! 🎉**
