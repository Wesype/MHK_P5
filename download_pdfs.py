import asyncio
import os
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from bs4 import BeautifulSoup
import json
from send_webhook import send_to_webhook

async def download_dossier_pdfs(numero_dossier, session_id="demarches_session"):
    """
    Télécharge tous les PDFs d'un dossier spécifique
    
    Args:
        numero_dossier: Le numéro du dossier (ex: "28754159")
        session_id: ID de session pour réutiliser la connexion
    
    Returns:
        Liste des fichiers téléchargés
    """
    # Configuration du dossier de téléchargement
    download_path = os.path.join(os.getcwd(), "downloads", numero_dossier)
    os.makedirs(download_path, exist_ok=True)
    
    # Configuration du navigateur avec téléchargements activés
    browser_config = BrowserConfig(
        headless=True,
        accept_downloads=True,
        downloads_path=download_path,
        verbose=False
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # ÉTAPE 1 : Connexion au site
        print(f"🔐 Connexion au site...")
        
        login_config = CrawlerRunConfig(
            js_code=[
                """
                document.querySelector('#user_email').value = 'administration.etrangers@mhk-avocats.com';
                document.querySelector('#user_password').value = 'MHKavocats-christiani2025@';
                """,
                "await new Promise(r => setTimeout(r, 500));",
                "document.querySelector('input[type=\"submit\"][value=\"Se connecter\"]').click();",
                "await new Promise(r => setTimeout(r, 5000));"  # Attendre la redirection
            ],
            delay_before_return_html=2.0,
            page_timeout=30000,
            session_id=session_id
        )
        
        result = await crawler.arun(
            url="https://demarche.numerique.gouv.fr/users/sign_in",
            config=login_config
        )
        
        if not result.success:
            print(f"❌ Échec de la connexion")
            return []
        
        print(f"✅ Connecté")
        
        # ÉTAPE 2 : Accéder au dossier
        url = f"https://demarche.numerique.gouv.fr/dossiers/{numero_dossier}/demande"
        
        print(f"📄 Accès au dossier {numero_dossier}...")
        
        # Configuration pour charger la page et détecter les PDFs
        page_config = CrawlerRunConfig(
            delay_before_return_html=2.0,
            page_timeout=30000,
            session_id=session_id
        )
        
        # Charger la page
        result = await crawler.arun(url=url, config=page_config)
        
        if not result.success:
            print(f"❌ Échec du chargement de la page")
            return []
        
        # Parser le HTML pour trouver tous les liens de téléchargement PDF
        soup = BeautifulSoup(result.html, 'html.parser')
        pdf_links = soup.find_all('a', class_='fr-download__link')
        
        if not pdf_links:
            print(f"⚠️  Aucun PDF trouvé pour le dossier {numero_dossier}")
            return []
        
        print(f"📎 {len(pdf_links)} PDF(s) détecté(s)")
        
        # Construire le code JavaScript pour télécharger tous les PDFs (sans doublons)
        js_code = """
        const downloadLinks = Array.from(document.querySelectorAll('a.fr-download__link'));
        const uniqueLinks = [...new Set(downloadLinks.map(l => l.href))];
        console.log(`Found ${uniqueLinks.length} unique download links`);
        
        for (let i = 0; i < uniqueLinks.length; i++) {
            const href = uniqueLinks[i];
            const link = downloadLinks.find(l => l.href === href);
            console.log(`Clicking link ${i + 1}: ${href}`);
            link.click();
            
            // Délai entre chaque téléchargement
            if (i < uniqueLinks.length - 1) {
                await new Promise(r => setTimeout(r, 2000));
            }
        }
        """
        
        # Configuration pour déclencher les téléchargements
        download_config = CrawlerRunConfig(
            js_code=js_code,
            delay_before_return_html=5.0 + (len(pdf_links) * 2),  # Attendre suffisamment pour tous les téléchargements
            page_timeout=60000,
            session_id=session_id
        )
        
        print(f"⬇️  Téléchargement en cours...")
        
        # Déclencher les téléchargements
        result = await crawler.arun(url=url, config=download_config)
        
        # Récupérer les fichiers téléchargés et dédupliquer
        if result.downloaded_files:
            # Dédupliquer par nom de fichier (garder le premier)
            unique_files = []
            seen_names = set()
            
            for file_path in result.downloaded_files:
                file_name = os.path.basename(file_path)
                if file_name not in seen_names:
                    seen_names.add(file_name)
                    unique_files.append(file_path)
            
            print(f"\n✅ {len(unique_files)} fichier(s) téléchargé(s):")
            for file_path in unique_files:
                file_size = os.path.getsize(file_path)
                file_name = os.path.basename(file_path)
                print(f"   📄 {file_name} ({file_size:,} octets)")
            
            # Envoyer au webhook
            print(f"\n📤 Envoi au webhook...")
            dossier_info = {
                'numero': numero_dossier,
                'type_changement': 'test',
                'nb_fichiers': len(unique_files)
            }
            response = send_to_webhook(dossier_info, unique_files)
            
            if response and response.status_code == 200:
                print(f"✅ Envoyé avec succès au webhook")
                
                # Supprimer les fichiers après envoi réussi
                print(f"🗑️  Suppression des fichiers...")
                import shutil
                try:
                    shutil.rmtree(download_path)
                    print(f"✅ Dossier {numero_dossier} supprimé")
                except Exception as e:
                    print(f"⚠️  Erreur lors de la suppression: {e}")
            else:
                status = response.status_code if response else "Aucune réponse"
                print(f"⚠️  Erreur webhook: {status}")
                print(f"📁 Fichiers conservés dans: {download_path}")
            
            return unique_files
        else:
            print(f"⚠️  Aucun fichier téléchargé")
            return []

async def download_multiple_dossiers(numeros_dossiers):
    """
    Télécharge les PDFs de plusieurs dossiers
    
    Args:
        numeros_dossiers: Liste des numéros de dossiers
    
    Returns:
        Dictionnaire {numero_dossier: [fichiers_téléchargés]}
    """
    results = {}
    
    for numero in numeros_dossiers:
        print(f"\n{'='*60}")
        print(f"Dossier {numero}")
        print(f"{'='*60}")
        
        try:
            files = await download_dossier_pdfs(numero)
            results[numero] = files
            
            # Petit délai entre chaque dossier
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Erreur pour le dossier {numero}: {e}")
            results[numero] = []
    
    return results

async def download_changed_dossiers(changements_file='changements.json'):
    """
    Télécharge les PDFs de tous les dossiers qui ont changé
    
    Args:
        changements_file: Fichier JSON contenant les changements détectés
    """
    if not os.path.exists(changements_file):
        print(f"❌ Fichier {changements_file} introuvable")
        return
    
    with open(changements_file, 'r', encoding='utf-8') as f:
        changements = json.load(f)
    
    if not changements:
        print("✅ Aucun changement détecté")
        return
    
    # Extraire les numéros de dossiers uniques
    numeros = list(set([c['numero'] for c in changements]))
    
    print(f"\n🔍 {len(numeros)} dossier(s) avec changements détectés")
    print(f"📥 Téléchargement des PDFs...\n")
    
    results = await download_multiple_dossiers(numeros)
    
    # Sauvegarder un rapport
    rapport = {
        'total_dossiers': len(numeros),
        'dossiers_traites': len(results),
        'details': {
            numero: {
                'nb_fichiers': len(files),
                'fichiers': [os.path.basename(f) for f in files]
            }
            for numero, files in results.items()
        }
    }
    
    with open('rapport_telechargements.json', 'w', encoding='utf-8') as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"📊 Résumé")
    print(f"{'='*60}")
    print(f"   Dossiers traités: {len(results)}")
    print(f"   Total fichiers: {sum(len(files) for files in results.values())}")
    print(f"   Rapport: rapport_telechargements.json")
    
    # Sauvegarder les PDFs dans PostgreSQL et envoyer au webhook
    print(f"\n{'='*60}")
    print(f"💾 Sauvegarde PDFs dans PostgreSQL et envoi webhook")
    print(f"{'='*60}\n")
    
    from send_webhook import send_to_webhook
    from db_postgres import save_pdf_to_db, get_pdf_url
    import shutil
    
    success_count = 0
    error_count = 0
    
    for changement in changements:
        numero = changement['numero']
        pdf_files = results.get(numero, [])
        
        # Sauvegarder les PDFs dans PostgreSQL et récupérer les URLs
        pdf_urls = []
        for pdf_path in pdf_files:
            pdf_id = save_pdf_to_db(numero, pdf_path)
            if pdf_id:
                url = get_pdf_url(pdf_id)
                pdf_urls.append({
                    'nom': os.path.basename(pdf_path),
                    'url': url,
                    'id': pdf_id
                })
                print(f"   💾 {os.path.basename(pdf_path)} → PostgreSQL (ID: {pdf_id})")
        
        # Préparer les infos complètes du dossier avec URLs
        dossier_info = {
            'numero': numero,
            'type_changement': changement.get('type'),
            'ancien_statut': changement.get('ancien_statut', ''),
            'nouveau_statut': changement.get('nouveau_statut', ''),
            'ancienne_categorie': changement.get('ancienne_categorie', ''),
            'nouvelle_categorie': changement.get('nouvelle_categorie', ''),
            'nb_fichiers': len(pdf_files),
            'pdf_urls': pdf_urls  # Ajouter les URLs des PDFs
        }
        
        # Envoyer au webhook avec PDFs + infos + URLs
        response = send_to_webhook(dossier_info, pdf_files)
        
        if response and response.status_code == 200:
            success_count += 1
            
            # Supprimer les fichiers locaux après envoi réussi
            if pdf_files:
                download_path = os.path.join(os.getcwd(), "downloads", numero)
                try:
                    shutil.rmtree(download_path)
                    print(f"   🗑️  Fichiers locaux supprimés")
                except Exception as e:
                    print(f"   ⚠️  Erreur suppression: {e}")
        else:
            error_count += 1
        
        # Petit délai entre chaque envoi
        await asyncio.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"📊 Résumé webhook")
    print(f"{'='*60}")
    print(f"   ✅ Succès: {success_count}")
    print(f"   ❌ Erreurs: {error_count}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Mode: télécharger un dossier spécifique
        numero = sys.argv[1]
        asyncio.run(download_dossier_pdfs(numero))
    else:
        # Mode: télécharger tous les dossiers avec changements
        asyncio.run(download_changed_dossiers())
