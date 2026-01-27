#!/bin/bash
# Script de déploiement pour VPS OVH

set -e

echo "🚀 Déploiement sur VPS OVH"
echo "================================"

# Mise à jour du système
echo "📦 Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# Installation de Python 3.11+
echo "🐍 Installation de Python..."
sudo apt install -y python3 python3-pip python3-venv

# Installation des dépendances système pour Playwright
echo "📦 Installation des dépendances système..."
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2

# Installation de PostgreSQL client
echo "🗄️  Installation du client PostgreSQL..."
sudo apt install -y postgresql-client

# Création du répertoire de travail
echo "📁 Création du répertoire de travail..."
mkdir -p ~/demarches_scraper
cd ~/demarches_scraper

# Création de l'environnement virtuel
echo "🔧 Création de l'environnement virtuel..."
python3 -m venv venv
source venv/bin/activate

# Installation des dépendances Python
echo "📦 Installation des dépendances Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Installation de Chromium pour Playwright
echo "🌐 Installation de Chromium..."
playwright install chromium
playwright install-deps chromium

# Configuration du fichier .env
echo "⚙️  Configuration de l'environnement..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  N'oubliez pas de configurer le fichier .env avec vos credentials !"
fi

# Configuration du cron job
echo "⏰ Configuration du cron job..."
CRON_CMD="0 */12 * * * cd ~/demarches_scraper && ~/demarches_scraper/venv/bin/python db_postgres.py >> ~/demarches_scraper/logs/scraper.log 2>&1"

# Créer le dossier logs
mkdir -p logs

# Ajouter au crontab si pas déjà présent
(crontab -l 2>/dev/null | grep -v "db_postgres.py"; echo "$CRON_CMD") | crontab -

echo ""
echo "✅ Déploiement terminé !"
echo ""
echo "📋 Prochaines étapes :"
echo "1. Configurez le fichier .env avec vos identifiants"
echo "2. Testez le script : ~/demarches_scraper/venv/bin/python db_postgres.py"
echo "3. Le cron job s'exécutera automatiquement toutes les 12h"
echo ""
echo "📝 Logs disponibles dans : ~/demarches_scraper/logs/scraper.log"
echo "🔍 Voir le cron : crontab -l"
