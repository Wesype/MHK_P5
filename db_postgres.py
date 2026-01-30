#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from ds import login_and_scrape_all
from send_webhook import send_to_webhook

# Charger les variables d'environnement
load_dotenv()

# Configuration PostgreSQL - Railway injecte DATABASE_URL automatiquement
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Parser DATABASE_URL pour Railway (format: postgresql://user:pass@host:port/db)
    import urllib.parse as urlparse
    url = urlparse.urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host': url.hostname,
        'port': url.port,
        'database': url.path[1:],  # Enlever le /
        'user': url.username,
        'password': url.password
    }
    print(f"✅ Connexion PostgreSQL via DATABASE_URL: {url.hostname}:{url.port}/{url.path[1:]}")
else:
    # Essayer les variables PG* de Railway
    pghost = os.getenv('PGHOST')
    if pghost:
        DB_CONFIG = {
            'host': pghost,
            'port': os.getenv('PGPORT', '5432'),
            'database': os.getenv('PGDATABASE', 'railway'),
            'user': os.getenv('PGUSER', 'postgres'),
            'password': os.getenv('PGPASSWORD', '')
        }
        print(f"✅ Connexion PostgreSQL via variables PG*: {pghost}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    else:
        # Fallback pour développement local
        DB_CONFIG = {
            'host': 'localhost',
            'port': '5432',
            'database': 'demarches',
            'user': 'postgres',
            'password': 'password'
        }
        print("⚠️  Aucune variable PostgreSQL trouvée, utilisation de localhost")

def get_connection():
    """Créer une connexion à PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)

def save_pdf_to_db(numero_dossier, pdf_path):
    """
    Sauvegarder un PDF dans PostgreSQL
    
    Args:
        numero_dossier: Numéro du dossier
        pdf_path: Chemin vers le fichier PDF
    
    Returns:
        ID du PDF inséré ou None en cas d'erreur
    """
    try:
        if not os.path.exists(pdf_path):
            print(f"⚠️  Fichier introuvable: {pdf_path}")
            return None
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Lire le contenu du PDF
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        nom_fichier = os.path.basename(pdf_path)
        taille = len(pdf_content)
        
        # Insérer dans la base
        cur.execute("""
            INSERT INTO pdfs (numero_dossier, nom_fichier, contenu, taille)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (numero_dossier, nom_fichier, pdf_content, taille))
        
        pdf_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return pdf_id
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde PDF {nom_fichier}: {e}")
        return None

def get_pdf_url(pdf_id, base_url=None):
    """Générer l'URL d'accès à un PDF"""
    if base_url is None:
        base_url = os.getenv('API_BASE_URL', 'https://your-app.up.railway.app')
    return f"{base_url}/pdf/{pdf_id}"

def init_database():
    """Initialiser la base de données PostgreSQL"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Créer la table si elle n'existe pas
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dossiers (
            id SERIAL PRIMARY KEY,
            numero VARCHAR(20) UNIQUE NOT NULL,
            statut VARCHAR(50),
            categorie VARCHAR(50),
            date_depot DATE,
            date_derniere_modification DATE,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Créer un index sur le numéro de dossier
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_dossier_numero 
        ON dossiers(numero)
    ''')
    
    # Créer un trigger pour mettre à jour updated_at
    cur.execute('''
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    ''')
    
    cur.execute('''
        DROP TRIGGER IF EXISTS update_dossiers_updated_at ON dossiers;
    ''')
    
    cur.execute('''
        CREATE TRIGGER update_dossiers_updated_at 
        BEFORE UPDATE ON dossiers 
        FOR EACH ROW 
        EXECUTE FUNCTION update_updated_at_column();
    ''')
    
    # Créer la table pour les PDFs
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pdfs (
            id SERIAL PRIMARY KEY,
            numero_dossier VARCHAR(20) NOT NULL,
            nom_fichier TEXT NOT NULL,
            contenu BYTEA NOT NULL,
            taille INTEGER NOT NULL,
            date_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (numero_dossier) REFERENCES dossiers(numero) ON DELETE CASCADE
        )
    ''')
    
    # Index pour recherche rapide par dossier
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_pdfs_numero_dossier 
        ON pdfs(numero_dossier)
    ''')
    
    # Index pour recherche par date
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_pdfs_date_upload 
        ON pdfs(date_upload DESC)
    ''')
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Base de données PostgreSQL initialisée")

def save_dossiers(dossiers):
    """Sauvegarder les dossiers dans PostgreSQL avec détection des changements"""
    changements = []
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    for dossier in dossiers:
        numero = dossier.get('numero')
        
        # Vérifier si le dossier existe déjà
        cur.execute('SELECT * FROM dossiers WHERE numero = %s', (numero,))
        existing = cur.fetchone()
        
        if existing:
            # Détecter les changements
            changement = None
            if existing['statut'] != dossier.get('statut'):
                changement = {
                    'type': 'statut_change',
                    'numero': numero,
                    'ancien_statut': existing['statut'],
                    'nouveau_statut': dossier.get('statut'),
                    'ancienne_categorie': existing['categorie'],
                    'nouvelle_categorie': dossier.get('categorie')
                }
            
            # Mettre à jour le dossier
            cur.execute('''
                UPDATE dossiers 
                SET statut = %s,
                    categorie = %s,
                    date_depot = %s,
                    date_derniere_modification = %s,
                    metadata = %s
                WHERE numero = %s
            ''', (
                dossier.get('statut'),
                dossier.get('categorie'),
                dossier.get('date_depot'),
                dossier.get('date_derniere_modification'),
                json.dumps(dossier.get('metadata', {})),
                numero
            ))
            
            if changement:
                changements.append(changement)
                print(f"🔄 Dossier {numero}: {changement['ancien_statut']} → {changement['nouveau_statut']}")
        else:
            # Nouveau dossier
            cur.execute('''
                INSERT INTO dossiers (numero, statut, categorie, date_depot, 
                                     date_derniere_modification, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                numero,
                dossier.get('statut'),
                dossier.get('categorie'),
                dossier.get('date_depot'),
                dossier.get('date_derniere_modification'),
                json.dumps(dossier.get('metadata', {}))
            ))
            
            changement = {
                'type': 'nouveau',
                'numero': numero,
                'nouveau_statut': dossier.get('statut'),
                'nouvelle_categorie': dossier.get('categorie')
            }
            changements.append(changement)
            print(f"✨ Nouveau dossier: {numero}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    # Sauvegarder les changements
    if changements:
        with open('changements.json', 'w', encoding='utf-8') as f:
            json.dump(changements, f, ensure_ascii=False, indent=2)
    
    return changements

def get_all_dossiers():
    """Récupérer tous les dossiers depuis PostgreSQL"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('SELECT * FROM dossiers ORDER BY numero')
    dossiers = cur.fetchall()
    
    cur.close()
    conn.close()
    return dossiers

def get_stats():
    """Obtenir des statistiques sur les dossiers"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Total des dossiers
    cur.execute('SELECT COUNT(*) FROM dossiers')
    total = cur.fetchone()[0]
    
    # Dossiers par statut
    cur.execute('''
        SELECT statut, COUNT(*) as count 
        FROM dossiers 
        GROUP BY statut 
        ORDER BY count DESC
    ''')
    par_statut = dict(cur.fetchall())
    
    # Dossiers par catégorie
    cur.execute('''
        SELECT categorie, COUNT(*) as count 
        FROM dossiers 
        GROUP BY categorie 
        ORDER BY count DESC
    ''')
    par_categorie = dict(cur.fetchall())
    
    cur.close()
    conn.close()
    
    return {
        'total': total,
        'par_statut': par_statut,
        'par_categorie': par_categorie
    }

def export_to_csv():
    """Exporter les dossiers complets vers CSV"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT numero, statut, categorie, date_depot, date_derniere_modification
        FROM dossiers
        ORDER BY numero
    """)
    
    dossiers = cur.fetchall()
    cur.close()
    conn.close()
    
    if dossiers:
        import pandas as pd
        df = pd.DataFrame(dossiers)
        df.to_csv('dossiers_complets.csv', index=False, encoding='utf-8')
        print(f"✅ {len(dossiers)} dossiers complets exportés vers dossiers_complets.csv")
    else:
        print("❌ Aucun dossier complet trouvé")

async def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🚀 Démarrage du scraping avec PostgreSQL")
    print("="*60)
    
    # Initialiser la base de données
    init_database()
    
    # Scraper les données (fonction async)
    print("\n📊 Scraping en cours...")
    dossiers = await login_and_scrape_all()
    
    if dossiers:
        print(f"\n✅ {len(dossiers)} dossiers récupérés")
        
        # Sauvegarder dans PostgreSQL
        changements = save_dossiers(dossiers)
        
        # Afficher les stats
        stats = get_stats()
        print("\n" + "="*60)
        print("📈 Statistiques")
        print("="*60)
        print(f"Total des dossiers: {stats['total']}")
        print(f"\nPar statut:")
        for statut, count in stats['par_statut'].items():
            print(f"  - {statut}: {count}")
        print(f"\nPar catégorie:")
        for categorie, count in stats['par_categorie'].items():
            print(f"  - {categorie}: {count}")
        
        # Exporter les dossiers complets
        print("\n" + "="*60)
        export_to_csv()
        
        # Télécharger PDFs et envoyer au webhook si des changements
        if changements:
            print("\n" + "="*60)
            print(f"🔔 {len(changements)} changement(s) détecté(s)")
            print("="*60)
            
            # Télécharger les PDFs et envoyer au webhook (tout en un)
            print("\n📥 Téléchargement des PDFs et envoi au webhook...")
            from download_pdfs import download_changed_dossiers
            await download_changed_dossiers(changements_list=changements)
    else:
        print("❌ Aucun dossier trouvé")

if __name__ == "__main__":
    asyncio.run(main())
