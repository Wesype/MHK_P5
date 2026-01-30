# API PDFs - Déploiement sur Railway

Cette API Flask permet de servir les PDFs stockés dans PostgreSQL via des URLs publiques.

## Déploiement sur Railway

### 1. Créer un nouveau service sur Railway

```bash
# Dans le dashboard Railway, créer un nouveau service "API PDFs"
# Lier le même repo GitHub
```

### 2. Variables d'environnement

Ajouter dans Railway :
```
DATABASE_URL=<votre_database_url_postgresql>
API_BASE_URL=https://votre-api.up.railway.app
PORT=5000
```

### 3. Configuration du service

Dans Railway, configurer :
- **Start Command**: `python api_pdfs.py`
- **Root Directory**: `/`
- **Port**: Le port sera automatiquement détecté

### 4. Déployer

Railway déploiera automatiquement l'API. Vous obtiendrez une URL type :
```
https://votre-api.up.railway.app
```

## Endpoints disponibles

### Santé de l'API
```
GET /health
```

### Récupérer un PDF
```
GET /pdf/<id>
```
Exemple : `https://votre-api.up.railway.app/pdf/123`

### Lister les PDFs d'un dossier
```
GET /dossier/<numero>/pdfs
```
Exemple : `https://votre-api.up.railway.app/dossier/28978093/pdfs`

Retourne :
```json
{
  "numero_dossier": "28978093",
  "nb_pdfs": 7,
  "pdfs": [
    {
      "id": 123,
      "nom_fichier": "passeport.pdf",
      "taille": 750396,
      "date_upload": "2026-01-30T10:00:00",
      "url": "https://votre-api.up.railway.app/pdf/123"
    }
  ]
}
```

## Utilisation dans le scraper

Le scraper sauvegarde automatiquement les PDFs dans PostgreSQL et ajoute les URLs dans le webhook :

```python
{
  "numero": "28978093",
  "type_changement": "nouveau",
  "nb_fichiers": 7,
  "pdf_urls": [
    {
      "nom": "passeport.pdf",
      "url": "https://votre-api.up.railway.app/pdf/123",
      "id": 123
    }
  ]
}
```

## Configuration du scraper

Ajouter dans votre `.env` :
```
API_BASE_URL=https://votre-api.up.railway.app
```

Le scraper utilisera cette URL pour générer les liens vers les PDFs.
