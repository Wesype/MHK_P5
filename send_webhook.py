import requests
import json
import os
from pathlib import Path

WEBHOOK_URL = "https://n8n.wesype.com/webhook-test/ce676bb0-4b87-4ce9-b93f-7fc97f589c07"

def send_to_webhook(dossier_info, pdf_files):
    """
    Envoie les informations d'un dossier et ses PDFs au webhook
    
    Args:
        dossier_info: Dict avec les infos du dossier (numero, type_changement, etc.)
        pdf_files: Liste des chemins vers les fichiers PDF
    
    Returns:
        Response object ou None en cas d'erreur
    """
    try:
        # Préparer les fichiers PDF pour l'upload
        files = []
        for pdf_path in pdf_files:
            if os.path.exists(pdf_path):
                file_name = os.path.basename(pdf_path)
                files.append(('files', (file_name, open(pdf_path, 'rb'), 'application/pdf')))
        
        # Préparer les données comme des champs de formulaire
        data = {
            'numero': dossier_info.get('numero'),
            'type_changement': dossier_info.get('type_changement'),
            'ancien_statut': dossier_info.get('ancien_statut', ''),
            'nouveau_statut': dossier_info.get('nouveau_statut', ''),
            'ancienne_categorie': dossier_info.get('ancienne_categorie', ''),
            'nouvelle_categorie': dossier_info.get('nouvelle_categorie', ''),
            'nb_fichiers': dossier_info.get('nb_fichiers', len(files))
        }
        
        # Ajouter test_mode si présent
        if dossier_info.get('test_mode'):
            data['test_mode'] = 'true'
        
        print(f"📤 Envoi au webhook pour le dossier {dossier_info.get('numero')}...")
        print(f"   📄 {len(files)} fichier(s) PDF")
        print(f"   📋 Type: {dossier_info.get('type_changement')}")
        
        # Envoyer la requête avec data et files séparés
        response = requests.post(WEBHOOK_URL, data=data, files=files, timeout=30)
        
        # Fermer les fichiers
        for _, file_tuple in files:
            file_tuple[1].close()
        
        if response.status_code == 200:
            print(f"✅ Envoyé avec succès (status: {response.status_code})")
            return response
        else:
            print(f"⚠️  Réponse webhook: {response.status_code}")
            print(f"   {response.text[:200]}")
            return response
            
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi au webhook: {e}")
        return None

def send_changements_to_webhook(changements_file='changements.json', downloads_dir='downloads'):
    """
    Envoie tous les changements détectés au webhook avec leurs PDFs
    
    Args:
        changements_file: Fichier JSON contenant les changements
        downloads_dir: Dossier contenant les PDFs téléchargés
    """
    if not os.path.exists(changements_file):
        print(f"❌ Fichier {changements_file} introuvable")
        return
    
    with open(changements_file, 'r', encoding='utf-8') as f:
        changements = json.load(f)
    
    if not changements:
        print("✅ Aucun changement à envoyer")
        return
    
    print(f"\n{'='*60}")
    print(f"📤 Envoi de {len(changements)} changement(s) au webhook")
    print(f"{'='*60}\n")
    
    success_count = 0
    error_count = 0
    
    for changement in changements:
        numero = changement.get('numero')
        
        # Chercher les PDFs du dossier
        dossier_path = os.path.join(downloads_dir, numero)
        pdf_files = []
        
        if os.path.exists(dossier_path):
            pdf_files = [
                os.path.join(dossier_path, f) 
                for f in os.listdir(dossier_path) 
                if f.endswith('.pdf')
            ]
        
        # Préparer les infos du dossier
        dossier_info = {
            'numero': numero,
            'type_changement': changement.get('type'),
            'ancien_statut': changement.get('ancien_statut'),
            'nouveau_statut': changement.get('nouveau_statut'),
            'ancienne_categorie': changement.get('ancienne_categorie'),
            'nouvelle_categorie': changement.get('nouvelle_categorie'),
            'nb_fichiers': len(pdf_files)
        }
        
        # Envoyer au webhook
        response = send_to_webhook(dossier_info, pdf_files)
        
        if response and response.status_code == 200:
            success_count += 1
        else:
            error_count += 1
        
        print()
    
    print(f"{'='*60}")
    print(f"📊 Résumé de l'envoi")
    print(f"{'='*60}")
    print(f"   ✅ Succès: {success_count}")
    print(f"   ❌ Erreurs: {error_count}")

def send_test_webhook(numero_dossier='21978078', downloads_dir='downloads'):
    """
    Envoie un test au webhook avec un dossier spécifique
    
    Args:
        numero_dossier: Numéro du dossier à envoyer
        downloads_dir: Dossier contenant les PDFs
    """
    print(f"\n{'='*60}")
    print(f"🧪 Mode TEST - Envoi du dossier {numero_dossier}")
    print(f"{'='*60}\n")
    
    # Chercher les PDFs du dossier
    dossier_path = os.path.join(downloads_dir, numero_dossier)
    pdf_files = []
    
    if os.path.exists(dossier_path):
        pdf_files = [
            os.path.join(dossier_path, f) 
            for f in os.listdir(dossier_path) 
            if f.endswith('.pdf')
        ]
    else:
        print(f"⚠️  Dossier {dossier_path} introuvable")
        print(f"💡 Téléchargez d'abord les PDFs avec: python download_pdfs.py {numero_dossier}")
        return
    
    if not pdf_files:
        print(f"⚠️  Aucun PDF trouvé dans {dossier_path}")
        return
    
    # Créer des infos de test
    dossier_info = {
        'numero': numero_dossier,
        'type_changement': 'test',
        'ancien_statut': 'en construction',
        'nouveau_statut': 'en instruction',
        'ancienne_categorie': 'en-cours',
        'nouvelle_categorie': 'en-cours',
        'nb_fichiers': len(pdf_files),
        'test_mode': True
    }
    
    # Envoyer au webhook
    response = send_to_webhook(dossier_info, pdf_files)
    
    if response and response.status_code == 200:
        print(f"\n✅ Test réussi !")
        print(f"📋 Réponse du webhook:")
        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print(response.text[:500])
    else:
        print(f"\n❌ Test échoué")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            # Mode test avec un dossier spécifique
            numero = sys.argv[2] if len(sys.argv) > 2 else '21978078'
            send_test_webhook(numero)
        else:
            # Envoyer un dossier spécifique
            numero = sys.argv[1]
            send_test_webhook(numero)
    else:
        # Mode normal : envoyer tous les changements
        send_changements_to_webhook()
