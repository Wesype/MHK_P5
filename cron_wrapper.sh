#!/bin/bash
# Wrapper pour exécuter le scraping en boucle avec délai

while true; do
    echo "🚀 Démarrage du scraping à $(date)"
    python db_postgres.py
    echo "✅ Scraping terminé à $(date)"
    echo "⏳ Attente de 1 heure avant le prochain scraping..."
    sleep 3600  # 1 heure
done
