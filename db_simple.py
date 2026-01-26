import psycopg2
from psycopg2.extras import execute_batch
import json

# Configuration de la base de données
DB_CONFIG = {
    'host': 'localhost',
    'database': 'demarches_db',
    'user': 'postgres',
    'password': '',  # Pas de mot de passe nécessaire avec auth "trust" sur Arch
    'port': 5432
}

class DossiersManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.changements = []
    
    def connect(self):
        """Établit la connexion à la base de données"""
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        print("✅ Connexion à PostgreSQL établie")
    
    def disconnect(self):
        """Ferme la connexion"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def creer_table_temp(self):
        """Crée une table temporaire pour le nouveau scraping"""
        self.cursor.execute("""
            DROP TABLE IF EXISTS dossiers_new;
            CREATE TABLE dossiers_new (
                numero VARCHAR(50) PRIMARY KEY,
                titre TEXT,
                lien TEXT,
                categorie VARCHAR(50),
                statut VARCHAR(50),
                demandeur VARCHAR(255),
                date_creation VARCHAR(50),
                date_modification VARCHAR(50),
                page INTEGER
            );
        """)
        self.conn.commit()
        print("📋 Table temporaire créée")
    
    def inserer_nouveau_scraping(self, dossiers_list, expirants_list):
        """Insère les nouveaux dossiers scrapés dans la table temporaire (sans les expirants)"""
        # Filtrer les dossiers expirants (qui sont des doublons)
        expirants_numeros = {d['numero'] for d in expirants_list}
        
        data = [
            (d['numero'], d['titre'], d['lien'], d['categorie'], d['statut'],
             d['demandeur'], d['date_creation'], d['date_modification'], d['page'])
            for d in dossiers_list if d.get('numero') and d['categorie'] != 'expirants'
        ]
        
        execute_batch(self.cursor, """
            INSERT INTO dossiers_new 
            (numero, titre, lien, categorie, statut, demandeur, 
             date_creation, date_modification, page)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero) DO NOTHING
        """, data)
        
        self.conn.commit()
        print(f"✅ {len(data)} dossiers insérés dans la table temporaire")
        print(f"   ⏭️  {len(expirants_numeros)} dossiers expirants exclus (doublons)")
    
    def detecter_expirants(self, expirants_list):
        """Détecte les nouveaux dossiers ajoutés à la catégorie expirants"""
        nouveaux_expirants = []
        
        # Créer table temporaire pour les expirants
        self.cursor.execute("DROP TABLE IF EXISTS dossiers_expirants_new;")
        self.cursor.execute("""
            CREATE TABLE dossiers_expirants_new (
                numero VARCHAR(50) PRIMARY KEY
            );
        """)
        
        # Insérer les expirants actuels
        if expirants_list:
            data = [(d['numero'],) for d in expirants_list if d.get('numero')]
            execute_batch(self.cursor, """
                INSERT INTO dossiers_expirants_new (numero)
                VALUES (%s)
                ON CONFLICT (numero) DO NOTHING
            """, data)
        
        # Détecter les nouveaux expirants
        self.cursor.execute("""
            SELECT n.numero
            FROM dossiers_expirants_new n
            LEFT JOIN dossiers_expirants o ON n.numero = o.numero
            WHERE o.numero IS NULL
        """)
        nouveaux = self.cursor.fetchall()
        
        for (numero,) in nouveaux:
            nouveaux_expirants.append(numero)
            # Enregistrer dans les changements
            self.cursor.execute("""
                INSERT INTO changements 
                (numero, type_changement, ancien_statut, nouveau_statut, 
                 ancienne_categorie, nouvelle_categorie)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (numero, 'expirant_ajout', None, None, None, 'expirants'))
        
        # Remplacer la table expirants
        self.cursor.execute("DROP TABLE IF EXISTS dossiers_expirants;")
        self.cursor.execute("ALTER TABLE dossiers_expirants_new RENAME TO dossiers_expirants;")
        
        self.conn.commit()
        
        if nouveaux_expirants:
            print(f"\n⏰ {len(nouveaux_expirants)} nouveaux dossiers expirants détectés")
        
        return nouveaux_expirants
    
    def detecter_changements(self):
        """Compare les deux tables et détecte les changements"""
        self.changements = []
        
        # 1. Nouveaux dossiers (dans new mais pas dans old)
        self.cursor.execute("""
            SELECT n.numero, n.categorie, n.statut
            FROM dossiers_new n
            LEFT JOIN dossiers o ON n.numero = o.numero
            WHERE o.numero IS NULL
        """)
        nouveaux = self.cursor.fetchall()
        
        for numero, categorie, statut in nouveaux:
            self.changements.append({
                'numero': numero,
                'type': 'nouveau',
                'nouveau_statut': statut,
                'nouvelle_categorie': categorie
            })
        
        # 2. Dossiers modifiés (changement de statut ou catégorie)
        self.cursor.execute("""
            SELECT n.numero, o.statut, n.statut, o.categorie, n.categorie
            FROM dossiers_new n
            JOIN dossiers o ON n.numero = o.numero
            WHERE n.statut != o.statut OR n.categorie != o.categorie
        """)
        modifies = self.cursor.fetchall()
        
        for numero, ancien_statut, nouveau_statut, ancienne_cat, nouvelle_cat in modifies:
            self.changements.append({
                'numero': numero,
                'type': 'modifie',
                'ancien_statut': ancien_statut,
                'nouveau_statut': nouveau_statut,
                'ancienne_categorie': ancienne_cat,
                'nouvelle_categorie': nouvelle_cat
            })
        
        # 3. Dossiers supprimés (dans old mais pas dans new)
        self.cursor.execute("""
            SELECT o.numero, o.categorie, o.statut
            FROM dossiers o
            LEFT JOIN dossiers_new n ON o.numero = n.numero
            WHERE n.numero IS NULL
        """)
        supprimes = self.cursor.fetchall()
        
        for numero, categorie, statut in supprimes:
            self.changements.append({
                'numero': numero,
                'type': 'supprime',
                'ancien_statut': statut,
                'ancienne_categorie': categorie
            })
        
        print(f"\n🔍 Changements détectés:")
        print(f"   ✨ Nouveaux: {len(nouveaux)}")
        print(f"   🔄 Modifiés: {len(modifies)}")
        print(f"   🗑️  Supprimés: {len(supprimes)}")
        
        return self.changements
    
    def enregistrer_changements(self):
        """Enregistre les changements dans la table changements"""
        if not self.changements:
            return
        
        for c in self.changements:
            self.cursor.execute("""
                INSERT INTO changements 
                (numero, type_changement, ancien_statut, nouveau_statut, 
                 ancienne_categorie, nouvelle_categorie)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                c['numero'],
                c['type'],
                c.get('ancien_statut'),
                c.get('nouveau_statut'),
                c.get('ancienne_categorie'),
                c.get('nouvelle_categorie')
            ))
        
        self.conn.commit()
        print(f"💾 {len(self.changements)} changements enregistrés")
    
    def remplacer_table(self):
        """Remplace la table principale par la nouvelle"""
        self.cursor.execute("""
            DROP TABLE IF EXISTS dossiers;
            ALTER TABLE dossiers_new RENAME TO dossiers;
        """)
        self.conn.commit()
        print("🔄 Table principale remplacée")
    
    def afficher_changements(self, limit=20):
        """Affiche les changements détectés"""
        if not self.changements:
            print("\n✅ Aucun changement détecté")
            return
        
        print(f"\n{'='*60}")
        print(f"📋 Détails des changements (max {limit}):")
        print(f"{'='*60}\n")
        
        for i, c in enumerate(self.changements[:limit]):
            print(f"Dossier {c['numero']}:")
            
            if c['type'] == 'nouveau':
                print(f"  ✨ NOUVEAU")
                print(f"     Catégorie: {c['nouvelle_categorie']}")
                print(f"     Statut: {c['nouveau_statut']}")
            
            elif c['type'] == 'modifie':
                print(f"  🔄 MODIFIÉ")
                if c['ancienne_categorie'] != c['nouvelle_categorie']:
                    print(f"     Catégorie: {c['ancienne_categorie']} → {c['nouvelle_categorie']}")
                if c['ancien_statut'] != c['nouveau_statut']:
                    print(f"     Statut: {c['ancien_statut']} → {c['nouveau_statut']}")
            
            elif c['type'] == 'supprime':
                print(f"  🗑️  SUPPRIMÉ")
                print(f"     Catégorie: {c['ancienne_categorie']}")
                print(f"     Statut: {c['ancien_statut']}")
            
            print()
    
    def sauvegarder_changements_json(self, filename='changements.json'):
        """Sauvegarde les changements dans un fichier JSON"""
        if self.changements:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.changements, f, ensure_ascii=False, indent=2)
            print(f"💾 Changements sauvegardés dans {filename}")
    
    def process_scraping(self, dossiers_list, expirants_list):
        """
        Processus complet: 
        1. Créer table temp
        2. Insérer nouveau scraping (sans expirants)
        3. Détecter changements normaux
        4. Détecter nouveaux expirants
        5. Enregistrer changements
        6. Remplacer table
        """
        print("\n" + "="*60)
        print("🔄 Traitement du scraping")
        print("="*60 + "\n")
        
        # Étape 1: Table temporaire
        self.creer_table_temp()
        
        # Étape 2: Insertion (sans expirants)
        self.inserer_nouveau_scraping(dossiers_list, expirants_list)
        
        # Étape 3: Détection changements normaux
        changements = self.detecter_changements()
        
        # Étape 4: Détection nouveaux expirants
        nouveaux_expirants = self.detecter_expirants(expirants_list)
        
        # Étape 5: Enregistrement
        if changements:
            self.enregistrer_changements()
            self.afficher_changements()
            self.sauvegarder_changements_json()
        
        # Étape 6: Remplacement
        self.remplacer_table()
        
        return changements
