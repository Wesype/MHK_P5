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
    # Connexion directe sans proxy
    print(f"🌐 Connexion directe (sans proxy)")
    
    # Mode headless activé (plus léger et rapide)
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox"
        ]
    )
    
    all_dossiers = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # ÉTAPE 1 : Connexion
        print(" Connexion en cours...")
        
        login_config = CrawlerRunConfig(
            js_code=[
                # Masquer les traces d'automatisation (renforcé pour headless)
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR', 'fr', 'en-US', 'en']});
                Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 1});
                Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});
                delete navigator.__proto__.webdriver;
                """,
                "await new Promise(r => setTimeout(r, 300));",
                """
                document.querySelector('#user_email').value = 'administration.etrangers@mhk-avocats.com';
                document.querySelector('#user_password').value = 'MHKavocats-christiani2025@';
                """,
                "await new Promise(r => setTimeout(r, 300));",
                "document.querySelector('input[type=\"submit\"][value=\"Se connecter\"]').click();",
                "await new Promise(r => setTimeout(r, 4000));"  # Attendre la redirection
            ],
            delay_before_return_html=1.5,  # Réduit à 1.5s
            page_timeout=30000,  # 30 secondes
            session_id="demarches_session"  # Maintenir la session
        )
        
        result = await crawler.arun(
            url="https://demarche.numerique.gouv.fr/users/sign_in",
            config=login_config
        )
        
        if not result.success:
            print(" Échec de la connexion")
            return
        
        # Vérifier qu'on est bien connecté
        print(f"✅ Connexion effectuée!")
        print(f"🔍 Vérification de la session...")
        
        # Vérifier qu'on n'est pas sur la page de login
        if "Sign in" in result.html and "/users/sign_in" in result.html:
            print("❌ ERREUR: Toujours sur la page de login!")
            print("Le site a rejeté la connexion (détection d'automatisation)")
            return
        
        # Attendre un peu pour stabiliser la session
        await asyncio.sleep(1.5)
        
        # Test de la session : essayer d'accéder à une page protégée
        test_config = CrawlerRunConfig(
            delay_before_return_html=1.0,
            page_timeout=20000,
            session_id="demarches_session"
        )
        test_result = await crawler.arun(
            url="https://demarche.numerique.gouv.fr/dossiers?statut=en-cours",
            config=test_config
        )
        
        if "Sign in" in test_result.html:
            print("❌ ERREUR: Session non maintenue - redirection vers login")
            print("Le site détecte l'automatisation et invalide la session")
            return
        
        print("✅ Session valide et maintenue\n")
        
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
                    delay_before_return_html=2.0,  # Réduit à 2s
                    page_timeout=20000,
                    session_id=session_id,
                    js_code=[
                        # Attendre que la pagination soit chargée
                        "await new Promise(r => setTimeout(r, 1000));",
                    ]
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
            
            # Debug: afficher et sauvegarder le HTML si aucune pagination trouvée
            print(f"⚠️  Aucune pagination trouvée pour {statut}")
            print(f"📄 HTML retourné (premiers 2000 caractères):")
            print("="*80)
            print(result.html[:2000])
            print("="*80)
            
            # Sauvegarder aussi dans un fichier
            debug_file = f'debug_pagination_{statut}.html'
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(result.html)
            print(f"💾 HTML complet sauvegardé dans: {debug_file}")
            
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
            delay_before_return_html=1.0,  # Réduit à 1s pour scraping plus rapide
            page_timeout=20000,
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
        
        print(f"\n✅ Scraping terminé!")
        print(f"   {len(all_dossiers)} dossiers extraits")
        
        return all_dossiers

if __name__ == "__main__":
    # Exécuter seulement si appelé directement
    dossiers = asyncio.run(login_and_scrape_all())