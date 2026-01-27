import asyncio
import json
import os
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from bs4 import BeautifulSoup
from db_simple import DossiersManager
from dotenv import load_dotenv

load_dotenv()

async def login_and_scrape_all():
    # Configuration du proxy résidentiel
    proxy_config = None
    proxy_server = os.getenv('PROXY_SERVER')
    proxy_username = os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('PROXY_PASSWORD')
    
    if proxy_server and proxy_username and proxy_password:
        proxy_config = f"http://{proxy_username}:{proxy_password}@{proxy_server}"
        print(f"🌐 Utilisation du proxy: {proxy_server}")
    
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        proxy_config=proxy_config
    )
    
    all_dossiers = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # ÉTAPE 1 : Connexion
        print(" Connexion en cours...")
        
        login_config = CrawlerRunConfig(
            js_code=[
                # Masquer les traces d'automatisation
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR', 'fr', 'en-US', 'en']});
                """,
                "await new Promise(r => setTimeout(r, 500));",
                """
                document.querySelector('#user_email').value = 'administration.etrangers@mhk-avocats.com';
                document.querySelector('#user_password').value = 'MHKavocats-christiani2025@';
                """,
                "await new Promise(r => setTimeout(r, 500));",
                "document.querySelector('input[type=\"submit\"][value=\"Se connecter\"]').click();",
                "await new Promise(r => setTimeout(r, 5000));"  # Attendre la redirection
            ],
            delay_before_return_html=2.0,
            page_timeout=30000,  # 30 secondes max
            session_id="demarches_session"  # Maintenir la session
        )
        
        result = await crawler.arun(
            url="https://demarche.numerique.gouv.fr/users/sign_in",
            config=login_config
        )
        
        if not result.success:
            print(" Échec de la connexion")
            return
        
        print("✅ Connexion effectuée!\n")
        
        # ÉTAPE 2 : Définir tous les statuts à scraper
        statuts_config = [
            {'nom': 'en-cours', 'statut': 'en-cours'},
            {'nom': 'traités', 'statut': 'traites'},
            {'nom': 'dossiers invités', 'statut': 'dossiers-invites'},
            {'nom': 'expirants', 'statut': 'dossiers-expirant'},  # Scraper mais ne pas inclure dans la table principale
            {'nom': 'corbeille', 'statut': 'dossiers-supprimes'}
        ]
        
        async def get_max_pages(crawler, statut, session_id):
            """Détecte automatiquement le nombre de pages pour un statut donné"""
            url = f"https://demarche.numerique.gouv.fr/dossiers?page=1&statut={statut}"
            
            try:
                config = CrawlerRunConfig(
                    delay_before_return_html=2.0,
                    page_timeout=30000,
                    session_id=session_id
                )
                
                result = await crawler.arun(url=url, config=config)
                
                if not result.success:
                    print(f"⚠️  Impossible de détecter le nombre de pages pour {statut}, utilisation de 1 par défaut")
                    return 1
                
                soup = BeautifulSoup(result.html, 'html.parser')
            except Exception as e:
                print(f"❌ Erreur lors de la détection des pages pour {statut}: {e}")
                return 1
            
            # Chercher le lien "Dernier" qui contient le numéro de la dernière page
            last_link = soup.find('a', class_='fr-pagination__link--last')
            
            if last_link and last_link.get('href'):
                # Extraire le numéro de page de l'URL
                match = re.search(r'page=(\d+)', last_link['href'])
                if match:
                    max_pages = int(match.group(1))
                    return max_pages
            
            # Si pas de lien "Dernier", chercher tous les liens de pagination
            pagination_links = soup.find_all('a', class_='fr-pagination__link')
            page_numbers = []
            
            for link in pagination_links:
                if link.get('href'):
                    match = re.search(r'page=(\d+)', link['href'])
                    if match:
                        page_numbers.append(int(match.group(1)))
            
            if page_numbers:
                return max(page_numbers)
            
            # Par défaut, retourner 1
            return 1
        
        # ÉTAPE 2.5 : Détecter automatiquement le nombre de pages pour chaque statut
        print("🔍 Détection automatique du nombre de pages...\n")
        
        for statut_info in statuts_config:
            max_pages = await get_max_pages(crawler, statut_info['statut'], "demarches_session")
            statut_info['pages'] = max_pages
            print(f"   📊 {statut_info['nom']}: {max_pages} pages")
        
        print()
        
        page_config = CrawlerRunConfig(
            delay_before_return_html=2.0,
            page_timeout=30000,
            session_id="demarches_session"
        )
        
        # Boucle sur chaque statut
        for statut_info in statuts_config:
            statut_nom = statut_info['nom']
            statut_param = statut_info['statut']
            nb_pages = statut_info['pages']
            
            print(f"\n{'='*60}")
            print(f" Scraping des dossiers '{statut_nom}' ({nb_pages} pages)")
            print(f"{'='*60}\n")
            
            for page_num in range(1, nb_pages + 1):
                url = f"https://demarche.numerique.gouv.fr/dossiers?page={page_num}&statut={statut_param}"
                
                print(f" [{statut_nom}] Page {page_num}/{nb_pages}... ", end='', flush=True)
                
                result = await crawler.arun(url=url, config=page_config)
                
                if not result.success:
                    print(f" Échec")
                    continue
                
                # Parser avec BeautifulSoup
                soup = BeautifulSoup(result.html, 'html.parser')
                dossiers = soup.find_all('div', class_='card')
                
                # Debug: vérifier si on est toujours connecté
                if len(dossiers) == 0:
                    # Vérifier si on est redirigé vers la page de login
                    login_form = soup.find('form', action='/users/sign_in')
                    if login_form:
                        print(f"❌ Session perdue - redirection vers login")
                    else:
                        # Sauvegarder le HTML pour debug
                        with open(f'debug_page_{statut_param}_{page_num}.html', 'w', encoding='utf-8') as f:
                            f.write(result.html[:5000])  # Premiers 5000 caractères
                        print(f"⚠️  0 dossiers (HTML sauvegardé pour debug)")
                else:
                    print(f"✅ {len(dossiers)} dossiers")
                
                for dossier in dossiers:
                    try:
                        # ID
                        dossier_id = dossier.get('id', '').replace('dossier_', '')
                        
                        # Titre et lien
                        titre_elem = dossier.find('h3', class_='card-title')
                        titre_link = titre_elem.find('a') if titre_elem else None
                        titre = titre_link.text.strip() if titre_link else ""
                        lien = f"https://demarche.numerique.gouv.fr{titre_link['href']}" if titre_link and titre_link.get('href') else ""
                        
                        # Statut
                        badge = dossier.find('span', class_='fr-badge')
                        statut = badge.text.strip() if badge else ""
                        
                        # Demandeur
                        identite_elem = dossier.find('p', class_='fr-icon-user-line')
                        if identite_elem:
                            demandeur = identite_elem.get_text(strip=True).replace('Identité du demandeur', '').strip()
                        else:
                            demandeur = ""
                        
                        # Dates
                        date_elem = dossier.find('p', class_='fr-icon-edit-box-line')
                        date_creation = ""
                        date_modification = ""
                        
                        if date_elem:
                            dates_text = date_elem.get_text()
                            if "Créé le" in dates_text:
                                date_creation = dates_text.split("Créé le")[1].split("modifié")[0].strip()
                            if "modifié le" in dates_text:
                                date_modification = dates_text.split("modifié le")[1].strip()
                        
                        # Ajouter le dossier avec la catégorie
                        all_dossiers.append({
                            'numero': dossier_id,
                            'titre': titre,
                            'lien': lien,
                            'categorie': statut_nom,  # Ajout de la catégorie
                            'statut': statut,
                            'demandeur': demandeur,
                            'date_creation': date_creation,
                            'date_modification': date_modification,
                            'page': page_num
                        })
                        
                    except Exception as e:
                        print(f"\n   ⚠️ Erreur: {e}")
                
                # Petit délai entre les pages
                await asyncio.sleep(0.5)
        
        # ÉTAPE 3 : Sauvegarder
        print(f"\n Sauvegarde de {len(all_dossiers)} dossiers...")
        
        # JSON
        with open('dossiers_complets.json', 'w', encoding='utf-8') as f:
            json.dump(all_dossiers, f, ensure_ascii=False, indent=2)
        
        # CSV
        import csv
        with open('dossiers_complets.csv', 'w', encoding='utf-8', newline='') as f:
            if all_dossiers:
                writer = csv.DictWriter(f, fieldnames=all_dossiers[0].keys())
                writer.writeheader()
                writer.writerows(all_dossiers)
        
        print(f"\n TERMINÉ!")
        print(f"   {len(all_dossiers)} dossiers extraits")
        print(f"   dossiers_complets.json")
        print(f"   dossiers_complets.csv")
        
        # ÉTAPE 4 : Comparer avec PostgreSQL et détecter les changements
        try:
            db = DossiersManager()
            db.connect()
            
            # Séparer les dossiers expirants des autres
            expirants = [d for d in all_dossiers if d['categorie'] == 'expirants']
            autres_dossiers = [d for d in all_dossiers if d['categorie'] != 'expirants']
            
            print(f"\n📊 Répartition:")
            print(f"   Dossiers normaux: {len(autres_dossiers)}")
            print(f"   Dossiers expirants (tracking séparé): {len(expirants)}")
            
            # Processus complet: créer table temp, comparer, remplacer
            changements = db.process_scraping(autres_dossiers, expirants)
            
            db.disconnect()
            
            # ÉTAPE 5 : Si des changements détectés, télécharger les PDFs et envoyer au webhook
            if changements:
                print(f"\n✨ {len(changements)} changements détectés")
                print(f"📥 Lancement du téléchargement des PDFs et envoi au webhook...\n")
                
                # Importer et exécuter le téléchargement
                from download_pdfs import download_changed_dossiers
                await download_changed_dossiers()
            
        except Exception as e:
            print(f"\n ⚠️  Erreur PostgreSQL: {e}")
            print("   Les données sont sauvegardées dans les fichiers JSON/CSV")
        
        # Stats
        statuts = {}
        for d in all_dossiers:
            statuts[d['statut']] = statuts.get(d['statut'], 0) + 1
        
        print(f"\n Répartition par statut:")
        for statut, count in statuts.items():
            print(f"   - {statut}: {count}")
        
        return all_dossiers

if __name__ == "__main__":
    # Exécuter seulement si appelé directement
    dossiers = asyncio.run(login_and_scrape_all())