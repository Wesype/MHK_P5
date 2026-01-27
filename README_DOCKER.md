# 🐳 Déploiement Docker

Ce guide explique comment déployer le scraper MHK avec Docker.

## 📋 Prérequis

- Docker installé
- Docker Compose installé
- Fichier `.env` configuré

## 🚀 Construction de l'image

```bash
docker build -t mhk-scraper .
```

## ⚙️ Configuration

1. Créez un fichier `.env` à la racine du projet :

```bash
cp .env.example .env
```

2. Éditez `.env` avec vos credentials :

```env
DATABASE_URL=postgresql://user:password@host:port/database
WEBHOOK_URL=https://votre-webhook.com/endpoint
IPROYAL_PROXY_SERVER=geo.iproyal.com:12321
IPROYAL_PROXY_USERNAME=votre_username
IPROYAL_PROXY_PASSWORD=votre_password_country-fr
```

## 🏃 Exécution

### Avec Docker Compose (recommandé)

```bash
docker-compose up -d
```

### Avec Docker directement

```bash
docker run -d \
  --name mhk-scraper \
  --env-file .env \
  --shm-size=2gb \
  -v $(pwd)/pdfs:/app/pdfs \
  mhk-scraper
```

## 📊 Logs

```bash
# Voir les logs en temps réel
docker-compose logs -f

# Ou avec Docker
docker logs -f mhk-scraper
```

## 🛑 Arrêt

```bash
# Avec Docker Compose
docker-compose down

# Ou avec Docker
docker stop mhk-scraper
docker rm mhk-scraper
```

## 🔄 Mise à jour

```bash
# Reconstruire l'image
docker-compose build

# Redémarrer le service
docker-compose up -d
```

## 🐛 Dépannage

### Le navigateur ne se lance pas

Augmentez la mémoire partagée :
```bash
docker run --shm-size=4gb ...
```

### Problème de permissions

Vérifiez que l'utilisateur dans le conteneur a les bonnes permissions :
```bash
docker exec -it mhk-scraper ls -la /app
```

## 📝 Notes

- L'image utilise `mcr.microsoft.com/playwright/python:v1.48.0-jammy`
- Playwright et tous les navigateurs sont pré-installés
- Le mode headless est automatiquement activé dans le conteneur
- Les PDFs sont sauvegardés dans `./pdfs` sur l'hôte
