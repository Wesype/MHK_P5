#!/bin/bash

# Script pour configurer le cron job du scraper

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
SCRIPT_PATH="$SCRIPT_DIR/db_postgres.py"
LOG_FILE="/tmp/demarches_scraper.log"

# Créer l'entrée cron
CRON_ENTRY="0 */12 * * * cd $SCRIPT_DIR && $VENV_PYTHON $SCRIPT_PATH >> $LOG_FILE 2>&1"

# Vérifier si l'entrée existe déjà
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "❌ Le cron job existe déjà"
    echo "Pour le supprimer : crontab -e"
else
    # Ajouter l'entrée au crontab
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "✅ Cron job ajouté avec succès !"
    echo "📅 Le script s'exécutera toutes les 12 heures"
    echo "📝 Logs disponibles dans : $LOG_FILE"
    echo ""
    echo "Pour voir le cron actuel : crontab -l"
    echo "Pour modifier le cron : crontab -e"
fi
