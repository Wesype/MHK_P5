# Déploiement sur VPS OVH

## 📋 Prérequis

- VPS OVH avec Ubuntu 22.04 ou Debian 11+
- Accès SSH root ou sudo
- Base de données PostgreSQL (Railway ou autre)

## 🚀 Installation

### 1. Connexion au VPS

```bash
ssh root@votre-ip-ovh
```

### 2. Cloner le projet

```bash
cd ~
git clone https://github.com/Wesype/MHK_P5.git demarches_scraper
cd demarches_scraper
```

### 3. Exécuter le script de déploiement

```bash
chmod +x deploy_ovh.sh
./deploy_ovh.sh
```

### 4. Configurer les variables d'environnement

Éditez le fichier `.env` :

```bash
nano .env
```

Remplissez avec vos identifiants :

```env
# Identifiants du site
LOGIN_EMAIL=votre.email@example.com
LOGIN_PASSWORD=votre_mot_de_passe

# PostgreSQL (Railway ou autre)
DATABASE_URL=postgresql://user:password@host:port/database
```

### 5. Test manuel

```bash
cd ~/demarches_scraper
source venv/bin/activate
python db_postgres.py
```

Vous devriez voir :
- ✅ Connexion effectuée
- 📊 en-cours: 43 pages (ou votre nombre de pages)
- Scraping des dossiers...

## ⏰ Cron Job

Le script s'exécute automatiquement toutes les 12 heures.

### Vérifier le cron

```bash
crontab -l
```

### Modifier le cron

```bash
crontab -e
```

### Voir les logs

```bash
tail -f ~/demarches_scraper/logs/scraper.log
```

## 🔧 Maintenance

### Mettre à jour le code

```bash
cd ~/demarches_scraper
git pull
source venv/bin/activate
pip install -r requirements.txt
```

### Redémarrer le cron

Le cron redémarre automatiquement. Pour forcer une exécution :

```bash
cd ~/demarches_scraper
source venv/bin/activate
python db_postgres.py
```

## 🐛 Dépannage

### Chromium ne se lance pas

```bash
cd ~/demarches_scraper
source venv/bin/activate
playwright install-deps chromium
```

### Erreur de connexion PostgreSQL

Vérifiez que l'IP du VPS est autorisée dans Railway (Settings > Networking > Allowlist).

### Logs du cron

```bash
grep CRON /var/log/syslog
```

## 📊 Monitoring

### Vérifier que le script tourne

```bash
ps aux | grep python
```

### Vérifier la base de données

```bash
# Depuis le VPS
psql $DATABASE_URL -c "SELECT COUNT(*) FROM dossiers;"
```

## 🔐 Sécurité

- Changez le mot de passe root du VPS
- Configurez un firewall (ufw)
- Activez les mises à jour automatiques
- Sauvegardez régulièrement la base de données

```bash
# Firewall basique
sudo ufw allow 22/tcp
sudo ufw enable
```
