# Utiliser l'image officielle Playwright avec Python
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Définir les locales et timezone français
ENV LANG=fr_FR.UTF-8 \
    LANGUAGE=fr_FR:fr \
    LC_ALL=fr_FR.UTF-8 \
    TZ=Europe/Paris \
    DEBIAN_FRONTEND=noninteractive

# Installer Xvfb, fonts et locales pour éviter la détection via canvas fingerprinting
RUN apt-get update && apt-get install -y \
    xvfb \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-color-emoji \
    fonts-noto-cjk \
    fonts-freefont-ttf \
    fontconfig \
    locales \
    tzdata \
    && locale-gen fr_FR.UTF-8 \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Installer les navigateurs Playwright
RUN playwright install chromium

# Copier tous les fichiers du projet
COPY . .

# Variables d'environnement (à surcharger au runtime)
ENV DATABASE_URL=""
ENV WEBHOOK_URL=""
ENV IPROYAL_PROXY_SERVER=""
ENV IPROYAL_PROXY_USERNAME=""
ENV IPROYAL_PROXY_PASSWORD=""

# L'image Playwright a déjà un utilisateur pwuser (UID 1000)
# On change juste les permissions du dossier /app
RUN chown -R pwuser:pwuser /app

# Créer le répertoire pour Xvfb avec les bonnes permissions
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix

USER pwuser

# Définir DISPLAY et variables d'environnement pour le navigateur
ENV DISPLAY=:99 \
    LANGUAGE=fr_FR:fr \
    LANG=fr_FR.UTF-8

# Rendre le script cron exécutable (si vous voulez l'utiliser)
# COPY cron_wrapper.sh /app/
# RUN chmod +x /app/cron_wrapper.sh

# Commande par défaut avec Xvfb (résolution réaliste pour éviter la détection)
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -ac +extension GLX +render -noreset & sleep 2 && python db_postgres.py"]