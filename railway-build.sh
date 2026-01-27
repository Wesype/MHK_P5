#!/bin/bash
set -e

echo "📦 Installation des dépendances Python..."
pip install -r requirements.txt

echo "📦 Installation de Chromium pour Playwright..."
playwright install chromium
playwright install-deps chromium

echo "✅ Build terminé avec succès"
