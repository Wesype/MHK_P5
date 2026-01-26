# Utiliser l'image officielle Playwright qui inclut Python et tous les navigateurs
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

# Définir le répertoire de travail
WORKDIR /app

# Copier le fichier requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Installer les navigateurs Playwright (déjà inclus dans l'image mais au cas où)
RUN playwright install chromium && \
    playwright install-deps chromium

# Copier le reste du code
COPY . .

# Créer le dossier downloads s'il n'existe pas
RUN mkdir -p downloads

# Exposer le port si nécessaire (pour une future API)
EXPOSE 8000

# Commande par défaut
CMD ["python", "db_postgres.py"]
