#!/bin/bash
# Script d'installation pour Railway (Railpack)

echo "📦 Installation de Chromium pour Playwright..."
playwright install chromium
playwright install-deps chromium

echo "✅ Chromium installé avec succès"
