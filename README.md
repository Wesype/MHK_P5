# Scraper Démarches Simplifiées avec Docker

## 🚀 Déploiement sur Railway

### Déploiement super simple

1. **Sur Railway :**
   - Créer un nouveau projet
   - Déployer depuis GitHub
   - Ajouter un service PostgreSQL (Railway injecte automatiquement les variables)
   - C'est tout ! Railway utilise le `Dockerfile` et `railway.json`

### Variables d'environnement sur Railway

Railway injecte automatiquement les variables PostgreSQL :
- `DATABASE_URL` - URL complète de connexion
- `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`

Ajouter manuellement :
- `WEBHOOK_URL` - URL du webhook n8n

### Test en local avec Docker

1. **Construire et lancer**
   ```bash
   docker-compose up --build
   ```
   
   Cela lance automatiquement PostgreSQL local + l'app

### Commandes utiles

```bash
# Voir les logs
docker-compose logs -f app

# Exécuter le scraping manuellement
docker-compose exec app python db_postgres.py

# Télécharger les PDFs d'un dossier
docker-compose exec app python download_pdfs.py 21978078

# Envoyer au webhook
docker-compose exec app python send_webhook.py

# Arrêter les containers
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v
```

### Architecture

```
projet/
├── Dockerfile              # Image Docker avec Playwright
├── docker-compose.yml      # Orchestration des services
├── requirements.txt        # Dépendances Python
├── .env                   # Variables d'environnement (non versionné)
├── db_postgres.py         # Script principal avec PostgreSQL
├── download_pdfs.py       # Téléchargement des PDFs
├── send_webhook.py        # Envoi au webhook n8n
└── downloads/            # Dossier des PDFs (volume Docker)
```

### Fonctionnalités

- ✅ Scraping automatique avec Playwright/crawl4ai
- ✅ Base de données PostgreSQL sur Railway
- ✅ Détection automatique des changements
- ✅ Téléchargement des PDFs
- ✅ Envoi des changements au webhook n8n
- ✅ Export CSV des dossiers complets

### Variables d'environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `POSTGRES_HOST` | Hôte PostgreSQL Railway | `roundhouse.proxy.rlwy.net` |
| `POSTGRES_PORT` | Port PostgreSQL | `5432` |
| `POSTGRES_DB` | Nom de la base | `railway` |
| `POSTGRES_USER` | Utilisateur PostgreSQL | `postgres` |
| `POSTGRES_PASSWORD` | Mot de passe | `your-password` |
| `WEBHOOK_URL` | URL du webhook n8n | `https://n8n.wesype.com/webhook-test/...` |

### Déploiement sur Railway

1. Créer un nouveau projet sur Railway
2. Ajouter PostgreSQL depuis le marketplace
3. Récupérer les credentials dans les variables
4. Configurer le `.env` avec ces informations
5. Lancer le container Docker localement ou déployer sur Railway

### Support

Pour tout problème, vérifier :
- Les logs Docker : `docker-compose logs -f`
- La connexion PostgreSQL : credentials Railway corrects
- L'accès réseau : le container peut accéder à internet
